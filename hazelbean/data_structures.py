import os, sys, json, math, random
from collections import OrderedDict
import logging
import xlrd
import numpy as np
import pandas as pd

from pprint import pprint as pp
# import nose
import markdown
import yaml
import csv

import hazelbean as hb
from hazelbean import config

# import numdal as nd
# import hazelbean as hb
# from hazelbean.data_structures

goals = """
Build robust pobject(dict, list, string, odict)-csv-json-markdown-yaml-xml converter,
Use recursive function to make generate_example_nested_odict complex at deeper levels.
"""


#index_synonyms = config.index_synonyms
index_synonyms = ['', 'name', 'names', 'unique_name', 'unique_names', 'index', 'indices', 'id', 'ids', 'var_name', 'var_names']




def xls_to_csv(xls_uri, csv_uri, xls_worksheet=None):
    wb = xlrd.open_workbook(xls_uri)
    if xls_worksheet:
        if isinstance(xls_worksheet, str):
            sh = wb.sheet_by_name(xls_worksheet)
        elif isinstance(xls_worksheet, int) or isinstance(xls_worksheet, float):
            sh = wb.sheet_by_index(xls_worksheet)
        else:
            raise NameError("file_to_python_object given unimplemented xls worksheet type")
    else:
        # Assume it's just the first sheet
        sh = wb.sheet_by_index(0)
    csv_file = open(csv_uri, 'w', newline='') # Python 2 version had 'wb' to avoid extra lines written. see http://stackoverflow.com/questions/3348460/csv-file-written-with-python-has-blank-lines-between-each-row
    wr = csv.writer(csv_file, quoting=csv.QUOTE_NONE, escapechar='\\') #  quoting=csv.QUOTE_ALL
    for rownum in range(sh.nrows):
        wr.writerow(sh.row_values(rownum))
    csv_file.close()

def crop_csv_to_rect(csv_uri, data_rect):
    # Data rect is [ul row, ul col, n_rows, n_cols]
    # -1 means no limit
    for n,i in enumerate(data_rect):
        if i == -1:
            data_rect[n] = hb.config.MAX_IN_MEMORY_ARRAY_SIZE

    new_rows = []
    with open(csv_uri, 'r', newline='') as f:

        reader = csv.reader(f)
        row_id = 0
        for row in reader:
            if data_rect[0] <= row_id <= data_rect[0] + data_rect[2]:
                new_row = row[data_rect[1]: data_rect[1] + data_rect[3]]
                new_rows.append(new_row)
            row_id += 1

    with open(csv_uri, 'w', newline='') as f:
        # Overwrite the old file with the modified rows
        writer = csv.writer(f)
        writer.writerows(new_rows)


def get_strings_between_values(input_string, value_1, value_2):
    """
    Get 
    :param input_string: 
    :param value_1: 
    :param value_2: 
    :return: 
    """

    strings = []
    while 1:
        r = input_string.split(value_1, 1)

        if len(r) > 1:
            r2 = r[1].split(value_2, 1)
            if len(r2) > 1:
                strings.append(r2[0])
                input_string = r2[1]
        else:
            break

    return strings



