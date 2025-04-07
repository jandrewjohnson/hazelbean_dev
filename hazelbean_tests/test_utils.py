import unittest, os, sys
import hazelbean as hb

from hazelbean.cog import *
from hazelbean.pyramids import *
from hazelbean.stats import *

class TestUtils(unittest.TestCase):
    def setUp(self):
        """Set up test data paths."""
        self.data_dir = os.path.join(os.path.dirname(__file__), "../data")
        self.test_data_dir = os.path.join(self.data_dir, "tests")
        self.cartographic_data_dir = os.path.join(self.data_dir, "cartographic/ee")
        self.valid_cog_path = os.path.join(self.test_data_dir, "valid_cog_example.tif")
        self.invalid_cog_path = os.path.join(self.test_data_dir, "invalid_cog_example.tif")        
        self.valid_pog_path = os.path.join(self.cartographic_data_dir, "ee_r264_ids_900sec.tif")
    
    def test_fn(self):
        equation = """
        depvar ~ mask(indvar_1, is_iindvar_1, [1, 2]) + indvar_2 + indvar_3 + indvar_4 + indvar_1 * indvar_3 + log(indvar_1) + indvar_2 ^ 2 + indvar_3 * 2 + dummy(indvar_5, indvar_5_is_cropland, [10,20])

        """

        
        r = parse_equation_to_dict(equation)
        print(r)            

if __name__ == "__main__":
    unittest.main()

    