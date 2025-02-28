from unittest import TestCase
import os, sys, time

# NOTE Awkward inclusion heere so that I don't have to run the test via a setup config each  time
sys.path.extend(['../..'])

import hazelbean as hb
import pandas as pd
import numpy as np

class DataStructuresTester(TestCase):
    def setUp(self):
        self.global_15m_floats_path = 'data/ag_30km_change.tif'
        self.global_1deg_raster_path = 'data/global_1deg_floats.tif'
        self.two_polygon_shapefile_path = 'data/two_poly_wgs84_aoi.shp'

    def tearDown(self):
        pass

    def test_get_wkt_from_epsg_code(self):
        hb.get_wkt_from_epsg_code(hb.common_epsg_codes_by_name['robinson'])

    # def test_reclassify_int_by_dict(self):
    #
    #     a = np.random.randint(1, 7, (32, 32)).astype(np.float)
    #
    #     rules= {
    #         2: 23,
    #         # 3: 23,
    #         # 4: 24,
    #         # 5: 25,
    #         # 6: 26,
    #         # 7: 27,
    #     }
    #
    #     temp_path = hb.temp('.tif', remove_at_exit=True)
    #
    #     b = hb.reclassify_raster_hb(a, rules, temp_path)
    #     self.assertIsInstance(b, np.ndarray)

    def test_rank_array(self):
        array = np.random.rand(6, 6)
        nan_mask = np.zeros((6, 6))
        nan_mask[1:3, 2:5] = 1
        ranked_array, ranked_pared_keys = hb.get_rank_array_and_keys(array, nan_mask=nan_mask)

        assert (ranked_array[1, 2] == -9999)
        assert (len(ranked_pared_keys[0] == 30))

    def test_create_vector_from_raster_extents(self):
        extent_path = hb.temp('.shp', remove_at_exit=True)
        hb.create_vector_from_raster_extents(self.global_15m_floats_path, extent_path)
        self.assertTrue(os.path.exists(extent_path))

    def test_read_1d_npy_chunk(self):
        path = r"C:\temp\_20180327_144427_046hh9\allocate_all_sectors\bau\sector_change_lists.npy"

        r = np.random.randint(2,9,200)
        temp_path = hb.temp('.npy', remove_at_exit=True)
        hb.save_array_as_npy(r, temp_path)
        output = hb.read_1d_npy_chunk(temp_path, 3, 8)

        self.assertTrue(sum(r[3:3+8])==sum(output))

    def test_read_2d_npy_chunk(self):
        pass
        # path = r"C:\temp\_20180327_144427_046hh9\allocate_all_sectors\bau\sector_proportion_allocated_lists.npy"
        #
        # # r = hb.load_npy_as_array(path)
        # output = hb.read_2d_npy_chunk(path, 3, 1, 8)
        #
        # self.assertEqual(len(output), 8)

        # self.assertTrue(sum(r[3:3+8])==sum(output))

    def test_read_3d_npy_chunk(self):
        # path = r"C:\temp\_20180327_144427_046hh9\allocate_all_sectors\bau\sector_change_lists.npy"
        #
        # d1_index = 0
        # d2_index = 1
        # d3_start = 33
        # d3_end = 444
        # output1 = hb.read_3d_npy_chunk(path, d1_index, d2_index, d3_start, d3_end)
        #
        # self.assertIsInstance(output1, np.ndarray)
        pass

    def test_get_attribute_table_columns_from_shapefile(self):
        shapefile_path = 'data/two_poly_wgs84_aoi.shp'
        r = hb.get_attribute_table_columns_from_shapefile(shapefile_path, cols='adm1_code')
        self.assertIsNotNone(r)

    def test_extract_features_in_shapefile_by_attribute(self):
        input_shp_uri = 'data/two_poly_wgs84_aoi.shp'
        output_shp_uri = hb.temp('.shp', remove_at_exit=True)
        column_name = 'adm1_code'
        column_filter = 'NLD-903'

        hb.extract_features_in_shapefile_by_attribute(input_shp_uri, output_shp_uri, column_name, column_filter)

    # def test_resample_arrayframe(self):
    #     temp_path = hb.temp('.tif', 'temp_test_resample_array', True)
    #     hb.resample(self.global_15m_floats_path, temp_path, 12)
    #
    #
    # def test_clip_raster_by_vector(self):
    #     temp_path = hb.temp('.tif', 'temp_test_clip_raster_by_vector', True)
    #     hb.clip_raster_by_vector(self.global_1deg_raster_path, temp_path, self.two_polygon_shapefile_path, all_touched=True, ensure_fits=True)
    #     hb.resample(self.global_15m_floats_path, temp_path, 12)
    #

