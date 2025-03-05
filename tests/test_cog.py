import unittest, os, sys
import hazelbean as hb

from hazelbean.cog import *
from hazelbean.pyramids import *

class TestCOGCompliance(unittest.TestCase):
    def setUp(self):
        """Set up test data paths."""
        self.test_data_dir = os.path.join(os.path.dirname(__file__), "../data")
        self.cartographic_data_dir = os.path.join(self.test_data_dir, "cartographic/ee")
        self.invalid_cog_path = os.path.join(self.cartographic_data_dir, "ee_r264_ids_900sec.tif")


    def test_is_cog(self):
        """Check if TIFF files are valid Cloud-Optimized GeoTIFFs (COGs)."""

        with self.subTest(file=self.invalid_cog_path):
            result = is_path_cog(self.invalid_cog_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertFalse(result, f"{self.invalid_cog_path} is not a valid COG")
            
    def test_make_path_cog(self):
        """Test make_path_cog() Need to find a non-translate way. maybe rio?"""

        with self.subTest(file=self.invalid_cog_path):
            temp_path = hb.temp('.tif', remove_at_exit=True)
            make_path_cog(self.invalid_cog_path, temp_path, output_data_type=1, overview_resampling_method='mode', ndv=255, compression="ZSTD", blocksize=512, verbose=True)
            result = is_path_cog(temp_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertTrue(result, f"{temp_path} is a valid COG")

    # def test_make_path_cog(self):
    #     """Test make_path_cog() Need to find a non-translate way. maybe rio?"""

    #     with self.subTest(file=self.invalid_cog_path):
    #         temp_path = hb.temp('.tif', remove_at_exit=True)
    #         make_path_cog_FAILED(self.invalid_cog_path, output_raster_path=temp_path, output_data_type=1, overview_resampling_method='mode', ndv=255, compression="ZSTD", blocksize=512, verbose=True)
    #         result = is_path_cog(temp_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=True)
    #         self.assertTrue(result, f"{temp_path} is a valid COG")


    def test_write_random_cog(self):
        """Test make_path_cog() Need to find a non-translate way. maybe rio?"""

        with self.subTest(file=self.invalid_cog_path):
            temp_path = hb.temp('.tif', remove_at_exit=True)
            write_random_cog(temp_path)

            # make_path_cog(self.invalid_cog_path, output_raster_path=temp_path, output_data_type=1, overview_resampling_method='mode', ndv=255, compression="ZSTD", blocksize=512, verbose=True)
            result = is_path_cog(temp_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertTrue(result, f"{temp_path} is a valid COG")
            
            
    def test_is_path_pog(self):
        """Test make_path_cog()"""

        
        ### START HERE, think through logic  of this test. Should I use a base data from hb that is eventually going to be a pog?
        with self.subTest(file=self.invalid_cog_path):
            temp_path = hb.temp('.tif', remove_at_exit=True)
            make_path_cog(self.invalid_cog_path, temp_path, output_data_type=5, overview_resampling_method='mode', ndv=-9999, compression="ZSTD", blocksize=512, verbose=True)
            result = is_path_pog(temp_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=True)
            self.assertTrue(result, f"{temp_path} is a valid POG")
            
    def test_make_path_pog(self):
        """Test make_path_pog"""


        # START HERE: If I run the test in debug mode via launch.json, it works. If I run it in the vs code click button, it fails.
        with self.subTest(file=self.invalid_cog_path):
            temp_path = hb.temp('.tif', 'test_make_path_pog', remove_at_exit=True)
            make_path_pog(self.invalid_cog_path, temp_path, output_data_type=1, overview_resampling_method='mode', ndv=255, compression="ZSTD", blocksize=512, verbose=True)
            result = is_path_cog(temp_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertTrue(result, f"{temp_path} is a valid COG")


if __name__ == "__main__":
    unittest.main()