import unittest, os, sys
import hazelbean as hb

from hazelbean.pyramids import *

class TestPyramids(unittest.TestCase):
    def setUp(self):
        """Set up test data paths."""
        self.data_dir = os.path.join(os.path.dirname(__file__), "../data")
        self.test_data_dir = os.path.join(self.data_dir, "tests")
        self.cartographic_data_dir = os.path.join(self.data_dir, "cartographic/ee")
        self.pyramids_dir = os.path.join(self.data_dir, "pyramids")
        self.valid_cog_path = os.path.join(self.test_data_dir, "valid_cog_example.tif")
        self.invalid_cog_path = os.path.join(self.test_data_dir, "invalid_cog_example.tif")        
        self.valid_pog_path = os.path.join(self.cartographic_data_dir, "ee_r264_ids_900sec.tif")
        self.ha_per_cell_path = os.path.join(self.pyramids_dir, "ha_per_cell_300sec.tif")


    def test_raster_to_area_raster(self):
        """Check if TIFF files are valid Cloud-Optimized GeoTIFFs (COGs)."""

        temp_path = hb.temp('.tif', filename_start='test_raster_to_area_raster', remove_at_exit=True, tag_along_file_extensions=['.aux.xml'])
        with self.subTest(file=self.ha_per_cell_path):
            raster_to_area_raster(self.ha_per_cell_path, temp_path)
            result = hb.path_exists(temp_path)
            self.assertTrue(result)
            
            
            # Make it a pog
            temp_pog_path = hb.temp('.tif', filename_start='test_area_raster_as_pog', remove_at_exit=True, tag_along_file_extensions=['.aux.xml'])
            hb.make_path_pog(temp_path, temp_pog_path, output_data_type=7, verbose=True)

            result = hb.is_path_pog(temp_pog_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=True)
            self.assertTrue(result)

if __name__ == "__main__":
    unittest.main()

