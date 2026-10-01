"""hb.get_temp_dir is the one root for temp files; HB_TEMP_DIR (machine.env) overrides it.

Since 2026-09-03. Before this there were three temp roots (hb.config.TEMPORARY_DIR,
~/temp for hb.temp(), and PRIMARY_DRIVE/temp for p.temporary_dir set inside execute).
"""
import os
import tempfile

import pytest

import hazelbean as hb


def test_default_is_namespaced_per_user_under_os_temp(monkeypatch):
    monkeypatch.delenv('HB_TEMP_DIR', raising=False)
    root = hb.get_temp_dir()
    assert os.path.dirname(root) == tempfile.gettempdir()
    assert os.path.basename(root).startswith('hazelbean_temp_')
    assert os.path.isdir(root)


def test_hb_temp_dir_override_is_used_as_given(monkeypatch, tmp_path):
    override = tmp_path / 'scratch'
    monkeypatch.setenv('HB_TEMP_DIR', str(override))
    assert hb.get_temp_dir() == str(override)
    assert override.is_dir(), 'created on demand'


def test_temp_helpers_land_under_the_root(monkeypatch, tmp_path):
    monkeypatch.setenv('HB_TEMP_DIR', str(tmp_path))
    assert os.path.dirname(hb.temp('.tif', remove_at_exit=False)) == str(tmp_path)
    assert os.path.dirname(hb.temporary_dir(remove_at_exit=False)) == str(tmp_path)
    assert os.path.dirname(hb.make_run_dir(just_return_string=True)) == str(tmp_path)


def test_project_flow_gets_a_per_run_folder_named_for_the_run(monkeypatch, tmp_path):
    monkeypatch.setenv('HB_TEMP_DIR', str(tmp_path))
    p = hb.ProjectFlow(project_dir=str(tmp_path / 'proj'))
    assert os.path.dirname(p.temporary_dir) == str(tmp_path)
    assert os.path.basename(p.temporary_dir) == p.project_name + '_' + p.run_string
    assert not os.path.exists(p.temporary_dir), 'only created when execute() starts'


def test_retired_config_globals_are_gone():
    for name in ('TEMPORARY_DIR', 'HAZELBEAN_WORKING_DIRECTORY', 'TEST_DATA_DIR',
                 'HAZELBEAN_CONFIG_DIR', 'default_hazelbean_config_uri', 'write_default_config'):
        assert not hasattr(hb.config, name), name
