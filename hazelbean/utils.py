import os, sys, shutil, warnings
import geopandas as gpd
import pprint
from collections import OrderedDict
import numpy as np
import json

import hazelbean as hb



import math
from osgeo import gdal
import contextlib
import logging
from google.cloud import storage
import hashlib
import inspect
import subprocess
from tqdm import tqdm

import pandas as pd
from hazelbean import config as hb_config

L = hb_config.get_logger('hazelbean utils')

def get_all_frames_locations_as_list():
    locations = []
    # Start with the current frame, then follow the chain of calling frames
    frame = inspect.currentframe()

    while frame:
        # Extract the file name and line number from the current frame
        file_name = frame.f_code.co_filename
        line_number = frame.f_lineno
        locations.append(f"{file_name}:{line_number}")
        frame = frame.f_back  # Move to the next outer frame

    # Remove the call to this function itself from the list
    return locations[1:]  # Skip the first entry (this function call)



def get_current_script_location(exclude_frame_string_filter=None, separator=', '):
    if exclude_frame_string_filter is None:
        exclude_frame_string_filter = ['ProjectFlow', 'project_flow', '.vscode', 'runpy', 'hazelbean\\utils', 'hazelbean/utils']

    # Get the current frame object, then go back one step to get the frame of the caller
    caller_frame = inspect.currentframe().f_back
    # Extract the file name and line number from the caller's frame
    file_name = caller_frame.f_code.co_filename
    line_number = caller_frame.f_lineno
    locations = get_all_frames_locations_as_list()
    return separator.join([i for i in locations if not any([j in i for j in exclude_frame_string_filter])])

def print_with_location(*args, **kwargs):
    # Get the current frame object, then go back one step to get the frame of the caller
    caller_frame = inspect.currentframe().f_back
    # Extract the file name and line number from the caller's frame
    file_name = caller_frame.f_code.co_filename
    line_number = caller_frame.f_lineno
    # Print the file name, line number, and the original message
    print(f"[{file_name}:{line_number}]", *args, **kwargs)
    
def debug(msg, *args, level=100, same_line_as_previous=False, **kwargs):
    # LEARNING POINT, when using the * operator in a function with other named args, it had to come before the named args, e.g. level=10 in the above.
        
    if level <= 50:
        to_print = str(msg) + ' ' + ' '.join([str(i) for i in args]) + ' ' + ' '.join([str(k) + ': ' + str(v) + '\n' for k, v in kwargs.items() if k != 'logger_level'])
        
        if same_line_as_previous:
            print("\r" + to_print, end="")    
        else:
            print(to_print)

def log(msg, *args, level=10, same_line_as_previous=False, include_script_location=False, **kwargs):
    # LEARNING POINT, when using the * operator in a function with other named args, it had to come before the named args, e.g. level=10 in the above.
        
    if level <= 50:
        to_print = str(msg) + ' ' + ' '.join([str(i) for i in args]) + ' ' + ' '.join([str(k) + ': ' + str(v) + '\n' for k, v in kwargs.items() if k != 'logger_level'])
        
        if include_script_location:
            to_print += ' ' + get_current_script_location()
        
        if same_line_as_previous:
            print("\r" + to_print, end="")    
        else:
            print(to_print)
    
def hprint(*args, **kwargs):
    return hb_pprint(*args, **kwargs)

def pp(*args, **kwargs):
    return hb_pprint(*args, **kwargs)

def hb_pprint(*args, **kwargs):

    num_values = len(args)

    print_level = kwargs.get('print_level', 2) # NO LONGER IMPLEMENTED
    return_as_string = kwargs.get('return_as_string', False)
    include_type = kwargs.get('include_type', False)

    indent = kwargs.get('indent', 2)
    width = kwargs.get('width', 120)
    depth = kwargs.get('depth', None)

    printable = ''

    for i in range(num_values):
        if type(args[i]) == hb.ArrayFrame:
            # handles its own pretty printing via __str__
            line = str(args[i])
        elif type(args[i]) is OrderedDict:
            line = 'OrderedDict\n'
            for k, v in args[i].items():
                if type(v) is str:
                    item = '\'' + v + '\''
                else:
                    item = str(v)
                line += '    ' + str(k) + ': ' + item + ',\n'
                # PREVIOS ATTEMPT Not sure why was designed this way.
                # line += '    \'' + str(k) + '\': ' + item + ',\n'
        elif type(args[i]) is dict:
            line = 'dict\n'
            line += pprint.pformat(args[i], indent=indent, width=width, depth=depth)
            # for k, v in args[i].items():
            #     if type(v) is str:
            #         item = '\'' + v + '\''
            #     else:
            #         item = str(v)
            #     line += '    ' + str(k) + ': ' + item + ',\n'
        elif type(args[i]) is list:
            line = 'list\n'
            line += pprint.pformat(args[i], indent=indent, width=width, depth=depth)
            # for j in args[i]:
            #     line += '  ' + str(j) + '\n'
        elif type(args[i]) is np.ndarray:

            try:
                line = hb.describe_array(args[i])
            except:
                line = '\nUnable to describe array.'

        else:
            line = pprint.pformat(args[i], indent=indent, width=width, depth=depth)

        if include_type:
            line = type(args[i]).__name__ + ': ' + line
        if i < num_values - 1:
            line += '\n'
        printable += line

    if return_as_string:
        return printable
    else:
        print (printable)
        return printable

def concat(*to_concat):
    to_return = ''
    for v in to_concat:
        to_return += str(v)

    return to_return


@contextlib.contextmanager
def capture_gdal_logging():
    """Context manager for logging GDAL errors with python logging.

    GDAL error messages are logged via python's logging system, at a severity
    that corresponds to a log level in ``logging``.  Error messages are logged
    with the ``osgeo.gdal`` logger.

    Parameters:
        ``None``

    Returns:
        ``None``"""
    osgeo_logger = logging.getLogger('osgeo')

    def _log_gdal_errors(err_level, err_no, err_msg):
        """Log error messages to osgeo.

        All error messages are logged with reasonable ``logging`` levels based
        on the GDAL error level.

        Parameters:
            err_level (int): The GDAL error level (e.g. ``gdal.CE_Failure``)
            err_no (int): The GDAL error number.  For a full listing of error
                codes, see: http://www.gdal.org/cpl__error_8h.html
            err_msg (string): The error string.

        Returns:
            ``None``"""
        osgeo_logger.log(
            level=GDAL_ERROR_LEVELS[err_level],
            msg='[errno {err}] {msg}'.format(
                err=err_no, msg=err_msg.replace('\n', ' ')))

    gdal.PushErrorHandler(_log_gdal_errors)
    try:
        yield
    finally:
        gdal.PopErrorHandler()

def describe(input_object, file_extensions_in_folder_to_describe=None, surpress_print=False, surpress_logger=False):
    # Generalization of describe_array for many types of things.

    description = ''

    input_object_type = type(input_object).__name__
    if type(input_object) is hb.ArrayFrame:
        description = hb.describe_af(input_object.path)

    if type(input_object) is np.ndarray:
        description = hb.describe_array(input_object)
    elif type(input_object) is str:
        try:
            folder, filename = os.path.split(input_object)
        except:
            folder, filename = None, None
        try:
            file_label, file_ext = os.path.splitext(filename)
        except:
            file_label, file_ext = None, None
        if file_ext in hb.common_gdal_readable_file_extensions or file_ext in ['.npy']:
            description = hb.describe_path(input_object)
        elif not file_ext:
            description = 'type: folder, contents: '
            description += ' '.join(os.listdir(input_object))
            if file_extensions_in_folder_to_describe == '.tif':
                description += '\n\nAlso describing all files of type ' + file_extensions_in_folder_to_describe
                for filename in os.listdir(input_object):
                    if os.path.splitext(filename)[1] == '.tif':
                        description += '\n' + describe_path(input_object)
        else:
            description = 'Description of this is not yet implemented: ' + input_object

    ds = None
    array = None
    if not surpress_print:
        pp_output = hb.hb_pprint(description)
    else:
        pp_output = hb.hb_pprint(description, return_as_string=True)

    if not surpress_logger:
        hb.log(pp_output)
    return description

def safe_string(string_possibly_unicode_or_number):
    """Useful for reading Shapefile DBFs with funnycountries"""
    return str(string_possibly_unicode_or_number).encode("utf-8", "backslashreplace").decode()

