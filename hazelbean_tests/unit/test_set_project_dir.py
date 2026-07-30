"""Tests for ProjectFlow project-dir resolution.

Covers the merged API where hb.ProjectFlow(project_name=..., run_mode=...) does the
directory setup that used to need a second set_project_dir_for_run_mode() call, plus
the legacy call shapes that must keep working and the deferred-materialization
guarantee that stops a bare constructor from leaving an orphan project dir behind.

Each test runs from a throwaway git repo so the git-aware inference paths
(_derive_default_project_dir, _infer_project_parent_dir) are exercised for real
rather than mocked, and nothing is written outside tmp_path.
"""

import os
import subprocess
import sys
import textwrap

import pytest

sys.path.extend(['../..'])

import hazelbean as hb


RUNNER_TEMPLATE = """
import json, os, sys
import hazelbean as hb

def emit(obj):
    sys.stdout.write('@@RESULT@@' + json.dumps(obj) + '@@END@@')

{body}
"""


def run_in_repo(tmp_path, body):
    """Execute `body` from a script inside a throwaway git repo; return its emitted dict.

    ProjectFlow derives its default dir from the *calling script*, so these have to
    run as real scripts on disk rather than inside pytest's own process.
    """
    repo = tmp_path / 'repo'
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'init', '-q'], cwd=repo, check=True)

    script = repo / 'run_widget.py'
    script.write_text(RUNNER_TEMPLATE.format(body=textwrap.dedent(body)))

    proc = subprocess.run([sys.executable, str(script)], cwd=repo,
                          capture_output=True, text=True)
    assert proc.returncode == 0, 'script failed:\n' + proc.stdout + '\n' + proc.stderr
    out = proc.stdout
    assert '@@RESULT@@' in out, 'no result emitted:\n' + out
    import json
    return json.loads(out.split('@@RESULT@@')[1].split('@@END@@')[0])


@pytest.fixture
def projects_dir(tmp_path):
    """Where the git-aware inference puts project dirs for the throwaway repo."""
    return tmp_path / 'projects'


class TestBareConstructor:
    def test_derives_git_aware_dir_without_writing(self, tmp_path, projects_dir):
        """A bare ProjectFlow() resolves its dir but must not create anything.

        This is the regression guard: it used to create the derived dir (and copy
        input_template/ into it) during __init__, so a run file that constructed
        bare and then re-pointed left an orphan tree behind.
        """
        r = run_in_repo(tmp_path, """
            p = hb.ProjectFlow()
            emit({'project_dir': p.project_dir,
                  'exists': os.path.exists(p.project_dir),
                  'input_dir': p.input_dir,
                  'project_name': p.project_name})
        """)
        assert r['project_dir'] == str(projects_dir / 'widget')  # 'run_' stripped
        assert r['exists'] is False
        assert r['input_dir'] == str(projects_dir / 'widget' / 'input')
        assert r['project_name'] == 'widget'

    def test_execute_materializes_the_dirs(self, tmp_path, projects_dir):
        """Deferring creation must not break the bare-constructor run path."""
        r = run_in_repo(tmp_path, """
            def demo_task(p):
                p.out_path = os.path.join(p.cur_dir, 'demo.txt')
                if p.run_this:
                    open(p.out_path, 'w').write('ok')

            p = hb.ProjectFlow()
            before = os.path.exists(p.project_dir)
            p.add_task(demo_task)
            p.execute()
            emit({'before': before,
                  'after': os.path.isdir(p.project_dir),
                  'task_output_written': os.path.exists(p.out_path)})
        """)
        assert r['before'] is False
        assert r['after'] is True
        assert r['task_output_written'] is True


