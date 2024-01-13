from unittest import TestCase
import os, sys, time

# NOTE Awkward inclusion heere so that I don't have to run the test via a setup config each  time
sys.path.extend(['../..'])

import hazelbean as hb
import pandas as pd
import numpy as np

L = hb.get_logger('raster_vector_interface')

class DataStructuresTester(TestCase):
    def setUp(self):
        self.global_5m_raster_path = 'data/ha_per_cell_5m.tif'
        self.global_1deg_raster_path = 'data/global_1deg_floats.tif'
        self.two_polygon_shapefile_path = 'data/two_poly_wgs84_aoi.shp'
        self.countries_wgs84_zone_ids_path = 'data/countries_wgs84_zone_ids.tif'
        self.ag_30km_change_wgs84_path = 'data/ag_30km_change.tif'
        self.countries_mollweide_path = 'optional_test_data/countries_mollweide.shp'
        self.countries_wgs84_path = 'data/countries_wgs84.shp'
        self.hydrosheds_path = 'data/hybas_af_lev02_v1c.shp'

    def tearDown(self):
        pass

    def test_raster_calculator_hb(self):
        t1 = hb.temp(remove_at_exit=True)
        hb.raster_calculator_hb([(self.global_1deg_raster_path, 1), (self.global_1deg_raster_path, 1)], lambda x, y: x + y, t1, 7, -9999)

        # LEARNING POINT, I had to be very careful here with type casting to ensure the summation methods yielded the same.
        a = np.sum(hb.as_array(t1))
        b = np.sum(hb.as_array(self.global_1deg_raster_path).astype(np.float64)) * np.float64(2.0)

        assert  a == b

    def test_assert_gdal_paths_in_same_projection(self):
        self.assertTrue(
            hb.assert_gdal_paths_in_same_projection([
                self.hydrosheds_path,
                self.global_1deg_raster_path,
                self.ag_30km_change_wgs84_path,
            ], return_result=True)
        )

        self.assertTrue(
            hb.assert_gdal_paths_in_same_projection([
                self.countries_wgs84_path,
                self.global_1deg_raster_path,
                self.ag_30km_change_wgs84_path,
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
        start = time.time()
        results_dict = hb.zonal_statistics_flex(self.ag_30km_change_wgs84_path, self.countries_wgs84_path,
                                                zone_ids_raster_path=zone_ids_raster_path, id_column_label='OBJECTID', verbose=False)
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
        results_dict = hb.zonal_statistics_flex(self.ag_30km_change_wgs84_path, self.countries_wgs84_path,
                                                zone_ids_raster_path=zone_ids_raster_path, id_column_label='OBJECTID', verbose=False)
        print('results_dict', results_dict)
