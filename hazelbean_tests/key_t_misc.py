import hazelbean as hb
import os, sys, time

# NOTE Awkward inclusion heere so that I don't have to run the test via a setup config each  time
sys.path.extend(['../..'])

import hazelbean as hb
import pandas as pd
import numpy as np

delete_on_finish = True

global_1deg_raster_path = 'data/global_1deg_floats.tif'
zones_vector_path = "data/countries_iso3.gpkg"
zone_ids_raster_path = "data/country_ids_300sec.tif"
zone_values_path = "data/ha_per_cell_300sec.tif"

output_dir = 'data'


output_path = hb.temp('.tif', 'resampled', delete_on_finish, output_dir)

# Test arraframes and their functions
temp_path = hb.temp('.tif', 'testing_arrayframe_add', delete_on_finish, output_dir)

hb.add(global_1deg_raster_path, global_1deg_raster_path, temp_path)

temp_path = hb.temp('.tif', 'testing_arrayframe_add', delete_on_finish, output_dir)
af1 = hb.ArrayFrame(global_1deg_raster_path)
hb.add(af1, af1, temp_path)

from hazelbean import cat_ears
assert hb.convert_string_to_implied_type('true') is True
assert hb.convert_string_to_implied_type('FALSE') is False
assert type(hb.convert_string_to_implied_type('0.05')) is float

# assert type(hb.convert_string_to_implied_type('1')) is int
assert not type(hb.convert_string_to_implied_type('1.1a')) is float
assert type(hb.convert_string_to_implied_type('1.1a')) is str

assert cat_ears.parse_to_ce_list('') == ''
assert cat_ears.parse_to_ce_list('a') == 'a'
assert cat_ears.parse_to_ce_list('a<^>b') == ['a', 'b']
assert cat_ears.parse_to_ce_list('a<^>b<^>c') == ['a', 'b', 'c']
# assert str(cat_ears.parse_to_ce_list('1<^>2.0<^>3')) == str([1, 2.0, 3])
assert not str(cat_ears.parse_to_ce_list('1<^>2.0<^>3')) == str([1, 2, 3])
# assert str(cat_ears.parse_to_ce_list('1<^>2<^>3')) == str([1, 2, 3])
assert not str(cat_ears.parse_to_ce_list('1<^>2<^>3')) == str([1, 2.0, 3])
assert (cat_ears.parse_to_ce_list('<^k1^>v1<^k2^>v2')) == [{'k1': 'v1'}, {'k2': 'v2'}]
assert (cat_ears.parse_to_ce_list('asdf<^k1^>v1<^k2^>v2')) == ['asdf', {'k1': 'v1'}, {'k2': 'v2'}]
assert (cat_ears.parse_to_ce_list('asdf<^>asdf2<^>asdf3<^k1^>v1<^k2^>v2<^>asdf4<^>asdf5')) == ['asdf', 'asdf2', 'asdf3', {'k1': 'v1'}, {'k2': 'v2'}, 'asdf4', 'asdf5']

odict_string = 'asdf<^>asdf2<^>asdf3<^k1^>v1<^k2^>v2<^>asdf4<^>asdf5'
assert str(cat_ears.get_combined_list(odict_string)) == str(['asdf', 'asdf2', 'asdf3', 'asdf4', 'asdf5'])
assert str(cat_ears.get_combined_odict(odict_string)) == """OrderedDict([('k1', 'v1'), ('k2', 'v2')])"""
assert str((cat_ears.collapse_ce_list(odict_string))) == """[['asdf', 'asdf2', 'asdf3'], OrderedDict([('k1', 'v1'), ('k2', 'v2')]), ['asdf4', 'asdf5']]"""


input_string = '''0,1,1
3,2,2
1,4,1'''
a = hb.comma_linebreak_string_to_2d_array(input_string)

a = hb.comma_linebreak_string_to_2d_array(input_string, dtype=np.int8)



a = np.random.rand(5, 5)
temp_path = hb.temp('.npy', 'npytest', delete_on_finish, output_dir)

hb.save_array_as_npy(a, temp_path)
r = hb.describe(temp_path, surpress_print=True, surpress_logger=True)


folder_list = ['asdf', 'asdf/qwer']
hb.create_directories(folder_list)
hb.remove_dirs(folder_list, safety_check='delete')


input_dict = {
    'row_1': {'col_1': 1, 'col_2': 2},
    'row_2': {'col_1': 3, 'col_2': 4}
}

df = hb.dict_to_df(input_dict)
generated_dict = hb.df_to_dict(df)
assert(input_dict == generated_dict)





print('Test complete.')
