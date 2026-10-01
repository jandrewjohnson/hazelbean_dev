"""
Unit tests for get_path's shared data root tier.

A shared data root is a read-only directory that mirrors base_data's ref_path layout
-- a mounted lab drive (Google Drive for Desktop, Dropbox), a group scratch dir, an
external disk. get_path searches configured roots after base_data_dir and before the
cloud bucket, and copies any hit into base_data_dir so later runs resolve locally.

The tier is opportunistic by design: Google Drive for Desktop has no Linux client, so
an absent root is the normal state on the cluster and must never be an error.

Covers:
- unset config is a strict no-op (the regression that matters most)
- a configured-but-absent root falls through cleanly
- a hit copies to base_data and returns the LOCAL path
- the second call resolves locally without touching the root
- sidecars come along; Google-native placeholders do not
- an interrupted copy leaves no .partial behind for a later run to trust
- the not-found message distinguishes "not mounted" from "not there"
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

import hazelbean as hb


class SharedDataRootTest(unittest.TestCase):
    """Base fixture: a project dir, a local base_data, and a fake shared root."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.tmp, 'project')
        self.base_data_dir = os.path.join(self.tmp, 'base_data')
        self.shared_root = os.path.join(self.tmp, 'shared_drive', 'base_data')
        os.makedirs(self.project_dir)
        os.makedirs(self.base_data_dir)
        os.makedirs(os.path.join(self.shared_root, 'global_invest', 'terrestrial_carbon'))

        self.ref_path = os.path.join('global_invest', 'terrestrial_carbon', 'carbon_zones.tif')
        self.shared_file = os.path.join(self.shared_root, self.ref_path)
        with open(self.shared_file, 'wb') as f:
            f.write(b'RASTERBYTES' * 100)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _project(self, shared_dirs=None):
        p = hb.ProjectFlow(project_dir=self.project_dir)
        p.base_data_dir = self.base_data_dir
        p.shared_data_dirs = shared_dirs if shared_dirs is not None else []
        return p

    @property
    def local_path(self):
        return os.path.join(self.base_data_dir, self.ref_path)


