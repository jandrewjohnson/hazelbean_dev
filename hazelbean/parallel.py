import rioxarray
import os
import concurrent
import numpy as np
import dask.array as da
import hazelbean as hb
import multiprocessing
import xarray as xr
import dask
from dask.diagnostics import ProgressBar
from dask.distributed import Client, LocalCluster, Lock
from dask.distributed import worker_client
import logging
from osgeo import gdal
# gdal.SetConfigOption("IGNORE_COG_LAYOUT_BREAK", "YES") 
# gdal.PushErrorHandler('CPLQuietErrorHandler')
import dask.distributed
import dask.config
dask.config.set({'logging.distributed': 'error'})

import pygeoprocessing as pgp
import geopandas as gpd
import pandas as pd

# pbar = ProgressBar()
# pbar.register()
# dask.config.set({'diagnostics.progress': 'None'})

L = hb.get_logger()

def array_sum(input_path, use_client=False):
    # Using the client is about 10x slower but provides an example of how to use a distributed cluster.
    if use_client:
        print('Launching array_sum using Dask. View progress at http://localhost:8787/status or view the file at ' + input_path)
        with LocalCluster(n_workers=16, threads_per_worker=2, memory_limit='8GB') as cluster, Client(cluster) as client:
            hb.timer()   
            xds = rioxarray.open_rasterio(input_path, chunks='auto', lock=Lock("rio", client=client) )
            delayed_computation = np.sum(xds)
            result_xds = delayed_computation.compute()
            result_array = result_xds.to_numpy()
        return result_array
    else:
        print('Launching array_sum using Dask based on input path: ' + input_path)
        input_xds = rioxarray.open_rasterio(input_path, chunks='auto', lock=False, )
        delayed_computation = np.sum(input_xds)
        result_xds = delayed_computation.compute()
        result_array = result_xds.to_numpy()
        return result_array

def array_op(input_path, op):

    # print('Launching array_op using Dask. View progress at http://localhost:8787/status or view the file at ' + input_path)
    print('Launching array_op using Dask based on input path: ' + input_path)
    input_xds = rioxarray.open_rasterio(input_path, chunks='auto', lock=False, )
    delayed_computation = op(input_xds)
    result_xds = delayed_computation.compute()
    # result_array = result_xds.to_numpy()
    return result_xds


def unique_count_dask(input_path, n_workers=16, threads_per_worker=2, memory_limit='8GB', use_client=False):
    import dask
    from dask.distributed import Client, LocalCluster, Lock

    if use_client:
        with LocalCluster(n_workers=n_workers, threads_per_worker=threads_per_worker, memory_limit=memory_limit) as cluster, Client(cluster) as client:

            L.info('Starting Local Cluster at http://localhost:8787/status')

            dask_array = rioxarray.open_rasterio(input_path, chunks=(1, 512 * 4, 512 * 4), lock=Lock("rio", client=client))
            dask_array_flat = dask.array.ravel(dask_array)

            unique_computation, counts_counts_computation = da.unique(dask_array_flat, return_counts=True)

            unique, counts = dask.compute(unique_computation, counts_counts_computation)
            result = dict(zip(unique, counts))

        return result
    else:
        L.info('Starting Local Cluster at http://localhost:8787/status')

        dask_array = rioxarray.open_rasterio(input_path, chunks=(1, 512 * 4, 512 * 4), lock=False)
        dask_array_flat = dask.array.ravel(dask_array)

        unique_computation, counts_counts_computation = da.unique(dask_array_flat, return_counts=True)

        unique, counts = dask.compute(unique_computation, counts_counts_computation)
        result = dict(zip(unique, counts))

        return result
    
def raster_calculator(inputs, op, output_path, n_workers=None, memory_limit=None, use_client=False, verbose=True):
    # inputs can be a string path or a list of string paths
    # op is a function to be computed in parallel chunks. it must have as many inputs as the number of input_paths. op must return an array
    # output_path is where the tiled set of op arrays is saved.
    
    from dask.distributed import Client, LocalCluster, Lock
    from dask.utils import SerializableLock

    if isinstance(inputs, str):
        inputs = [inputs]

    if not isinstance(inputs, list):
        raise NameError('dask_compute inputs must be a single path-string or a list of strings.')

    input_types = []
    for input_ in inputs:
        if hb.path_exists(input_):
            input_types.append('path')
        elif isinstance(input_, np.ndarray):
            input_types.append('array')
        elif isinstance(input_, dict):
            input_types.append('dict')
        else:
            input_types.append('raw')

    optimal_chunk_size = hb.spatial_utils.check_chunk_sizes_from_list_of_paths([i for c, i in enumerate(inputs) if input_types[c] == 'path'])[0]

    if n_workers is None:
        n_cpus = multiprocessing.cpu_count()
        n_workers = n_cpus - 1 

    if memory_limit is None:
        memory_limit = '8GB'

    threads_per_worker = 1 # Cause hyperthreading

    # I have found that using the client slows the process down considerably and creates larger files
    # I leave it as an option for when we create a full cluster.
    if use_client:
        print('Launching raster_calculator using Dask. View progress at http://localhost:8787/status or view the file at ' + output_path)

        with LocalCluster(n_workers=n_workers, threads_per_worker=threads_per_worker, memory_limit=memory_limit) as cluster, Client(cluster) as client, ProgressBar():
            if verbose:
                hb.timer('Starting client')

            # NYI
            xds0 = rioxarray.open_rasterio(inputs[0],  chunks=optimal_chunk_size, lock=Lock("rio", client=client))
            xds1 = rioxarray.open_rasterio(inputs[1], chunks=optimal_chunk_size, lock=Lock("rio", client=client))

            xds2 = op(xds0, xds1)
            xds2.rio.to_raster(output_path, Tiled=True, compress='DEFLATE', lock=Lock("rio", client=client)) 
            if verbose:
                hb.timer('Ended client')

    else:
        print('Launching raster_calculator using Dask without Client. View the file at ' + output_path)

        if verbose:
            hb.timer('Starting rioxarray calculation')

        conformed_inputs = []
        for c, input_ in enumerate(inputs):
            if input_types[c] == 'path':
                xds = rioxarray.open_rasterio(input_, chunks=optimal_chunk_size, lock=False)
                conformed_inputs.append(xds)
            elif input_types[c] == 'array': #NYI
                conformed_inputs.append(input_)
            elif input_types[c] == 'dict':
                conformed_inputs.append(input_)
            else:
                conformed_inputs.append(input_)

        delayed_computation = op(*conformed_inputs)
        layer_array_xr = xr.DataArray(delayed_computation, 
                              coords=xds.coords, 
                              dims=['band', 'y', 'x'],
                              attrs=xds.attrs)
        layer_array_xr.rio.to_raster(output_path, tiled=True, compress='DEFLATE')

        if verbose:
            hb.timer('Finished rioxarray calculation')

    
