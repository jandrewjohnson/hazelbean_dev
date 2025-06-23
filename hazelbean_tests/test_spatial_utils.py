from unittest import TestCase
import unittest
import os, sys, time

# NOTE Awkward inclusion heere so that I don't have to run the test via a setup config each  time
sys.path.extend(['../..'])

import hazelbean as hb
import pandas as pd
import numpy as np

delete_on_finish = True

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
        self.global_1deg_raster_path = os.path.join(self.pyramid_data_dir, "ha_per_cell_3600sec.tif")
        user_dir = os.path.expanduser("~")
        self.output_dir = os.path.join(user_dir, "temp")
        
    def tearDown(self):
        pass

    def test_get_wkt_from_epsg_code(self):
        hb.get_wkt_from_epsg_code(hb.common_epsg_codes_by_name['wgs84'])
        # hb.get_wkt_from_epsg_code(hb.common_epsg_codes_by_name['robinson'])



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

    def test_get_bounding_box(self):
        zones_vector_path = self.ee_r264_correspondence_vector_path
        zone_ids_raster_path = self.ee_r264_ids_900sec_path
        zone_values_path = self.ha_per_cell_900sec_path

        run_all = 0
        remove_temporary_files = 1
        output_dir = self.test_data_dir


        # Test getting a Bounding Box of a raster
        bb = hb.get_bounding_box(self.global_1deg_raster_path)
        print(bb)

        # Test getting a Bounding Box of a vector
        bb = hb.get_bounding_box(zones_vector_path)
        print(bb)

        # Create a new GPKG for just the country of RWA
        rwa_vector_path = hb.temp('.gpkg', 'rwa', remove_temporary_files, output_dir)
        hb.extract_features_in_shapefile_by_attribute(zones_vector_path, rwa_vector_path, "ee_r264_id", 70)

        # Get the bounding box of that new vector
        bb = hb.get_bounding_box(rwa_vector_path)
        print(bb)

        # Try again with a different one

        # LEARNING POINT: When pasting a windows path, you get BACKSLASHES
        # VS Code has a fast way to replace all backslashes with forward slashes
        # Highlight one of the backslashes and then press CTRL + SHIFT + L
        # This will highlight all instances of that character in the file.
        # Then you can just type a forward slash and it will replace all of them
        

    
    # TEST auto downloading of files via get_path
    def test_reading_csvs(self):
        
        # Test that it does find a path that exists 
        p = hb.ProjectFlow(self.output_dir)
        p.base_data_dir = '../../../base_data'
        
        # You can put the api credentials anywhere in the folder structure. Preferred is at the root of base data.
            
        p.data_credentials_path = None
        p.input_bucket_name = 'gtap_invest_seals_2023_04_21'
        
        test_path = p.get_path('cartographic/gadm/gadm_410_adm0_labels_test.csv', verbose=True)
        df = pd.read_csv(test_path)
        assert len(df) > 0
        hb.remove_path(test_path)
        
        # Now try it WITH credentials
        p.data_credentials_path = p.get_path('api_key_credentials.json')
        test_path = p.get_path('cartographic/gadm/gadm_410_adm0_labels_test.csv', verbose=True)
        df = pd.read_csv(test_path)
        assert len(df) > 0
        hb.remove_path(test_path)        
        
        

    # TEST get_reclassification_dict_from_df
    def test_get_reclassification_dict_from_df(self):
        # Test that it does find a path that exists 
        p = hb.ProjectFlow(self.output_dir)
        p.base_data_dir = '../../../base_data'
        
        correspondence_path = p.get_path(os.path.join(self.data_dir, 'cartographic', 'ee', 'ee_r264_correspondence.csv'))
        from hazelbean import utils
        
        # TODO This should be extended to cover classifcation dicts from correspondences but also structured and unstructured mappings.
        r = utils.get_reclassification_dict_from_df(correspondence_path, 'gtapv7_r160_id', 'gtapv7_r50_id', 'gtapv7_r160_label', 'gtapv7_r50_label')
        
        hb.print_iterable(r)
        
    
    def test_clipping_simple(self):
        global_1deg_raster_path = 'data/global_1deg_floats.tif'
        zones_vector_path = "data/countries_iso3.gpkg"
        country_vector_path = "data/rwa.gpkg"
        zone_ids_raster_path = "data/country_ids_300sec.tif"
        zone_values_path = "data/ha_per_cell_300sec.tif"

        output_dir = 'data'
        output_path = hb.temp('.tif', 'clipped', delete_on_finish, self.output_dir)

        hb.clip_raster_by_vector_simple(self.ee_r264_ids_900sec_path, 
                                        output_path, 
                                        self.ee_r264_correspondence_vector_path, 
                                        output_data_type=6, 
                                        gtiff_creation_options=hb.DEFAULT_GTIFF_CREATION_OPTIONS)

        print('Created', output_path)


        output_path = hb.temp('.tif', 'clipped_attr', delete_on_finish, output_dir)

        hb.clip_raster_by_vector_simple(self.ee_r264_ids_900sec_path, 
                                        output_path, 
                                        self.ee_r264_correspondence_vector_path, 
                                        output_data_type=6, 
                                        clip_vector_filter='ee_r264_id="120"',
                                        
                                        gtiff_creation_options=hb.DEFAULT_GTIFF_CREATION_OPTIONS)

        print('Created', output_path)
    
            # hb.clip_raster_by_vector_simple(zone_values_path, 
            #                                  output_path, 
            #                                  zones_vector_path, 
            #                                  output_data_type=6, 
            #                                  clip_vector_filter='ISO3="RWA"',
            #                                  
            #                                  gtiff_creation_options=hb.DEFAULT_GTIFF_CREATION_OPTIONS)
            # 
            # print('Created', output_path)

    def test_reclassify_raster_hb(self):
        # input_flex, rules, output_path, output_data_type=None, array_threshold=10000, match_path=None, output_ndv=None, invoke_full_callback=False, verbose=False):
        # self.data_dir = os.path.join(os.path.dirname(__file__), "../data")
        # self.test_data_dir = os.path.join(self.data_dir, "tests")
        # self.cartographic_data_dir = os.path.join(self.data_dir, "cartographic/ee")        
        # self.pyramid_data_dir = os.path.join(self.data_dir, "pyramids")
        # self.ee_r264_ids_900sec_path = os.path.join(self.cartographic_data_dir, "ee_r264_ids_900sec.tif")
        # self.ee_r264_correspondence_vector_path = os.path.join(self.cartographic_data_dir, "ee_r264_simplified900sec.gpkg")
        # self.ee_r264_correspondence_csv_path = os.path.join(self.cartographic_data_dir, "ee_r264_correspondence.csv")
        
        # self.maize_calories_path = os.path.join(self.data_dir, "crops/johnson/crop_calories/maize_calories_per_ha_masked.tif")
        # self.ha_per_cell_column_900sec_path = hb.get_path(hb.ha_per_cell_column_ref_paths[900])
        # self.ha_per_cell_900sec_path = hb.get_path(hb.ha_per_cell_ref_paths[900])
        # self.pyramid_match_900sec_path = hb.get_path(hb.pyramid_match_ref_paths[900])
        # self.global_1deg_raster_path = os.path.join(self.pyramid_data_dir, "ha_per_cell_3600sec.tif")
        # user_dir = os.path.expanduser("~")
        # self.output_dir = os.path.join(user_dir, "temp")     
        # rules = {241: 33}   
        rules = {235: 34}   
        output_path = hb.temp('.tif', 'reclassify', True, self.output_dir)
        # output_path = hb.temp('.tif', 'reclassify', delete_on_finish, self.output_dir)
        hb.reclassify_raster_hb(self.ee_r264_ids_900sec_path, 
                                rules,
                                output_path, 
                                # output_data_type=6, 
                                # array_threshold=10000, 
                                # match_path=self.ha_per_cell_900sec_path, 
                                # output_ndv=-9999, 
                                # invoke_full_callback=False, 
                                # verbose=True
                                )
        
        
    def test_reclassify_raster_with_negatives_hb(self):

        rules = {235: -555}   
        output_path = hb.temp('.tif', 'reclassify', False, self.output_dir)
        # output_path = hb.temp('.tif', 'reclassify', delete_on_finish, self.output_dir)
        hb.reclassify_raster_hb(self.ee_r264_ids_900sec_path, 
                                rules,
                                output_path, 
                                output_data_type=5, 
                                # array_threshold=10000, 
                                # match_path=self.ha_per_cell_900sec_path, 
                                # output_ndv=-9999, 
                                # invoke_full_callback=False, 
                                # verbose=True
                                )
        
        print(hb.enumerate_raster_path(output_path))
                
        output_with_neg_path = hb.temp('.tif', 'reclassify_with_neg', False, self.output_dir)
        # output_path = hb.temp('.tif', 'reclassify', delete_on_finish, self.output_dir)
        
        rules = {
            235: -444,
            241: -9999,
            -555: -888,
            }  # Adding a rule for 241 to be reclassified to -9999
        
        
        hb.reclassify_raster_hb(output_path, 
                                rules,
                                output_with_neg_path, 
                                output_data_type=5, 
                                # array_threshold=10000, 
                                # match_path=self.ha_per_cell_900sec_path, 
                                # output_ndv=-9999, 
                                # invoke_full_callback=False, 
                                # verbose=True
                                )
        
        print(hb.enumerate_raster_path(output_with_neg_path))
        
        5
                

    def test_reclassify_raster_arrayframe(self):
        # input_flex, rules, output_path, output_data_type=None, array_threshold=10000, match_path=None, output_ndv=None, invoke_full_callback=False, verbose=False):
        # self.data_dir = os.path.join(os.path.dirname(__file__), "../data")
        # self.test_data_dir = os.path.join(self.data_dir, "tests")
        # self.cartographic_data_dir = os.path.join(self.data_dir, "cartographic/ee")        
        # self.pyramid_data_dir = os.path.join(self.data_dir, "pyramids")
        # self.ee_r264_ids_900sec_path = os.path.join(self.cartographic_data_dir, "ee_r264_ids_900sec.tif")
        # self.ee_r264_correspondence_vector_path = os.path.join(self.cartographic_data_dir, "ee_r264_simplified900sec.gpkg")
        # self.ee_r264_correspondence_csv_path = os.path.join(self.cartographic_data_dir, "ee_r264_correspondence.csv")
        
        # self.maize_calories_path = os.path.join(self.data_dir, "crops/johnson/crop_calories/maize_calories_per_ha_masked.tif")
        # self.ha_per_cell_column_900sec_path = hb.get_path(hb.ha_per_cell_column_ref_paths[900])
        # self.ha_per_cell_900sec_path = hb.get_path(hb.ha_per_cell_ref_paths[900])
        # self.pyramid_match_900sec_path = hb.get_path(hb.pyramid_match_ref_paths[900])
        # self.global_1deg_raster_path = os.path.join(self.pyramid_data_dir, "ha_per_cell_3600sec.tif")
        # user_dir = os.path.expanduser("~")
        # self.output_dir = os.path.join(user_dir, "temp")     
        # rules = {241: 33}   
        rules = {235: 34}   
        output_path = hb.temp('.tif', 'reclassify', True, self.output_dir)
        # output_path = hb.temp('.tif', 'reclassify', delete_on_finish, self.output_dir)
        hb.reclassify_raster_arrayframe(self.ee_r264_ids_900sec_path, 
                                rules,
                                output_path, 
                                # output_data_type=6, 
                                # array_threshold=10000, 
                                # match_path=self.ha_per_cell_900sec_path, 
                                # output_ndv=-9999, 
                                # invoke_full_callback=False, 
                                # verbose=True
                                )
        
        
if __name__ == "__main__":
    unittest.main()

