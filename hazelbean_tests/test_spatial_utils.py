from unittest import TestCase
import unittest
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

    def test_get_wkt_from_epsg_code(self):
        hb.get_wkt_from_epsg_code(hb.common_epsg_codes_by_name['robinson'])



    def test_rank_array(self):
        array = np.random.rand(6, 6)
        nan_mask = np.zeros((6, 6))
        nan_mask[1:3, 2:5] = 1
        ranked_array, ranked_pared_keys = hb.get_rank_array_and_keys(array, nan_mask=nan_mask)

        assert (ranked_array[1, 2] == -9999)
        assert (len(ranked_pared_keys[0] == 30))

    def test_create_vector_from_raster_extents(self):
        extent_path = hb.temp('.shp', remove_at_exit=True)
        hb.create_vector_from_raster_extents(self.pyramid_match_900sec_path, extent_path)
        self.assertTrue(os.path.exists(extent_path))

    def test_read_1d_npy_chunk(self):
        r = np.random.randint(2,9,200)
        temp_path = hb.temp('.npy', remove_at_exit=True)
        hb.save_array_as_npy(r, temp_path)
        output = hb.read_1d_npy_chunk(temp_path, 3, 8)
        self.assertTrue(sum(r[3:3+8])==sum(output))

    def test_get_attribute_table_columns_from_shapefile(self):
        r = hb.get_attribute_table_columns_from_shapefile(self.ee_r264_correspondence_vector_path, cols='ee_r264_id')
        self.assertIsNotNone(r)

    def test_extract_features_in_shapefile_by_attribute(self):
        output_gpkg_path = hb.temp('.gpkg', remove_at_exit=True)
        column_name = 'ee_r264_id'
        column_filter = 77

        hb.extract_features_in_shapefile_by_attribute(self.ee_r264_correspondence_vector_path, output_gpkg_path, column_name, column_filter)

    # def test_resample_arrayframe(self):
    #     temp_path = hb.temp('.tif', 'temp_test_resample_array', True)
    #     hb.resample(self.pyramid_match_900sec_path, temp_path, 12)
    #
    #
    # def test_clip_raster_by_vector(self):
    #     temp_path = hb.temp('.tif', 'temp_test_clip_raster_by_vector', True)
    #     hb.clip_raster_by_vector(self.global_1deg_raster_path, temp_path, self.two_polygon_shapefile_path, all_touched=True, ensure_fits=True)
    #     hb.resample(self.pyramid_match_900sec_path, temp_path, 12)
    #


if __name__ == "__main__":
    unittest.main()

