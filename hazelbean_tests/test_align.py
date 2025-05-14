from unittest import TestCase
import os, sys, time

# NOTE Awkward inclusion heere so that I don't have to run the test via a setup config each  time
sys.path.extend(['../..'])

import hazelbean as hb
import pandas as pd
import numpy as np

delete_on_finish = 1


# global_1deg_raster_path = 'data/global_1deg_floats.tif'
# zones_vector_path = "data/countries_iso3.gpkg"
# zone_ids_raster_path = "data/country_ids_300sec.tif"
# ee_r264_ids_900sec_path = "data/ha_per_cell_300sec.tif"



output_dir = 'data'
output_path = hb.temp('.tif', 'resampled', delete_on_finish, output_dir)

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
          
    def test_resample_to_match(self): 

        hb.resample_to_match(self.ee_r264_ids_900sec_path, 
                     self.global_1deg_raster_path, 
                     output_path, 
                     resample_method='near',
                     output_data_type=6, 
                     src_ndv=None, 
                     ndv=None, 
                     compress=True,
                     calc_raster_stats=False,
                     add_overviews=False,
                     pixel_size_override=None)

        output2_path = hb.temp('.tif', 'mask', delete_on_finish, output_dir)
        hb.create_valid_mask_from_vector_path(self.ee_r264_correspondence_vector_path, self.global_1deg_raster_path, output2_path,
                                        all_touched=True)

        # output3_path = hb.temp('.tif', 'masked', delete_on_finish, output_dir)
        # hb.set_ndv_by_mask_path(output_path, output2_path, output_path=output3_path, ndv=-9999.)

    def misc(self):
        input_string = '''0,1,1
        3,2,2
        1,4,1'''
        a = hb.comma_linebreak_string_to_2d_array(input_string)

        a = hb.comma_linebreak_string_to_2d_array(input_string, dtype=np.int8)



        a = np.random.rand(5, 5)
        temp_path = hb.temp('.npy', 'npytest', delete_on_finish, output_dir)

        hb.save_array_as_npy(a, temp_path)
        r = hb.describe(temp_path, surpress_print=True, surpress_logger=True)


        folder_list = ['asdf', 'asdf/qwer']
        hb.create_directories(folder_list)
        hb.remove_dirs(folder_list, safety_check='delete')


        input_dict = {
            'row_1': {'col_1': 1, 'col_2': 2},
            'row_2': {'col_1': 3, 'col_2': 4}
        }

        df = hb.dict_to_df(input_dict)
        generated_dict = hb.df_to_dict(df)
        assert(input_dict == generated_dict)


if __name__ == "__main__":
    import unittest
    unittest.main()


