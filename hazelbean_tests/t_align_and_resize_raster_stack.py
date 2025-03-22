from unittest import TestCase
from osgeo import gdal
import os, sys

sys.path.insert(0, '..') #
import hazelbean as hb
from pygeoprocessing.geoprocessing import get_raster_info, align_and_resize_raster_stack


class TestAlign_and_resize_raster_stack(TestCase):
    def setUp(self):
        self.global_floats_path = os.path.join(hb.TEST_DATA_DIR, 'ag_30km_change.tif')
        self.two_poly_eckert_iv_aoi_path = os.path.join(hb.TEST_DATA_DIR, 'two_poly_eckert_iv_aoi.shp')
        self.two_poly_wgs84_aoi_path = os.path.join(hb.TEST_DATA_DIR, 'two_poly_wgs84_aoi.shp')

    def test_align_and_resize_raster_stack_ensuring_fit(self):
        base_raster_path_list = [self.global_floats_path]
        target_raster_path_list = [hb.temp('.tif', 'clip1', True)]
        resample_method_list = ['bilinear']
        target_pixel_size = get_raster_info(self.global_floats_path)['pixel_size']
        bounding_box_mode = 'intersection'
        base_vector_path_list = [self.two_poly_wgs84_aoi_path]
        raster_align_index = 0


        hb.align_and_resize_raster_stack_ensuring_fit(
            base_raster_path_list, target_raster_path_list, resample_method_list,
            target_pixel_size, bounding_box_mode, base_vector_path_list=base_vector_path_list,
            raster_align_index=raster_align_index, all_touched=True,
            gtiff_creation_options=hb.DEFAULT_GTIFF_CREATION_OPTIONS)

        # os.remove(target_raster_path_list[0])
        # self.fail()


