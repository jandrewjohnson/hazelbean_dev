import unittest, os, sys
from hazelbean.cog import is_path_cog

class TestCOGCompliance(unittest.TestCase):
    def setUp(self):
        """Set up test data paths."""
        self.test_data_dir = os.path.join(os.path.dirname(__file__), "../data")
        self.invalid_cog_path = os.path.join(self.test_data_dir, "ee_r264_ids_900sec.tif"),


    def test_is_cog(self):
        """Check if TIFF files are valid Cloud-Optimized GeoTIFFs (COGs)."""

        with self.subTest(file=self.invalid_cog_path):
            result = is_path_cog(self.invalid_cog_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertFalse(result, f"{self.invalid_cog_path} is not a valid COG")

if __name__ == "__main__":
    unittest.main()