class TestNoOpWhenUnconfigured(SharedDataRootTest):

    @pytest.mark.unit
    def test_unset_config_leaves_get_path_unchanged(self):
        """No shared roots configured -> the file is simply not found, exactly as before.

        This is the most important test in the file: the tier must be strictly additive.
        """
        p = self._project(shared_dirs=[])
        with self.assertRaises(NameError):
            p.get_path(self.ref_path)
        self.assertFalse(os.path.exists(self.local_path),
                         'nothing should have been cached when no root is configured')

    @pytest.mark.unit
    def test_env_var_absent_gives_empty_list(self):
        """A ProjectFlow built with HB_SHARED_DATA_DIRS unset has no shared roots."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('HB_SHARED_DATA_DIRS', None)
            p = hb.ProjectFlow(project_dir=self.project_dir)
            self.assertEqual(p.shared_data_dirs, [])

    @pytest.mark.unit
    def test_env_var_is_pathsep_separated(self):
        """Several roots can be configured at once, and blanks are dropped."""
        value = os.pathsep.join([self.shared_root, '', '/nonexistent/second_root'])
        with patch.dict(os.environ, {'HB_SHARED_DATA_DIRS': value}):
            p = hb.ProjectFlow(project_dir=self.project_dir)
            self.assertEqual(p.shared_data_dirs, [self.shared_root, '/nonexistent/second_root'])


class TestAbsentRootFallsThrough(SharedDataRootTest):

    @pytest.mark.unit
    def test_unmounted_root_is_skipped_not_raised(self):
        """The normal state on Linux: configured, but no such directory. Must not blow up."""
        p = self._project(shared_dirs=[os.path.join(self.tmp, 'not_mounted')])
        self.assertFalse(p.shared_root_is_available(os.path.join(self.tmp, 'not_mounted')))
        with self.assertRaises(NameError):
            p.get_path(self.ref_path)   # falls through to not-found, not to a crash

    @pytest.mark.unit
    def test_availability_is_cached(self):
        """get_path runs thousands of times per run; the root is stat-ed once per ProjectFlow."""
        p = self._project(shared_dirs=[self.shared_root])
        with patch('os.path.isdir', wraps=os.path.isdir) as spy:
            p.shared_root_is_available(self.shared_root)
            p.shared_root_is_available(self.shared_root)
            p.shared_root_is_available(self.shared_root)
            calls_on_root = [c for c in spy.call_args_list if c[0] and c[0][0] == self.shared_root]
        self.assertEqual(len(calls_on_root), 1, 'availability should be cached after the first check')


class TestHitCachesLocally(SharedDataRootTest):

    @pytest.mark.unit
    def test_hit_returns_local_path_and_copies(self):
        """A hit copies into base_data and returns the LOCAL path, not the shared one."""
        p = self._project(shared_dirs=[self.shared_root])
        got = p.get_path(self.ref_path)

        self.assertEqual(got, self.local_path)
        self.assertNotIn('shared_drive', got, 'must not hand back the shared-root path')
        self.assertTrue(os.path.isfile(self.local_path))
        with open(self.local_path, 'rb') as f:
            self.assertEqual(f.read(), b'RASTERBYTES' * 100)

    @pytest.mark.unit
    def test_second_call_resolves_locally(self):
        """Once cached, the shared root is not consulted again."""
        p = self._project(shared_dirs=[self.shared_root])
        p.get_path(self.ref_path)

        # Make the shared root vanish; the ref_path must still resolve, from base_data.
        shutil.rmtree(os.path.join(self.tmp, 'shared_drive'))
        p2 = self._project(shared_dirs=[self.shared_root])
        self.assertEqual(p2.get_path(self.ref_path), self.local_path)

    @pytest.mark.unit
    def test_local_base_data_wins_over_shared_root(self):
        """base_data is searched first, so a local copy is never re-fetched."""
        os.makedirs(os.path.dirname(self.local_path))
        with open(self.local_path, 'wb') as f:
            f.write(b'LOCAL')
        p = self._project(shared_dirs=[self.shared_root])
        got = p.get_path(self.ref_path)
        with open(got, 'rb') as f:
            self.assertEqual(f.read(), b'LOCAL', 'the local copy should not be overwritten')

    @pytest.mark.unit
    def test_shared_root_is_not_written_to(self):
        """The contract is read-only: nothing new appears on the shared root."""
        before = sorted(os.listdir(os.path.dirname(self.shared_file)))
        p = self._project(shared_dirs=[self.shared_root])
        p.get_path(self.ref_path)
        after = sorted(os.listdir(os.path.dirname(self.shared_file)))
        self.assertEqual(before, after)


class TestSidecarsAndPlaceholders(SharedDataRootTest):

    @pytest.mark.unit
    def test_gdal_sidecar_is_copied(self):
        """Dropping .aux.xml is a silent stats/pyramid regression, not an error."""
        with open(self.shared_file + '.aux.xml', 'w') as f:
            f.write('<PAMDataset/>')
        p = self._project(shared_dirs=[self.shared_root])
        p.get_path(self.ref_path)
        self.assertTrue(os.path.isfile(self.local_path + '.aux.xml'))

    @pytest.mark.unit
    def test_shapefile_siblings_are_copied(self):
        """A .shp without its .dbf/.shx is unopenable, so the siblings must come along."""
        vec_dir = os.path.join(self.shared_root, 'vec')
        os.makedirs(vec_dir)
        for extension in ('.shp', '.dbf', '.shx', '.prj'):
            with open(os.path.join(vec_dir, 'countries' + extension), 'w') as f:
                f.write(extension)

        p = self._project(shared_dirs=[self.shared_root])
        got = p.get_path(os.path.join('vec', 'countries.shp'))
        copied = sorted(os.listdir(os.path.dirname(got)))
        self.assertEqual(copied, ['countries.dbf', 'countries.prj', 'countries.shp', 'countries.shx'])

    @pytest.mark.unit
    def test_google_native_placeholder_is_not_a_match(self):
        """A .gsheet on a mounted Drive is a ~100-byte JSON pointer, not data."""
        ref = os.path.join('global_invest', 'terrestrial_carbon', 'notes.gsheet')
        with open(os.path.join(self.shared_root, ref), 'w') as f:
            f.write('{"doc_id": "abc123"}')
        p = self._project(shared_dirs=[self.shared_root])
        with self.assertRaises(NameError):
            p.get_path(ref)
        self.assertFalse(os.path.exists(os.path.join(self.base_data_dir, ref)))

    @pytest.mark.unit
    def test_is_google_native_file_helper(self):
        self.assertTrue(hb.is_google_native_file('a/b/notes.gsheet'))
        self.assertTrue(hb.is_google_native_file('a/b/NOTES.GDOC'))
        self.assertFalse(hb.is_google_native_file('a/b/raster.tif'))


class TestAtomicity(SharedDataRootTest):

    @pytest.mark.unit
    def test_interrupted_copy_leaves_no_partial(self):
        """A killed copy must not leave a truncated file that later passes path_exists."""
        p = self._project(shared_dirs=[self.shared_root])
        with patch('shutil.copyfile', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                p.get_path(self.ref_path)

        self.assertFalse(os.path.exists(self.local_path))
        stray = []
        for root, _dirs, files in os.walk(self.base_data_dir):
            stray += [f for f in files if '.partial' in f]
        self.assertEqual(stray, [], 'a .partial file must never survive a failed copy')

    @pytest.mark.unit
    def test_short_read_is_detected(self):
        """A stalled mount that yields a truncated copy must raise, not cache."""
        def _truncating_copy(src, dst):
            with open(dst, 'wb') as f:
                f.write(b'short')
        p = self._project(shared_dirs=[self.shared_root])
        with patch('shutil.copyfile', side_effect=_truncating_copy):
            with self.assertRaises(IOError):
                p.get_path(self.ref_path)
        self.assertFalse(os.path.exists(self.local_path))


class TestErrorMessage(SharedDataRootTest):

    @pytest.mark.unit
    def test_message_marks_root_unavailable(self):
        """'Not mounted' and 'not there' must not produce identical messages."""
        missing_root = os.path.join(self.tmp, 'not_mounted')
        p = self._project(shared_dirs=[missing_root])
        with self.assertRaises(NameError) as caught:
            p.get_path(os.path.join('nowhere', 'absent.tif'))
        message = str(caught.exception)
        self.assertIn('shared data root', message)
        self.assertIn('NOT AVAILABLE', message)
        self.assertIn(missing_root, message)

    @pytest.mark.unit
    def test_message_marks_root_available(self):
        p = self._project(shared_dirs=[self.shared_root])
        with self.assertRaises(NameError) as caught:
            p.get_path(os.path.join('nowhere', 'absent.tif'))
        message = str(caught.exception)
        self.assertIn('shared data root (available)', message)


if __name__ == "__main__":
    unittest.main()
