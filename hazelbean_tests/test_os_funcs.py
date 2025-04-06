from unittest import TestCase
import os, sys
import pandas as pd

from hazelbean.os_utils import *

class DataStructuresTester(TestCase):
    def setUp(self):        
        self.data_dir = os.path.join(os.path.dirname(__file__), "../data")
        self.test_data_dir = os.path.join(self.data_dir, "tests")
        self.cartographic_data_dir = os.path.join(self.data_dir, "cartographic/ee")        
        self.pyramid_data_dir = os.path.join(self.data_dir, "pyramids")
        self.ee_r264_ids_900sec_path = os.path.join(self.cartographic_data_dir, "ee_r264_ids_900sec.tif")
        self.global_1deg_raster_path = os.path.join(self.pyramid_data_dir, "ha_per_cell_3600sec.tif")        
        self.ee_r264_correspondence_vector_path = os.path.join(self.cartographic_data_dir, "ee_r264_simplified900sec.gpkg")
        self.ee_r264_correspondence_csv_path = os.path.join(self.cartographic_data_dir, "ee_r264_correspondence.csv")        
        self.maize_calories_path = os.path.join(self.data_dir, "crops/johnson/crop_calories/maize_calories_per_ha_masked.tif")
        self.ha_per_cell_column_900sec_path = hb.get_path(hb.ha_per_cell_column_ref_paths[900])
        self.ha_per_cell_900sec_path = hb.get_path(hb.ha_per_cell_ref_paths[900])
        self.pyramid_match_900sec_path = hb.get_path(hb.pyramid_match_ref_paths[900])      
    
    def test_misc(self):
        input_dict = {
            'row_1': {'col_1': 1, 'col_2': 2},
            'row_2': {'col_1': 3, 'col_2': 4}
        }

        df = hb.dict_to_df(input_dict)
        generated_dict = hb.df_to_dict(df)
        assert(input_dict == generated_dict)


        run_all = True
        test_this = 0
        if test_this or run_all:
            input_dict = {
                'row_1': {'col_1': 1, 'col_2': 2},
                'row_2': {'col_1': 3, 'col_2': 4}
            }
            df = hb.dict_to_df(input_dict)
            hb.df_to_dict(df)

            print(df)
            print('Test complete.')
        test_this = 1
        if test_this or run_all:
            input_dict = {
                'row_1': {
                    'col_1': 1,
                    'col_2': 2,
                },
                'row_2': {
                    'col_1': 3,
                    'col_2': {
                        'third_dict': {
                            'this': 'this_value',
                            'that': 3,
                            'thee other': 2,
                        },
                    },
                },
                'empty_dict_row': {
                },
                'empty_list': [],
                'single_list': [
                    5, 'this', 44,
                ],
                'outer_dict': {
                    'mid_dict': {
                        'inner1': [
                            1, 2, 3
                        ],
                        'inner2': [
                            4, 5, 6,
                        ],
                    }
                },
                '2d_lists': 
                    [
                        [
                            1, 2, 3,
                        ],
                        [7, 8, 9,]
                    ],
                'empty': '',
                
            }

            a = hb.describe_iterable(input_dict)
            expected_len = 840
            
            # assert a == input_dict
            b = hb.print_iterable(input_dict)

            # if len(b) != expected_len:
            #     raise NameError('print_iterable FAILED ITS TEST!')
            
            input_str = 'tricky_string'
            a = hb.describe_iterable(input_str)
            # assert a == input_dict
            b = hb.print_iterable(input_str)



