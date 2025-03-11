import unittest, os, sys
import hazelbean as hb

from hazelbean.cog import *
from hazelbean.pyramids import *

class TestUtils(unittest.TestCase):
    def setUp(self):
        """Set up test data paths."""
        self.data_dir = os.path.join(os.path.dirname(__file__), "../data")
        self.test_data_dir = os.path.join(self.data_dir, "tests")
        self.cartographic_data_dir = os.path.join(self.data_dir, "cartographic/ee")
        self.valid_cog_path = os.path.join(self.test_data_dir, "valid_cog_example.tif")
        self.invalid_cog_path = os.path.join(self.test_data_dir, "invalid_cog_example.tif")        
        self.valid_pog_path = os.path.join(self.cartographic_data_dir, "ee_r264_ids_900sec.tif")
    
    def test_write_pog_of_value_from_match(self):
        with self.subTest(file=self.valid_cog_path):
 
            write_pog_of_value_from_match = hb.temp('.tif', filename_start='write_pog_of_value_from_match', remove_at_exit=1, tag_along_file_extensions=['.aux.xml'])
            value = 55
            output_data_type = 1
            ndv = 255
            overview_resampling_method = 'mode'
            hb.write_pog_of_value_from_match(write_pog_of_value_from_match, self.valid_pog_path, value=value, output_data_type=output_data_type, ndv=ndv, overview_resampling_method=overview_resampling_method, compression='ZSTD', blocksize='512')
            
            result = is_path_pog(write_pog_of_value_from_match, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertTrue(result, f"{write_pog_of_value_from_match} is a valid POG" + str(result))
            
    def test_write_pog_of_value_from_scratch(self):
        with self.subTest(file=self.valid_cog_path):
 
            write_pog_of_value_from_scratch = hb.temp('.tif', filename_start='write_pog_of_value_from_scratch', remove_at_exit=0, tag_along_file_extensions=['.aux.xml'])
            value = 55
            arcsecond_resolution = 900.0
            output_data_type = 1
            ndv = 255
            overview_resampling_method = 'mode'                        
            hb.write_pog_of_value_from_scratch(write_pog_of_value_from_scratch, value=value, arcsecond_resolution=arcsecond_resolution, output_data_type=output_data_type, ndv=ndv, overview_resampling_method=overview_resampling_method, compression='ZSTD', blocksize='512')
            
            result = is_path_pog(write_pog_of_value_from_scratch, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertTrue(result, f"{write_pog_of_value_from_scratch} is a valid POG" + str(result))

            
            

if __name__ == "__main__":
    unittest.main()

    