def describe_af(input_af):
    if not input_af.path and not input_af.shape:
        return '''Hazelbean ArrayFrame (empty). The usual next steps are to set the shape (af.shape = (30, 50),
                    then set the path (af.path = \'C:\\example_raster_folder\\example_raster.tif\') and finally set the raster
                    with one of the set raster functions (e.g. af = af.set_raster_with_zeros() )'''
    elif input_af.shape and not input_af.path:
        return 'Hazelbean ArrayFrame with shape set (but no path set). Shape: ' + str(input_af.shape)
    elif input_af.shape and input_af.path and not input_af.data_type:
        return 'Hazelbean ArrayFrame with path set. ' + input_af.path + ' Shape: ' + str(input_af.shape)
    elif input_af.shape and input_af.path and input_af.data_type and not input_af.geotransform:
        return 'Hazelbean ArrayFrame with array set. ' + input_af.path + ' Shape: ' + str(input_af.shape) + ' Datatype: ' + str(input_af.data_type)

    elif not os.path.exists(input_af.path):
        raise NameError('AF pointing to ' + str(input_af.path) + ' used as if the raster existed, but it does not. This often happens if tried to load an AF from a path that does not exist.')

    else:
        if input_af.data_loaded:
            return '\nHazelbean ArrayFrame (data loaded) at ' + input_af.path + \
                   '\n      Shape: ' + str(input_af.shape) + \
                   '\n      Datatype: ' + str(input_af.data_type) + \
                   '\n      No-Data Value: ' + str(input_af.ndv) + \
                   '\n      Geotransform: ' + str(input_af.geotransform) + \
                   '\n      Bounding Box: ' + str(input_af.bounding_box) + \
                   '\n      Projection: ' + str(input_af.projection)+ \
                   '\n      Num with data: ' + str(input_af.num_valid) + \
                   '\n      Num no-data: ' + str(input_af.num_ndv) + \
                   '\n      ' + str(hb.pp(input_af.data, return_as_string=True)) + \
                   '\n      Histogram ' + hb.pp(hb.enumerate_array_as_histogram(input_af.data), return_as_string=True) + '\n\n'
        else:
            return '\nHazelbean ArrayFrame (data not loaded) at ' + input_af.path + \
                   '\n      Shape: ' + str(input_af.shape) + \
                   '\n      Datatype: ' + str(input_af.data_type) + \
                   '\n      No-Data Value: ' + str(input_af.ndv) + \
                   '\n      Geotransform: ' + str(input_af.geotransform) + \
                   '\n      Bounding Box: ' + str(input_af.bounding_box) + \
                   '\n      Projection: ' + str(input_af.projection)

                    # '\nValue counts (up to 30) ' + str(hb.pp(hb.enumerate_array_as_odict(input_af.data), return_as_string=True)) + \

def describe_dataframe(df):
    p = 'Dataframe of length ' + str(len(df.index)) + ' with ' + str(len(df.columns)) + ' columns. Index first 10: ' + str(list(df.index.values)[0:10])
    for column in df.columns:
        col = df[column]
        p += '\n    ' + str(column) + ': min ' + str(np.min(col)) + ', max ' + str(np.max(col)) + ', mean ' + str(np.mean(col)) + ', median ' + str(np.median(col)) + ', sum ' + str(np.sum(col)) + ', num_nonzero ' + str(np.count_nonzero(col)) + ', nanmin ' + str(np.nanmin(col)) + ', nanmax ' + str(np.nanmax(col)) + ', nanmean ' + str(np.nanmean(col)) + ', nanmedian ' + str(np.nanmedian(col)) + ', nansum ' + str(np.nansum(col))
    return(p)

def describe_path(path):
    ext = os.path.splitext(path)[1]
    # TODOO combine the disparate describe_* functionality
    # hb.pp(hb.common_gdal_readable_file_extensions)
    if ext in hb.common_gdal_readable_file_extensions:
        ds = gdal.Open(path)
        if ds.RasterXSize * ds.RasterYSize > 10000000000:
            return 'too big to describe'  # 'type: LARGE gdal_uri, dtype: ' + str(ds.GetRasterBand(1).DataType) + 'no_data_value: ' + str(ds.GetRasterBand(1).GetNoDataValue()) + ' sum: ' + str(sum_geotiff(input_object)) +  ', shape: ' + str((ds.RasterYSize, ds.RasterXSize)) + ', size: ' + str(ds.RasterXSize * ds.RasterYSize) + ', object: ' + input_object
        else:
            try:
                array = ds.GetRasterBand(1).ReadAsArray()
                return hb.describe_array(array)
            except:
                return 'Too big to open.'
    elif ext in ['.npy', '.npz']:
        try:
            array = hb.load_npy_as_array(path)
            return hb.describe_array(array)
        except:
            return 'Unable to describe NPY file because it couldnt be opened as an array'

    # try:
    #     af = hb.ArrayFrame(input_path)
    #     s = describe_af(af)
    #     hb.log(str(s))
    # except:
    #     pass


def describe_array(input_array):
    description = 'Array of shape '  + str(np.shape(input_array))+ ' with dtype ' + str(input_array.dtype) + '. sum: ' + str(np.sum(input_array)) + ', min: ' + str(
        np.min(input_array)) + ', max: ' + str(np.max(input_array)) + ', range: ' + str(
        np.max(input_array) - np.min(input_array)) + ', median: ' + str(np.median(input_array)) + ', mean: ' + str(
        np.mean(input_array)) + ', num_nonzero: ' + str(np.count_nonzero(input_array)) + ', size: ' + str(np.size(input_array)) + ' nansum: ' + str(
        np.nansum(input_array)) + ', nanmin: ' + str(
        np.nanmin(input_array)) + ', nanmax: ' + str(np.nanmax(input_array)) + ', nanrange: ' + str(
        np.nanmax(input_array) - np.nanmin(input_array)) + ', nanmedian: ' + str(np.nanmedian(input_array)) + ', nanmean: ' + str(
        np.nanmean(input_array))
    return description

def round_to_nearest_base(x, base):
    return base * round(x/base)

def round_up_to_nearest_base(x, base):
    return base * math.ceil(x/base)

def round_down_to_nearest_base(x, base):
    return base * math.floor(x/base)


def round_significant_n(input, n):
    # round_significant_n(3.4445678, 1)
    x = input
    try:
        int(x)
        absable = True
    except:
        absable = False
    if x != 0 and absable:
        out = round(x, -int(math.floor(math.log10(abs(x)))) + (n - 1))
    else:
        out = 0.0
    return out

def round_to_nearest_containing_increment(input, increment, direction):
    if direction == 'down':
        return int(increment * math.floor(float(input) / increment))
    elif direction == 'up':
        return int(increment * math.ceil(float(input) / increment))
    else:
        raise NameError('round_to_nearest_containing_increment failed.')


# TODOO Rename to_bool and maybe have a separate section of casting functions?
def str_to_bool(input):
    """Convert alternate versions of the word true (e.g. from excel) to actual python bool object."""
    return str(input).lower() in ("yes", "true", "t", "1", "y")

def normalize_array_memsafe(input_path, output_path, low=0, high=1, min_override=None, max_override=None, ndv=None, log_transform=True):

    raster_statistics =  hb.read_raster_stats(input_path)
    if min_override is None:
        min_override = raster_statistics['min']
    if max_override is None:
        max_override = raster_statistics['max']

    input_list = [input_path, low, high, min_override, max_override, ndv, log_transform]
    hb.log('normalize_array_memsafe on ', input_path, output_path, low, high, min_override, max_override, ndv, log_transform)
    hb.raster_calculator_flex(input_list, normalize_array, output_path=output_path)

def normalize_array(array, low=0, high=1, min_override=None, max_override=None, ndv=None, log_transform=True):
    """Returns array with range (0, 1]
    Log is only defined for x > 0, thus we subtract the minimum value and then add 1 to ensure 1 is the lowest value present. """
    array = array.astype(np.float64)
    if ndv is not None: # Slightly slower computation if has ndv. optimization here to only consider ndvs if given.
        if log_transform:
            if min_override is None:
                L.debug('Starting to log array for normalize with ndv.')
                min = np.min(array[array != ndv])
                L.debug('  Min was ' + str(min))
            else:
                min = min_override
            to_add = np.float64(min * -1.0 + 1.0) # This is just to subtract out the min and then add 1 because can't log zero
            array = np.where(array != ndv, np.log(array + to_add), ndv)
            L.debug('  Finished logging array')

        # Have to do again to get new min after logging.
        if min_override is None:
            L.debug('Getting min from array', array, array[array != ndv], array.shape)

            min = np.min(array[array != ndv])
        else:
            min = min_override

        if max_override is None:
            hb.log('Getting max from array', array, array[array != ndv], array.shape)
            max = np.max(array[array != ndv])
        else:
            max = max_override

        normalizer = np.float64((high - low) / (max - min))

        output_array = np.where(array != ndv, (array - min) * normalizer, ndv)
    else:
        if log_transform:
            hb.log('Starting to log array for normalize with no ndv.')
            min = np.min(array)
            to_add = np.float64(min * -1.0 + 1.0)
            array = array + to_add

            array = np.log(array)

        # Have to do again to get new min after logging.
        if min_override is None:
            min = np.min(array[array != ndv])
        else:
            min = min_override

        if max_override is None:
            max = np.max(array[array != ndv])
        else:
            max = max_override
        normalizer = np.float64((high - low) / (max - min))

        output_array = (array - min) *  normalizer

    return output_array


def get_ndv_from_path(intput_path):
    """Return nodata value from first band in gdal dataset cast as numpy datatype.

    Args:
        dataset_uri (string): a uri to a gdal dataset

    Returns:
        nodata: nodata value for dataset band 1
    """
    dataset = gdal.Open(intput_path)
    band = dataset.GetRasterBand(1)
    nodata = band.GetNoDataValue()
    if nodata is not None:
        nodata_out = nodata
    else:
        # warnings.warn(
        #     "Warning the nodata value in %s is not set", dataset_uri)
        nodata_out = None

    band = None
    gdal.Dataset.__swig_destroy__(dataset)
    dataset = None
    return nodata_out

