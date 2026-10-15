"""A failing iteration and a dying worker must both stop the run, loudly and without data loss.

Pool.starmap gave neither guarantee. A raising iteration abandoned everything still queued while
reporting only its own exception, and an abruptly killed worker -- an OOM kill -- never delivered a
result, so the parent waited forever. The second is the one that cannot be caught by inspection:
the only way to know it terminates is to kill a worker and watch the clock, which is what these
tests do. Every test is bounded, so a regression to waiting forever FAILS rather than hanging.
"""
import os
import signal
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

from hazelbean.project_flow import ParallelIterationFailure, run_parallel_iterations

TIME_LIMIT_SECONDS = 90


class FakeProject:
    """Stands in for the project copy an iteration is handed; only cur_dir is read."""

    def __init__(self, cur_dir):
        self.cur_dir = str(cur_dir)


@contextmanager
def time_limit(seconds):
    def expired(signum, frame):
        raise TimeoutError(
            'did not terminate within %ds -- this is the hang the fix exists to remove' % seconds)
    previous = signal.signal(signal.SIGALRM, expired)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


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
    with time_limit(TIME_LIMIT_SECONDS):
        results = run_parallel_iterations(4, write_output_then_raise, build(tmp_path, 12, -1))
    assert sorted(results) == list(range(12))
    assert len(list(tmp_path.glob('tile_*/output.txt'))) == 12


def test_a_raising_iteration_stops_the_run_and_names_what_was_not_attempted(tmp_path):
    with time_limit(TIME_LIMIT_SECONDS):
        with pytest.raises(ParallelIterationFailure) as raised:
            run_parallel_iterations(2, write_output_then_raise, build(tmp_path, 40, 7))
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
    with time_limit(TIME_LIMIT_SECONDS):
        with pytest.raises(ParallelIterationFailure) as raised:
            run_parallel_iterations(4, write_output_then_die, build(tmp_path, 40, 5))
    elapsed = time.time() - started
    message = str(raised.value)
    assert 'died abruptly' in message, message
    assert 'OOM' in message, 'the message must point at the usual cause: %s' % message
    assert 'preserved on disk' in message
    assert elapsed < TIME_LIMIT_SECONDS
    # Work finished before the kill is still on disk.
    assert len(list(tmp_path.glob('tile_*/output.txt'))) >= 1


def test_the_failure_counts_add_up(tmp_path):
    with time_limit(TIME_LIMIT_SECONDS):
        with pytest.raises(ParallelIterationFailure) as raised:
            run_parallel_iterations(2, write_output_slowly_then_raise, build(tmp_path, 30, 0))
    message = str(raised.value)
    import re
    found = re.search(r'(\d+) of (\d+) iterations finished, (\d+) were never attempted', message)
    assert found, message
    done, total, unattempted = (int(g) for g in found.groups())
    assert total == 30
    assert done + unattempted <= total
    assert unattempted > 0, 'a fail-fast stop must report the iterations it dropped'
    assert done < total, 'the run must stop before working through everything'