def file_to_python_object(file_uri, declare_type=None, verbose=False, return_all_parts=False, xls_worksheet=None, output_key_data_type=None, output_value_data_type=None):
    """
    Version that follows the simple rule of if the UL cell is blank its a DD. Else LL

    """
    if not output_value_data_type:
        output_value_data_type = str

    if not output_key_data_type:
        output_key_data_type = str

    def cast_type(input, data_type):
        if data_type is str:
            return str(input)
        elif data_type is int:
            try:
                return int(input)
            except:
                return int(float(input))
        elif data_type is float:
            return float(input)

    file_extension = None

    if os.path.exists(file_uri):
        (file_path, file_extension) = os.path.splitext(file_uri)
        (folder, file_name) = os.path.split(file_path)
    else:
        raise NameError('File given to file_to_python_object does not exist: ' + file_uri)

    if file_extension == '.json':
        json_data=open(file_uri).read()
        data = json.loads(json_data)
        return data

    elif file_extension == '.xls' or file_extension == '.xlsx':
        # If XLS, convert to a temporary csv.
        tmp_csv_uri = os.path.join(folder, file_name + '_tmp_' + hb.pretty_time() + '.csv')
        hb.remove_uri_at_exit(tmp_csv_uri)
        xls_to_csv(file_uri, tmp_csv_uri, xls_worksheet=xls_worksheet)
        file_uri = tmp_csv_uri

    data_type, num_rows, num_cols = determine_data_type_and_dimensions_from_uri(file_uri)

    if declare_type:
        data_type = declare_type

    row_headers = []
    col_headers = []

    data = None
    if data_type == 'singleton':
        with open(file_uri, 'r') as f:
            for row in f:
                split_row = row.replace('\n', '').split(',')
        data = cast_type(split_row[0], output_value_data_type)
    elif data_type == 'L':
        data = []
        with open(file_uri, 'r') as f:
            for row in f:
                split_row = row.replace('\n','').split(',')
                data.append(cast_type(split_row[0], output_value_data_type))
    elif data_type == 'D':
        data = OrderedDict()
        with open(file_uri, 'r') as f:
            for row in f:
                split_row = row.replace('\n','').split(',')
                data[cast_type(split_row[0], output_key_data_type)] = cast_type(split_row[1], output_value_data_type)
    elif data_type == 'DD':
        data = OrderedDict()
        first_row = True
        with open(file_uri, 'r') as f:
            for row in f:
                split_row = row.replace('\n','').split(',')
                if first_row:
                    col_headers = [cast_type(i, output_key_data_type) for i in split_row[1:]]
                    first_row = False
                else:
                    row_odict = OrderedDict()
                    row_headers.append(cast_type(split_row[0], output_key_data_type))
                    for col_header_index in range(len(col_headers)):
                        row_odict[col_headers[col_header_index]] = cast_type(split_row[col_header_index + 1], output_value_data_type) # Plus 1 because the first in the split_row is the row_header
                    data[cast_type(split_row[0], output_key_data_type)] = row_odict
    elif data_type == 'LL':
        data = []
        blank_ul = False
        first_row = True
        with open(file_uri, 'r') as f:
            for row in f:
                if first_row:
                    if row.split(',')[0] in index_synonyms:
                        blank_ul = True

                if blank_ul:
                    if not first_row:
                        split_row = row.replace('\n', '').split(',')
                        data.append([cast_type(i, output_value_data_type) for i in split_row[1:]])
                else:
                    split_row = row.replace('\n', '').split(',')
                    data.append([cast_type(i, output_value_data_type) for i in split_row])

                first_row = False

    else:
        raise NameError('Unable to load file ' + file_uri + ' because datatype could not be determined from the file contents.')
    metadata = OrderedDict()
    metadata.update({'data_type':data_type,'num_rows':num_rows, 'num_cols':num_cols, 'row_headers':row_headers, 'col_headers':col_headers})

    if verbose:
        print ('\nReading file at ' + file_uri)
        print ('data_type: ' + data_type + ',  shape: num_rows ' + str(num_rows) + ', num_cols ' + str(num_cols))
        print ('col_headers: ' + ', '.join(col_headers))
        print ('row_headers: ' + ', '.join(row_headers))
        print ('python object loaded (next line):')
        print (data)

    if return_all_parts:
        return data, metadata
    else:
        return data

def determine_data_type_and_dimensions_from_uri(file_uri):
    """
    Inspects a file of type to determine what the dimensions of the data are and make a guess at the best file_type to
    express the data as. The prediction is based on what content is in the upper-left cell and the dimensions.
    Useful when converting a python iterable to a file output.
    Function forked from original found in geoecon_utils library, used with permission open BSD from Justin Johnson.

    :param file_uri:
    :return: data_type, num_rows, num_cols
    """

    row_headers = []
    col_headers = []

    if os.path.exists(file_uri):
        # Iterate trough one initial time to ddetermine dimensions and
        with open(file_uri, 'r') as f:
            # Save all col_lengths to allow for truncated rows.
            col_lengths = []
            first_row = True
            for row in f:
                split_row = row.replace('\n', '').split(',')
                col_lengths.append(len(split_row))
                if split_row[0] in index_synonyms and first_row:
                    blank_ul = True
                else:
                    blank_ul = False
                    break

        num_rows = len(col_lengths)
        num_cols = max(col_lengths)

        # with open(file_uri, 'r') as f:
        if num_cols == 1:
            if num_rows == 1:
                if blank_ul:
                    data_type = 'empty'
                else:
                    data_type = 'singleton'
            else:
                if blank_ul:
                    data_type = 'row_headers'
                else:
                    data_type = 'vertical_list'
        elif num_cols >= 2:
            if num_rows == 1:
                if blank_ul:
                    data_type = 'col_headers'
                else:
                    data_type = 'horizontal_list'
            if num_rows >= 2:
                if blank_ul:
                    data_type = 'DD'
                else:
                    data_type = 'LL'


        return data_type, num_rows, num_cols
    else:
        raise NameError('File given to ' + file_uri + ' determine_data_type_and_dimensions_for_read does not exist.')