def get_nodata_from_uri(dataset_uri):
    """Return nodata value from first band in gdal dataset cast as numpy datatype.

    Args:
        dataset_uri (string): a uri to a gdal dataset

    Returns:
        nodata: nodata value for dataset band 1
    """

    warnings.warn('get_nodata_from_uri deprecated for get_ndv_from_path ')
    dataset = gdal.Open(dataset_uri)
    band = dataset.GetRasterBand(1)
    nodata = band.GetNoDataValue()
    if nodata is not None:
        nodata_out = nodata
    else:
        # warnings.warn(
        #     "Warning the nodata value in %s is not set", dataset_uri)
        nodata_out = None

    band = None
    gdal.Dataset.__swig_destroy__(dataset)
    dataset = None
    return nodata_out


# Make a non line breaking printer for updates.
def print_in_place(to_print, pre=None, post=None):
    to_print = str(to_print)
    if pre:
        to_print = str(pre) + to_print
    if post:
        to_print = to_print + str(post)

    # print("\r", end="")
    print(to_print, end="\r")
    # print('\r' + to_print, end="\r")

    # LEARNING POINT, print with end='\r' didn't work because it was cleared before it was visible, possibly by pycharm
    # print(to_print,  end='\r')



# Make a non line breaking printer for updates.
def pdot(pre=None, post=None):
    to_dot = '.'
    if pre:
        to_dot = str(pre) + to_dot
    if post:
        to_dot = to_dot + str(post)
    sys.stdout.write(to_dot)

def parse_input_flex(input_flex):
    if isinstance(input_flex, str):
        output = hb.ArrayFrame(input_flex)
    elif isinstance(input_flex, np.ndarray):
        print('parse_input_flex is NYI for arrays because i first need to figure out how to have an af without georeferencing.')
        # output = hb.create_af_from_array(input_flex)
    else:
        output = input_flex
    return output

def get_unique_keys_from_vertical_dataframe(df, columns_to_check=None):
    if columns_to_check is None:
        columns_to_check = list(df.columns)

    keys_dict = {}
    lengths_dict = {}

    for column in columns_to_check:
        uniques = df[column].unique()
        keys_dict[column] = uniques
        lengths_dict[column] = len(uniques)

    return lengths_dict, keys_dict

def calculate_on_vertical_df(df, level, op_type, focal_cell, suffix):
    original_indices = df.index.copy()
    original_columns = df.columns.copy()
    if len(original_columns) > 1:
        raise NameError('Are you sure this is vertical data?')
    original_label = original_columns.values[0]

    dfp = df.unstack(level=level)
    r = dfp.columns.get_level_values(level=1)

    dfp.columns = r

    output_labels = []
    for i in dfp.columns:
        if op_type == 'difference_from_row' and i != focal_cell:
            dfp[i + suffix] = dfp[i] - dfp[focal_cell]
            output_labels.append(suffix)
        if op_type == 'percentage_change_from_row' and i != focal_cell:
            dfp[i + suffix] = ((dfp[i] - dfp[focal_cell]) / dfp[i]) * 100.0
            output_labels.append(suffix)

    dfo = pd.DataFrame(dfp.stack())

    dfo = dfo.rename(columns={0: original_label})

    dfor = dfo.reset_index()
    dforr = dfor.set_index(original_indices.names)

    # Reorder indices so it matches the input (restacking puts the targetted level outermost)

    return dforr

def df_plot(input_df, output_png_path, type='bar', legend_labels=None):

    # Create the bar plot
    input_df
    import matplotlib.pyplot as plt
    ax = input_df.plot(kind=type, rot=0, colormap='viridis', figsize=(10, 6))
    # Set labels and title
    plt.xlabel('Regions')
    var = hb.file_root(output_png_path)
    plt.ylabel('Percent change in ' + var)
    plt.title('Change in ' + var + ' by region under three ag productivity shocks')
    if legend_labels is not None:
        plt.legend(title='Shock', loc='upper left', labels=legend_labels)

    plt.axhline(y=0, color='gray', linestyle='dotted', linewidth=1, label='100%')

    # Save the png to output_png_path
    plt.savefig(output_png_path, dpi=300, bbox_inches='tight')

def df_merge_list_of_csv_paths(csv_path_list, output_csv_path=None, on='index', left_on=None, right_on=None, column_suffix='fileroot',verbose=False):
    print('CAVEAT NYI, only use on otherwise left and right_on get overwrit')
    merged_df = None

    if on == 'index':
        left_index = True
        right_index = True
        left_on = None
        right_on = None
        new_on = None
    else:
        new_on = on
        left_index = False
        right_index = False
        left_on = on
        right_on = on

    for c, csv_path in enumerate(csv_path_list):
        current_df = pd.read_csv(csv_path)  

        if column_suffix == 'fileroot':
            columns = {k: v for k, v in zip(current_df.columns, [str(i) + '_' + hb.file_root(csv_path) for i in current_df.columns])}
            current_df.rename(columns=columns, inplace=True)
           
        elif column_suffix == 'ignore':
            pass # This means we're assuming each csv has some unique col.
        elif type(column_suffix) is str:
            columns = {k: v for k, v in zip(current_df.columns, [str(i) + '_' + column_suffix for i in current_df.columns])}
            columns = {k: v for k, v in columns.items() if v != on and v != left_on and v != right_on}
            current_df.rename(columns=columns, inplace=True)
            
        
        elif type(column_suffix) is list:
            if len(column_suffix) == len(csv_path_list):
                columns = {k: v for k, v in zip(current_df.columns, [str(i) + '_' + column_suffix[c] for i in current_df.columns if 'Unnamed' not in i])}
                columns = {k: v for k, v in columns.items() if v != on + '_' + column_suffix[c] and v != left_on + '_' + column_suffix[c] and v != right_on + '_' + column_suffix[c]}

                current_df.rename(columns=columns, inplace=True)
               
            else:
                raise NameError('column_suffix list must be same length as csv_path_list')

        else:
            raise NameError('column_suffix must be fileroot or a string or a list of strings.')


        if c == 0:
            merged_df = current_df
        else:  

            cols = [i for i in current_df.columns if i not in merged_df.columns]
            if right_on:
                cols += [right_on]
            # new_df = current_df[cols]
            
            new_df = current_df
            
            # merged_df = pd.merge(merged_df, new_df, how='outer', left_on=left_on, right_on=right_on, left_index=left_index, right_index=right_index)
            merged_df = df_merge(merged_df, new_df, how='outer', left_on=left_on, right_on=right_on, supress_warnings=True, verbose=False)
    if output_csv_path:
        merged_df.to_csv(output_csv_path, index=False)  
        
    return merged_df


