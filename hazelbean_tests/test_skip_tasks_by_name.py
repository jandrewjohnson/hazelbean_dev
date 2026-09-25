"""skip_tasks finds a task by its tree name, not only by a '<name>_task' attribute."""
import os

import hazelbean as hb


def _a(p):
    return p


def get_all_extended_vars(p):
    return p


def test_skip_tasks_reaches_a_task_stored_under_another_attribute(tmp_path):
    p = hb.ProjectFlow(project_dir=str(tmp_path / 'proj_skip_test'))
    parent = p.add_task(_a)
    p.get_vars_task = p.add_task(get_all_extended_vars, parent=parent, creates_dir=False)
    p.skip_tasks(['get_all_extended_vars', '_a'])
    assert parent.run == 0 and p.get_vars_task.run == 0
