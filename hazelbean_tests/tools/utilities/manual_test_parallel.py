### UNLIKE OTHER tests, this one requires base data for big files


import pathlib
from hazelbean.parallel import *
from hazelbean import parallel
from hazelbean import geoprocessing_extension
from hazelbean.geoprocessing_extension import *
import dask
import dask.distributed
import dask.config

from multiprocessing import Process, freeze_support
freeze_support()

# TODO make it so xds is returned and then have writing as separte step

run_all = 1

remove_temporary_files = 1
output_dir = 'data'

if __name__ == '__main__':

    # NOTE: All multiprocessing things need to be under a name == main block.
    from multiprocessing import Process, freeze_support
    freeze_support()
    import os
    import hazelbean as hb
    import numpy as np
    import pygeoprocessing as pgp
    import rioxarray

    import pathlib
    usr_dir = pathlib.Path.home()

    country_ids_300sec_path = os.path.join(usr_dir, "Files/base_data/pyramids/country_ids_300sec.tif")
    ha_per_cell_300sec_path = os.path.join(usr_dir, "Files/base_data/pyramids/ha_per_cell_300sec.tif")
    country_vector_path = os.path.join(usr_dir, "Files/base_data/pyramids/countries_iso3.gpkg")
    # Large test
    country_ids_10sec_path = os.path.join(usr_dir, "Files/base_data/pyramids/country_ids_10sec.tif")
    country_ids_10sec_alt_path = os.path.join(usr_dir, "Files/base_data/pyramids/country_ids_10sec_alt.tif")
    ha_per_cell_10sec_path = os.path.join(usr_dir, "Files/base_data/pyramids/ha_per_cell_10sec.tif")

    # parallel.unique_count_dask(input_path, n_workers=16, threads_per_worker=2, memory_limit='8GB')

    test_array_sum = 0
    if test_array_sum or run_all:
        hb.timer('Starting test_array_sum')
        sum = hb.parallel.array_sum(country_ids_10sec_path)
        print('sum is ' + str(sum))
        hb.timer('Completed test_array_sum')

        do_comparison = 1
        if do_comparison:
            hb.timer('read start')
            a = hb.as_array(country_ids_10sec_path)
            hb.timer('sum_start')
            print(np.sum(a))
            hb.timer('simple sum end')

    test_array_op = 0
    if test_array_op or run_all:
        hb.timer('Starting test_array_op')
        # NOTE: much slower if you multiply by a python float. However, is only a little slower than int int if you multiply by np.float32()
        def op(x):
            return x * np.int32(2)       
        
        xds = hb.parallel.array_op(country_ids_10sec_path, op)
        hb.timer('Completed test_array_op')

    test_raster_calculator = 0
    if test_raster_calculator or run_all:

        # Performance note: much slower if you multiply by a python float. However, 
        # is only a little slower than int int if you multiply by np.float32()
        def op(x, y):
            return x * y * np.int32(20)
        temp_path = hb.temp('.tif', 'compute', remove_temporary_files, output_dir)
        hb.parallel.raster_calculator([country_ids_10sec_path, country_ids_10sec_alt_path], op, temp_path, use_client=0)

    test_cython_raster_calculator = 0
    if test_cython_raster_calculator or run_all:

        # After 1 day of attempting this, I gave up. Gonna stick with pygeoprocesing for now for CYTHON specific tasks. However
        # for non-cythonized functions (above) or numpy etc, raster_calculator with dask is great.

        # Performance note: much slower if you multiply by a python float. However, 
        # is only a little slower than int int if you multiply by np.float32()
        from hazelbean.calculation_core.cython_functions import reclassify_uint8_to_uint8_by_dict_with_dask, array_plus_one
        # op = reclassify_uint8_to_uint8_by_dict_with_dask
        op = array_plus_one
        replace_dict = {k: v for k, v in zip(range(0, 256), range(0, 256))}
        replace_dict[80] = 83

        temp_path = hb.temp('.tif', 'compute', remove_temporary_files, output_dir)
        hb.parallel.cython_raster_calculator(ha_per_cell_300sec_path, op, temp_path, use_client=0)
        print('done')


    do_this = 0
    if do_this or run_all:
        output_path = hb.temp('.tif', 'dict', remove_temporary_files, output_dir)
        hb.parallel.rewrite_raster_to_output_path(ha_per_cell_300sec_path, output_path)

        go_big = 0
        if go_big:
            hb.timer('big read write with client')
            output_path = hb.temp('.tif', 'dict', remove_temporary_files, output_dir)
            hb.parallel.read_then_write(ha_per_cell_10sec_path, output_path, use_client=1)
            hb.timer('big read write with client finished')
            output_path = hb.temp('.tif', 'dict', remove_temporary_files, output_dir)
            hb.parallel.rewrite_raster_to_output_path(ha_per_cell_10sec_path, output_path, use_client=0)
            hb.timer('big read write without client finished')


  
    do_this = 0
    if do_this or run_all:
        # Here, standard GDAL outperformed dask.
        hb.parallel.as_array(ha_per_cell_300sec_path)
        hb.timer(silent=True)
        hb.as_array(ha_per_cell_300sec_path)
        hb.timer('Finished standard as_array')

        go_big = 0
        if go_big:
            a = hb.parallel.as_array(country_ids_10sec_path, use_client=1)
            hb.timer(silent=True)
            b = hb.as_array(country_ids_10sec_path)
            hb.timer('Finished standard as_array')
            print(a)
            print(b)



  
    do_this = 0
    if do_this or run_all:
        
        def op(x, y, z):
            return dask.array.where(x == y, z, x)
        
        temp_path = hb.temp('.tif', 'reclass', remove_temporary_files, output_dir)
        hb.parallel.raster_calculator([country_ids_300sec_path, 238, 248], op, temp_path, use_client=0)


        go_big = 0
        if go_big:
            temp_path = hb.temp('.tif', 'reclass', remove_temporary_files, output_dir)
            hb.parallel.raster_calculator([country_ids_10sec_path, 238, 248], op, temp_path, use_client=0)

  
    do_this = 0
    if do_this or run_all:
        
        temp_path = hb.temp('.tif', 'replace', remove_temporary_files, output_dir)
        hb.parallel.raster_replace_value(country_ids_300sec_path, 238, 249, temp_path, use_client=0)


        go_big = 0
        if go_big:
            temp_path = hb.temp('.tif', 'replace', remove_temporary_files, output_dir)
            hb.parallel.raster_replace_value(country_ids_10sec_path, 238, 249, temp_path, use_client=0)

        do_comparison = 0
        if do_comparison:
            rules = {238: 249}
            temp_path = hb.temp('.tif', 'old_replace', remove_temporary_files, output_dir)
            hb.timer()
            hb.reclassify_raster(country_ids_10sec_path, rules, output_path=temp_path, output_data_type=1)
            hb.timer('Finished old replace')

print('Test complete.')