def df_pivot_vertical_up(df, row_indices, column_indices, values, aggregation_dict=None, filter_dict=None, non_summarized_vars_to_keep='all', require_single_values=True, aggregation_functions=None, flatten_column_multiindex=True):
    """This is turning out to be a very good funciton and i almost renamed it just pivot_vertical but I still need
    to test if it works for non vertical data.
    
    TODO Clarify the difference between row_indices and non_summarized_vars_to_keep
    """
    
    
    ### One tricky thing in gtap_invest is that if you filter to just the terminal year, you don't have the baseline in the filtered data to comapre to
    
    # column_indices specifies which columns should be the column-indices. If there's more than 1, it will make it a multiindex, ready for reshaping.
    if column_indices is None:
        column_indices = []
    
    # Specify which indices should be eliminated via aggregation. If it's aggregated, it drops out of what can be in the rows or columns
    if aggregation_dict is None:
        aggregation_dict = {}   

    # Specify which index values should just be eliminate. For example, if you have multiple years, you might want to just plot the last year
    if filter_dict is None: 
        filter_dict = {} 

    # Determine which index values should be eliminated, based all the above. 
    fullydrop_filter_dict = {k: v for k, v in filter_dict.items() if type(v) != list} 
    if row_indices == 'all':
        row_indices = [i for i in df.columns if i not in column_indices and i != values and i not in aggregation_dict and i not in fullydrop_filter_dict]
        
    # Read the raw input
    if isinstance(df, str):
        df = pd.read_csv(df)
            
    # Apply filter by creating a condition 
    if filter_dict:
        condition = True 
        for key, value in filter_dict.items():
            if str(value).startswith('int('):
                value = int(value.split('int(')[1].split(')')[0])
            if key in df.columns:
                if isinstance(value, list):
                    condition &= (df[key].isin(value))
                else:
                    condition &= (df[key] == value)
            else:
                # condition &= (df[key] == value)
                raise NameError(f'Filter key {key} not in dataframe columns {df.columns}')
        df = df.loc[condition]    

    # Check if filter eliminated everything.
    if df.size == 0:
        raise NameError(f'No data after filtering. Filter dict: {filter_dict}, original columns {df.columns}')
    
    # Determine if there are duplicates. This controls whether or not you need to keep the count columns (which implies maybe an error)
    has_duplicates = False
    correct_vals = 1
    if aggregation_dict:
        # Count the unique values in each aggregated col
        for agg_label, operation in aggregation_dict.items():
            n_properly_aggregated = len(df[agg_label].unique())
            correct_vals *= n_properly_aggregated
    
    # Determine which columns should be kept (even if they're neither summarized values nor indices. For example, you might have an index region_label but also just want to keep region_longname
    if non_summarized_vars_to_keep == 'all':
        non_summarized_vars_to_keep = [i for i in df.columns if i not in column_indices and i not in aggregation_dict and i not in fullydrop_filter_dict and i != values]
    elif isinstance(non_summarized_vars_to_keep, list):
        pass
    else:
        raise NameError('non_summarized_vars_to_keep must be all or a list of strings.')
    non_summarized_df = df[non_summarized_vars_to_keep]
    non_summarized_df = non_summarized_df.set_index(row_indices)
    
    # Current logic means we'll incluse sum and count, check if count=1 for all, then drop count if so. 
    # I might want to generalize this, but perhaps that goes in a new func.
    all_aggregations = ['sum', 'mean', 'median', 'min', 'max', 'std', 'var', 'count', 'size', 'nunique', 'first', 'last']
    if aggregation_functions is None:
        if require_single_values:
            aggregation_functions = ['sum', 'count']
        else:
            aggregation_functions = all_aggregations
    elif aggregation_functions == 'all':
        aggregation_functions = all_aggregations
    elif isinstance(aggregation_functions, str):
        aggregation_functions = [aggregation_functions] 
        for func in aggregation_functions:
            if func not in all_aggregations:
                raise NameError('aggregation_functions must be all or one of the following: ' + str(all_aggregations))
    else:
        raise NameError('Shouldnt get here')
        
    ### DO THE PIVOT       
    df_p = df.pivot_table(index=row_indices, columns=column_indices, values=values, aggfunc=aggregation_functions)
    
    # Check if any of the column_indices are empty
    for col in df_p.columns:
        if df_p[col].isnull().any():
            raise NameError('Column ' + str(col) + ' has nan values in the pivoted dataframe. This function is supposed to not have that. Heres the dataframe head:\n' + str(df_p.head()))
            
    
    ### After we pivot, we currently flatten the multiindex. not sure if this is beset.
    # Define an op to flatten the multiindex.
    def op(x):
        if isinstance(x, float):
            return str(int(x))
        else:
            return str(x)
    
    # Flatten multiindex columns to a single string. This is a weakness and perhasps i should figure out how to use hyphens or something so i can recover the multiindex.
    if flatten_column_multiindex:
        df_p.columns = ['-'.join(map(op, col[::-1])).strip() for col in df_p.columns.values]
    
    # Merge back in the non_summarized vars
    if non_summarized_df.size > 0:
        df_p = pd.merge(non_summarized_df, df_p, on=row_indices, how="inner")

    # Check if any count cols have more than the number of entries the agg_label suggests it should have
    for col in df_p.columns:
        if col.endswith(('-count')):
            if df_p[col].max() > correct_vals:
                has_duplicates = True
               
    if not has_duplicates:
        if require_single_values:
            # If there aren't duplicates and we require a single value, the only thing should be the sums that come out of the pivot cause count should be 1, mean should be the same, etc. WAIT THATS NOT TRUE
            if len(aggregation_dict) == 0:
                # Then just take the sum
                to_drop = [i for i in aggregation_functions if i != 'sum']
                
            elif len(aggregation_dict) <= 1:
                to_drop = [i for i in aggregation_functions if i not in aggregation_dict.values()]
            else:
                to_drop = []
                
            # Drop anything not in the dict
            for i in to_drop:
                df_p = df_p[[j for j in df_p.columns if not j.endswith(i)]]
            
            if len(aggregation_dict) == 0:
                # Then just take the sum
                df_p = df_p.rename(columns={j: j.replace('-sum', '') for j in df_p.columns}) 
            else:
                to_keep = [i for i in aggregation_functions if i in aggregation_dict.values()]
                for i in to_keep:
                    df_p = df_p.rename(columns={j: j.replace('-' + i, '') for j in df_p.columns})
        else:
            raise NotImplementedError('Not sure what to do here.')
    else:
        raise NotImplementedError('Not sure what to do here.')

    # Keep only named indices
    if df_p.index.name or isinstance(df_p.index, pd.MultiIndex):
        df_p = df_p.reset_index()
        df_p = df_p.loc[:, df_p.columns[df_p.columns != 'index']]
    else:
        df_p = df_p.reset_index(drop=True)    
        
    return df_p
                
    
def df_merge_quick(
    left_df, 
    right_df, 
    left_on=False,
    right_on=False,
    how=None,
    check_identicality=True,
    raise_error_if_not_identical=False, 
    verbose=False,
    ):
    
    """ Quick merge of two dataframe where it will drop the right columns that are identical to the left columns. This
    Prevents the annoying proliferation of _x and _y columns when they're the same."""
    
    comparison = hb.df_compare_column_labels_as_dict(left_df, right_df)
    right_df = right_df.rename(columns={i: i + '_right' for i in comparison['intersection'] if i != left_on and i != right_on})

    # Merge
    merged_df = pd.merge(left_df, right_df, how=how, left_on=left_on, right_on=right_on)
    
    if check_identicality:
        keep_right = []
        for col in comparison['intersection']:
            right_col = col + '_right'
            if col in merged_df.columns and right_col in merged_df.columns:
                if not hb.arrays_equal_ignoring_order(merged_df[col].values, merged_df[right_col].values): # , ignore_values=[-9999]        
                    if raise_error_if_not_identical:
                        raise NameError('Column ' + col + ' is not identical between left and right dataframes. Contents: ' + str(left_df[col].values) + ' ' + str(right_df[col].values))
                    else:
                        if verbose:
                            print('Column ' + col + ' is not identical between left and right dataframes. Contents: ' + str(left_df[col].values) + ' ' + str(right_df[right_col].values))
            keep_right.append(right_col)
        merged_df = merged_df[[i for i in merged_df.columns if i[-7:-1] != '_right' or i in keep_right]]
        
    return merged_df
        
