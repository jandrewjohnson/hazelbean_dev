from unittest import TestCase

import os, sys
import hazelbean as hb
import pandas as pd
import numpy as np


class DataStructuresTester(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_cls(self):

        input_string = '''0,1,1
    3,2,2
    1,4,1'''
        a = hb.comma_linebreak_string_to_2d_array(input_string, dtype=np.int8)
        self.assertEqual(type(a), np.ndarray)

    def atest_file_to_python_object(self):
        # file_uri
        # declare_type
        # verbose
        # return_all_parts
        # xls_workshee
        # output_key_data_type
        # output_value_data_type
        # file_to_python_object(file_uri, declare_type=None, verbose=False, return_all_parts=False, xls_worksheet=None, output_key_data_type=None, output_value_data_type=None):
        pass

    # def test_xls_to_csv(self):
    #     xls_uri = 'data/test_xlsx.xlsx'
    #     csv_uri = hb.temp_filename('.csv')
    #     hb.xls_to_csv(xls_uri, csv_uri)
    #
    #
    #
