from unittest import TestCase
import os, sys
import pandas as pd

from hazelbean.os_utils import *



folder_list = ['asdf', 'asdf/qwer']
hb.create_directories(folder_list)
remove_dirs(folder_list, safety_check='delete')


input_dict = {
    'row_1': {'col_1': 1, 'col_2': 2},
    'row_2': {'col_1': 3, 'col_2': 4}
}

df = hb.dict_to_df(input_dict)
generated_dict = hb.df_to_dict(df)
assert(input_dict == generated_dict)


print('test_os_funcs_complete')