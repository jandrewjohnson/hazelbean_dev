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
            
            ### START HERE: Finished write_pog_of_value_from_match() and its test. Use this to generate empty but cannonical pyramid rasters. Then, do this at scale on the base_data.
            
            write_pog_of_value_from_match = hb.temp('.tif', filename_start='write_pog_of_value_from_match', remove_at_exit=False, tag_along_file_extensions=['.aux.xml'])
            hb.write_pog_of_value_from_match(write_pog_of_value_from_match, self.valid_pog_path, 5, 1, 255, 'mode', 'mode', compression='ZSTD', blocksize='512')
            
            result = is_path_pog(write_pog_of_value_from_match, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertTrue(result, f"{write_pog_of_value_from_match} is a valid POG" + str(result))

            
            

if __name__ == "__main__":
    unittest.main()

    