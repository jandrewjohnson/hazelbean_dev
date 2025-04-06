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
        self.global_1deg_raster_path = os.path.join(self.pyramid_data_dir, "ha_per_cell_3600sec.tif")        
        self.ee_r264_correspondence_vector_path = os.path.join(self.cartographic_data_dir, "ee_r264_simplified900sec.gpkg")
        self.ee_r264_correspondence_csv_path = os.path.join(self.cartographic_data_dir, "ee_r264_correspondence.csv")        
        self.maize_calories_path = os.path.join(self.data_dir, "crops/johnson/crop_calories/maize_calories_per_ha_masked.tif")
        self.ha_per_cell_column_900sec_path = hb.get_path(hb.ha_per_cell_column_ref_paths[900])
        self.ha_per_cell_900sec_path = hb.get_path(hb.ha_per_cell_ref_paths[900])
        self.pyramid_match_900sec_path = hb.get_path(hb.pyramid_match_ref_paths[900])        

    def tearDown(self):
        pass

    def test_load_geotiff_chunk_by_cr(self):

        hb.load_geotiff_chunk_by_cr_size(self.global_1deg_raster_path, (1, 2, 5, 5))

    def test_load_geotiff_chunk_by_bb(self):
        input_path = self.maize_calories_path
        left_lat = -40
        bottom_lon = -25
        lat_size = .2
        lon_size = 1
        bb = [left_lat,
              bottom_lon,
              left_lat + lat_size,
              bottom_lon + lon_size]
        hb.load_geotiff_chunk_by_bb(input_path, bb)

    def test_add_rows_or_cols_to_geotiff(self):
        incomplete_array = hb.load_geotiff_chunk_by_bb(self.global_1deg_raster_path, [-180, -80, 180, 70])
        temp_path = hb.temp('.tif', 'test_add_rows_or_cols_to_geotiff', True)
        geotransform_override = hb.get_raster_info_hb(self.global_1deg_raster_path)['geotransform']
        geotransform_override = [-180, 1, 0, 80, 0, -1]
        n_rows_override = 150

        hb.save_array_as_geotiff(incomplete_array, temp_path, self.global_1deg_raster_path, geotransform_override=geotransform_override, n_rows_override=n_rows_override)
        temp2_path = hb.temp('.tif', 'test_add_rows_or_cols_to_geotiff', True)
        r_above, r_below, c_above, c_below = 10, 20, 0, 0
        hb.add_rows_or_cols_to_geotiff(temp_path, r_above, r_below, c_above, c_below, remove_temporary_files=True)

    # def test_fill_ndv_to_match_extent(self):
    #
    #     incomplete_array = hb.load_geotiff_chunk_by_bb(self.global_1deg_raster_path, 80, -180, 150, 360)
    #     # TODO Here is an interesting starting point to assess the question of how to generalize AF as flex inputs. For now it is path based.
    #
    #     temp_path = hb.temp('.tif', 'test_add_rows_or_cols_to_geotiff', True)
    #     geotransform_override = hb.get_raster_info_hb(self.global_1deg_raster_path)['geotransform']
    #     geotransform_override = [-180, 1, 0, 80, 0, -1]
    #     n_rows_override = 150
    #
    #     hb.save_array_as_geotiff(incomplete_array, temp_path, self.global_1deg_raster_path, geotransform_override=geotransform_override, n_rows_override=n_rows_override)
    #
    #     temp2_path = hb.temp('.tif', 'expand_to_bounding_box', True)
    #
    #     hb.fill_to_match_extent(temp_path, self.global_1deg_raster_path, None, temp2_path)


    def test_fill_to_match_extent(self):

        incomplete_array = hb.load_geotiff_chunk_by_bb(self.global_1deg_raster_path, [-180, -80, 180, 70])
        # TODO Here is an interesting starting point to assess the question of how to generalize AF as flex inputs. For now it is path based.

        temp_path = hb.temp('.tif', 'test_add_rows_or_cols_to_geotiff', True)
        geotransform_override = hb.get_raster_info_hb(self.global_1deg_raster_path)['geotransform']
        geotransform_override = [-180, 1, 0, 80, 0, -1]
        n_rows_override = 150

        hb.save_array_as_geotiff(incomplete_array, temp_path, self.global_1deg_raster_path, geotransform_override=geotransform_override, n_rows_override=n_rows_override)

        temp2_path = hb.temp('.tif', 'expand_to_bounding_box', True)

        hb.fill_to_match_extent(temp_path, self.global_1deg_raster_path, temp2_path)



    def test_fill_to_match_extent_manual(self):

        incomplete_array = hb.load_geotiff_chunk_by_bb(self.global_1deg_raster_path, [-180, -80, 180, 70])
        # TODO Here is an interesting starting point to assess the question of how to generalize AF as flex inputs. For now it is path based.

        temp_path = hb.temp('.tif', 'test_add_rows_or_cols_to_geotiff', True)
        geotransform_override = hb.get_raster_info_hb(self.global_1deg_raster_path)['geotransform']
        geotransform_override = [-180, 1, 0, 80, 0, -1]
        n_rows_override = 150

        hb.save_array_as_geotiff(incomplete_array, temp_path, self.global_1deg_raster_path, geotransform_override=geotransform_override, n_rows_override=n_rows_override)

        temp2_path = hb.temp('.tif', 'expand_to_bounding_box', True)

        hb.fill_to_match_extent(temp_path, self.global_1deg_raster_path, temp2_path)




    # def test_make_path_global_pyramid(self):
    #     # hb.make_path_global_pyramid(r"C:\Files\Research\hazelbean\hazelbean_dev\tests\data\crop_harvested_area_fraction.tif", verbose=False)
    #     hb.make_path_global_pyramid(self.global_1deg_raster_path, verbose=False)

    ### TAKEN OUT until resample_via_pyramid_overviews works for cogs
    # def test_resample_via_pyramid_overviews(self):

    #     # Remove auxiliary files so that we can test regenerating them.
    #     hb.remove_path(self.maize_calories_path + '.aux.xml')
    #     hb.remove_path(self.maize_calories_path + '.ovr')

    #     # Pyramid resampling only works when there are no NDVs and thus each value is correctly defined (e.g. 0 or 1). For
    #     # testing purposes, just replace all negatives with zero to emulate this.
    #     zero_fix_path = hb.temp(folder=os.path.dirname(self.maize_calories_path), suffix='zero_fix', remove_at_exit=True)
    #     hb.raster_calculator_flex(self.maize_calories_path, lambda x: np.where(x  < 0, 0., x), zero_fix_path)

    #     resampled_path = hb.temp(folder=os.path.dirname(self.maize_calories_path), suffix='test_resample_via_pyramid_overviews', remove_at_exit=True)
    #     hb.make_path_global_pyramid(zero_fix_path, verbose=False)

    #     hb.resample_via_pyramid_overviews(zero_fix_path, 900, resampled_path, overview_resampling_algorithm='bilinear', force_overview_rewrite=True)

    #     input_array = hb.as_array(self.maize_calories_path)
    #     output_array = hb.as_array(resampled_path)

    #     input_sum = np.sum(input_array[input_array>=0])
    #     output_sum = np.sum(output_array) * 9.0

    #     # print ('input_sum', input_sum)
    #     # print ('output_sum', output_sum)

    #     assert(abs(output_sum - input_sum) / output_sum < .00001)

    def test_convert_ndv_to_alpha_band(self):
        output_path = hb.temp(folder=os.path.dirname(self.maize_calories_path), remove_at_exit=True)
        hb.convert_ndv_to_alpha_band(self.maize_calories_path, output_path)



if __name__ == "__main__":
    import unittest
    unittest.main()