def rewrite_raster_to_output_path(input_path, 
                    output_path, 
                    compression_method='DEFLATE', 
                    add_overviews=False, n_workers=None, memory_limit=None, use_client=False, verbose=True):
    # Useful to change the compression.

    # NOTE!!! MUCH FASTER WITH CLIENT. I think it's because it coordinates with the read to start the next thing asap.
            
    # check if input exists
    if not hb.path_exists(input_path):
        raise NameError('read_then_write input_path does not exist: ' + str(input_path))
    
    chunk_size = hb.get_blocksize_from_path(input_path)

    if n_workers is None:
        n_cpus = multiprocessing.cpu_count()
        n_workers = n_cpus - 1 

    if memory_limit is None:
        memory_limit = '8GB'

    threads_per_worker = 1 # Cause hyperthreading

    if use_client:
        from dask.distributed import Client, LocalCluster, Lock
        print('Launching rewrite_raster_to_output_path using Dask. View progress at http://localhost:8787/status or view the file at ' + output_path)

        with LocalCluster(n_workers=n_workers, threads_per_worker=threads_per_worker, memory_limit=memory_limit) as cluster, Client(cluster) as client:
            if verbose:
                hb.timer('Starting client')

            xds = rioxarray.open_rasterio(input_path, chunks=chunk_size, lock=Lock("rio", client=client))
            xds.rio.to_raster(output_path, tiled=True, compress=compression_method, lock=Lock("rio", client=client)) 

            xds.close()
            if verbose:
                hb.timer('Ended client')

    else:
        print('Launching rewrite_raster_to_output_path using Dask without Client. View the file at ' + output_path)
        if verbose:
            hb.timer('Starting rioxarray calculation')

        xds = rioxarray.open_rasterio(input_path, chunks=chunk_size, lock=False)
        xds.rio.to_raster(output_path, tiled=True, lock=False)
        xds.close()

        if verbose:
            hb.timer('Finished rioxarray calculation')

    if add_overviews:
        hb.add_overviews_to_path(output_path)
        
def as_array(input_path, n_workers=None, memory_limit=None, use_client=False, verbose=True):
    # Returns a numpy array. Not memory safe, but at least is faster by having multiple threads read it
    # NOT FASTER THAN STANDARD GDAL.
            
    # check if input exists
    if not hb.path_exists(input_path):
        raise NameError('read_then_write input_path does not exist: ' + str(input_path))
    
    chunk_size = hb.get_blocksize_from_path(input_path)

    if n_workers is None:
        n_cpus = multiprocessing.cpu_count()
        n_workers = n_cpus - 1 

    if memory_limit is None:
        memory_limit = '8GB'

    threads_per_worker = 1 # Cause hyperthreading

    if use_client:
        from dask.distributed import Client, LocalCluster, Lock
        print('Launching as_array using Dask. View progress at http://localhost:8787/status')

        with LocalCluster(n_workers=n_workers, threads_per_worker=threads_per_worker, memory_limit=memory_limit) as cluster, Client(cluster) as client:
            if verbose:
                hb.timer('Starting client')

            xds = rioxarray.open_rasterio(input_path, chunks='auto', lock=Lock("rio", client=client))
            array = xds.to_numpy()
            xds.close()
            if verbose:
                hb.timer('Ended client')

    else:
        print('Launching as_array using Dask without Client.')
        if verbose:
            hb.timer('Starting rioxarray calculation')

        xds = rioxarray.open_rasterio(input_path, chunks=chunk_size, lock=False)
        array = xds.to_numpy()
        xds.close()

        if verbose:
            hb.timer('Finished rioxarray calculation')
        
    return array

