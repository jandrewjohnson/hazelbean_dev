import unittest, os, sys
import hazelbean as hb        
import pandas as pd
import numpy as np # Optional, as None can be used directly


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
        
    def test_parse_flex_to_python_object(self):
        """Test parsing a flex item (int, float, string, None, string that represents a python object) element to a Python object."""

        

        # Data extracted from the image
        data = {
            'columns': [
                'counterfactual',
                '"year"',
                'year, counterfactual',
                'counterfactual',
                'counterfactual',
                'counterfactual',
                '["counterfactual", "year"]',
                '["counterfactual", "year"]',
                'counterfactual',
                'counterfactual'
            ],
            'aggregation_dict': [
                None,  # Representing empty cell
                None,
                None,
                None,
                None,
                None,
                'AEZS:sum',
                '{AEZS:"sum"}',
                None,
                None
            ],
            'filter_dict': [
                'aggregation:v11_s26_r50, year:2050',
                '{aggregation:v11_s26_r50 ,counterfactual: bau_ignore_es}',
                '{aggregation:v11_s26_r50}',
                'aggregation: v11_s26_r50, "year":2050', # Note space after colon
                'aggregation: v11_s26_r50, "year":[2030, 2050]', # Note space after colon
                '{"aggregation":"v11_s26_r50", "year":2050}',
                None, # Representing empty cell
                None,
                '"aggregation":"v11_s26_r50", "year":2050',
                '{"aggregation":"v11_s26_r50", "year":2050}'
            ]
        }

        # Create the DataFrame
        df = pd.DataFrame(data)
        
        # Iterate rows
        for index, row in df.iterrows():
            
            # iterate columns of the row
            for col in df.columns:
                
                # get the value
                value = row[col]
                parsed_value = hb.parse_flex_to_python_object(value)
                
                # print('parsed_value', row, col, value, parsed_value)


if __name__ == "__main__":
    unittest.main()

    