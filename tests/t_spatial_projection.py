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
        self.global_countries_wgs84_path = r"data\countries_wgs84.shp"

    def tearDown(self):
        pass

    def test_resample_to_cell_size(self):
        output_path = hb.temp('.tif', 'test_resample_to_match', True)
        pixel_size_override = 1.0
        hb.resample_to_match(self.global_15m_floats_path, self.global_15m_floats_path, output_path, resample_method='near',
                             output_data_type=6, src_ndv=None, ndv=None, compress=True,
                             calc_raster_stats=False,
                             add_overviews=False,
                             pixel_size_override=pixel_size_override)

    def test_resample_to_match(self):
        output_path = hb.temp('.tif', 'test_resample_to_match', True)
        hb.resample_to_match(self.global_15m_floats_path, self.global_1deg_raster_path, output_path, resample_method='near',
                             output_data_type=6, src_ndv=None, ndv=None, compress=True,
                             calc_raster_stats=False,
                             add_overviews=False,)

        output2_path = hb.temp('.tif', 'mask', True)
        hb.create_valid_mask_from_vector_path(self.global_countries_wgs84_path, self.global_1deg_raster_path, output2_path,
                                              all_touched=True)

        output3_path = hb.temp('.tif', 'masked', True)
        hb.set_ndv_by_mask_path(output_path, output2_path, output_path=output3_path, ndv=-9999.)