def raster_replace_value(input_raster_path, src_value, dst_value, output_path, n_workers=None, memory_limit=None, use_client=False, verbose=True):
    # Write a new raster with the src_value replaced by the dst_value.

    def op(x, y, z):
        return dask.array.where(x == y, z, x)
            
    # check if input input_raster_path
    if not hb.path_exists(input_raster_path):
        raise NameError('read_then_write input_path does not exist: ' + str(input_raster_path))
    
    chunk_size = hb.get_blocksize_from_path(input_raster_path)

    if n_workers is None:
        n_cpus = multiprocessing.cpu_count()
        n_workers = n_cpus - 1 

    if memory_limit is None:
        memory_limit = '8GB'

    threads_per_worker = 1 # Cause hyperthreading
    use_cluster = False
    if use_client:
        from dask.distributed import Client, LocalCluster, Lock
        print('Launching as_array using Dask. View progress at http://localhost:8787/status')
        
        
        
        cluster = LocalCluster(n_workers=60, threads_per_worker=1)
        client = Client(cluster, timeout="3600s", heartbeat_interval="90s")        
        # client = Client(n_workers=n_workers)
        def process_data():
            xds = rioxarray.open_rasterio(input_raster_path, chunks='auto', lock=False)

            delayed_computation = op(xds, src_value, dst_value)

            layer_array_xr = xr.DataArray(delayed_computation, coords=xds.coords, dims=['band', 'y', 'x'], attrs=xds.attrs)

            layer_array_xr.rio.to_raster(output_path, tiled=True, compress='LZW')
        
        future = client.submit(process_data)
        processed = future.result() 

    elif use_cluster:
        with LocalCluster(n_workers=n_workers, threads_per_worker=threads_per_worker, memory_limit=memory_limit) as cluster, Client(cluster) as client:
            if verbose:
                hb.timer('Starting client')


            xds = rioxarray.open_rasterio(input_raster_path, chunks='auto', lock=False)

            delayed_computation = op(xds, src_value, dst_value)

            layer_array_xr = xr.DataArray(delayed_computation, coords=xds.coords, dims=['band', 'y', 'x'], attrs=xds.attrs)

            layer_array_xr.rio.to_raster(output_path, tiled=True, compress='LZW')



            # xds = rioxarray.open_rasterio(input_raster_path, chunks='auto', lock=Lock("rio", client=client))
            # array = xds.to_numpy()
            # xds.close()
            # if verbose:
            #     hb.timer('Ended client')

    else:
        print('Launching as_array using Dask without Client.')
        if verbose:
            hb.timer('Starting rioxarray calculation')

        xds = rioxarray.open_rasterio(input_raster_path, chunks='auto', lock=False)

        delayed_computation = op(xds, src_value, dst_value)

        layer_array_xr = xr.DataArray(delayed_computation, coords=xds.coords, dims=['band', 'y', 'x'], attrs=xds.attrs)

        layer_array_xr.rio.to_raster(output_path, tiled=True, compress='LZW')



        if verbose:
            hb.timer('Finished rioxarray calculation')


### ---------- BELOW HERE IS EXPERIMENTAL -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=


def apply_cython_function(chunk, replace_dict):  
     # After 1 day of attempting this, I gave up. Gonna stick with pygeoprocesing for now for CYTHON specific tasks. However
    # for non-cythonized functions (above) or numpy etc, raster_calculator with dask is great.
    from hazelbean.calculation_core.cython_functions import reclassify_uint8_to_uint8_by_dict_with_dask
    r = reclassify_uint8_to_uint8_by_dict_with_dask(np.asarray(chunk[0], dtype=np.uint8), replace_dict)
    return r

