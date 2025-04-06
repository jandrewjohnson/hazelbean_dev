from unittest import TestCase

import os, sys
import hazelbean as hb
import pandas as pd
import numpy as np

delete_on_finish = True
class ArrayFrameTester(TestCase):
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

    def test_arrayframe_load_and_save(self):
        input_array = np.arange(0, 18, 1).reshape((3,6))
        input_uri = hb.temp('.tif', remove_at_exit=True)
        geotransform = hb.calc_cylindrical_geotransform_from_array(input_array)

        projection = 'wgs84'
        ndv = 255
        data_type = 1
        hb.save_array_as_geotiff(input_array, input_uri, geotransform_override=geotransform, projection_override=projection, ndv=ndv, data_type=data_type)

        af = hb.ArrayFrame(input_uri)
        
        
        output_dir = self.data_dir
        output_path = hb.temp('.tif', 'resampled', delete_on_finish, output_dir)

        # Test arraframes and their functions
        temp_path = hb.temp('.tif', 'testing_arrayframe_add', delete_on_finish, output_dir)

        hb.add(self.global_1deg_raster_path, self.global_1deg_raster_path, temp_path)

        temp_path = hb.temp('.tif', 'testing_arrayframe_add', delete_on_finish, output_dir)
        af1 = hb.ArrayFrame(self.global_1deg_raster_path)
        hb.add(af1, af1, temp_path)



if __name__ == "__main__":
    import unittest
    unittest.main()