def df_merge(left_input, 
             right_input, 
             how=None, 
             on=None, 
             left_on=False,
             right_on=False,
             fill_left_col_nan_with_right_value=False,
             compare_inner_outer=True, 
             full_check_for_identicallity=False,
             cols_to_ignore_for_analysis=['geometry'],
             verbose=False,
             supress_warnings=False,
             ):
    
    """
    Convenience wrapper for pd.merge. Differences:
    
    - Works with Geopandas too while minimizing slowness from printing geometry
    - Simplified to taking left_on and right_on as primary 
        - The only way to set left_index = True is via left_on = 'index'
    - Removes duplicate columns before merge
    - Readds _on column so it doesn't go away
    - Better logging
    - Checks for cases where left or right merge cols have unique columns (which could lead to nans getting filled in.
    - Lets you merge right values into left ndv
    
    All this assumes that left is primary and we will ignore geometry from right.
    
    """
    
    # Check if is string. If its not a string, we will strongly assume
    # it is a GDF or a DF.
    if type(left_input) is str:
        if os.path.splitext(left_input)[1] == '.shp' or os.path.splitext(left_input)[1] == '.gpkg':
            left_df = gpd.read_file(left_input)
        else:
            left_df = pd.read_csv(left_input)
    else:
        left_df = left_input
        
    if type(right_input) is str:
        if os.path.splitext(right_input)[1] == '.shp' or os.path.splitext(right_input)[1] == '.gpkg':
            left_df = gpd.read_file(right_input)
        else:
            left_df = pd.read_csv(right_input)
    else:
        right_df = right_input

    # Always specify left_on and right_on as the merge names
    if on and not left_on:
        left_on = on
    if on and not right_on:
        right_on = on
        
    # If left_on is 'index' we'll use that

    # Check if either df is a GeoDataFrame
    if type(right_df) is gpd.GeoDataFrame and not type(left_df) is gpd.GeoDataFrame:
        raise NameError('Right df is a GeoDataFrame but left is not. This is not supported. Because it will drop the geometry column and fail on .to_file()')

    left_geometry = None
    right_geometry = None
    # Drop geometry cols for now for faster processing
    if type(left_df) is gpd.GeoDataFrame:
        left_geometry = left_df[[left_on, 'geometry']]
        left_df = left_df[[i for i in left_df.columns if i != 'geometry']]
    if type(right_df) is gpd.GeoDataFrame:
        # right_geometry = right_df['geometry']
        right_df = right_df[[i for i in right_df.columns if i != 'geometry']]


    if verbose:
        hb.log(
"""Merging: 
    
    left_df:
""" + str(left_df[[i for i in left_df.columns if i != 'geometry']]) + """
    right_df: 
""" + str(right_df[[i for i in right_df.columns if i != 'geometry']]) + """    
"""
)

    if how is None:
        how = 'outer'

    # If no on, left_on, or right_on is set, try to infer it from identical columns

    shared_column_labels = set(left_df.columns).intersection(set(right_df.columns))
    
    # Ignore columns that need ignoring
    shared_column_labels = [i for i in shared_column_labels if i not in cols_to_ignore_for_analysis]
    
    identical_columns = []
    identical_column_labels = []
    for col in shared_column_labels:
        # LEARNING POINT, using df == df failed unintuitively because np.nan != np.nan. Any one instance of a nan cannot EQUAL another instance of a nan even though they seem identical. Perhaps this is because equals is implied to be a function of numbers?
        # LEARNING POINT: left_df[col].equals(right_df[col]) solved the np.nan != np.nan problem that arose with left_df[col] == (right_df[col])
        # LEARNING Point, however the above didn't address the fact that the column values being identical fails equals if the indices associated are not the same.
        
        # LEARNING POINT: in gtapv7_s65_a24_correspondence I had the case where the ids were identical but in different order.
        # This is exactly what the merge function deals with, but it makes for a non-trivial identify-identical case
        # I chose to have this be considered non-identical and let the user deal with it pre function.
        if full_check_for_identicallity:
            if 'int' in str(left_df[col].dtype) or 'float' in str(left_df[col].dtype):
                # temporarily replace np.nan with -9999 so that it can test equality between nans
                left_df[col + '_temp'] = left_df[col].fillna(-9999)
                right_df[col + '_temp'] = right_df[col].fillna(-9999)

                if hb.arrays_equal_ignoring_order(left_df[col + '_temp'].values, right_df[col + '_temp'].values, ignore_values=[-9999]):
                    identical_columns.append(left_df[col])
                    identical_column_labels.append(col)
                    
                # Now drop the temp columns
                left_df = left_df.drop(col + '_temp', axis=1)
                right_df = right_df.drop(col + '_temp', axis=1)
                
            else:
                if left_df[col].sort_values().reset_index(drop=True).equals(right_df[col].sort_values().reset_index(drop=True)):
                    identical_columns.append(left_df[col])
                    identical_column_labels.append(col)
        else:
            if left_df[col].equals(right_df[col]):
                identical_columns.append(left_df[col])
                identical_column_labels.append(col)            
            
    if not any([left_on, right_on]):
        # If found, assign the first int column as the col to merge on
        for c, col in enumerate(identical_columns):
            if 'int' in str(col.dtype):
                left_on = identical_column_labels[c]
                right_on = identical_column_labels[c]
            break

        # If still not found, try to find a suitable string-based merge column, but fail if
        if not any([left_on, right_on]):
            remove_unnamed = [i for i in identical_column_labels if 'Unnamed:' not in i]
            if len(remove_unnamed) < 0:
                raise NameError('BORK!')
                # raise NameError('Too many identical column headers to infer which to merge on.')
            elif len(remove_unnamed) == 0:
                print('No identical column headers to infer which to merge on.')
            else:
                left_on = remove_unnamed[0]
                right_on = remove_unnamed[0]

    # Drop one of the identical columns so we don't get tons of redundant columns.
    for col in identical_column_labels:
        if col != left_on and col != right_on:
            if verbose:
                hb.log('Identical cols i that are not index or listed as merging on, so dropping right.')
            right_df = right_df.drop(col, axis=1)
    if not supress_warnings:
        if len(identical_column_labels) > 0:
            hb.log('Identical columns found: ' + str(identical_column_labels) + ' which might cause troubles if youre doing something like math that is supposed to have a zero (rather than dropping)')
    
    # Check types of merge columns
    if verbose:
        pass
        # hb.log('Left merge column type: ' + str(left_df[left_on].dtype) + ' Right merge column type: ' + str(right_df[right_on].dtype))
        
        # Also print all the columns dtypes
        # hb.log('Left columns: ' + ['    ' + k +': ' + v + '\n' for k, v in zip(str(left_df.columns), str(left_df.dtypes))] + ' Right columns: ' + ['    ' + k +': ' + v + '\n' for k, v in zip(right_df.columns, right_df.dtypes)])


    if compare_inner_outer:
        if left_on == 'index' and right_on == 'index':
            df_inner = pd.merge(left_df, right_df, how='inner', left_index=True, right_index=True)
            df_outer = pd.merge(left_df, right_df, how='outer', left_index=True, right_index=True)
        elif left_on == 'index':
            df_inner = pd.merge(left_df, right_df, how='inner', left_index=True, right_on=right_on)
            df_outer = pd.merge(left_df, right_df, how='outer', left_index=True, right_on=right_on)      
        elif right_on == 'index':
            df_inner = pd.merge(left_df, right_df, how='inner', left_on=left_on, right_index=True)
            df_outer = pd.merge(left_df, right_df, how='outer', left_on=left_on, right_index=True)
        else:
            if not left_on in left_df.columns:
                raise NameError('Left merge column not in left df columns: ' + left_on + ' not in ' + str(left_df.columns))
            if not left_on in left_df.columns:
                raise NameError('Right merge column not in right df columns: ' + right_on + ' not in ' + str(right_df.columns))            
            df_inner = pd.merge(left_df, right_df, how='inner', left_on=left_on, right_on=right_on)    
            df_outer = pd.merge(left_df, right_df, how='outer', left_on=left_on, right_on=right_on)    
            
        if how == 'inner':
            df = df_inner
        elif how == 'outer':
            df = df_outer
        else:
            if left_on == 'index' and right_on == 'index':
                df = pd.merge(left_df, right_df, how=how, left_index=True, right_index=True)
            elif left_on == 'index':
                df = pd.merge(left_df, right_df, how=how, left_index=True, right_on=right_on)     
            elif right_on == 'index':
                df = pd.merge(left_df, right_df, how=how, left_on=left_on, right_index=True)          
            else:
                df = pd.merge(left_df, right_df, how=how, left_on=left_on, right_on=right_on)     
                
        comparison_dict = hb.df_compare_column_contents_as_dict(df_outer[left_on], df_outer[right_on])
        
        if verbose:
            hb.log('Comparison of entries in left and right after merge: ' + hb.print_iterable(comparison_dict, return_as_string=True))
        
        if not supress_warnings:
            if len(comparison_dict['left_only']) > 0:
                hb.log('\nWARNING!\nIn hb.df_merge, left had non-shared values in merge-col: ' + str(comparison_dict['left_only'])[:100] + '...')
            if len(comparison_dict['right_only']) > 0:
                hb.log('\nWARNING!\nIn hb.df_merge, right had non-shared values in merge-col: ' + str(comparison_dict['right_only'])[:100] + '...')
            
    else:
        if left_on == 'index' and right_on == 'index':
            df = pd.merge(left_df, right_df, how=how, left_index=True, right_index=True)
        elif left_on == 'index':
            df = pd.merge(left_df, right_df, how=how, left_index=True, right_on=right_on)     
        elif right_on == 'index':
            df = pd.merge(left_df, right_df, how=how, left_on=left_on, right_index=True)          
        else:
            df = pd.merge(left_df, right_df, how=how, left_on=left_on, right_on=right_on)    

    if verbose:
        hb.log('Finished merge. Found the following DF:\n' + str(df) +'\n which has columns ' + str(list(df.columns.values)))
        
    if left_geometry is not None:
        df = pd.merge(df, left_geometry, how='outer', on=left_on)
        
        # print('df', df)
        
        # Convert the df to a geodataframe
        df = gpd.GeoDataFrame(df, geometry='geometry')
        
    # NYI fill_left_col_nan_with_right_value
    ## Have to think this through. Would those inherit the geometry of right then?]
    return df

def df_fill_left_col_nan_with_right_value(df, left_col, right_col, output_col_name=None):
    
    # Combines two columns, filling missing values of left with the value of right
    # while also checking that no value in left does not equal the value in right
    # good for validating merge.
    
    if output_col_name is None:
        output_col_name = left_col
    
    left_series = df[left_col]
    right_series = df[right_col]
    
    mismatch = df[left_col] != df[right_col]
    mismatch_df = df[df[left_col] != df[right_col]][[left_col, right_col]]
    
    # Drop where at least one column has a nan
    mismatch_df = mismatch_df.dropna()
    
    # if len(mismatch_df) > 0:
    #     raise NameError('Mismatched values in columns ' + left_col + ' and ' + right_col + ' in dataframe ' + str(df) + ' at indices ' + str(mismatch_df.index.values))
    
    output_col_name_temp = output_col_name + '_' + hb.random_alphanumeric_string()
    df[output_col_name_temp] = np.where(left_series.isnull(), right_series, left_series)

    # Drop the two columns that were merged
    df = df.drop([left_col, right_col], axis=1)
    
    columns = {output_col_name_temp: output_col_name}
    df.rename(columns=columns, inplace=True)

    return df



# TODOO Move this to a new dataframe_utils file.
def df_reorder_columns(input_df, initial_columns=None, prespecified_order=None, remove_columns=None, sort_method=None):
    """If both initial_columns and prespecified_order are given, initial columns will override. Initial columns will also
    override remove columns. sort_method can be alphabetic or reverse_alphabetic."""
    if initial_columns is None:
        initial_columns = []
    if prespecified_order is None:
        prespecified_order = []
    if initial_columns is None:
        initial_columns = []
    if remove_columns is None:
        remove_columns = []

    if len(prespecified_order) <= 0:

        if sort_method == 'alphabetic':
            sorted_columns = sorted(list(input_df.columns))
        elif sort_method == 'reverse_alphabetic':
            sorted_columns = sorted(list(input_df.columns), reverse=True)
        else:
            sorted_columns = list(input_df.columns)
    else:
        sorted_columns = prespecified_order

    final_columns = initial_columns + [i for i in sorted_columns if i not in initial_columns and i not in remove_columns]

    return input_df[final_columns]


