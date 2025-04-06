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
          
    def test_ProjectFlow(self): 


        p = hb.ProjectFlow('test_project')

        # NOTE, for the task-level logging differentiation to happen, the logger must be assigned to the projectflow object.
        p.L = hb.get_logger('manual_t_project_flow')



        # print(af1)
        def calculation_1(p):
            # global path1
            p.path1 = p.get_path(os.path.join(self.data_dir, "cartographic/ee/ee_r264_ids_900sec.tif"))

            hb.debug('Debug 1')
            hb.log('Info 1')
            p.L.warning('warning 1')
            # p.L.critical('critical 1')

            p.temp_path = hb.temp('.tif', remove_at_exit=True)
            if p.run_this:
                4

        def calculation_2(p):
            hb.debug('Debug 2')
            hb.log('Info 2')
            p.L.warning('warning 2')
            if p.run_this:
                hb.log(p.temp_path)
                af1 = hb.ArrayFrame(p.path1)
                hb.log(af1)



        p.add_task(calculation_1, logging_level=10)
        p.add_task(calculation_2)


        p.execute()

        hb.remove_dirs('test_project', safety_check='delete')




if __name__ == "__main__":
    import unittest
    unittest.main()