def determine_data_type_and_dimensions_from_object(input_python_object):
    """
    Inspects a file of type to determine what the dimensions of the data are and make a guess at the best file_type to
    express the data as. The prediction is based on what content is in the upper-left cell and the dimensions.
    Useful when converting a python iterable to a file output.
    Function forked from original found in geoecon_utils library, used with permission open BSD from Justin Johnson.
    """

    data_type = None
    blank_ul = False

    # First check to see if more than 2 dimensions. Currently, I do not detect beyond 2 dimensions here and instead just use the
    # Str function in python in the write function.
    if isinstance(input_python_object, str):
        data_type = 'singleton'
    elif isinstance(input_python_object, dict):
        raise TypeError('Only works with OrderedDicts not dicts.')
    elif isinstance(input_python_object, list):
        first_row = input_python_object[0]
        if isinstance(first_row, (str, int, float, bool)):
            data_type = 'vertical_list'
        elif isinstance(first_row, dict):
            raise TypeError('Only works with OrderedDicts not dicts.')
        elif isinstance(first_row, list):
            if first_row[0]: # If it's blank, assume it's an empty headers column
                data_type = 'LL'
            else:
                data_type = 'column_headers'
        elif isinstance(first_row, OrderedDict):
            data_type = 'LD' # Unimplemented
        else:
            raise NameError('type unknown')
    elif isinstance(input_python_object, OrderedDict):
        first_row_key = next(iter(input_python_object))
        first_row = input_python_object[first_row_key]
        if isinstance(first_row, (str, int, float, bool)):
            data_type = 'D'
        elif isinstance(first_row, dict):
            raise TypeError('Only works with OrderedDicts not dicts.')
        elif isinstance(first_row, list):
            data_type = 'DL' # NYI
            raise TypeError(data_type + ' unsupported.')
        elif isinstance(first_row, OrderedDict):
            data_type = 'DD'
        else:
            raise NameError('Unsupported object type. Did you give a blank OrderedDict to python_object_to_csv()?. \nYou Gave:\n\n' + str(input_python_object))
    else:
        raise NameError('Unsupported object type. You probably gave "None" to python_object_to_csv()')
    return data_type


def python_object_to_csv(input_iterable, output_uri, csv_type=None, verbose=False):
    if csv_type:
        data_type = csv_type
    else:
        data_type = determine_data_type_and_dimensions_for_write(input_iterable)
    protected_characters = [',', '\n']
    first_row = True

    if not os.path.exists(os.path.split(output_uri)[0]) and os.path.split(output_uri)[0]:
        print(('Specified output_uri folder ' + os.path.split(output_uri)[0] + ' does not exist. Creating it.'))
        os.makedirs(os.path.split(output_uri)[0])

    to_write = ''

    if data_type == 'singleton':
        to_write = input_iterable

    # TODO This is a potential simpler way: just declare it.
    elif data_type == 'rc_2d_odict':
        first_row = True
        for key, value in list(input_iterable.items()):
            if first_row:
                first_row = False
                to_write += ',' + ','.join(list(value.keys())) + '\n'

            write_list = [str(i) for i in list(value.values())]
            to_write += str(key)+ ',' + ','.join(write_list) + '\n'

    elif data_type == 'cr_2d_odict':
        first_row = True
        for key, value in list(input_iterable.items()):
            if first_row:
                first_row = False
                to_write += ',' + ','.join(list(value.keys())) + '\n'

            write_list = [str(i) for i in list(value.values())]
            to_write += str(key)+ ',' + ','.join(write_list) + '\n'


    elif data_type == '1d_list':
        to_write += ', '.join(input_iterable) # TODO THIS IS BROKEN. For instance, didn't work when i gave it a list to gdalbuildvirt because i needed it to be a vertically stored list. decide if have space by default or create new type.
    elif data_type == '2d_list':
        for row in input_iterable:
            if any(character in row for character in protected_characters):
                raise NameError('Protected character found in the string-ed version of the iterable.')

            # TODO Note that this wouldn't work with eg. a list of strings.
            to_write += ','.join(row) + '\n'
    elif data_type == '2d_list_odict_NOT_SUPPORTED':
        raise NameError('2d_list_odict_NOT_SUPPORTED unknown')
    elif data_type == '1d_odict':
        for key, value in list(input_iterable.items()):
            # check to see if commas or line breaks are in the iterable string.
            value = str(value)
            if any(character in str(key) for character in protected_characters) or any(character in value for character in protected_characters):
                raise NameError('Protected character found in the string-ed version of the iterable: '+ str(key))
            to_write += str(key) + ',' + str(value) + '\n'
    elif data_type == '2d_odict_list':
        raise NameError('2d_odict_list unknown')
    elif data_type == '2d_odict':
        if isinstance(input_iterable, list):
            # The only way you can get here is it was manually declared to be this type and the list implies that it was empty (1 row).
            # TODOO Currently, I do not deal with indexed data_types consistently, nor do I account for empty data (as in here) the same on IO operations.
            to_write += ','.join(input_iterable)
        else:
            for key, value in list(input_iterable.items()):
                if first_row:
                    # On the first row, we need to write BOTH th efirst and second rows for col_headers and data respecitvely.
                    if key is not None and value is not None:
                        if any(character in str(key) for character in protected_characters) or any(character in value for character in protected_characters):
                            raise NameError('Protected character found in the string-ed version of the iterable.')
                    to_write += ','.join([''] + [str(i) for i in value.keys()]) + '\n' # Note the following duplication of keys, values to address the nature of first row being keys.
                if key is not None and value is not None:
                    if any(character in str(key) for character in protected_characters) or any(character in value for character in protected_characters):
                        raise NameError('Protected character found in the string-ed version of the iterable.')
                    first_col = True
                    for value2 in list(value.values()):
                        if first_col:
                            # if first_row:
                            #     to_write += ','
                            to_write += str(key) + ','
                            first_col = False
                        else:
                            to_write += ','
                        if isinstance(value2, list):
                            to_write += '<^>'.join(value2)
                        else:
                            to_write += str(value2)
                    to_write += '\n'
                    first_row = False
                else:
                    to_write +=','
    else:
        raise NameError('Not sure how to handle that data_type.')

    open(output_uri, 'w').write(to_write)

    if verbose:
        print(('\nWriting python object to csv at ' + output_uri + '. Auto-detected the data_type to be: ' + data_type))
        print(('String written:\n' + to_write))


