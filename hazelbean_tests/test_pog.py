import unittest, os, sys
import hazelbean as hb

from hazelbean.cog import *
from hazelbean.pyramids import *

class TestPOGCompliance(unittest.TestCase):
    def setUp(self):
        """Set up test data paths."""
        self.data_dir = os.path.join(os.path.dirname(__file__), "../data")
        self.test_data_dir = os.path.join(self.data_dir, "tests")
        self.cartographic_data_dir = os.path.join(self.data_dir, "cartographic/ee")
        self.valid_cog_path = os.path.join(self.test_data_dir, "valid_cog_example.tif")
        self.invalid_cog_path = os.path.join(self.test_data_dir, "invalid_cog_example.tif")        
        self.valid_pog_path = os.path.join(self.cartographic_data_dir, "ee_r264_ids_900sec.tif")

    def test_is_path_pog(self):
        """Test make_path_cog()"""

        with self.subTest(file=self.invalid_cog_path):
            temp_path = hb.temp('.tif', remove_at_exit=True, tag_along_file_extensions=['.aux.xml'])
            
            hb.make_path_pog(self.invalid_cog_path, temp_path, output_data_type=5, overview_resampling_method='mode', ndv=-111, compression="ZSTD", blocksize=512, verbose=True)
            result = hb.is_path_pog(temp_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=True)
            self.assertTrue(result, f"{temp_path} is a valid POG")
            
            result = hb.is_path_pog(self.invalid_cog_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=True)
            self.assertFalse(result, f"{temp_path} is a valid POG")
            
            
    def test_make_path_pog_from_non_global_cog(self):
        """Test make_path_pog"""

        with self.subTest(file=self.invalid_cog_path):
            
            # Make a non-global subset of the COG
            non_global_subset = hb.temp('.tif', 'nonglobal', remove_at_exit=1)
            bb = [-130, -60, 130, 50]            
            # NOTE TRICKY ASSUMPTION: It returns a mem array without writing anything UNLESS you specify an output path, but that is often the intended use of this.
            hb.load_geotiff_chunk_by_bb(self.invalid_cog_path, bb, inclusion_behavior='centroid', stride_rate=None, datatype=None, output_path=non_global_subset, ndv=None, raise_all_exceptions=False)
            
            # Make the subset back into a POG, which is thus global.
            temp_path = hb.temp('.tif', 'test_make_path_pog', remove_at_exit=True)
            hb.make_path_pog(non_global_subset, temp_path, output_data_type=1, overview_resampling_method='mode', ndv=255, compression="ZSTD", blocksize=512, verbose=True)
            
            # Test that it is a POG. 
            result = is_path_cog(temp_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertTrue(result, f"{temp_path} is a valid POG")

    def test_write_pog_of_value_from_match(self):
        with self.subTest(file=self.valid_cog_path):
 
            write_pog_of_value_from_match = hb.temp('.tif', filename_start='write_pog_of_value_from_match', remove_at_exit=1, tag_along_file_extensions=['.aux.xml'])
            value = 55
            output_data_type = 1
            ndv = 255
            overview_resampling_method = 'mode'
            hb.write_pog_of_value_from_match(write_pog_of_value_from_match, self.valid_pog_path, value=value, output_data_type=output_data_type, ndv=ndv, overview_resampling_method=overview_resampling_method, compression='ZSTD', blocksize='512')
            
            result = hb.is_path_pog(write_pog_of_value_from_match, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertTrue(result, f"{write_pog_of_value_from_match} is a valid POG" + str(result))
            
    def test_write_pog_of_value_from_scratch(self):
        with self.subTest(file=self.valid_cog_path):
 
            write_pog_of_value_from_scratch = hb.temp('.tif', filename_start='write_pog_of_value_from_scratch', remove_at_exit=1, tag_along_file_extensions=['.aux.xml'])
            value = 55
            arcsecond_resolution = 900.0
            output_data_type = 1
            ndv = 255
            overview_resampling_method = 'mode'                        
            hb.write_pog_of_value_from_scratch(write_pog_of_value_from_scratch, value=value, arcsecond_resolution=arcsecond_resolution, output_data_type=output_data_type, ndv=ndv, overview_resampling_method=overview_resampling_method, compression='ZSTD', blocksize='512')
            
            result = hb.is_path_pog(write_pog_of_value_from_scratch, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertTrue(result, f"{write_pog_of_value_from_scratch} is a valid POG" + str(result))


if __name__ == "__main__":
    unittest.main()

