from unittest import TestCase
import os, sys, time

# NOTE Awkward inclusion heere so that I don't have to run the test via a setup config each  time
sys.path.extend(['../..'])

import hazelbean as hb
import pandas as pd
import numpy as np

class DataStructuresTester(TestCase):
    def setUp(self):
       
        self.data_dir = os.path.join(os.path.dirname(__file__), "../data")
        self.test_data_dir = os.path.join(self.data_dir, "tests")
        self.cartographic_data_dir = os.path.join(self.data_dir, "cartographic/ee")        
        self.pyramid_data_dir = os.path.join(self.data_dir, "pyramids")
        self.ee_r264_ids_900sec_path = os.path.join(self.cartographic_data_dir, "ee_r264_ids_900sec.tif")
        self.ee_r264_correspondence_vector_path = os.path.join(self.cartographic_data_dir, "ee_r264_simplified900sec.gpkg")
        self.ee_r264_correspondence_csv_path = os.path.join(self.cartographic_data_dir, "ee_r264_correspondence.csv")
        
        self.maize_calories_path = os.path.join(self.data_dir, "crops/johnson/crop_calories/maize_calories_per_ha_masked.tif")
        self.ha_per_cell_column_900sec_path = hb.get_path(hb.ha_per_cell_column_ref_paths[900])
        self.ha_per_cell_900sec_path = hb.get_path(hb.ha_per_cell_ref_paths[900])
        self.pyramid_match_900sec_path = hb.get_path(hb.pyramid_match_ref_paths[900])
        
    def tearDown(self):
        pass

    def test_resample_to_cell_size(self):
        output_path = hb.temp('.tif', 'test_resample_to_match', True)
        pixel_size_override = 1.0
        hb.resample_to_match(self.maize_calories_path, self.ee_r264_ids_900sec_path, output_path, resample_method='near',
                             output_data_type=6, src_ndv=None, ndv=None, compress=True,
                             calc_raster_stats=False,
                             add_overviews=False,
                             pixel_size_override=pixel_size_override)

    def test_resample_to_match(self):
        output_path = hb.temp('.tif', 'test_resample_to_match', True)
        hb.resample_to_match(self.maize_calories_path, self.ee_r264_ids_900sec_path, output_path, resample_method='near',
                             output_data_type=6, src_ndv=None, ndv=None, compress=True,
                             calc_raster_stats=False,
                             add_overviews=False,)

        output2_path = hb.temp('.tif', 'mask', True)
        hb.create_valid_mask_from_vector_path(self.ee_r264_correspondence_vector_path, self.ee_r264_ids_900sec_path, output2_path,
                                              all_touched=True)

        output3_path = hb.temp('.tif', 'masked', True)
        hb.set_ndv_by_mask_path(output_path, output2_path, output_path=output3_path, ndv=-9999.)


if __name__ == "__main__":
    import unittest
    unittest.main()