def zonal_statistics_dask(
    input_raster,
    zone_vector_path,
    zone_ids_raster_path=None,
    id_column_label=None,
    zones_raster_data_type=None,
    values_raster_data_type=None,
    zones_ndv=None,
    values_ndv=None,
    all_touched=None,
    assert_projections_same=True,
    unique_zone_ids=None,
    csv_output_path=None,
    vector_output_path=None,
    stats_to_retrieve='sums',
    enumeration_classes=None,
    multiply_raster_path=None,
    verbose=False,
    rewrite_zone_ids_raster=True,
    max_enumerate_value=1000,
):

    L.info('Launching dask_zonal_statistics.')

    # Test that input_raster and shapefile are in the same projection. Sillyness results if not.
    if assert_projections_same:
        hb.assert_gdal_paths_in_same_projection([input_raster, zone_vector_path])
    else:
        if verbose:
            a = hb.assert_gdal_paths_in_same_projection([input_raster, zone_vector_path], return_result=True)
            if not a:
                L.critical('Ran zonal_statistics_flex but the inputs werent in identical projections.')
        else:
            pass

    # if zone_ids_raster_path is not defined, use the PGP version, which doesn't use a rasterized approach.
    if not zone_ids_raster_path and rewrite_zone_ids_raster is False:
        base_raster_path_band = 'fix'
        to_return = pgp.zonal_statistics(
            base_raster_path_band, zone_vector_path,
            aggregate_layer_name=None, ignore_nodata=True,
            polygons_might_overlap=True, working_dir=None)
        if csv_output_path is not None:
            hb.python_object_to_csv(to_return, csv_output_path)
        return to_return

    # if zone_ids_raster_path is defined, then we are using a rasterized approach.
    # NOTE that by construction, this type of zonal statistics cannot handle overlapping polygons (each polygon is just represented by its id int value in the raster).
    else:
        if zones_ndv is None:
            zones_ndv = -9999

    if values_ndv is None:
        values_ndv = hb.get_raster_info_hb(input_raster)['nodata'][0]

    # Double check in case get_Raster fails
    if values_ndv is None:
        values_ndv = -9999.0

    # if zone_ids_raster_path is not set, make it a temporary file
    if zone_ids_raster_path is None:
        zone_ids_raster_path = 'zone_ids_' + hb.random_string() + '.tif'

    # if zone_ids_raster_path is given, use it to speed up processing (creating it first if it doesnt exist)
    if not hb.path_exists(zone_ids_raster_path) and rewrite_zone_ids_raster is not False:
        # Calculate the id raster and save it
        if verbose:
            L.info('Creating id_raster with convert_polygons_to_id_raster')
        hb.convert_polygons_to_id_raster(zone_vector_path, zone_ids_raster_path, input_raster, id_column_label=id_column_label, data_type=zones_raster_data_type,
                                         ndv=zones_ndv, all_touched=all_touched)
    else:
        if verbose:
            L.info('Zone_ids_raster_path existed, so not creating it.')

    # Much of the optimization happens by using sparse arrays rather than look-ups so that the index int is the id of the zone.
    if unique_zone_ids is None:
        gdf = gpd.read_file(zone_vector_path)
        if id_column_label is None:
            id_column_label = gdf.columns[0]

        unique_zone_ids_pre = np.unique(gdf[id_column_label][gdf[id_column_label].notnull()]).astype(np.int64)

        to_append = []
        if 0 not in unique_zone_ids_pre:
            to_append.append(0)
        # if zones_ndv not in unique_zone_ids_pre:
        #     to_append.append(zones_ndv)
        unique_zone_ids = np.asarray(to_append + list(unique_zone_ids_pre))
        # unique_zone_ids = np.asarray(to_append + list(unique_zone_ids_pre) + [max(unique_zone_ids_pre) + 1])

    if verbose:
        L.info('Starting zonal_statistics_rasterized using zone_ids_raster_path at ' + str(zone_ids_raster_path))

    # Call zonal_statistics_rasterized to parse vars into cython-format and go from there.

    if stats_to_retrieve == 'sums':
        L.debug('Exporting sums.')
        L.debug('unique_zone_ids', unique_zone_ids)
        r = hb.zonal_statistics_rasterized_dask(zone_ids_raster_path, input_raster, zones_ndv=zones_ndv, values_ndv=values_ndv, unique_zone_ids=unique_zone_ids, stats_to_retrieve=stats_to_retrieve, verbose=verbose)
        # unique_ids, sums = hb.zonal_statistics_rasterized(zone_ids_raster_path, input_raster, zones_ndv=zones_ndv, values_ndv=values_ndv,
        #                                                   unique_zone_ids=unique_zone_ids, stats_to_retrieve=stats_to_retrieve, verbose=verbose)
        # print(r)
        unique_ids = None
        sums = None
        df = pd.DataFrame(index=unique_ids, data={'sums': sums})
        df[df == 0] = np.nan
        df.dropna(inplace=True)
        if csv_output_path is not None:
            df.to_csv(csv_output_path)

        if vector_output_path is not None:
            gdf = gpd.read_file(zone_vector_path)
            gdf = gdf.merge(df, how='outer', left_on=id_column_label, right_index=True)
            gdf.to_file(vector_output_path, driver='GPKG')

        return df

    elif stats_to_retrieve == 'sums_counts':
        L.debug('Exporting sums_counts.')
        unique_ids, sums, counts = hb.zonal_statistics_rasterized(zone_ids_raster_path, input_raster, zones_ndv=zones_ndv, values_ndv=values_ndv,
                                                                  unique_zone_ids=unique_zone_ids, stats_to_retrieve=stats_to_retrieve, verbose=verbose)

        df = pd.DataFrame(index=unique_ids, data={'sums': sums, 'counts': counts})
        df[df == 0] = np.nan
        df.dropna(inplace=True)
        if csv_output_path is not None:
            df.to_csv(csv_output_path)

        if vector_output_path is not None:
            gdf = gpd.read_file(zone_vector_path)
            gdf = gdf.merge(df, how='outer', left_on=id_column_label, right_index=True)
            gdf.to_file(vector_output_path, driver='GPKG')

        return df

    elif stats_to_retrieve == 'enumeration':
        L.debug('Exporting enumeration.')

        if enumeration_classes is None:
            enumeration_classes = hb.unique_raster_values_path(input_raster)

        unique_ids, enumeration = hb.zonal_statistics_rasterized(zone_ids_raster_path, input_raster, zones_ndv=zones_ndv, values_ndv=values_ndv,
                                                                 unique_zone_ids=unique_zone_ids, stats_to_retrieve=stats_to_retrieve,
                                                                 enumeration_classes=enumeration_classes, multiply_raster_path=multiply_raster_path,
                                                                 verbose=verbose, )
        enumeration = np.asarray(enumeration)
        df = pd.DataFrame(index=unique_ids, columns=[str(i) for i in list(range(0, len(enumeration_classes)))], data=enumeration)

        if vector_output_path is not None:
            gdf = gpd.read_file(zone_vector_path)
            gdf = gdf.merge(df, how='outer', left_on=id_column_label, right_index=True)
            gdf.to_file(vector_output_path, driver='GPKG')
            gdf_no_geom = gdf.drop(columns='geometry')

        if csv_output_path is not None:
            gdf_no_geom.to_csv(csv_output_path)

        return df