def convert_py_script_to_jupyter(input_path):
    output_lines = []

    output_lines.append('#%% md')
    output_lines.append('')
    output_lines.append('# ' + hb.file_root(input_path))
    output_lines.append('')

    current_state = 'md'
    previous_state = 'md'

    with open(input_path) as fp:
        for line in fp:
            line = line.replace('\n', '')
            if line != '':

                if line.replace(' ', '')[0] == '#':
                    current_state = 'md'
                else:
                    current_state = 'py'
                # print(current_state + ': ', line, line)

                if current_state != previous_state:
                    if current_state == 'md':
                        output_lines.append('#%% md')
                    elif current_state == 'py':
                        output_lines.append('#%%')
                    else:
                        raise NameError('wtf')
                    previous_state = current_state

                if current_state == 'md':
                    to_append = line.split('#', 1)[1].lstrip()
                    output_lines.append(to_append)
                elif current_state == 'py':
                    output_lines.append(line)
                else:
                    raise NameError('wtf')

                # output_lines.append(line + '\n')
            else:
                # print(current_state + ': ', 'BLANK LINE', line)
                output_lines.append('')

    for line in output_lines:
        print(line)

    # ## DOESNT WORK BECAUSE NEED TO STRUCTURE JSON AS WELL, better is just to copy paste into pycharm lol
    # with open(output_path, 'w') as fp:
    #     for line in output_lines:
    #         print(line)
    #         fp.write(line)

def flatten_nested_dictionary(input_dict, return_type='values'):
    def walk_dictionary(d, return_type):
        for key, value in d.items():

            if isinstance(value, dict):
                yield from walk_dictionary(value, return_type)
            else:
                if return_type == 'both':
                    yield (key, value)
                elif return_type == 'keys':
                    yield key
                elif return_type == 'values':
                    yield value

    if return_type == 'both':
        to_return = {}
        returned_list = list(walk_dictionary(input_dict, return_type=return_type))
        for i in returned_list:
            to_return[i[0]] = i[1]
        return to_return
    elif return_type == 'keys':
        return list((walk_dictionary(input_dict, return_type=return_type)))
    elif return_type == 'values':
        return list((walk_dictionary(input_dict, return_type=return_type)))

def flatten_list(input_list):
    stack = input_list[::-1]
    flat_list = []
    while stack:
        element = stack.pop()
        if isinstance(element, list):
            stack.extend(element[::-1])
        else:
            flat_list.append(element)
    return flat_list

def get_attributes_of_object_as_list_of_strings(input_object):
    return [a for a in dir(input_object) if not a.startswith('__') and not callable(getattr(input_object, a))]

def get_reclassification_dict_from_df(input_df_or_path, src_id_col='src_id', dst_id_col='dst_id', src_label_col='src_label', dst_label_col='dst_label'):
    if isinstance(input_df_or_path, str):
        df = pd.read_csv(input_df_or_path)
    else:
        df = input_df_or_path
    src_ids = []
    src_labels = []
    dst_ids = []
    dst_labels = []

    dst_to_src_reclassification_dict = {}
    src_to_dst_reclassification_dict = {}
    dst_to_src_labels_dict = {}
    src_to_dst_labels_dict = {}
    for index, row in df.iterrows():
        dst_id = row[dst_id_col]
        dst_label = row[dst_label_col]
        src_id = row[src_id_col]
        src_label = row[src_label_col]
        if not pd.isna(dst_id):
            dst_ids.append(dst_id)
        if not pd.isna(dst_label):
            dst_labels.append(dst_label)

        if not pd.isna(dst_id):
            if dst_id not in dst_to_src_reclassification_dict:
                dst_to_src_reclassification_dict[int(dst_id)] = []

            if src_id not in src_to_dst_reclassification_dict:
                src_to_dst_reclassification_dict[int(src_id)] = int(dst_id)

            if src_label not in src_to_dst_labels_dict:
                src_to_dst_labels_dict[src_label] = dst_label

            if dst_label not in dst_to_src_labels_dict:
                dst_to_src_labels_dict[str(dst_label)] = []

            try:
                if not pd.isna(row[src_id_col]):
                    dst_to_src_reclassification_dict[dst_id].append(int(row[src_id_col]))
                    src_ids.append(int(row[src_id_col]))

            except:
                L.debug('Failed to read ' + str(dst_id) + ' as int from ' + str(input_df_or_path) + ' so skipping.')

            try:
                if not pd.isna(row[src_label_col]):
                    dst_to_src_labels_dict[dst_label].append(row[src_label_col])
                    src_labels.append(row[src_label_col])
            except:
                L.debug('Failed to read ' + str(dst_label) + ' as int from ' + str(input_df_or_path) + ' so skipping.')
    return_dict = {}
    return_dict['dst_to_src_reclassification_dict'] = dst_to_src_reclassification_dict  # Dict of one-to-many keys to lists of what each dst_key should be mapped to from each src_key. Useful when aggrigating multiple layers to a aggregated dest type
    return_dict['src_to_dst_reclassification_dict'] = src_to_dst_reclassification_dict # Dict of one to one src to dst mapping. Useful when going to a specific value.
    return_dict['dst_to_src_labels_dict'] = dst_to_src_labels_dict # Dictionary of lists of labels that map to each dst label
    return_dict['src_ids'] = remove_duplicates_in_order(src_ids) # Unique list of src_ids
    return_dict['dst_ids'] = remove_duplicates_in_order(dst_ids) # Unique list of dst_ids
    return_dict['src_labels'] = remove_duplicates_in_order(src_labels) # Unique list of src_labels
    return_dict['dst_labels'] = remove_duplicates_in_order(dst_labels) # Unique list of dst_labels
    return_dict['src_ids_to_labels'] = {k: v for k, v in zip(return_dict['src_ids'], return_dict['src_labels'])} # one-to-one dictionary of src ids to labels
    return_dict['dst_ids_to_labels'] = {k: v for k, v in zip(return_dict['dst_ids'], return_dict['dst_labels'])} # one-to-one dictionary of dst ids to labels
    return_dict['src_labels_to_ids'] = {k: v for k, v in zip(return_dict['src_labels'], return_dict['src_ids'])} # one-to-one dictionary of src labels to ids
    return_dict['dst_labels_to_ids'] = {k: v for k, v in zip(return_dict['dst_labels'], return_dict['dst_ids'])} # one-to-one dictionary of dst labels to ids

    return return_dict

def assign_df_row_to_object_attributes(input_object, input_row):
    for attribute_name, attribute_value in list(zip(input_row.index, input_row.values)):
        setattr(input_object, attribute_name, attribute_value)

def call_conda_info():
    command = 'conda info'
    output = subprocess.check_output(command)
    print('output', output)
    return output

def get_list_of_conda_envs_installed(include_dirs=True):
   
    command = 'conda info --envs'
    output = subprocess.check_output(command)

    output_as_list = str(output).split('\\r\\n')
    output_replaced = str(output).replace('\\r\\n', '\\\\')
    output_split = output_replaced.split(' ')
    if include_dirs:
        pared_list = []
        
        for c, i in enumerate(output_as_list[3:]):
            j = i.split(' ')[-1]
            k = j.replace('\\\\', '/')

            # Check if j is a directory
            if os.path.isdir(k):
                pared_list.append(k)

    else:
        pared_list = [i.split(' ')[0] for i in output_as_list[2:]]
    return pared_list

def check_if_library_in_conda_env(library_name, conda_env_name):

    """Check if a package is installed in a specific Conda environment."""
    try:
        call_conda_info()
        # Run 'conda list' in the specified environment
        result = subprocess.run(['conda', 'list', '-p', conda_env_name, library_name], stdout=subprocess.PIPE, text=True)
        if library_name in result.stdout:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error checking package {library_name} in environment at {conda_env_name}: {e}")
        return False

def check_which_conda_envs_have_library_installed(library_name):
    envs_list = get_list_of_conda_envs_installed(include_dirs=True)
    
    envs_with_library = []
    for env_name in envs_list:
        if check_if_library_in_conda_env(library_name, env_name):
            envs_with_library.append(env_name)
    return envs_with_library
        


def check_conda_env_exists(env_name):
    envs_installed = get_list_of_conda_envs_installed()
    hb.log('envs_installed', envs_installed)
    if any([env_name in i for i  in envs_installed]):
        return True
    else:
        return False


