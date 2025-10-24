import unittest, os, sys
import pytest
import hazelbean as hb

from hazelbean.cog import *
from hazelbean.pyramids import *

class TestCOGCompliance(unittest.TestCase):
    def setUp(self):
        """Set up test data paths."""
        self.data_dir = os.path.join(os.path.dirname(__file__), "../../data")
        self.test_data_dir = os.path.join(self.data_dir, "tests")
        self.cartographic_data_dir = os.path.join(self.data_dir, "cartographic/ee")
        self.valid_cog_path = os.path.join(self.test_data_dir, "valid_cog_example.tif")
        self.invalid_cog_path = os.path.join(self.test_data_dir, "invalid_cog_example.tif")        
        self.valid_pog_path = os.path.join(self.cartographic_data_dir, "ee_r264_ids_900sec.tif")


    @pytest.mark.unit
    def test_is_cog(self):
        """Check if TIFF files are valid Cloud-Optimized GeoTIFFs (COGs)."""

        with self.subTest(file=self.invalid_cog_path):
            result = is_path_cog(self.invalid_cog_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertFalse(result, f"{self.invalid_cog_path} is a valid COG")
            
            result = is_path_cog(self.valid_cog_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertTrue(result, f"{self.invalid_cog_path} is Not a valid COG")
            
    @pytest.mark.integration
    @pytest.mark.slow
    def test_make_path_cog(self):
        """Test make_path_cog() Need to find a non-translate way. maybe rio?"""

        with self.subTest(file=self.invalid_cog_path):
            temp_path = hb.temp('.tif', remove_at_exit=True, tag_along_file_extensions=['.aux.xml'])
            make_path_cog(self.invalid_cog_path, temp_path, output_data_type=1, overview_resampling_method='mode', ndv=255, compression="ZSTD", blocksize=512, verbose=True)
            
            result = is_path_cog(temp_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertTrue(result, f"{temp_path} is a valid COG")

    @pytest.mark.integration
    def test_write_random_cog(self):
        """Test make_path_cog() Need to find a non-translate way. maybe rio?"""

        with self.subTest(file=self.invalid_cog_path):
            temp_path = hb.temp('.tif', remove_at_exit=True, tag_along_file_extensions=['.aux.xml'])
            write_random_cog(temp_path)

            result = is_path_cog(temp_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertTrue(result, f"{temp_path} is a valid COG")
            
    @pytest.mark.benchmark
    @pytest.mark.integration
    def test_cog_validation_performance(self):
        """Benchmark COG validation performance."""
        import pytest
        
        def validate_cog():
            return is_path_cog(self.valid_cog_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
        
        # This will work if the test is run through pytest with benchmark plugin
        try:
            # Check if we're running under pytest with benchmark
            if hasattr(self, '_testMethodName') and 'benchmark' in str(self._testMethodName):
                result = validate_cog()
                self.assertTrue(result)
        except:
            # Fallback for regular unittest
            result = validate_cog()
            self.assertTrue(result)
            
            
    

if __name__ == "__main__":
    unittest.main()

