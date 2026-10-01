"""
Unit tests for hb-setup-machine-env, the one-shot shared-data-root detector.

The script scans a few bounded, OS-specific locations for a directory that mirrors
base_data, and records what it finds in ~/.config/hazelbean/machine.env so
ProjectFlow.get_path can use it as a shared root.

Covers:
- a candidate is only accepted if it actually looks like base_data
- writing creates the config dir, and appends safely to an existing file
- an already-set key is reported, never clobbered
- --print writes nothing
- no candidates is a clean, informative exit rather than a failure
"""

import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch

import pytest

# NOTE: Awkward inclusion here so that I don't have to run the test via a setup config each time
sys.path.extend(['../../..'])

from hazelbean import setup_machine_env as sme


class SetupMachineEnvTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.machine_env = os.path.join(self.tmp, 'config', 'machine.env')
        # A directory that looks like base_data, and one that only shares its name.
        self.real_mirror = os.path.join(self.tmp, 'drive', 'Files', 'base_data')
        self.decoy = os.path.join(self.tmp, 'decoy', 'Files', 'base_data')
        for marker in ('cartographic', 'lulc', 'pyramids'):
            os.makedirs(os.path.join(self.real_mirror, marker))
        os.makedirs(os.path.join(self.decoy, 'holiday_photos'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestCandidateScoring(SetupMachineEnvTest):

    @pytest.mark.unit
    def test_a_real_mirror_scores(self):
        self.assertGreaterEqual(sme.score_candidate(self.real_mirror), sme.MINIMUM_MARKERS)

    @pytest.mark.unit
    def test_a_lookalike_does_not_score(self):
        """Named base_data but holding none of its contents -- must not be proposed."""
        self.assertLess(sme.score_candidate(self.decoy), sme.MINIMUM_MARKERS)

    @pytest.mark.unit
    def test_unreadable_dir_scores_zero_rather_than_raising(self):
        """An unmounted or unauthenticated cloud dir can raise on listdir."""
        with patch('os.listdir', side_effect=OSError('stale mount')):
            self.assertEqual(sme.score_candidate(self.real_mirror), 0)

    @pytest.mark.unit
    def test_only_marker_bearing_candidates_are_returned(self):
        with patch.object(sme, '_candidate_patterns',
                          return_value=[os.path.join(self.tmp, '*', 'Files', 'base_data')]):
            found = sme.find_shared_data_root_candidates()
        paths = [i for i, _ in found]
        self.assertIn(self.real_mirror, paths)
        self.assertNotIn(self.decoy, paths)

    @pytest.mark.unit
    def test_linux_has_no_drive_patterns(self):
        """Google Drive for Desktop has no Linux client, so nothing is detectable there."""
        with patch('platform.system', return_value='Linux'):
            patterns = sme._candidate_patterns()
        self.assertFalse([i for i in patterns if 'CloudStorage' in i or 'Shared drives' in i])


class TestWriting(SetupMachineEnvTest):

    @pytest.mark.unit
    def test_write_creates_config_dir(self):
        sme.write_machine_env_value('/a/base_data', self.machine_env)
        self.assertTrue(os.path.isfile(self.machine_env))
        self.assertEqual(sme.read_existing_value(self.machine_env), '/a/base_data')

    @pytest.mark.unit
    def test_append_preserves_existing_keys(self):
        os.makedirs(os.path.dirname(self.machine_env))
        with open(self.machine_env, 'w') as f:
            f.write('GTAP_SC_SLURM_ACCOUNT=abc')   # deliberately no trailing newline
        sme.write_machine_env_value('/b/base_data', self.machine_env)
        content = open(self.machine_env).read()
        self.assertIn('GTAP_SC_SLURM_ACCOUNT=abc', content)
        self.assertIn('HB_SHARED_DATA_DIRS=/b/base_data', content)
        # The pre-existing key had no trailing newline; the new block must not be
        # glued onto the end of it.
        self.assertTrue(content.startswith('GTAP_SC_SLURM_ACCOUNT=abc\n'))
        self.assertEqual(len(sme.read_existing_value(self.machine_env, 'GTAP_SC_SLURM_ACCOUNT') or ''), 3)

    @pytest.mark.unit
    def test_read_existing_handles_export_prefix(self):
        os.makedirs(os.path.dirname(self.machine_env))
        with open(self.machine_env, 'w') as f:
            f.write('export HB_SHARED_DATA_DIRS=/c/base_data\n')
        self.assertEqual(sme.read_existing_value(self.machine_env), '/c/base_data')

    @pytest.mark.unit
    def test_read_existing_returns_none_when_absent(self):
        self.assertIsNone(sme.read_existing_value(self.machine_env))


class TestMain(SetupMachineEnvTest):

    def _run(self, argv, candidates=None):
        candidates = self.real_mirror if candidates is None else candidates
        found = [(candidates, 3)] if candidates else []
        with patch.object(sme, 'USER_MACHINE_ENV_PATH', self.machine_env), \
             patch.object(sme, 'find_shared_data_root_candidates', return_value=found):
            return sme.main(argv)

    @pytest.mark.unit
    def test_print_only_writes_nothing(self):
        self.assertEqual(self._run(['--print']), 0)
        self.assertFalse(os.path.exists(self.machine_env))

    @pytest.mark.unit
    def test_yes_writes(self):
        self.assertEqual(self._run(['--yes']), 0)
        self.assertEqual(sme.read_existing_value(self.machine_env), self.real_mirror)

    @pytest.mark.unit
    def test_existing_value_is_never_clobbered(self):
        os.makedirs(os.path.dirname(self.machine_env))
        with open(self.machine_env, 'w') as f:
            f.write('HB_SHARED_DATA_DIRS=/set/by/hand\n')
        self.assertEqual(self._run(['--yes']), 0)
        self.assertEqual(sme.read_existing_value(self.machine_env), '/set/by/hand')

    @pytest.mark.unit
    def test_no_candidates_exits_cleanly(self):
        """Nothing found is a normal outcome, not a failure: the bucket still works."""
        self.assertEqual(self._run(['--yes'], candidates=''), 0)
        self.assertFalse(os.path.exists(self.machine_env))

    @pytest.mark.unit
    def test_declining_the_prompt_writes_nothing(self):
        with patch('builtins.input', return_value='n'):
            self.assertEqual(self._run([]), 1)
        self.assertFalse(os.path.exists(self.machine_env))

    @pytest.mark.unit
    def test_accepting_the_prompt_writes(self):
        with patch('builtins.input', return_value='y'):
            self.assertEqual(self._run([]), 0)
        self.assertEqual(sme.read_existing_value(self.machine_env), self.real_mirror)


class TestGetPathHint(unittest.TestCase):

    @pytest.mark.unit
    def test_not_found_message_points_at_the_script(self):
        """The hint must land where someone actually is: a failed resolution."""
        import hazelbean as hb
        tmp = tempfile.mkdtemp()
        try:
            p = hb.ProjectFlow(project_dir=os.path.join(tmp, 'proj'))
            p.base_data_dir = os.path.join(tmp, 'base_data')
            os.makedirs(p.base_data_dir)
            p.shared_data_dirs = []
            with self.assertRaises(NameError) as caught:
                p.get_path(os.path.join('nowhere', 'absent.tif'))
            message = str(caught.exception)
            self.assertIn('No shared data roots are configured', message)
            self.assertIn('hb-setup-machine-env', message)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.mark.unit
    def test_hint_is_absent_when_roots_are_configured(self):
        import hazelbean as hb
        tmp = tempfile.mkdtemp()
        try:
            p = hb.ProjectFlow(project_dir=os.path.join(tmp, 'proj'))
            p.base_data_dir = os.path.join(tmp, 'base_data')
            os.makedirs(p.base_data_dir)
            p.shared_data_dirs = [os.path.join(tmp, 'some_root')]
            with self.assertRaises(NameError) as caught:
                p.get_path(os.path.join('nowhere', 'absent.tif'))
            self.assertNotIn('hb-setup-machine-env', str(caught.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
