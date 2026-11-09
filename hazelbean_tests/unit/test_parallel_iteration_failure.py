"""A failing iteration and a dying worker both stop the run, without waiting forever or losing outputs.

Every call is bounded by a thread join, so a regression to waiting forever fails the test rather than
hanging the suite. A thread is used rather than SIGALRM so the tests also run on Windows.
"""
import os
import re
import threading
import time
from pathlib import Path

import pytest

from hazelbean.project_flow import ParallelIterationFailure, run_parallel_iterations

TIME_LIMIT_SECONDS = 90


class FakeProject:
    """Stands in for the project copy an iteration is handed; only cur_dir is read."""

    def __init__(self, cur_dir):
        self.cur_dir = str(cur_dir)


def run_within_time_limit(*arguments):
    """run_parallel_iterations(*arguments), failing the test if it has not returned within the limit."""
    outcome = {}

    def target():
        try:
            outcome['value'] = run_parallel_iterations(*arguments)
        except BaseException as error:  # re-raised in the test thread below
            outcome['error'] = error

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(TIME_LIMIT_SECONDS)
    if thread.is_alive():
        pytest.fail('run_parallel_iterations did not return within %ds' % TIME_LIMIT_SECONDS)
    if 'error' in outcome:
        raise outcome['error']
    return outcome['value']


def write_output_then_raise(project, task, counter):
    """Write this iteration's output, then fail if this is the designated bad iteration."""
    Path(project.cur_dir).mkdir(parents=True, exist_ok=True)
    (Path(project.cur_dir) / 'output.txt').write_text('iteration %s' % counter)
    if task == counter:
        (Path(project.cur_dir) / 'failure.json').write_text('{"status": "failed"}')
        raise ValueError('missing coefficients for this tile')
    return counter


def write_output_then_die(project, task, counter):
    """Write this iteration's output, then leave abruptly, as an OOM-killed worker does."""
    Path(project.cur_dir).mkdir(parents=True, exist_ok=True)
    (Path(project.cur_dir) / 'output.txt').write_text('iteration %s' % counter)
    if task == counter:
        os._exit(137)
    time.sleep(0.05)
    return counter


def write_output_slowly_then_raise(project, task, counter):
    """Good iterations take long enough that work is still queued when the bad one fails.

    With every iteration trivial, all of them finish before the failure is noticed and nothing is
    dropped -- a truthful count, but one that cannot show that a fail-fast stop REPORTS what it
    dropped. Real tiles take seconds each, so that is the case worth pinning.
    """
    Path(project.cur_dir).mkdir(parents=True, exist_ok=True)
    if task == counter:
        raise ValueError('missing coefficients for this tile')
    time.sleep(1.0)
    (Path(project.cur_dir) / 'output.txt').write_text('iteration %s' % counter)
    return counter


def build(tmp_path, n, bad):
    return [(FakeProject(tmp_path / ('tile_%d' % i)), bad, i) for i in range(n)]


def test_all_iterations_run_when_none_fail(tmp_path):
    results = run_within_time_limit(4, write_output_then_raise, build(tmp_path, 12, -1))
    assert sorted(results) == list(range(12))
    assert len(list(tmp_path.glob('tile_*/output.txt'))) == 12


def test_a_raising_iteration_stops_the_run_and_names_what_was_not_attempted(tmp_path):
    with pytest.raises(ParallelIterationFailure) as raised:
        run_within_time_limit(2, write_output_then_raise, build(tmp_path, 40, 7))
    message = str(raised.value)
    assert 'A parallel iteration raised' in message
    assert 'tile_7' in message, 'the failing iteration must be named: %s' % message
    assert 'never attempted' in message
    assert 'ValueError: missing coefficients for this tile' in message
    # Evidence and completed outputs survive: nothing in the orchestration deletes.
    assert (tmp_path / 'tile_7' / 'failure.json').is_file()
    assert len(list(tmp_path.glob('tile_*/output.txt'))) >= 1


def test_an_abruptly_killed_worker_stops_the_run_instead_of_waiting_forever(tmp_path):
    started = time.time()
    with pytest.raises(ParallelIterationFailure) as raised:
        run_within_time_limit(4, write_output_then_die, build(tmp_path, 40, 5))
    elapsed = time.time() - started
    message = str(raised.value)
    assert 'died abruptly' in message, message
    assert 'OOM' in message, 'the message must point at the usual cause: %s' % message
    assert 'preserved on disk' in message
    assert elapsed < TIME_LIMIT_SECONDS
    # Work finished before the kill is still on disk.
    assert len(list(tmp_path.glob('tile_*/output.txt'))) >= 1


def test_the_failure_counts_add_up(tmp_path):
    with pytest.raises(ParallelIterationFailure) as raised:
        run_within_time_limit(2, write_output_slowly_then_raise, build(tmp_path, 30, 0))
    message = str(raised.value)
    found = re.search(r'(\d+) of (\d+) iterations finished, (\d+) were never attempted', message)
    assert found, message
    done, total, unattempted = (int(g) for g in found.groups())
    assert total == 30
    assert done + unattempted <= total
    assert unattempted > 0, 'a fail-fast stop must report the iterations it dropped'
    assert done < total, 'the run must stop before working through everything'
