from unittest import TestCase
import os, sys, time

# NOTE Awkward inclusion heere so that I don't have to run the test via a setup config each  time
sys.path.extend(['../..'])

import hazelbean as hb
import pandas as pd
import numpy as np

import hazelbean.raster_vector_interface as raster_vector_interface

L = hb.get_logger('raster_vector_interface')

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

    def test_raster_calculator_hb(self):
        t1 = hb.temp(remove_at_exit=True)
        hb.raster_calculator_hb([(self.ee_r264_ids_900sec_path, 1), (self.ee_r264_ids_900sec_path, 1)], lambda x, y: x + y, t1, 7, -9999)

        # LEARNING POINT, I had to be very careful here with type casting to ensure the summation methods yielded the same.
        a = np.sum(hb.as_array(t1))
        b = np.sum(hb.as_array(self.ee_r264_ids_900sec_path).astype(np.float64)) * np.float64(2.0)

        assert  a == b

    def test_assert_gdal_paths_in_same_projection(self):
        self.assertTrue(
            hb.assert_gdal_paths_in_same_projection([
                self.ee_r264_correspondence_vector_path,
                self.ee_r264_ids_900sec_path,
                self.maize_calories_path,
            ], return_result=True)
        )

        self.assertTrue(
            hb.assert_gdal_paths_in_same_projection([
                self.ee_r264_correspondence_vector_path,
                self.ee_r264_ids_900sec_path,
                self.maize_calories_path,
            ], return_result=True)
        )

    def test_zonal_statistics_faster(self):

        test_results = []
        # Test pgp method
        # start = time.time()
        # results_dict = hb.zonal_statistics_flex(self.ag_30km_change_wgs84_path, self.countries_wgs84_path)
        # test_result = results_dict[60]['sum']
        # test_results.append(test_result)
        # L.info('Time with pgp ' + str(time.time() - start) + ' ' + str(test_result)) # NOTE pgp method starts counting at zero where hb method uses an explicit field name

        # Test with generating the zone_ids_raster
        zone_ids_raster_path = hb.temp('.tif', remove_at_exit=True)

        # start = time.time()
        # results_dict = hb.zonal_statistics_flex(self.ag_30km_change_wgs84_path, self.countries_wgs84_path, zone_ids_raster_path=zone_ids_raster_path, use_iterblocks=False)
        # test_result = results_dict[61]['sum']
        # test_results.append(test_result)
        # L.info('Time without iterblocks without pregenerated raster ' + str(time.time() - start) + ' ' + str(test_result))

        # start = time.time()
        # results_dict = hb.zonal_statistics_flex(self.ag_30km_change_wgs84_path, self.countries_wgs84_path, zone_ids_raster_path=zone_ids_raster_path, use_iterblocks=False)
        # test_result = results_dict[61]['sum']
        # test_results.append(test_result)
        # L.info('Time without iterblocks but using pregenerated ' + str(time.time() - start) + ' ' + str(test_result))

        # Test using the pregenereated
        # id_column_label='OBJECTID',
        start = time.time()
        results_dict = hb.zonal_statistics_flex(self.maize_calories_path, self.ee_r264_correspondence_vector_path,
                                                zone_ids_raster_path=zone_ids_raster_path, verbose=False)
        print('results_dict', results_dict)
        # test_result = results_dict[61]['sum']
        # test_results.append(test_result)
        # L.info('Time with iterblocks ' +str(time.time() - start) + ' ' + str(test_result))

        # Decided not to test equality because PGP has different aggregation logic
        # self.assertEqual(len(set(test_results)), 1)

    def test_zonal_statistics_enumeration(self):

        test_results = []
        zone_ids_raster_path = hb.temp('.tif', remove_at_exit=True)
        # Test using the pregenereated
        start = time.time()
        # id_column_label='OBJECTID'
        results_dict = hb.zonal_statistics_flex(self.ee_r264_ids_900sec_path, self.ee_r264_correspondence_vector_path,
                                                zone_ids_raster_path=zone_ids_raster_path, verbose=False)
        print('results_dict', results_dict)



    def test_super_simplify(self):
        # raster_vector_interface.raster_to_polygon(input_raster_path, output_vector_path, id_label, dissolve_on_id=True)
        input_vector_path = self.ee_r264_correspondence_vector_path
        id_column_label = 'ee_r264_id'
        blur_size = 300.0 
        output_path = 'simplified_vector.gpkg'
        raster_vector_interface.vector_super_simplify(input_vector_path, id_column_label, blur_size, output_path, remove_temp_files=True)



if __name__ == "__main__":
    import unittest
    unittest.main()