def get_first_extant_path(relative_path, possible_dirs, verbose=False):
    do_deprecation_statement = 1
    if do_deprecation_statement:
        hb.log('hb.get_first_extant_path is deprecated. Use p.get_path() instead. This fucntion was called via ', relative_path, possible_dirs)
    # Searches for a file in a list of possible directories and returns the first one it finds.
    # If it doesn't find any, it returns the first one it tried.
    # If it was given None, just return None

    if hb.path_exists(relative_path):
        return relative_path

    # Check if it's relative
    if relative_path is not None:
        if relative_path[1] == ':':
            hb.log('The path given to hb.get_first_extant_path() does not appear to be relative (nor does it exist at the unmodified path): ' + str(relative_path) + ', ' + str(possible_dirs))

    for possible_dir in possible_dirs:
        if relative_path is not None:
            path = os.path.join(possible_dir, relative_path)
            if verbose:
                hb.log('Checking for path: ' + str(path))
            if hb.path_exists(path, verbose=verbose):
                return path
        else:
            return None
    
    # If it was neither found nor None, THEN return the path constructed from the first element in possible_dirs
    path = os.path.join(possible_dirs[0], relative_path)
    return path



def path_to_url(input_path, local_path_to_strip, url_start=''):
    splitted_path = hb.split_assume_two(input_path.replace('\\', '/'), local_path_to_strip.replace('\\', '/')) 
    right_path = splitted_path[1]
    if right_path.startswith('/'):
        right_path = right_path[1:]
    url = os.path.join(url_start, right_path)
    url = url.replace('\\', '/')

    return url

def url_to_path(input_url, left_path, path_start):
    splitted_path = hb.split_assume_two(input_url, left_path) 

    path = os.path.join(path_start, left_path, splitted_path[1])
    path = path.replace('/', '\\')

    return path

def remove_duplicates_in_order(lst):
  """
  Removes duplicates from a list while preserving the order of the remaining elements.

  Args:
    lst: The list to remove duplicates from.

  Returns:
    A new list without duplicates.
  """

  seen = set()
  new_lst = []
  for item in lst:
    if item not in seen:
      seen.add(item)
      new_lst.append(item)

  return new_lst

def df_convert_column_type(input_df, type_to_replace, new_type, columns='all', ignore_nan=False, verbose=False):
    # Refer to types as numpy types    
    
    hb.log('WARNING!  this failed when there were nans in the field being inted.', level=200)
    ### One possiblie solution is to replace with intable and nanable types as below
    # # Manually set dtype for two remaining cols. This was not possible to fix via the function
    # # df_convert_column_type for unknown reasons, but probably because the nan-value in gadm
    # # combined with Operation on a Copy Warning.
    # df['gadm_r263_id'] = df['gadm_r263_id'].astype('Int64')
    # df['gtapv7_r251_id'] = df['gtapv7_r251_id'].astype('Int64')

    if columns == 'all':
        columns = input_df.columns
        
    for col in columns:
        hb.log('Converting column ' + str(col) + ' from ' + str(type_to_replace) + ' to ' + str(new_type), level=100)
        
        # check if it has the dtype attribute
        if hasattr(input_df[col], 'dtype'):
        
            if input_df[col].dtype == type_to_replace:
                if ignore_nan:
                    to_fill = -999999991
                    its_in_it = to_fill in input_df[col].values
                    if its_in_it:
                        raise NameError('Really wtf... what are the odds of that. please submit a pull request to fix this improbable case.')
                    else:
                        # Test if there are ONLY nans
                        if input_df[col].isnull().values.all():
                            if verbose:
                                hb.log('All values in column ' + str(col) + ' are nan, so skipping.', level=10)
                        else:
                            pd.set_option('mode.chained_assignment', None)
                            input_df[col] = input_df[col].replace(np.nan, to_fill)
                            input_df[col] = input_df[col].astype(new_type) 
                            input_df[col] = input_df[col].replace(to_fill, np.nan)
                            pd.set_option('mode.chained_assignment', 'warn')
                            
                else:
                    input_df.loc[:, col] = input_df[col].astype(new_type)
    return input_df


def list_find_duplicates(lst):
    seen = set()
    duplicates = set()
    for x in lst:
        if x in seen:
            duplicates.add(x)
        else:
            seen.add(x)
    return duplicates


def arrays_equal_ignoring_order(array1, array2, ignore_values=None):
    unique1, counts1 = np.unique(array1.astype(str), return_counts=True)
    unique2, counts2 = np.unique(array2.astype(str), return_counts=True)
    
    if ignore_values is not None:
        for ignore_value in ignore_values:
            # Take that O(n) = 1!
            if unique1[0] == ignore_value:
                unique1 = unique1[1:]
                counts1 = counts1[1:]
            if unique2[0] == ignore_value:
                unique2 = unique2[1:]
                counts2 = counts2[1:]
            if unique1[-1] == ignore_value:
                unique1 = unique1[:-1]
                counts1 = counts1[:-1]
            if unique2[-1] == ignore_value:
                unique2 = unique2[:-1]
                counts2 = counts2[:-1]
                
    identical = np.array_equal(np.asarray((unique1, counts1)).T, np.asarray((unique2, counts2)).T)
    if not identical:
        hb.log('Compared arrays and found different unique, count sets: ', unique1, counts1, unique2, counts2, level=100)
    return identical