def zonal_statistics_rasterized_dask(zone_ids_raster_path, values_raster_path, zones_ndv=None, values_ndv=None, zone_ids_data_type=None,
                                values_data_type=None, unique_zone_ids=None, stats_to_retrieve='sums', enumeration_classes=None,
                                multiply_raster_path=None, verbose=True, max_enumerate_value=1000):
    """
This turned out to be extrordinarily hard becasue of the implied dimensionality reduction. Gonna need to rethink it.


    """
    if verbose:
        L.info('Starting to run zonal_statistics_rasterized_dask.')

    if unique_zone_ids is None:
        if verbose:
            L.info('Load zone_ids_raster and compute unique values in it. Could be slow (and could be pregenerated for speed if desired).')

        zone_ids = hb.as_array(zone_ids_raster_path)
        unique_zone_ids = np.unique(zone_ids).astype(np.int64)
        L.warning('Generated unique_zone_ids via brute force. This could be optimized.', str(unique_zone_ids))
        zone_ids = None
    else:
        unique_zone_ids = unique_zone_ids.astype(np.int64)



    import dask
    from dask import array
    from dask.array import from_array
    from dask.distributed import Client, LocalCluster, Lock
    import rioxarray

    input_paths = [zone_ids_raster_path, values_raster_path]

    block_sizes = []
    for path in input_paths:
        if not hb.path_exists(path):
            raise NameError('dask_compute unable to find path: ' + str(path))
        block_sizes.append(hb.get_blocksize_from_path(path))

    t_b = tuple([tuple(i) for i in block_sizes])

    if len(set(t_b)) > 1:
        critical_string = 'Paths given to dask_computer were not all saved in the same blocksize. This will have dramatic performance implications.'
        critical_string += '\n' + str(input_paths)
        critical_string += '\n' + str(block_sizes)
        L.critical(critical_string)

    from dask.diagnostics import ProgressBar
    import threading

    # Use reioxarray to read with specified chunksize.
    zone_ids_da = rioxarray.open_rasterio(zone_ids_raster_path, chunks={'band': 1, 'x': 1024, 'y': 1024})
    values_da = rioxarray.open_rasterio(values_raster_path, chunks={'band': 1, 'x': 1024, 'y': 1024})
    return_da = dask.array.from_array(unique_zone_ids)



    # define the operation, which hasn't run yet.
    # subtraction = ds_scenario - ds_baseline
    def op(zone_ids_da, values_da, return_da, zones_ndv, values_ndv):
        return_list = []

        values_array = values_da.to_numpy()
        values_array = values_array.astype(np.double)[0, :, :]
        zones_array = zone_ids_da.to_numpy()
        zones_array = zones_array.astype(np.longlong)[0,:,:]
        unique_zone_ids = np.asarray(list(range(0, 255)), dtype=np.longlong)
        enumeration_classes = np.asarray(list(range(0, 255)), dtype=np.longlong)
        zones_ndv = np.longlong(255)
        values_ndv = np.double(-9999.0)

        print('values_array', values_array.dtype, values_array.shape)

        # dask_stats_df = xrspatial.zonal.stats(zones=zones_xds, values=values_xds)
        # print('dask_stats_df', dask_stats_df)
        # unique_zone_ids = xr
        # hb.zonal_statistics_flex()
        r = hb.zonal_stats_cythonized(zones_array,
                                      values_array,
                                      unique_zone_ids,
                                      zones_ndv,
                                      values_ndv,
                                      stats_to_retrieve='sums',
                                      reporting_frequency=1000,
                                      enumeration_classes=enumeration_classes,
                                      # enumeration_classes = np.asarray([1], dtype=np.int64),
                                      )
        return r
        #
        # return_da = zone_ids_da - values_da
        # return return_da

    # Now it actually runs.
    hb.timer('start')
    r = op(zone_ids_da, values_da, return_da, zones_ndv, values_ndv)
    print('r', r)
    r.compute()
    print(r)
    hb.timer('Small')
    #
    # with LocalCluster() as cluster, Client(cluster) as client:
    # # with LocalCluster() as cluster, Client(cluster) as client:
    # # with LocalCluster(n_workers=math.floor(multiprocessing.cpu_count() / 2), threads_per_worker=2, memory_limit=str(math.floor(64 / (multiprocessing.cpu_count() + 1))) + 'GB') as cluster, Client(cluster) as client:
    #
    #     L.info('Starting Local Cluster at http://localhost:8787/status')
    #
    #     xds_list = []
    #     for input_path in input_paths:
    #         # xds = rioxarray.open_rasterio(input_path, chunks=(1, 512*4, 512*4), lock=False)
    #         # xds = rioxarray.open_rasterio(input_path, chunks=(1, 512*4, 512*4), lock=False)
    #         xds = rioxarray.open_rasterio(input_path, chunks='auto', lock=False)
    #         xds_list.append(xds)
    #
    #     delayed_computation = op(*xds_list)
    #     delayed_computation.rio.to_raster(output_path, tiled=True, compress='DEFLATE', lock=Lock("rio", client=client))  # NOTE!!! MUCH FASTER WITH THIS. I think it's because it coordinates with the read to start the next thing asap.
    #
    # # delayed_computation.compute()
        # delayed_computation.rio.to_raster(output_path, tiled=True, compress='DEFLATE', lock=Lock("rio", client=client))  # NOTE!!! MUCH FASTER WITH THIS. I think it's because it coordinates with the read to start the next thing asap.
    #
    #
    #
    #
    #
    # # Get dimensions of rasters for callback reporting'
    # zone_ds = gdal.OpenEx(zone_ids_raster_path)
    # n_cols = zone_ds.RasterYSize
    # n_rows = zone_ds.RasterXSize
    # n_pixels = n_cols * n_rows
    #
    # # Create new arrays to hold results.
    # # NOTE THAT this creates an array as long as the MAX VALUE in unique_zone_ids, which means there could be many zero values. This
    # # is intended as it increases computation speed to not have to do an additional lookup.
    # aggregated_sums = np.zeros(len(unique_zone_ids), dtype=np.float64)
    # aggregated_counts = np.zeros(len(unique_zone_ids), dtype=np.int64)
    #
    # last_time = time.time()
    # pixels_processed = 0
    #
    # # Iterate through block_offsets
    # zone_ids_raster_path_band = (zone_ids_raster_path, 1)
    # aggregated_enumeration = None
    # for c, block_offset in enumerate(list(hb.iterblocks(zone_ids_raster_path_band, offset_only=True))):
    #     sample_fraction = None # TODOO add this in to function call.
    #     # sample_fraction = .05
    #     if sample_fraction is not None:
    #         if random.random() < sample_fraction:
    #             select_block = True
    #         else:
    #             select_block = False
    #     else:
    #         select_block = True
    #
    #     if select_block:
    #         block_offset_new_gdal_api = {
    #             'xoff': block_offset['xoff'],
    #             'yoff': block_offset['yoff'],
    #             'buf_ysize': block_offset['win_ysize'],
    #             'buf_xsize': block_offset['win_xsize'],
    #         }
    #
    #         zones_ds = gdal.OpenEx(zone_ids_raster_path)
    #         values_ds = gdal.OpenEx(values_raster_path)
    #         # No idea why, but using **block_offset_new_gdal_api failed, so I unpack it manually here.
    #         try:
    #             zones_array = zones_ds.ReadAsArray(block_offset_new_gdal_api['xoff'], block_offset_new_gdal_api['yoff'], block_offset_new_gdal_api['buf_xsize'], block_offset_new_gdal_api['buf_ysize']).astype(np.int64)
    #             values_array = values_ds.ReadAsArray(block_offset_new_gdal_api['xoff'], block_offset_new_gdal_api['yoff'], block_offset_new_gdal_api['buf_xsize'], block_offset_new_gdal_api['buf_ysize']).astype(np.float64)
    #
    #         except:
    #             L.critical('unable to load' + zone_ids_raster_path + ' ' + values_raster_path)
    #             pass
    #             # zones_array = zones_ds.ReadAsArray(block_offset_new_gdal_api['xoff'], block_offset_new_gdal_api['yoff']).astype(np.int64)
    #             # values_array = values_ds.ReadAsArray(block_offset_new_gdal_api['xoff'], block_offset_new_gdal_api['yoff']).astype(np.float64)
    #
    #         if zones_array.shape != values_array.shape:
    #             L.critical('zones_array.shape != values_array.shape', zones_array.shape, values_array.shape)
    #
    #         unique_zone_ids_np = np.asarray(unique_zone_ids, dtype=np.int64)
    #
    #         if len(unique_zone_ids_np) > 1000:
    #             L.critical('Running zonal_statistics_flex with many unique_zone_ids: ' + str(unique_zone_ids_np))
    #
    #         if stats_to_retrieve=='sums':
    #             sums = hb.zonal_stats_cythonized(zones_array, values_array, unique_zone_ids_np, zones_ndv=zones_ndv, values_ndv=values_ndv, stats_to_retrieve=stats_to_retrieve)
    #             aggregated_sums += sums
    #         elif stats_to_retrieve == 'sums_counts':
    #             sums, counts = hb.zonal_stats_cythonized(zones_array, values_array, unique_zone_ids_np, zones_ndv=zones_ndv, values_ndv=values_ndv, stats_to_retrieve=stats_to_retrieve)
    #             aggregated_sums += sums
    #             aggregated_counts += counts
    #         elif stats_to_retrieve == 'enumeration':
    #             if multiply_raster_path is not None:
    #                 multiply_ds = gdal.OpenEx(multiply_raster_path)
    #                 shape = hb.get_shape_from_dataset_path(multiply_raster_path)
    #                 if shape[1] == 1: # FEATURE NOTE: if you give a 1 dim array, it will be multiplied repeatedly over the vertical cols of the input_array. This is useful for when you want to multiple just the hectarage by latitude vertical strip array.
    #
    #                     # If is vertical stripe, just read based on y buffer.
    #                     multiply_raster = multiply_ds.ReadAsArray(0, block_offset_new_gdal_api['yoff'], 1, block_offset_new_gdal_api['buf_ysize']).astype(np.float64)
    #                 else:
    #                     multiply_raster = multiply_ds.ReadAsArray(block_offset_new_gdal_api['xoff'], block_offset_new_gdal_api['yoff'], block_offset_new_gdal_api['buf_xsize'], block_offset_new_gdal_api['buf_ysize']).astype(np.float64)
    #             else:
    #                 multiply_raster = np.asarray([[1]], dtype=np.float64)
    #             enumeration = hb.zonal_stats_cythonized(zones_array, values_array, unique_zone_ids_np, zones_ndv=zones_ndv, values_ndv=values_ndv,
    #                                                     stats_to_retrieve=stats_to_retrieve, enumeration_classes=np.asarray(enumeration_classes, dtype=np.int64), multiply_raster=np.asarray(multiply_raster, dtype=np.float64))
    #
    #             if aggregated_enumeration is None:
    #                 aggregated_enumeration = np.copy(enumeration)
    #             else:
    #                 aggregated_enumeration += enumeration
    #         pixels_processed += block_offset_new_gdal_api['buf_xsize'] * block_offset_new_gdal_api['buf_ysize']
    #
    #         last_time = hb.invoke_timed_callback(
    #             last_time, lambda: L.info('Zonal statistics rasterized percent complete:', float(pixels_processed) / n_pixels * 100.0), 3)
    # if stats_to_retrieve == 'sums':
    #     return unique_zone_ids, aggregated_sums
    # elif stats_to_retrieve == 'sums_counts':
    #     return unique_zone_ids, aggregated_sums, aggregated_counts
    # elif stats_to_retrieve == 'enumeration':
    #
    #     return unique_zone_ids, aggregated_enumeration


