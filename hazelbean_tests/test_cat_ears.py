# coding=utf-8
import unittest
import os, sys, warnings
from collections import OrderedDict
import hazelbean as hb

class CatEarsTester(unittest.TestCase):

    def test_basics(self):
        assert hb.convert_string_to_implied_type('true') is True
        assert hb.convert_string_to_implied_type('FALSE') is False
        assert type(hb.convert_string_to_implied_type('0.05')) is float
        print(hb.convert_string_to_implied_type('1'))
        # assert type(hb.convert_string_to_implied_type('1')) is int
        assert not type(hb.convert_string_to_implied_type('1.1a')) is float
        assert type(hb.convert_string_to_implied_type('1.1a')) is str

        assert hb.cat_ears.parse_to_ce_list('') == ''
        assert hb.cat_ears.parse_to_ce_list('a') == 'a'
        assert hb.cat_ears.parse_to_ce_list('a<^>b') == ['a', 'b']
        assert hb.cat_ears.parse_to_ce_list('a<^>b<^>c') == ['a', 'b', 'c']
        # assert str(hb.cat_ears.parse_to_ce_list('1<^>2.0<^>3')) == str([1, 2.0, 3])
        assert not str(hb.cat_ears.parse_to_ce_list('1<^>2.0<^>3')) == str([1, 2, 3])
        # assert str(hb.cat_ears.parse_to_ce_list('1<^>2<^>3')) == str([1, 2, 3])
        assert not str(hb.cat_ears.parse_to_ce_list('1<^>2<^>3')) == str([1, 2.0, 3])
        assert (hb.cat_ears.parse_to_ce_list('<^k1^>v1<^k2^>v2')) == [{'k1': 'v1'}, {'k2': 'v2'}]
        assert (hb.cat_ears.parse_to_ce_list('asdf<^k1^>v1<^k2^>v2')) == ['asdf', {'k1': 'v1'}, {'k2': 'v2'}]
        assert (hb.cat_ears.parse_to_ce_list('asdf<^>asdf2<^>asdf3<^k1^>v1<^k2^>v2<^>asdf4<^>asdf5')) == ['asdf', 'asdf2', 'asdf3', {'k1': 'v1'}, {'k2': 'v2'}, 'asdf4', 'asdf5']

        odict_string = 'asdf<^>asdf2<^>asdf3<^k1^>v1<^k2^>v2<^>asdf4<^>asdf5'
        assert str(hb.cat_ears.get_combined_list(odict_string)) == str(['asdf', 'asdf2', 'asdf3', 'asdf4', 'asdf5'])
        # a = str(hb.cat_ears.get_combined_odict(odict_string))
        # assert str(hb.cat_ears.get_combined_odict(odict_string)) == """OrderedDict({'k1': 'v1', 'k2': 'v2'})"""
        # assert str((hb.cat_ears.collapse_ce_list(odict_string))) == """[['asdf', 'asdf2', 'asdf3'], OrderedDict([('k1', 'v1'), ('k2', 'v2')]), ['asdf4', 'asdf5']]"""

    def test_make_and_remove_folders(self):
        folder_list = ['asdf', 'asdf/qwer']
        hb.create_directories(folder_list)
        hb.remove_dirs(folder_list, safety_check='delete')

    def test_list_dirs_in_dir_recursively(self):
        # warnings.warn('This will show up. Print will note')
        first_drive = hb.list_mounted_drive_paths()[0]
        first_folder = os.listdir(first_drive)[1]
        path = os.path.join(first_drive, first_folder)
        a = hb.list_dirs_in_dir_recursively(path, max_folders_analyzed=33)

