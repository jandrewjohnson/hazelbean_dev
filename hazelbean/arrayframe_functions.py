import os, sys, warnings, logging, inspect

from osgeo import gdal, osr, ogr
import numpy as np
import hazelbean as hb

L = hb.get_logger('arrayframe_functions', logging_level='warning') # hb.arrayframe.L.setLevel(logging.DEBUG)

def raster_calculator_flex(input_, op, output_path, **kwargs): #KWARGS: datatype=None, ndv=None, gtiff_creation_options=None, add_overviews=False
    """Convenience wrapper sending parsed inputs to raster_calculator_hb"""
    # If input is a string, put it into a list
    if isinstance(input_, str):
        input_ = [input_]
    elif isinstance(input_, hb.ArrayFrame):
        input_ = input_.path

    final_input = [''] * len(input_)
    for c, i in enumerate(input_):
        if isinstance(i, hb.ArrayFrame):
            final_input[c] = i.path
        else:
            final_input[c] = i
    input_ = final_input

    # Determine size of inputs
    if isinstance(input_, str) or isinstance(input_, hb.ArrayFrame):
        input_size = 1
    elif isinstance(input_, list):
        input_size = len(input_)
    else:
        raise NameError('input_ given to raster_calculator_flex() not understood. Give a path or list of paths.')

    # # Check that files exist.
    # for i in input_:
    #     if not os.path.exists(i):
    #         raise FileNotFoundError(str(input_) + ' not found by raster_calculator_flex()')

     # Verify datatypes
    datatype = kwargs.get('datatype', None)
    if not datatype:
        datatypes = [hb.get_datatype_from_uri(i) for i in input_ if type(i) not in [bool, float, int]]
        if len(set(datatypes)) > 1:
            L.info('Rasters given to raster_calculator_flex() were not all of the same type. Defaulting to using first input datatype.')
        datatype = datatypes[0]

    # Check NDVs.
    ndv = kwargs.get('ndv', None)
    if ndv is None:
        ndvs = [hb.get_ndv_from_path(i) for i in input_ if type(i) not in [bool, float, int]]
        if len(set(ndvs)) > 1:
            L.info('NDVs used in rasters given to raster_calculator_flex() were not all the same. Defaulting to using first value.')
        ndv = ndvs[0]

    gtiff_creation_options = kwargs.get('gtiff_creation_options', None)
    if not gtiff_creation_options:
        gtiff_creation_options = hb.DEFAULT_GTIFF_CREATION_OPTIONS


    # Build tuples to match the required format of raster_calculator.
    if input_size == 1:
        if isinstance(input_[0], str):
            input_tuples_list = [(input_[0], 1)]
        else:
            input_tuples_list = [(input_[0].path, 1)]
    else:
        if isinstance(input_[0], str):
            input_tuples_list = [(i, 1) for i in input_]
        if isinstance(input_[0], hb.ArrayFrame):
            input_tuples_list = [(i.path, 1) for i in input_]
        else:
            input_tuples_list = [(i, 1) for i in input_]

    # CONFUSED here, why did i have it this structure?
    for c, i in enumerate(input_tuples_list):
        if type(i[0]) in [int, float, list, bool, dict]:
            input_tuples_list[c] = (i[0], 'raw')


    # Check that the op matches the number of rasters.
    if len(inspect.signature(op).parameters) != input_size:
        raise NameError('op given to raster_calculator_flex() did not have the same number of parameters as the number of rasters given.')

    L.info('Launching raster_calculator_hb on ', str(input_tuples_list), '    \nto output path', output_path)
    hb.raster_calculator_hb(input_tuples_list, op, output_path,
                         datatype, ndv, gtiff_creation_options=gtiff_creation_options)

    if kwargs.get('add_overviews'):
        hb.add_overviews_to_path(output_path)


    
    return 


def apply_op(op, output_path):
    input_ = 0
    raster_calculator_flex(input_, op, output_path)

def add(a_flex, b_flex, output_path):
    def op(a, b):
        return a + b
    hb.raster_calculator_flex([a_flex, b_flex], op, output_path)
    return hb.ArrayFrame(output_path)

def add_with_valid_mask(a_path, b_path, output_path, valid_mask_path, ndv):
    def op(a, b, valid_mask):
        return np.where(valid_mask==1, a + b, ndv)
    hb.raster_calculator_flex([a_path, b_path, valid_mask_path], op, output_path, ndv=ndv)
    return hb.ArrayFrame(output_path)

def add_smart(a, b, a_valid_mask, b_valid_mask, output_ndv, output_path):
    def op(a, b, a_valid_mask, b_valid_mask, output_ndv):
        return np.where((a_valid_mask==1 & b_valid_mask==1), a + b, output_ndv)
    hb.raster_calculator_flex([a, b, a.valid_mask, b.valid_mask], op, output_path, ndv=output_ndv)
    return hb.ArrayFrame(output_path)



def subtract(a_path, b_path, output_path):
    def op(a, b):
        return a - b
    hb.raster_calculator_flex([a_path, b_path], op, output_path)
    return hb.ArrayFrame(output_path)

def multiply(a_path, b_path, output_path):
    def op(a, b):
        return a * b
    hb.raster_calculator_flex([a_path, b_path], op, output_path)
    return hb.ArrayFrame(output_path)

def divide(a_path, b_path, output_path):
    def op(a, b):
        return a / b
    hb.raster_calculator_flex([a_path, b_path], op, output_path)
    return hb.ArrayFrame(output_path)

def greater_than(a_path, b_path, output_path):
    def op(a, b):
        return np.where(a > b, 1, 0)
    hb.raster_calculator_flex([a_path, b_path], op, output_path)
    return hb.ArrayFrame(output_path)

def a_greater_than_zero_b_equal_zero(a_path, b_path, output_path):
    def op(a, b):
        return np.where((a > 0) & (b==0), 1, 0)
    hb.raster_calculator_flex([a_path, b_path], op, output_path)
    return hb.ArrayFrame(output_path)

def proportion_change(after, before, output_path):
    def op(after, before):
        return (after - before) / before

    hb.raster_calculator_flex([after, before], op, output_path)
    return hb.ArrayFrame(output_path)


def af_where_lt_value_set_to(a, value, set_to, output_path):
    def op(a):
        return np.where(a < value, set_to, a)

    hb.raster_calculator_flex([a], op, output_path)
    return hb.ArrayFrame(output_path)



def tiled_sum(input_path):
    return_sum = 0
    for offsets, data in hb.iterblocks_hb(input_path):
        return_sum += np.sum(data)

    return return_sum

def tiled_num_nonzero(input_path):
    return_sum = 0
    for offsets, data in hb.iterblocks_hb(input_path):
        return_sum += np.count_nonzero(data)

    return return_sum