def cython_raster_calculator(inputs, op, output_path, n_workers=None, memory_limit=None, use_client=False, verbose=True):
    # After 1 day of attempting this, I gave up. Gonna stick with pygeoprocesing for now for CYTHON specific tasks. However
    # for non-cythonized functions (above) or numpy etc, raster_calculator with dask is great.    
    # inputs can be a string path or a list of string paths
    # op is a function to be computed in parallel chunks. it must have as many inputs as the number of input_paths. op must return an array
    # output_path is where the tiled set of op arrays is saved.
    
    from dask.distributed import Client, LocalCluster, Lock
    from dask.utils import SerializableLock

    if isinstance(inputs, str):
        inputs = [inputs]

    if not isinstance(inputs, list):
        raise NameError('dask_compute inputs must be a single path-string or a list of strings.')

    input_types = []
    for input_ in inputs:
        if hb.path_exists(input_):
            input_types.append('path')
        elif isinstance(input_, np.ndarray):
            input_types.append('array')
        elif isinstance(input_, dict):
            input_types.append('dict')

    
    optimal_chunk_size = hb.spatial_utils.check_chunk_sizes_from_list_of_paths([i for c, i in enumerate(inputs) if input_types[c] == 'path'])[0]

    if n_workers is None:
        n_cpus = multiprocessing.cpu_count()
        n_workers = n_cpus - 1 

    if memory_limit is None:
        memory_limit = '8GB'

    threads_per_worker = 1 # Cause hyperthreading

    # I have found that using the client slows the process down considerably and creates larger files
    # I leave it as an option for when we create a full cluster.
    if use_client:
        print('Launching raster_calculator using Dask. View progress at http://localhost:8787/status or view the file at ' + output_path)

        with LocalCluster(n_workers=n_workers, threads_per_worker=threads_per_worker, memory_limit=memory_limit) as cluster, Client(cluster) as client, ProgressBar():
            if verbose:
                hb.timer('Starting client')

            conformed_inputs = []
            for c, input_ in enumerate(inputs):
                if input_types[c] == 'path':
                    xds = rioxarray.open_rasterio(input_, chunks=optimal_chunk_size).astype(np.float64)
                    conformed_inputs.append(xds)
                elif input_types[c] == 'array': #NYI
                    conformed_inputs.append(input_)
                elif input_types[c] == 'dict':
                    conformed_inputs.append(input_)

            # delayed_computation = apply_cython_function(*conformed_inputs)
            print(xds)
            src = rioxarray.open_rasterio(inputs[0])

            from hazelbean.calculation_core.cython_functions import reclassify_uint8_to_uint8_by_dict_with_dask
            # r = reclassify_uint8_to_uint8_by_dict_with_dask(np.asarray(chunk[0], dtype=np.uint8), replace_dict)        

            result = xr.apply_ufunc(op, (conformed_inputs[0]), dask="parallelized", output_dtypes=['byte'])

            # result = xds.map_blocks(apply_cython_function, [inputs[1]], template=xds)
            # delayed_computation = op(*conformed_inputs)
            result.rio.to_raster(output_path, tiled=True, compress='DEFLATE', dtype=np.float64)


            if verbose:
                hb.timer('Ended client')

    else:
        if verbose:
            hb.timer('Starting rioxarray calculation')

        conformed_inputs = []
        for c, input_ in enumerate(inputs):
            if input_types[c] == 'path':
                xds = rioxarray.open_rasterio(input_, chunks=optimal_chunk_size, lock=False).astype(np.float64)
                conformed_inputs.append(xds)
            elif input_types[c] == 'array': #NYI
                conformed_inputs.append(input_)
            elif input_types[c] == 'dict':
                conformed_inputs.append(input_)

        # delayed_computation = apply_cython_function(*conformed_inputs)
        print(xds)
        src = rioxarray.open_rasterio(inputs[0])

        from hazelbean.calculation_core.cython_functions import reclassify_uint8_to_uint8_by_dict_with_dask
        # r = reclassify_uint8_to_uint8_by_dict_with_dask(np.asarray(chunk[0], dtype=np.uint8), replace_dict)        

        result = xr.apply_ufunc(op, (conformed_inputs[0]), dask="parallelized", output_dtypes=['byte'])

        # result = xds.map_blocks(apply_cython_function, [inputs[1]], template=xds)
        # delayed_computation = op(*conformed_inputs)
        result.rio.to_raster(output_path, tiled=True, compress='DEFLATE', dtype=np.float64)

        # Compute the result
        # result_computed = result.compute()


        # result_computed.rio.to_raster(output_path, tiled=True, compress='DEFLATE')

        # Create a new DataArray with processed data and copy metadata
        # result_dataarray = rioxarray.DataArray(result_computed, coords=src.coords, attrs=src.attrs)

        # # Write the DataArray to a new GeoTIFF
        # dst_path = "path_to_output_geotiff.tif"
        # result_dataarray.rio.to_raster(dst_path)        

        if verbose:
            hb.timer('Finished rioxarray calculation')
 


