import os, sys, warnings, logging, inspect

from osgeo import gdal, osr, ogr
import numpy as np
import hazelbean as hb

L = hb.get_logger('arrayframe_numpy_functions', logging_level='warning') # hb.arrayframe.L.setLevel(logging.DEBUG)

def apply_op(op, output_path):
    input_ = 0
    hb.raster_calculator_flex(input_, op, output_path)

def add(a_path, b_path, output_path):
    def op(a, b):
        return a + b
    hb.raster_calculator_flex([a_path, b_path], op, output_path)
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



def tiled_sum(input_path):
    return_sum = 0
    for offsets, data in hb.iterblocks(input_path):
        return_sum += np.sum(data)

    return return_sum

def tiled_num_nonzero(input_path):
    return_sum = 0
    for offsets, data in hb.iterblocks(input_path):
        return_sum += np.count_nonzero(data)

    return return_sum