def hash_file_path(file_path):
    """Compute and return the SHA-256 hash of a binary-redable file (like a png) specified by its file path.
    And return a string of the hash."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except FileNotFoundError:
        return "File not found."
    except Exception as e:
        return f"An error occurred: {e}"
    
    
def concatenate_list_of_df_paths(input_df_paths, output_path=None, verbose=False):
    """Concatenate a list of dataframes into a single dataframe. Return DF. Also write to output_path if given"""
    dfs = []
    shapes = []
    for df_path in input_df_paths:
        if verbose:
            hb.log('Reading ' + str(df_path))
        if not hb.path_exists(df_path):
            raise NameError('Path not found: ' + str(df_path))
        
        df = pd.read_csv(df_path)
        
        # Get only the number of cols, cause we're concatentating vertically
        shapes.append(df.shape[1])
        
        dfs.append(df)
    
    # Check if all same shape
    if len(set(shapes)) > 1:
        raise NameError('Dataframes are not all the same shape: ' + str(shapes))
    
    concatenated_df = pd.concat(dfs)
    
    if output_path:
        hb.create_directories(output_path)
        concatenated_df.to_csv(output_path, index=False)
    return concatenated_df

def is_nan(input_):
    return isnan(input_)

def isnan(input_):
    if isinstance(input_, str):
        if input_.lower() == 'nan':
            return True
        else:
            return False
    elif not input_:
        return False
    else:
        try:
            return np.isnan(input_)
        except:
            False
    

def df_move_col_before_col(df, col_to_move, col_to_put_it_before):
    cols = df.columns.tolist()
    cols.remove(col_to_move)
    idx = cols.index(col_to_put_it_before)
    cols.insert(idx, col_to_move)
    return df[cols]

def df_move_col_after_col(df, col_to_move, col_to_put_it_after):
    cols = df.columns.tolist()
    cols.remove(col_to_move)
    idx = cols.index(col_to_put_it_after)
    cols.insert(idx + 1, col_to_move)
    return df[cols]

def parse_flex_to_python_object(input_df_element, verbose=False):
    
    if input_df_element == 'year, counterfactual':
        pass
    if input_df_element == 'aggregation:v11_s26_r50, year:2050':
        pass
    # Check if it evaluates to none
    if hb.isnan(input_df_element):
        return None
    elif input_df_element is None:
        return None
    elif input_df_element == 'None':
        return None
    elif input_df_element == '':
        return None
    

    
    if 'int' in str(type(input_df_element)):
        return input_df_element
    
    if 'float' in str(type(input_df_element)):
        return input_df_element
    
    if 'str' in str(type(input_df_element)) or 'object' in str(type(input_df_element)):
        
        # Strip leading and trailing spaces
        input_df_element = input_df_element.strip()    
    
        # Check if it's verbatim json
        is_json = False
        if (input_df_element.startswith('{') and input_df_element.endswith('}')) or (input_df_element.startswith('[') and input_df_element.endswith(']')):
            
        #     if input_df_element.startswith('{'):
        #         split_element = input_df_element[1:-1].split(',')
        #         for i in split_element:
        #             j = i.split(':')  
        #             if len(j) > 1:                   
        #                 for c, k in enumerate(j): # Strip leading and trailing spaces from each element
        #                     j[c] = j[c].strip()                    
        #                 # add quotation marks if needed
        #                 if not j[0].startswith('"') and not j[0].startswith("'"):
        #                     # no .isdigit() check because json spec says it has to be a string in the keys
        #                     input_df_element = input_df_element.replace(j[0], '"' + j[0] + '"')
        #                 if not j[1].startswith('"') and not j[1].startswith("'"):
        #                     # Check if the first element is numeric
        #                     if not j[1][0].isdigit():
        #                         input_df_element = input_df_element.replace(j[1], '"' + j[1] + '"')
                                
                        
            
            try:            
                s = hb.json_helper.parse_json_with_detailed_error(input_df_element)
                is_json = True
                return s
            except:
                is_json = False
                raise NameError('Failed to parse json: ' + str(input_df_element) + ' as json. If something starts with a { or [ and ends with a } or ] it should be json, but if you have syntax error, like a missing comma or qutation mark, it will fail.')  
            
            
        could_be_json = False
        if not is_json and ',' in input_df_element and ':' not in input_df_element:
            input_df_element = '[' + input_df_element + ']'
            split_element = split_respecting_nesting(input_df_element[1:-1], ',')
            for c, i in enumerate(split_element):
                split_element[c] = i.strip()
                if split_element[c].startswith('[') or split_element[c].startswith('{'):
                    split_element[c] = parse_flex_to_python_object(split_element[c])
            input_df_element = split_element    
            
        if not is_json and ':' in input_df_element:
            input_df_element = '{' + input_df_element + '}'

            if input_df_element.startswith('{'):
                split_element = split_respecting_nesting(input_df_element[1:-1], ',')
                # split_element = input_df_element[1:-1].split(',')
                for i in split_element:
                    j = i.split(':')  

                    if len(j) > 1:                  
                        for c, k in enumerate(j): # Strip leading and trailing spaces from each element
                            j[c] = j[c].strip()                    
                        # add quotation marks if needed
                        if not j[0].startswith('"') and not j[0].startswith("'") and not j[0].startswith('[') and not j[0].startswith('{'):
                            input_df_element = input_df_element.replace(j[0], '"' + j[0] + '"')
                        if not j[1].startswith('"') and not j[1].startswith("'") and not j[1].startswith('[') and not j[1].startswith('{'):
                            # Check if the first element is numeric
                            if not j[1][0].isdigit():
                                input_df_element = input_df_element.replace(j[1], '"' + j[1] + '"')
                        if j[1].startswith('[') or j[1].startswith('{'):
                            j[1] = parse_flex_to_python_object(j[1])
                        
        try:            
            s = hb.json_helper.parse_json_with_detailed_error(input_df_element)
            could_be_json = True
            return s
        except:
            could_be_json = False                
            

        # Then it's not jsonable
        return input_df_element
                
        
                
                

    
    
    
    # print('input_df_string', input_df_string)
    
    # terminal_types = ['int(', 'float(', 'str(', 'bool(', '"', "'", '{', '[']
    
    # # Cast to string becasue pandas will interpret ints as ints lol!
    # input_df_string = str(input_df_string)
    
    # # Check if input_df_string starts with a terminal type
    # for terminal_type in terminal_types:
    #     if input_df_string.startswith(terminal_type):
    #         if terminal_type == 'int(':
    #             return int(json.loads(input_df_string[4:-2]))
    #         elif terminal_type == 'float(':
    #             return float(json.loads(input_df_string[6:-2]))
    #         elif terminal_type == 'str(':
    #             return str(json.loads(input_df_string[4:-2]))
    #         elif terminal_type == 'bool(':
    #             return bool(json.loads(input_df_string[5:-2]))
    #         elif terminal_type == '"':
    #             return str(json.loads(input_df_string[1:-1]))
    #         elif terminal_type == "'":
    #             return str(json.loads(input_df_string[1:-1]))
    #         elif terminal_type == "{":
    #             return json.loads(input_df_string)
    #         elif terminal_type == "[":
    #             return json.loads(input_df_string)
    #         else:
    #             'not a terminal type'
    # # Then it's a basic type
    # try:
    #     float(input_df_string)
    #     floatable = True
    # except:
    #     floatable = False
    
    # try:
    #     int(input_df_string)
    #     intable = True  
    # except:
    #     intable = False
        
    # if '.' in input_df_string and floatable:
    #     return float(input_df_string)
    # elif intable:
    #     return int(input_df_string)
    # else:
    #     return str(input_df_string)    

    # # Check if it's an iterator
    # explicit_iterator_types = ['[', '{']    
    # for explicit_iterator_type in explicit_iterator_types:
    #     if input_df_string.startswith(explicit_iterator_type):
    #         if explicit_iterator_type == '[':
    #             input_df_string = input_df_string.replace(', ', ',').replace(' ', ',')
    #             return [parse_flex_to_python_object(i) for i in input_df_string[1:-2].split(',')]
    #         elif explicit_iterator_type == '{':
    #             input_df_string = input_df_string.replace(', ', ',').replace(' ', ',')
    #             return {i.split(':')[0]: parse_flex_to_python_object(i.split(':')[1]) for i in input_df_string[1:-2].split(',')}
            
            
    # # Check if it's an implied iterator
    # has_implicit_iterator = False
    # implicit_iterator_types = [', ', ' ', ',']
    # for implicit_iterator_type in implicit_iterator_types:
    #     if implicit_iterator_type in input_df_string:
    #         has_implicit_iterator = True
            
    # if has_implicit_iterator:
    #     # Replace all of them with a uniform one
    #     input_df_string = input_df_string.replace(implicit_iterator_types[0], ',').replace(implicit_iterator_types[1], ',')
    #     split_input = input_df_string.split(implicit_iterator_types[-1])
    #     for item in split_input:
    #         if ':' in item:
    #             return {item.split(':')[0]: parse_flex_to_python_object(item.split(':')[1]) }
    #         else:
    #             return [parse_flex_to_python_object(i) for i in item]
            
    # # Then it's a basic type
    # try:
    #     float(input_df_string)
    #     floatable = True
    # except:
    #     floatable = False
    
    # try:
    #     int(input_df_string)
    #     intable = True  
    # except:
    #     intable = False
        
    # if '.' in input_df_string and floatable:
    #     return float(input_df_string)
    # elif intable:
    #     return int(input_df_string)
    # else:
    #     return str(input_df_string)
    
    
    
    
    
    # Check if it's json
    
    # # Check if it is an iterable
    # if ' ' in input_df_string or ',' in input_df_string:
    #     split = input_df_string.split(' ').split(', ').split(',')
    #     for i in split:
    #         if ':' in i:
    #             output_type = 'dict'
    #             to_return = {}
    #         elif i.startswith('{'):
    #             output_type = 'dict'
    #             to_return = {}
    #         elif i.startswith('['):
    #             output_type = 'list'
    #             to_return = []
    #         elif i.startswith('int('):
    #             output_type = 'int'
    #         elif i.startswith('float('):
    #             output_type = 'float'
    #         elif i.startswith('str('):
    #             output_type = 'str'
    #         else:
    #             output_type = 'list'
    #             to_return = []
        
    #     for i in split:
    #         if output_type == 'dict':
    #             if ':' in i:
    #                 split2 = i.split(':')
    #                 key = split2[0]
    #                 value = split2[1]
    #                 value = parse_flex_to_python_object(value)
    #                 to_return[key] = value
    #         elif output_type == 'int':
    #             to_return = int(i[4:-1])
    #         elif output_type == 'float':
    #             to_return = float(i[6:-1])
    #         elif output_type == 'str':
    #             to_return = str(i[4:-1])
    #         else:
    #             to_return.append(parse_flex_to_python_object(i))
    # else:
        
    #     if ':' in input_df_string:
    #         output_type = 'dict'
    #         to_return = {}
    #         split = input_df_string.split(':')
    #         to_return[split[0]] = split[1]
    #     elif input_df_string.startswith('{'):
    #         output_type = 'dict'
    #         to_return = {}
    #         removed_brackets = input_df_string[1:-1]
    #         split = input_df_string.split(':')
    #         to_return[split[0]] = split[1]            
            
    #     elif input_df_string.startswith('['):
    #         output_type = 'list'
    #         to_return = []
    #         to_return.append(input_df_string(i))
    #     elif i.startswith('int('):
    #         output_type = 'int'
    #     elif i.startswith('float('):
    #         output_type = 'float'
    #     elif i.startswith('str('):
    #         output_type = 'str'
    #     else:
    #         output_type = 'list'
    #         to_return = []        
    
        

    #     if input_df_string.startswith('int('):
    #         to_return = int(input_df_string[4:-1])
    #     elif input_df_string.startswith('float('):
    #         to_return = float(input_df_string[6:-1])
    #     elif input_df_string.startswith('str('):
    #         to_return = str(input_df_string[4:-1])
    #     else:
    #         to_return = input_df_string

    # if verbose:
    #     hb.log('parse_flex_to_python_object:\n' + input_df_string + '\nparsed to\n' + str(to_return))
    # return to_return



    
def split_respecting_nesting(s, delimiter):
    parts = []
    bracket_level = 0
    brace_level = 0
    start_index = 0
    
    for i, char in enumerate(s):
        if char == '[':
            bracket_level += 1
        elif char == ']':
            bracket_level -= 1 # Consider error check: level shouldn't go below 0
        elif char == '{':
            brace_level += 1
        elif char == '}':
            brace_level -= 1 # Consider error check: level shouldn't go below 0
        elif char == delimiter and bracket_level == 0 and brace_level == 0:
            # Found a top-level comma
            parts.append(s[start_index:i].strip()) # Add the segment, stripping whitespace
            start_index = i + 1 # Start the next segment after the comma
    
    # Add the last part (from the last comma to the end)
    parts.append(s[start_index:].strip()) 
    
    # Filter out potentially empty strings if the input starts/ends with commas
    # or has consecutive top-level commas (though not in the example)
    # parts = [p for p in parts if p] # Optional: remove empty strings if needed

    return parts
    
    
    
    
    
    
    