class TestConstructorArguments:
    def test_project_name_sets_and_creates_dir(self, tmp_path, projects_dir):
        r = run_in_repo(tmp_path, """
            p = hb.ProjectFlow(project_name='ctor_named', run_mode='check')
            emit({'project_dir': p.project_dir,
                  'exists': os.path.isdir(p.project_dir),
                  'project_name': p.project_name})
        """)
        assert r['project_dir'] == str(projects_dir / 'ctor_named')
        assert r['exists'] is True

    def test_project_name_survives_basename_derivation(self, tmp_path):
        """project_name must not be clobbered by the dir-basename derivation.

        The two used to be assigned by different methods in a fixed order; only the
        ordering kept them agreeing.
        """
        r = run_in_repo(tmp_path, """
            p = hb.ProjectFlow(project_name='ctor_named', run_mode='check')
            emit({'project_name': p.project_name})
        """)
        assert r['project_name'] == 'ctor_named'

    def test_extra_dirs_places_project_under_user_dir(self, tmp_path):
        r = run_in_repo(tmp_path, """
            p = hb.ProjectFlow(project_name='x', run_mode='check',
                               extra_dirs=['a_test_stack', 'projects'])
            emit({'project_dir': p.project_dir,
                  'expected': os.path.join(os.path.expanduser('~'),
                                           'a_test_stack', 'projects', 'x')})
        """)
        assert r['project_dir'] == r['expected']
        # Clean up: this one necessarily lands under the real user dir.
        import shutil
        shutil.rmtree(os.path.join(os.path.expanduser('~'), 'a_test_stack'),
                      ignore_errors=True)

    def test_no_orphan_dir_when_repointing_after_bare_construction(self, tmp_path, projects_dir):
        """The canonical legacy pair must leave only the named dir behind."""
        r = run_in_repo(tmp_path, """
            p = hb.ProjectFlow()
            derived = p.project_dir
            p.set_project_dir(project_name='named_later', run_mode='check')
            emit({'named_exists': os.path.isdir(p.project_dir),
                  'orphan_exists': os.path.exists(derived),
                  'project_dir': p.project_dir})
        """)
        assert r['named_exists'] is True
        assert r['orphan_exists'] is False
        assert r['project_dir'] == str(projects_dir / 'named_later')


class TestRunModes:
    def test_full_appends_timestamp_to_name(self, tmp_path):
        r = run_in_repo(tmp_path, """
            p = hb.ProjectFlow(project_name='stamped', run_mode='full')
            emit({'project_name': p.project_name, 'exists': os.path.isdir(p.project_dir)})
        """)
        assert r['project_name'].startswith('stamped_')
        assert len(r['project_name']) > len('stamped_') + 8
        assert r['exists'] is True

    def test_full_appends_timestamp_to_explicit_dir(self, tmp_path):
        """run_mode is about reuse policy, so it composes with an explicit path too."""
        r = run_in_repo(tmp_path, """
            target = os.path.join(os.getcwd(), 'explicit_target')
            p = hb.ProjectFlow(project_dir=target, run_mode='full')
            emit({'project_dir': p.project_dir, 'target': target,
                  'exists': os.path.isdir(p.project_dir)})
        """)
        assert r['project_dir'] != r['target']
        assert r['project_dir'].startswith(r['target'] + '_')
        assert r['exists'] is True

    def test_check_reuses_the_stable_dir(self, tmp_path):
        r = run_in_repo(tmp_path, """
            a = hb.ProjectFlow(project_name='stable', run_mode='check')
            b = hb.ProjectFlow(project_name='stable', run_mode='check')
            emit({'same': a.project_dir == b.project_dir})
        """)
        assert r['same'] is True

    def test_fresh_intermediate_clears_intermediate_and_outputs(self, tmp_path):
        r = run_in_repo(tmp_path, """
            p = hb.ProjectFlow(project_name='test_fresh', run_mode='check')
            os.makedirs(p.intermediate_dir, exist_ok=True)
            os.makedirs(p.input_dir, exist_ok=True)
            stale = os.path.join(p.intermediate_dir, 'stale.txt')
            keep = os.path.join(p.input_dir, 'parameters.csv')
            open(stale, 'w').write('x')
            open(keep, 'w').write('key,value')

            p2 = hb.ProjectFlow(project_name='test_fresh', run_mode='fresh_intermediate')
            emit({'stale_gone': not os.path.exists(stale),
                  'input_kept': os.path.exists(keep),
                  'project_dir_kept': os.path.isdir(p2.project_dir)})
        """)
        assert r['stale_gone'] is True
        assert r['input_kept'] is True, 'input/ holds per-machine values and must survive'
        assert r['project_dir_kept'] is True


