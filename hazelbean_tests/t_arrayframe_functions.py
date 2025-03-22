from unittest import TestCase
import os, sys, time

# NOTE Awkward inclusion heere so that I don't have to run the test via a setup config each  time
sys.path.extend(['../..'])

import hazelbean as hb
import pandas as pd
import numpy as np

class DataStructuresTester(TestCase):
    def setUp(self):
        self.global_5m_raster_path = 'data/ha_per_cell_5m.tif'
        self.global_1deg_raster_path = 'data/global_1deg_floats.tif'
        # self.global_1deg_raster_path = 'data/global_1deg_floats.tif'

    def tearDown(self):
        pass

    def test_arrayframe_add(self):
        temp_path = hb.temp('.tif', 'testing_arrayframe_add', True)
        hb.add(self.global_1deg_raster_path, self.global_1deg_raster_path, temp_path)
        temp_path = hb.temp('.tif', 'testing_arrayframe_add', True)
        af1 = hb.ArrayFrame(self.global_1deg_raster_path)
        hb.add(af1, af1, temp_path)
