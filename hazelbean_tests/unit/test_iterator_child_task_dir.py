"""A task under an iterator shares the iteration's directory when registered with creates_dir=False.

By default each task under an iterator gets its own subdirectory inside each iteration.
"""
import os
from pathlib import Path

import hazelbean as hb


def _tree(tmp_path, seen):
    """One iterator over a single iteration, with a default child and a sharing child."""

    def zones(p):
        p.iterator_replacements = {'cur_dir_parent_dir': [os.path.join(p.cur_dir, '0_0')]}
        return p

    def own_dir(p):
        seen['own_dir'] = p.cur_dir
        return p

    def shared_dir(p):
        seen['shared_dir'] = p.cur_dir
        return p

    p = hb.ProjectFlow(project_dir=str(tmp_path / 'proj'))
    iterator = p.add_iterator(zones, run_in_parallel=False)
    p.add_task(own_dir, parent=iterator, skip_existing=0)
    p.add_task(shared_dir, parent=iterator, skip_existing=0, creates_dir=False)
    return p, iterator


def test_creates_dir_false_shares_the_iteration_dir_and_true_does_not(tmp_path):
    seen = {}
    p, iterator = _tree(tmp_path, seen)
    p.execute()
    iteration = os.path.join(iterator.task_dir, '0_0')
    # The sharing child writes into the iteration's own directory.
    assert seen['shared_dir'] == iteration
    # The default child keeps a directory named after itself, as before.
    assert seen['own_dir'] == os.path.join(iteration, 'own_dir')


def test_the_default_is_a_directory_per_task(tmp_path):
    """Guards the existing behaviour: creates_dir defaults to True, so nothing shares by accident."""
    seen = {}

    def zones(p):
        p.iterator_replacements = {'cur_dir_parent_dir': [os.path.join(p.cur_dir, '0_0')]}
        return p

    def first(p):
        seen['first'] = p.cur_dir
        return p

    def second(p):
        seen['second'] = p.cur_dir
        return p

    p = hb.ProjectFlow(project_dir=str(tmp_path / 'proj'))
    iterator = p.add_iterator(zones, run_in_parallel=False)
    p.add_task(first, parent=iterator, skip_existing=0)
    p.add_task(second, parent=iterator, skip_existing=0)
    p.execute()
    assert seen['first'] != seen['second']
    assert Path(seen['first']).name == 'first'
    assert Path(seen['second']).name == 'second'


def test_a_shared_child_does_not_create_a_directory_of_its_own(tmp_path):
    """The point of the flag: no per-task directory appears inside the iteration."""
    seen = {}
    p, iterator = _tree(tmp_path, seen)
    p.execute()
    iteration = Path(iterator.task_dir) / '0_0'
    assert not (iteration / 'shared_dir').exists()
    assert (iteration / 'own_dir').is_dir()