def determine_data_type_and_dimensions_for_write(input_python_object):
    """
    Inspects a file of type to determine what the dimensions of the data are and make a guess at the best file_type to
    express the data as. The prediction is based on what content is in the upper-left cell and the dimensions.
    Useful when converting a python iterable to a file output.
    Function forked from original found in geoecon_utils library, used with permission open BSD from Justin Johnson.
    """

    data_type = None

    # First check to see if more than 2 dimensions. Currently, I do not detect beyond 2 dimensions here and instead just use the
    # Str function in python in the write function.
    if isinstance(input_python_object, str):
        data_type = 'singleton'
    # elif isinstance(input_python_object, dict):
    #     raise TypeError('Only works with OrderedDicts not dicts.')
    elif isinstance(input_python_object, list):
        first_row = input_python_object[0]
        if isinstance(first_row, (str, int, float, bool)):
            data_type = '1d_list'
        elif isinstance(first_row, dict):
            raise TypeError('Only works with OrderedDicts not dicts.')
        elif isinstance(first_row, list):
            data_type = '2d_list'
        elif isinstance(first_row, OrderedDict):
            data_type = '2d_list_odict_NOT_SUPPORTED'
        else:
            raise NameError('2d_list_odict_NOT_SUPPORTED unknown')
    elif isinstance(input_python_object, OrderedDict):
        first_row_key = next(iter(input_python_object))
        first_row = input_python_object[first_row_key]
        if isinstance(first_row, (str, int, float, bool)):
            data_type = '1d_odict'
        # elif isinstance(first_row, dict):
        #     raise TypeError('Only works with OrderedDicts not dicts.')
        elif isinstance(first_row, list):
            data_type = '2d_odict_list'
        elif isinstance(first_row, OrderedDict):
            data_type = '2d_odict'
        else:
            raise NameError('Unsupported object type. Did you give a blank OrderedDict to python_object_to_csv()?. \nYou Gave:\n\n' + str(input_python_object))
    elif isinstance(input_python_object, np.ndarray):
        data_type = '2d_list'

    else:
        raise NameError('Unsupported object type. You probably gave "None" to python_object_to_csv()')
    return data_type

def comma_linebreak_string_to_2d_array(input_string, dtype=None):
    s = str(input_string)
    rows = s.split('\n')

    # First get size
    n_rows = len(rows)
    n_cols = len(rows[0].split(','))

    if dtype:
        a = np.zeros((n_rows, n_cols), dtype=dtype)
    else:
        a = np.zeros((n_rows, n_cols))

    for row_id, row in enumerate(rows):
        col = row.split(',')
        for col_id, value in enumerate(col):
            a[row_id][col_id] = value

    return a


if __name__=='__main__':
    pass
    #nose.run()