def parallel_rasterstack_to_dict_compute(zones_path, values_path, output_path, n_workers=None, memory_limit=None):
    # NOT WORKING BECAUSE CALLS CYTHON
    
    # input_paths can be a string path or a list of string paths
    # op is a function to be computed in parallel chunks. it must have as many inputs as the number of input_paths. op must return a dict
    # returns a dict that aggregates the tiled dicts.
    # optionally writes dict to csv at output_path

    from dask.distributed import Client, LocalCluster, Lock
    # import xrspatial

    input_paths = [zones_path, values_path]
    if isinstance(input_paths, str):
        input_paths = [input_paths]

    if not isinstance(input_paths, list):
        raise NameError('dask_compute inputs must be a single path-string or a list of strings.')

    block_sizes = []
    for path in input_paths:
        if not hb.path_exists(path):
            raise NameError('dask_compute unable to find path: ' + str(path))
        block_sizes.append(hb.get_blocksize_from_path(path))

    # LEARNING POINT
    t_b = tuple([tuple(i) for i in block_sizes])

    if len(set(t_b)) > 1:
        critical_string = 'Paths given to dask_computer were not all saved in the same blocksize. This will have dramatic performance implications.'
        critical_string += '\n' + str(input_paths)
        critical_string += '\n' + str(block_sizes)
        L.critical(critical_string)

    if n_workers is None:
        # print('num_cpu_available', str(multiprocessing.cpu_count()))
        n_workers = 8
        # n_workers = math.floor(multiprocessing.cpu_count() / 2) - 1 # For some reason, increasing this past like 8 even on a 128 core machine didn't help much. There must be some DASK magic utilizing all the cores even when n is low.
    if memory_limit is None:
        memory_limit = '8GB'
    threads_per_worker = 2 # Cause hyperthreading
    def op(values_xds, zones_xds):
        values_array = values_xds.to_numpy()
        zones_array = zones_xds.to_numpy()
        unique_zone_ids = np.asarray(list(range(0, 255)))
        enumeration_classes = np.asarray(list(range(0, 255)))
        zones_ndv = 255
        values_ndv = -9999.0

        # dask_stats_df = xrspatial.zonal.stats(zones=zones_xds, values=values_xds)
        # print('dask_stats_df', dask_stats_df)
        # unique_zone_ids = xr
        # hb.zonal_statistics_flex()
        from hazelbean.calculation_core.cython_functions import zonal_stats_cythonized
        r = zonal_stats_cythonized(zones_array,
                                         values_array,
                                         unique_zone_ids,
                                         zones_ndv,
                                         values_ndv,
                                         stats_to_retrieve = 'enumeration',
                                         reporting_frequency = 1000,
                                         enumeration_classes = enumeration_classes,
                                         # enumeration_classes = np.asarray([1], dtype=np.int64),
                                         )
        return r

    with LocalCluster(n_workers=n_workers, threads_per_worker=threads_per_worker, memory_limit=memory_limit) as cluster, Client(cluster) as client:
    # with LocalCluster() as cluster, Client(cluster) as client:
    # with LocalCluster(n_workers=math.floor(multiprocessing.cpu_count() / 2), threads_per_worker=2, memory_limit=str(math.floor(64 / (multiprocessing.cpu_count() + 1))) + 'GB') as cluster, Client(cluster) as client:

        L.info('Starting Local Cluster at http://localhost:8787/status')

        # xds_list = []
        # for input_path in input_paths:
        #     # xds = rioxarray.open_rasterio(input_path, chunks=(1, 512*4, 512*4), lock=False)
        #     # xds = rioxarray.open_rasterio(input_path, chunks=(1, 512*4, 512*4), lock=False)
        #     xds = rioxarray.open_rasterio(input_path, chunks='auto', lock=False)
        #     xds_list.append(xds)

        values_xds = rioxarray.open_rasterio(values_path, chunks=(1, 512*1, 512*1), lock=False)
        zones_xds = rioxarray.open_rasterio(zones_path, chunks=(1, 512*41, 512*1), lock=False)



        delayed_computation = op(values_xds, zones_xds)
        # delayed_computation = op(*xds_list)
        delayed_computation.rio.to_raster(output_path, tiled=True, compress='DEFLATE', lock=Lock("rio", client=client))  # NOTE!!! MUCH FASTER WITH THIS. I think it's because it coordinates with the read to start the next thing asap.



import subprocess

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout  # or result.returncode if that's what you need
    except subprocess.CalledProcessError as e:
        # Log or handle errors as needed
        print(f"Command failed with error: {e.stderr}")
        raise e


def run_commands_in_parallel(cmds, max_workers=8):
    print("Launching workers to run commands in this list: ", cmds)
    # Use a ThreadPoolExecutor to run os.system calls in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit each file to the executor.
        future_to_file = {executor.submit(run_command, cmd): cmd for cmd in cmds}
        
        # Wait for all submitted tasks to complete.
        for future in concurrent.futures.as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                # Retrieve the return code from os.system
                ret_code = future.result()
            except Exception as exc:
                print(f"{file_path} generated an exception: {exc}")