class TestInputTemplateSeeding:
    def test_template_copied_into_input_dir(self, tmp_path):
        r = run_in_repo(tmp_path, """
            template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        'input_template')
            os.makedirs(template_dir, exist_ok=True)
            open(os.path.join(template_dir, 'parameters.csv'), 'w').write('key,value\\nndv,-9999\\n')

            p = hb.ProjectFlow(project_name='templated', run_mode='check')
            emit({'copied': os.path.exists(os.path.join(p.input_dir, 'parameters.csv'))})
        """)
        assert r['copied'] is True

    def test_existing_input_file_is_never_overwritten(self, tmp_path):
        """input/ is the per-machine working copy; re-runs must not clobber edits."""
        r = run_in_repo(tmp_path, """
            template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        'input_template')
            os.makedirs(template_dir, exist_ok=True)
            open(os.path.join(template_dir, 'parameters.csv'), 'w').write('key,value\\ncred,\\n')

            p = hb.ProjectFlow(project_name='templated', run_mode='check')
            local = os.path.join(p.input_dir, 'parameters.csv')
            open(local, 'w').write('key,value\\ncred,/my/machine/path\\n')

            hb.ProjectFlow(project_name='templated', run_mode='check')
            emit({'contents': open(local).read()})
        """)
        assert '/my/machine/path' in r['contents']


class TestLegacyCallShapes:
    """Older run files and tests must keep working unchanged."""

    def test_positional_project_dir(self, tmp_path):
        r = run_in_repo(tmp_path, """
            target = os.path.join(os.getcwd(), 'explicit_path')
            p = hb.ProjectFlow(target)
            emit({'project_dir': p.project_dir, 'exists': os.path.isdir(target),
                  'project_name': p.project_name})
        """)
        assert r['exists'] is True
        assert r['project_name'] == 'explicit_path'

    def test_assign_then_set_project_dir(self, tmp_path):
        r = run_in_repo(tmp_path, """
            p = hb.ProjectFlow()
            p.project_dir = os.path.join(os.getcwd(), 'old_style')
            p.set_project_dir(p.project_dir)
            emit({'exists': os.path.isdir(p.project_dir),
                  'project_dir': p.project_dir})
        """)
        assert r['exists'] is True
        assert r['project_dir'].endswith('old_style')

    def test_deprecated_set_project_dir_for_run_mode(self, tmp_path, projects_dir):
        r = run_in_repo(tmp_path, """
            p = hb.ProjectFlow()
            p.set_project_dir_for_run_mode('legacy_wrapper', 'check')
            emit({'project_dir': p.project_dir, 'exists': os.path.isdir(p.project_dir)})
        """)
        assert r['project_dir'] == str(projects_dir / 'legacy_wrapper')
        assert r['exists'] is True

    def test_script_parent_sentinel_still_derives_default(self, tmp_path, projects_dir):
        r = run_in_repo(tmp_path, """
            p = hb.ProjectFlow('script_parent')
            emit({'project_dir': p.project_dir})
        """)
        assert r['project_dir'] == str(projects_dir / 'widget')


class TestArgumentValidation:
    @pytest.mark.parametrize('kwargs, needle', [
        ({'project_dir': '/tmp/x', 'project_name': 'y'}, 'not both'),
        ({'project_name': 'y', 'run_mode': 'bogus'}, 'run_mode must be one of'),
        ({'project_name': 'prod', 'run_mode': 'fresh_intermediate'}, 'dedicated test projects'),
    ])
    def test_invalid_combinations_raise_value_error(self, kwargs, needle):
        with pytest.raises(ValueError) as exc:
            hb.ProjectFlow(**kwargs)
        assert needle in str(exc.value)

    def test_fresh_intermediate_allowed_on_test_named_project(self, tmp_path):
        """The 'test' gate is the only thing standing between a typo and a deletion."""
        r = run_in_repo(tmp_path, """
            p = hb.ProjectFlow(project_name='test_ok', run_mode='fresh_intermediate')
            emit({'ok': os.path.isdir(p.project_dir)})
        """)
        assert r['ok'] is True
