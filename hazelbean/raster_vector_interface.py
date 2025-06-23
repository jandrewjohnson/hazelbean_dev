import os, sys, shutil, random, math, atexit, time
from collections import OrderedDict
import functools
from functools import reduce
from osgeo import gdal, osr, ogr
import numpy as np
import random
import multiprocessing
import multiprocessing.pool
import hazelbean as hb
import scipy
import geopandas as gpd
import warnings
import netCDF4
import logging
import pandas as pd
import pygeoprocessing.geoprocessing as pgp
from pygeoprocessing.geoprocessing import *
from hazelbean import calculation_core
from hazelbean.calculation_core import cython_functions
from osgeo import gdal, ogr, osr
from hazelbean import cloud_utils



numpy = np
L = hb.get_logger('hb_rasterstats')
pgp_logger = logging.getLogger('geoprocessing')

loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]

def raster_to_polygon(input_raster_path, output_vector_path, id_label, dissolve_on_id=True):
    #  get raster datasource
    src_ds = gdal.Open(input_raster_path)
    #
    srcband = src_ds.GetRasterBand(1)
    dst_layername = 'layer'
    drv = ogr.GetDriverByName("GPKG")
    
    # Make a ds from the gpkg driver
    
    dst_ds = drv.CreateDataSource(output_vector_path)

    sp_ref = osr.SpatialReference()
    sp_ref.SetFromUserInput('EPSG:4326')

    dst_layer = dst_ds.CreateLayer(dst_layername, srs=sp_ref)

    fld = ogr.FieldDefn(id_label, ogr.OFTInteger)
    dst_layer.CreateField(fld)
    dst_field = dst_layer.GetLayerDefn().GetFieldIndex(id_label)
    
    def callback(complete, message, cb_data):
        hb.log('Complete: ' + str(complete) + '% ' + ' from convert_id_raster_to_polygons on ' + str(input_raster_path))
        return 1    

    gdal.Polygonize(srcband, None, dst_layer, dst_field, [], callback=None )

    del src_ds
    del dst_ds
    
    
    
    if dissolve_on_id:
        
        # rename output_vector_path to a displaced name
        output_vector_displaced_path = hb.rsuri(output_vector_path, 'replaced_by_raster_to_polygon')
        hb.rename_with_overwrite(output_vector_path, output_vector_displaced_path)
        
        gdf = gpd.read_file(output_vector_displaced_path)
        gdf = gdf.dissolve(by=id_label)
        gdf.to_file(output_vector_path, driver='GPKG')
    
    
    # # Open the raster file
    # raster_ds = gdal.Open(input_raster_path)
    # if raster_ds is None:
    #     raise FileNotFoundError(f"Unable to open raster file {input_raster_path}")

    # # Get the raster band (assuming the raster data is in the first band)
    # band = raster_ds.GetRasterBand(1)
    # nodata_value = band.GetNoDataValue()

    # # Create a memory layer to store the polygons
    # mem_driver = ogr.GetDriverByName('Memory')
    # mem_ds = mem_driver.CreateDataSource('memData')
    # srs = osr.SpatialReference()
    # srs.ImportFromWkt(raster_ds.GetProjection())
    # mem_layer = mem_ds.CreateLayer('memLayer', srs, ogr.wkbPolygon)

    # # Add a field to store the ID values
    # id_field = ogr.FieldDefn('ID', ogr.OFTInteger)
    # mem_layer.CreateField(id_field)

    # # Perform the raster to vector conversion
    # gdal.Polygonize(band, None, mem_layer, 0, [], callback=None)

    # # Create the output GeoPackage
    # gpkg_driver = ogr.GetDriverByName('GPKG')
    # if os.path.exists(output_vector_path):
    #     gpkg_driver.DeleteDataSource(output_vector_path)
    # out_ds = gpkg_driver.CreateDataSource(output_vector_path)
    # out_layer = out_ds.CreateLayer(layer_name, srs, ogr.wkbPolygon)

    # # Add the ID field to the output layer
    # out_layer.CreateField(id_field)

    # # Copy features from the memory layer to the GeoPackage layer
    # for feature in mem_layer:
    #     id_value = feature.GetField('DN')
    #     if id_value != nodata_value:
    #         feature.SetField('ID', id_value)
    #         out_layer.CreateFeature(feature.Clone())

    # # Clean up
    # mem_ds = None
    # out_ds = None
    raster_ds = None

def convert_polygons_to_id_raster(input_vector_path, output_raster_path, match_raster_path,
                                  id_column_label, data_type=None, ndv=None, all_touched=None, compress=True):
    
    if id_column_label == 'fid':
        raise NameError('fid is a reserved name by gpkgs')
    
    hb.assert_file_existence(input_vector_path)
    hb.assert_file_existence(match_raster_path)

    gdf = gpd.read_file(input_vector_path)
    
    if id_column_label not in gdf.columns:
        gdf[id_column_label] = np.arange(1, len(gdf) + 1).astype(np.int64)
        
        # Move id_column_label to the front of the columns list, after fid
        cols = gdf.columns.tolist()
        cols.insert(1, cols.pop(cols.index(id_column_label)))
        gdf = gdf[cols] 
        
    
        #### ----- POSSIBLE BUG -------
        # I removed the following two lines, but i'm not sure if they are needed elsewhere.
        # # Save the gdf to the same location (because subsequent rasterize call will access the file.
        # hb.rename_with_overwrite(input_vector_path, hb.rsuri(input_vector_path, 'replaced_by_convert_polygons_to_id_raster'))        
        # gdf.to_file(input_vector_path, driver='GPKG')

    
    # If the target label is not in cols, generate a unique int per polygon
    if id_column_label not in gdf.columns:
        gdf[id_column_label] = np.arange(1, len(gdf) + 1).astype(np.float64)

    if not data_type:
        data_type = 1

    if ndv is None:
        ndv = 255
    band_nodata_list = [ndv]

    option_list = list(hb.DEFAULT_GTIFF_CREATION_OPTIONS)
    if all_touched:
        option_list.append("ALL_TOUCHED=TRUE")

    option_list.append("ATTRIBUTE=" + str(id_column_label))
    raster_option_list = [i for i in option_list if 'ATTRIBUTE=' not in i and 'ALL_TOUCHED' not in i]
    if compress:
        option_list.append("COMPRESS=DEFLATE")
    hb.new_raster_from_base_pgp(match_raster_path, output_raster_path, data_type, band_nodata_list, gtiff_creation_options=raster_option_list)
    burn_values = [1]  # will be ignored because attribute set but still needed.

    # option_list = []


    # The callback here is useful, but rather than rewrite the funciton, we just locallay reset the PGP logger level.
    prior_level = pgp_logger.getEffectiveLevel()
    pgp_logger.setLevel(logging.INFO)
    hb.rasterize(input_vector_path, output_raster_path, burn_values, option_list, layer_id=0)
                          
    pgp_logger.setLevel(prior_level)

# LEGACY FUNCTION, replaced by zonal_statistics
def zonal_statistics_flex(input_raster,
                          zones_vector_path,
                          zone_ids_raster_path=None,
                          id_column_label=None,
                          zones_raster_data_type=None,
                          values_raster_data_type=None,
                          zones_ndv=None,
                          values_ndv=None,
                          all_touched=None,
                          assert_projections_same=True,
                          unique_zone_ids=None,
                          output_column_prefix=None,
                          csv_output_path=None,
                          vector_output_path=None,
                          stats_to_retrieve='sums',
                          enumeration_classes=None,
                          enumeration_labels=None,
                          multiply_raster_path=None,
                          verbose=False,
                          rewrite_zone_ids_raster=True,
                          vector_columns_to_include_in_output=None,
                          vector_index_column=None,
                          max_enumerate_value=1000,
                          ):
    """

    # LEGACY FUNCTION, replaced by zonal_statistics

    :param input_raster: flexible input, but it needs to be able to be returned as a path by get_flex_as_path
    :param zones_vector_path: path to GPKG file that contains the zone definition.

    :param zone_ids_raster_path:
    If not provided, function will assume that you want the slower pygeoprocessing version that does extra features,
    for instance allowing polygons to overlap. If path given, but the path isn't a raster, it will create it from the vector.
    If path is given and it exists, it will assume it is a valid ID raster generated for the vector.

    :param id_column_label:
    Which column from the vector to write to the ID raster.

    :param zones_raster_data_type:
    :param values_raster_data_type:
    :param zones_ndv:
    :param values_ndv:
    :param all_touched: When rasterizing the vector, should it yuse the midpoint or all-touched definition of rasterization.
    :param assert_projections_same:

    :param unique_zone_ids:
    If given, will return statistics for these exact zones. Note that this is a highly-optimized object and must be
    Continuous, start at zero, and include the max value of Zones. If this is None, it will generate one
    (which calls np.unique() which can be slow).

    :param csv_output_path:
    :param vector_output_path:

    :param stats_to_retrieve: Sum, sum_count, enumeration
    If enumeration, it will interpret the value raster as having categorized data and will instead output the number of instances of
    each category for each zone. Enumeration classes below will control which of the values in the

    :param enumeration_classes:
    :param multiply_raster_path:
    :param verbose:
    :param rewrite_zone_ids_raster:
    :param max_enumerate_value:
    :return:
    """



    """ if zone_ids_raster_path is set, use it and/or create it for later processing speed-ups.

     Big caveat on unique_zone_ids: must start at 1 and be sequential by zone. Otherwise, if left None, will just test first 10000 ints. This speeds up a lot not having to have a lookup.
     """

    input_path = hb.get_flex_as_path(input_raster)
    base_raster_path_band = (input_path, 1)

    # Test that input_raster and shapefile are in the same projection. Sillyness results if not.
    if assert_projections_same:
        hb.assert_gdal_paths_in_same_projection([input_raster, zones_vector_path])
    else:
        if verbose:
            a = hb.assert_gdal_paths_in_same_projection([input_raster, zones_vector_path], return_result=True)
            if not a:
                L.critical('Ran zonal_statistics_flex but the inputs werent in identical projections.')
        else:
            pass

  # if zone_ids_raster_path is not defined, use the PGP version, which doesn't use a rasterized approach.
    if not zone_ids_raster_path and rewrite_zone_ids_raster is False:
        to_return = pgp.zonal_statistics(
            base_raster_path_band, zones_vector_path,
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
        hb.convert_polygons_to_id_raster(zones_vector_path, zone_ids_raster_path, input_raster, id_column_label=id_column_label, data_type=zones_raster_data_type,
                                         ndv=zones_ndv, all_touched=all_touched)
    else:
        if verbose:
            L.info('Zone_ids_raster_path existed, so not creating it.')

        # hb.assert_gdal_paths_have_same_geotransform([zone_ids_raster_path, input_raster])
    if unique_zone_ids is None:

        # LEARNING POINT, If you read a GPKG, it will automatically convert the FID into the DF ID. This means the ID is not available to, e.g., merge on and has to be an index merge. One option would be to always save an FID and an ID columns, as I did in country_ids.tif
        # Additionally, this could be challenging because you can't, as below, use the columns[0] as the index on the assumption that FID would still be there in the columns.
        gdf = gpd.read_file(zones_vector_path)
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
        unique_ids, sums = hb.zonal_statistics_rasterized(zone_ids_raster_path, input_raster, zones_ndv=zones_ndv, values_ndv=values_ndv,
                                                                  unique_zone_ids=unique_zone_ids, stats_to_retrieve=stats_to_retrieve, verbose=verbose)


        df = pd.DataFrame(data={'sums': sums})
        # df = pd.DataFrame(index=unique_ids, data={'sums': sums})
        df[df == 0] = np.nan
        df.dropna(inplace=True)

        if vector_columns_to_include_in_output is not None:
            gdf = gpd.read_file(zones_vector_path)
            df = df.merge(gdf[[vector_index_column] + vector_columns_to_include_in_output], how='outer', left_index=True, right_on=vector_index_column)
            df = df[[vector_index_column] + vector_columns_to_include_in_output + ['sums']]
            df = df.sort_values(by=[vector_index_column])
            if output_column_prefix is not None:
                if output_column_prefix == '':
                    rename_dict = {'sums': output_column_prefix}
                else:                    
                    rename_dict = {'sums': output_column_prefix + '_sums'}
                df = df.rename(columns=rename_dict)

        if csv_output_path is not None:
            df.to_csv(csv_output_path, index=None)

        if vector_output_path is not None:
            gdf = gpd.read_file(zones_vector_path)
            gdf = gdf.merge(df, how='outer', left_on=id_column_label, right_index=True)
            gdf.to_file(vector_output_path, driver='GPKG')

        return df

    elif stats_to_retrieve == 'sums_counts':
        L.debug('Exporting sums_counts.')
        unique_ids, sums, counts = hb.zonal_statistics_rasterized(zone_ids_raster_path, input_raster, zones_ndv=zones_ndv, values_ndv=values_ndv,
                                                                  unique_zone_ids=unique_zone_ids, stats_to_retrieve=stats_to_retrieve, verbose=verbose)

        if len(unique_ids) != len(sums):
            sums = sums[unique_ids]
            counts = counts[unique_ids]
        df = pd.DataFrame(index=unique_ids, data={'sums': sums, 'counts': counts})
        df[df == 0] = np.nan
        df.dropna(inplace=True)

        if vector_columns_to_include_in_output is not None:
            gdf = gpd.read_file(zones_vector_path)
            df = df.merge(gdf[[vector_index_column] + vector_columns_to_include_in_output], how='outer', left_index=True, right_on=vector_index_column)
            df = df[[vector_index_column] + vector_columns_to_include_in_output + ['sums', 'counts']]
            df = df.sort_values(by=[vector_index_column])
            if output_column_prefix is not None:
                rename_dict = {'sums': output_column_prefix + '_sums', 'counts': output_column_prefix + '_counts'}
                df = df.rename(columns=rename_dict)

        if csv_output_path is not None:
            df.to_csv(csv_output_path)

        if vector_output_path is not None:
            gdf = gpd.read_file(zones_vector_path)
            gdf = gdf.merge(df, how='outer', left_on=id_column_label, right_index=True)
            gdf.to_file(vector_output_path, driver='GPKG')

        return df

    elif stats_to_retrieve == 'enumeration':

        L.debug('Exporting enumeration.')

        if enumeration_classes is None:
            enumeration_classes = hb.unique_raster_values_path(input_raster)
            enumeration_classes = [int(i) for i in enumeration_classes]
            if len(enumeration_classes) > 30:
                L.warning('You are attempting to enumerate a map with more than 30 unique values. Are you sure about this? Sure as heck doesnt look like categorized data to me...')

        unique_ids, enumeration = hb.zonal_statistics_rasterized(zone_ids_raster_path, input_raster, zones_ndv=zones_ndv, values_ndv=values_ndv,
                                                                  unique_zone_ids=unique_zone_ids, stats_to_retrieve=stats_to_retrieve,
                                                                 enumeration_classes=enumeration_classes, multiply_raster_path=multiply_raster_path,
                                                                 verbose=verbose, )
        enumeration = np.asarray(enumeration)
        df = pd.DataFrame(index=unique_ids, columns=[str(i) for i in enumeration_classes], data=enumeration)

        if vector_columns_to_include_in_output is not None:
            gdf = gpd.read_file(zones_vector_path)
            df = df.merge(gdf[[vector_index_column] + vector_columns_to_include_in_output], how='outer', left_index=True, right_on=vector_index_column)

            df = df[[vector_index_column] + vector_columns_to_include_in_output + [str(i) for i in enumeration_classes]]

            if output_column_prefix is not None and output_column_prefix != '':
                
                if enumeration_labels is not None:
                    rename_dict = {str(i): output_column_prefix + '_' + enumeration_labels[c] for c, i in enumerate(enumeration_classes)}
                else:
                    rename_dict = {str(i): output_column_prefix + '_class_' + str(i) for i in enumeration_classes}
                # df = df[[vector_index_column] + vector_columns_to_include_in_output + [output_column_prefix + '_class_' + str(i) for i in enumeration_classes]]
            else:
                if enumeration_labels is not None:
                    rename_dict = {str(i): enumeration_labels[c] for c, i in enumerate(enumeration_classes)}
                else:
                    rename_dict = {str(i): 'class_' + str(i) for i in enumeration_classes}
            df = df.rename(columns=rename_dict)

            df = df.sort_values(by=[vector_index_column])


        if csv_output_path is not None:
            df.to_csv(csv_output_path, index=False)

        if vector_output_path is not None:
            gdf = gpd.read_file(zones_vector_path)
            gdf = gdf.merge(df, how='outer', left_on=id_column_label, right_index=True)
            gdf.to_file(vector_output_path, driver='GPKG')
            gdf_no_geom = gdf.drop(columns='geometry')




        return df


def zonal_statistics_rasterized(zone_ids_raster_path, values_raster_path, zones_ndv=None, values_ndv=None, zone_ids_data_type=None,
                                values_data_type=None, unique_zone_ids=None, stats_to_retrieve='sums', enumeration_classes=None,
                                multiply_raster_path=None, verbose=True, max_enumerate_value=1000):
    """
    Calculate zonal statistics using a pre-generated raster ID array.

    NOTE that by construction, this type of zonal statistics cannot handle overlapping polygons (each polygon is just represented by its id int value in the raster).
    """

    if verbose:
        L.info('Starting to run zonal_statistics_rasterized using iterblocks.')

    # TODOOO: Figure out how to make it work if there's no vector path
    if unique_zone_ids is None:
        if verbose:
            L.info('Load zone_ids_raster and compute unique values in it. Could be slow (and could be pregenerated for speed if desired).')

        zone_ids = hb.as_array(zone_ids_raster_path)
        unique_zone_ids = np.unique(zone_ids).astype(np.int64)
        L.warning('Generated unique_zone_ids via brute force. This could be optimized.', str(unique_zone_ids))
        zone_ids = None
    else:
        unique_zone_ids = unique_zone_ids.astype(np.int64)

    # Get dimensions of rasters for callback reporting'
    zone_ds = gdal.OpenEx(zone_ids_raster_path)
    n_cols = zone_ds.RasterYSize
    n_rows = zone_ds.RasterXSize
    n_pixels = n_cols * n_rows

    # Create new arrays to hold results.
    # NOTE THAT this creates an array as long as the MAX VALUE in unique_zone_ids, which means there could be many zero values. This
    # is intended as it increases computation speed to not have to do an additional lookup.
    aggregated_sums = np.zeros(np.max(unique_zone_ids) + 1, dtype=np.float64)
    aggregated_counts = np.zeros(np.max(unique_zone_ids) + 1, dtype=np.int64)
    # aggregated_sums = np.zeros(len(unique_zone_ids), dtype=np.float64)
    # aggregated_counts = np.zeros(len(unique_zone_ids), dtype=np.int64)

    last_time = time.time()
    pixels_processed = 0

    # Iterate through block_offsets
    zone_ids_raster_path_band = (zone_ids_raster_path, 1)
    aggregated_enumeration = None
    for c, block_offset in enumerate(list(hb.iterblocks_hb(zone_ids_raster_path_band, offset_only=True))):
        sample_fraction = None # TODOO add this in to function call.
        # sample_fraction = .05
        if sample_fraction is not None:
            if random.random() < sample_fraction:
                select_block = True
            else:
                select_block = False
        else:
            select_block = True

        if select_block:
            block_offset_new_gdal_api = {
                'xoff': block_offset['xoff'],
                'yoff': block_offset['yoff'],
                'buf_ysize': block_offset['win_ysize'],
                'buf_xsize': block_offset['win_xsize'],
            }

            zones_ds = gdal.OpenEx(zone_ids_raster_path)
            values_ds = gdal.OpenEx(values_raster_path)
            # No idea why, but using **block_offset_new_gdal_api failed, so I unpack it manually here.
            try:
                values_array = values_ds.ReadAsArray(block_offset_new_gdal_api['xoff'], block_offset_new_gdal_api['yoff'], block_offset_new_gdal_api['buf_xsize'], block_offset_new_gdal_api['buf_ysize']).astype(np.float64)
            except:
                L.critical('unable to load ' + values_raster_path)
                pass
            
            try:
                zones_array = zones_ds.ReadAsArray(block_offset_new_gdal_api['xoff'], block_offset_new_gdal_api['yoff'], block_offset_new_gdal_api['buf_xsize'], block_offset_new_gdal_api['buf_ysize']).astype(np.int64)

            except:
                L.critical('unable to load ' + zone_ids_raster_path)
                pass            
            
                # zones_array = zones_ds.ReadAsArray(block_offset_new_gdal_api['xoff'], block_offset_new_gdal_api['yoff']).astype(np.int64)
                # values_array = values_ds.ReadAsArray(block_offset_new_gdal_api['xoff'], block_offset_new_gdal_api['yoff']).astype(np.float64)

            if zones_array.shape != values_array.shape:
                L.critical('zones_array.shape != values_array.shape', zones_array.shape, values_array.shape)

            unique_zone_ids_np = np.asarray(unique_zone_ids, dtype=np.int64)

            if len(unique_zone_ids_np) > 1000:
                L.debug('Running zonal_statistics_flex with many unique_zone_ids: ' + str(unique_zone_ids_np))

            if stats_to_retrieve=='sums':
                sums = hb.calculation_core.cython_functions.zonal_stats_cythonized(zones_array, values_array, unique_zone_ids_np, zones_ndv=zones_ndv, values_ndv=values_ndv, stats_to_retrieve=stats_to_retrieve)
                sums = np.asarray(sums, dtype=float)
                sums[np.isnan(sums)] = 0.0 
                aggregated_sums = aggregated_sums + sums
            elif stats_to_retrieve == 'sums_counts':
                sums, counts = hb.calculation_core.cython_functions.zonal_stats_cythonized(zones_array, values_array, unique_zone_ids_np, zones_ndv=zones_ndv, values_ndv=values_ndv, stats_to_retrieve=stats_to_retrieve)
                sums = np.asarray(sums, dtype=float)
                counts = np.asarray(counts, dtype=int)

                sums[np.isnan(sums)] = 0.0 
                counts[np.isnan(counts)] = 0
                aggregated_sums = aggregated_sums + sums
                aggregated_counts = aggregated_counts + counts

            
            elif stats_to_retrieve == 'enumeration':
                if multiply_raster_path is not None:
                    multiply_ds = gdal.OpenEx(multiply_raster_path)
                    shape = hb.get_shape_from_dataset_path(multiply_raster_path)
                    if shape[1] == 1: # FEATURE NOTE: if you give a 1 dim array, it will be multiplied repeatedly over the vertical cols of the input_array. This is useful for when you want to multiple just the hectarage by latitude vertical strip array.

                        # If is vertical stripe, just read based on y buffer.
                        multiply_raster = multiply_ds.ReadAsArray(0, block_offset_new_gdal_api['yoff'], 1, block_offset_new_gdal_api['buf_ysize']).astype(np.float64)
                    else:
                        # "C:\Users\jajohns\Files\seals\projects\test_iucn_30by30\intermediate\project_aoi\pyramids\aoi_ha_per_cell_coarse.tif"
                        multiply_raster = multiply_ds.ReadAsArray(block_offset_new_gdal_api['xoff'], block_offset_new_gdal_api['yoff'], block_offset_new_gdal_api['buf_xsize'], block_offset_new_gdal_api['buf_ysize']).astype(np.float64)
                else:
                    multiply_raster = np.asarray([[1]], dtype=np.float64)
                enumeration = hb.calculation_core.cython_functions.zonal_stats_cythonized(zones_array, values_array, unique_zone_ids_np, zones_ndv=zones_ndv, values_ndv=values_ndv,
                                                        stats_to_retrieve=stats_to_retrieve, enumeration_classes=np.asarray(enumeration_classes, dtype=np.int64), multiply_raster=np.asarray(multiply_raster, dtype=np.float64))

                if aggregated_enumeration is None:
                    aggregated_enumeration = np.copy(enumeration)
                else:
                    aggregated_enumeration += enumeration
            pixels_processed += block_offset_new_gdal_api['buf_xsize'] * block_offset_new_gdal_api['buf_ysize']

            last_time = hb.invoke_timed_callback(
                last_time, lambda: print('Zonal statistics rasterized on ' + str(values_raster_path) + ': ' + str(float(pixels_processed) / n_pixels * 100.0)), 2)
    

    if stats_to_retrieve == 'sums':
        return unique_zone_ids, aggregated_sums
    elif stats_to_retrieve == 'sums_counts':
        return unique_zone_ids, aggregated_sums, aggregated_counts
    elif stats_to_retrieve == 'enumeration':

        return unique_zone_ids, aggregated_enumeration


def zonal_statistics(
        input_raster_path,
        zones_vector_path=None,
        id_column_label=None,
        zone_ids_raster_path=None,
        stats_to_retrieve='sums', # sums_counts
        enumeration_classes=None,
        enumeration_labels=None,
        multiply_raster_path=None,
        output_column_prefix=None, # If None uses the fileroot, use '' to be blank.
        vector_columns_to_keep='all',
        csv_output_path=None,
        vector_output_path=None,
        zones_ndv = None,
        zones_raster_data_type=None,
        unique_zone_ids=None, # CAUTION on changing this one. Cython code is optimized by assuming a continuous set of integers of the right bit size that covers all value possibilities and zero and the NDV.
        id_min = None,
        id_max = None,
        assert_projections_same=False,
        values_ndv=-9999,
        max_enumerate_value=20000,
        use_pygeoprocessing_version=False,
        verbose=False,
):
    """Returns a GDF with the zonal statistics for each zone in zones_vector_path. If csv_output_path is given, will also save a CSV, same with GPKG.
    If id_column_label is None, creates a unique ID column for each polygon.
    
    """
    # TODOO Need to consider the case to raise an exception when someone provides a pre-generated zone_ids that doesn't cover all in zones_vector_path.
    
    if not zones_vector_path and not zone_ids_raster_path:
        raise NameError('Must provide either zones_vector_path or zone_ids_raster_path.')
    
    # if not zones_vector_path and not csv_output_path:
    #     raise NameError('Must provide either zones_vector_path or csv_output_path.')


    # First just test that all files are present
    hb.path_exists(input_raster_path, verbose=verbose)
    
    if zones_vector_path:
        hb.path_exists(zones_vector_path, verbose=verbose)

        # Read the vector path
        gdf = gpd.read_file(zones_vector_path)


        # if no id_column_label or its not in gdf already, generate a unique int per polygon
        if id_column_label is None:
            id_column_label = 'generated_ids'
            
        if id_column_label not in gdf.columns:
                
            gdf[id_column_label] = np.arange(1, len(gdf) + 1).astype(np.int64)

            # Save the gdf to the same location (because subsequent rasterize call will access the file.
            gdf.to_file(zones_vector_path, driver='GPKG')

        if vector_columns_to_keep == 'all':
            'we good'
        elif vector_columns_to_keep == 'just_id':
            vector_columns_to_keep = [i for i in gdf.columns if i == id_column_label or i == 'geometry']
            gdf = gdf[vector_columns_to_keep]
        elif type(vector_columns_to_keep) is list:
            vector_columns_to_keep = [i for i in gdf.columns if i in vector_columns_to_keep or i == 'geometry']
            gdf = gdf[vector_columns_to_keep]
        else:
            raise NameError('vector_columns_to_keep must be all, just_id, or a list of column names.')
        
    # # REVERTED THIS IN FAVOR OF ABOVE #If no id_column_label is given, check the GDF for unique ints/floats and choose first
    # if id_column_label is None:
    #     possible_ids = []
    #     for column_label in gdf.columns:
    #         dtype = gdf[column_label].dtype
    #         if 'int' in str(dtype) or 'float' in str(dtype):
    #             uniques = gdf[column_label].unique()
                    
    #             if len(uniques) == gdf.shape[0]:
    #                 possible_ids.append(column_label)
    #     if len(possible_ids) == 0:
    #         possible_ids.append(gdf.columns[0])
    #     id_column_label = possible_ids[0]

    # # If the id_column is not an int, check to see if its at least unique, then generate that.
    # if not 'int' in str(gdf[id_column_label].dtype):
    #     if len(gdf[id_column_label].unique()) == gdf.shape[0]:
    #         print ('like this')
    #     raise NameError('NYI but could generate a unique ids from a unique non int.')

    # Determine if we can get away with 8bit data.
        if id_min is None:
            id_min = gdf[id_column_label].min()
            if '.' in str(id_min):
                raise NameError('id_min is a float. This is not allowed. Please provide an integer.')
            try: 
                id_min = int(id_min)
            except:
                raise NameError('id_min is not an intable. This is not allowed. Please provide an integer.')
            
            
        if id_max is None:
            id_max = gdf[id_column_label].max()
            if '.' in str(id_max):
                raise NameError('id_max is a float. This is not allowed. Please provide an integer.')
            try: 
                id_max = int(id_max)
            except:
                raise NameError('id_max is not an intable. This is not allowed. Please provide an integer.')
            
            
    else:
        if id_min is None or id_max is None:
            # GAVE UP HERE: DASK FAILS BECAUSE RIOXARRAY DOESNT SUPPORT 64bit int. wtf...
            # hb.log('Finding uniques to get min and max')
            # from hazelbean import parallel
            # from hazelbean.parallel import unique_count_dask
            # uniques = unique_count_dask(zone_ids_raster_path)
            
            ### WARNING not memory safe
            uniques = np.unique(hb.as_array(zone_ids_raster_path))
            sorted_uniques = sorted(uniques)
            id_min = sorted_uniques[0]
            id_max = sorted_uniques[-1]
            
            if id_min == zones_ndv:
                id_min = sorted_uniques[1]
                
            if id_max == zones_ndv:
                id_max = sorted_uniques[-2]
                
            # hb.log('    found min and max', id_min, id_max) 

        # hb.log('Getting unique_zone_ids min from ' + str(zone_ids_raster_path))
        # id_min = np.min(unique_zone_ids)
        # hb.log('Getting unique_zone_ids max from ' + str(zone_ids_raster_path))
        # id_max = np.max(unique_zone_ids)

    if not zones_raster_data_type:
        if not zones_ndv:
            if id_min > 0 and id_max < 255: # notice that i'm reserving 0 and 255 for values and NDV.
                zones_ndv = 255
                zones_raster_data_type = 1
                numpy_dtype = np.uint8
                if unique_zone_ids is None:
                    unique_zone_ids = np.arange(0, 256, dtype=numpy_dtype)
            else:
                zones_ndv = -9999
                zones_raster_data_type = 5
                numpy_dtype = np.int64
                if unique_zone_ids is None:
                    unique_zone_ids = np.arange(-9999, 9999 + 1, dtype=numpy_dtype)
        else:
            if zones_ndv == 255:
                zones_raster_data_type = 1
                numpy_dtype = np.uint8
                if unique_zone_ids is None:
                    unique_zone_ids = np.arange(-9999, 9999 + 1, dtype=numpy_dtype)
            else:
                zones_raster_data_type = 5
                numpy_dtype = np.int64
                if unique_zone_ids is None:
                    unique_zone_ids = np.arange(0, 256, dtype=numpy_dtype)
    else:

        if not zones_ndv:
            if zones_raster_data_type >= 5:
                zones_ndv = -9999
                numpy_dtype = np.int64
                if unique_zone_ids is None:
                    unique_zone_ids = np.arange(0, 256, dtype=numpy_dtype)
            else:
                zones_ndv = 255
                numpy_dtype = np.uint8
                if unique_zone_ids is None:
                    unique_zone_ids = np.arange(-9999, 9999 + 1, dtype=numpy_dtype)
        else:
            if zones_raster_data_type >= 5:
                numpy_dtype = np.int64
                if unique_zone_ids is None:
                    unique_zone_ids = np.arange(0, max_enumerate_value, dtype=numpy_dtype)
            else:
                numpy_dtype = np.uint8
                if unique_zone_ids is None:
                    unique_zone_ids = np.arange(-9999, 9999 + 1, dtype=numpy_dtype)

    if id_max - id_min < max_enumerate_value:
        create_unique_ids_array = True
    else:
        create_unique_ids_array = False

    # Test that input_raster and shapefile are in the same projection. Sillyness results if not.
    if assert_projections_same:
        hb.assert_gdal_paths_in_same_projection([zones_vector_path, zones_vector_path])
    else:
        if verbose:
            a = hb.assert_gdal_paths_in_same_projection([input_raster_path, zones_vector_path], return_result=True)
            if not a:
                L.critical('Ran zonal_statistics_flex but the inputs werent in identical projections.')
        else:
            pass

    # if zone_ids_raster_path is not set, make it a temporary file located where the vector file is
    if zone_ids_raster_path is None:
        zone_ids_raster_path = hb.suri(hb.path_replace_extension(zones_vector_path, '.tif'), 'zone_ids')

    # if zone_ids_raster_path is given, use it to speed up processing (creating it first if it doesnt exist)
    if not hb.path_exists(zone_ids_raster_path):
        # Calculate the id raster and save it
        if verbose:
            L.info('Creating id_raster with convert_polygons_to_id_raster')
        hb.raster_vector_interface.convert_polygons_to_id_raster(zones_vector_path, zone_ids_raster_path, input_raster_path, id_column_label=id_column_label, data_type=zones_raster_data_type,
                                         ndv=zones_ndv, all_touched=True)
    else:
        if verbose:
            L.info('Zone_ids_raster_path existed, so not creating it.')

    # Append all stat output columns with this output_column_prefix so that when things are merged later on its not confusing
    if output_column_prefix is None:
        output_column_prefix = hb.file_root(input_raster_path)

    if use_pygeoprocessing_version:
        # This version is much slower so it is not advised nless you need the greater flexibility of allowing polygons to overlap.
        base_raster_path_band = (input_raster_path, 1)
        to_return = pgp.zonal_statistics(
            base_raster_path_band, zones_vector_path,
            aggregate_layer_name=None, ignore_nodata=True,
            polygons_might_overlap=True, working_dir=None)
        if csv_output_path is not None:
            hb.python_object_to_csv(to_return, csv_output_path)
        return to_return

    if verbose:
        L.info('Starting zonal_statistics_rasterized using zone_ids_raster_path at ' + str(zone_ids_raster_path))

    if stats_to_retrieve == 'sums':
        L.debug('Exporting sums.')
        L.debug('unique_zone_ids', unique_zone_ids)
        _, sums = hb.raster_vector_interface.zonal_statistics_rasterized(zone_ids_raster_path, input_raster_path, zones_ndv=zones_ndv, values_ndv=values_ndv,
                                                                  unique_zone_ids=unique_zone_ids, stats_to_retrieve=stats_to_retrieve, verbose=verbose)

        # Make a df from unique_zone_ids
        u_df = pd.DataFrame(data=unique_zone_ids)
        # Create a DF of the exhaustive, continuous ints in unique_zone_ids, which may have lots of zeros.


        df_sums = pd.DataFrame(data={output_column_prefix + '_sums': sums})
        df_sums['id'] = df_sums.index
        df = hb.df_merge(u_df, df_sums, how='outer', left_on=0, right_on='id', supress_warnings=True, verbose=False)
        # df_sums = pd.DataFrame(index=unique_zone_ids, data={output_column_prefix + '_sums': sums})
        # df = pd.DataFrame(index=unique_zone_ids, data={output_column_prefix + '_sums': sums[1: ]}) # PREVIOUSLY HAD THIS LINE! PROBABLY BROKEN ELSEWHERE

    elif stats_to_retrieve == 'sums_counts':
        L.debug('Exporting sums_counts.')
        hb.path_exists(zone_ids_raster_path, verbose=verbose)
        _, sums, counts = hb.zonal_statistics_rasterized(zone_ids_raster_path, input_raster_path, zones_ndv=zones_ndv, values_ndv=values_ndv,
                                                                  unique_zone_ids=unique_zone_ids, stats_to_retrieve=stats_to_retrieve, verbose=verbose)

        # df = pd.DataFrame(index=unique_zone_ids, data={output_column_prefix + '_sums': sums, output_column_prefix + '_counts': counts})

        # Make a df from unique_zone_ids
        u_df = pd.DataFrame(data=unique_zone_ids)
        # Create a DF of the exhaustive, continuous ints in unique_zone_ids, which may have lots of zeros.

        df_sums = pd.DataFrame(data={output_column_prefix + '_sums': sums, output_column_prefix + '_counts': counts})
        df_sums['id'] = df_sums.index
        df = hb.df_merge(u_df, df_sums, how='outer', left_on=0, right_on='id', supress_warnings=True)






    elif stats_to_retrieve == 'enumeration':

        L.debug('Exporting enumeration.')

        if enumeration_classes is None:
            enumeration_classes = hb.unique_raster_values_path(input_raster_path)
            enumeration_classes = [int(i) for i in enumeration_classes]
            if len(enumeration_classes) > 90:
                L.warning('You are attempting to enumerate a map with more than 90 unique values. Are you sure about this? Sure as heck doesnt look like categorized data to me...')

        _, enumeration = hb.raster_vector_interface.zonal_statistics_rasterized(zone_ids_raster_path, input_raster_path, zones_ndv=zones_ndv, values_ndv=values_ndv,
                                                                  unique_zone_ids=unique_zone_ids, stats_to_retrieve=stats_to_retrieve,
                                                                 enumeration_classes=enumeration_classes, multiply_raster_path=multiply_raster_path,
                                                                 verbose=verbose, )
        enumeration = np.asarray(enumeration)
        if output_column_prefix:
            output_column_prefix_fixed = output_column_prefix + '_'
        else:
            output_column_prefix_fixed = ''
        
        if enumeration_labels is not None:
            
            df = pd.DataFrame(index=unique_zone_ids, columns=[output_column_prefix_fixed + enumeration_labels[c] for c, i in enumerate(enumeration_classes)], data=enumeration)
        else:
            df = pd.DataFrame(index=unique_zone_ids, columns=[output_column_prefix_fixed + str(i) for c, i in enumerate(enumeration_classes)], data=enumeration)

    # If a vector was given, use it to select out just the index values that are in the gdf
    if zones_vector_path:
        df[id_column_label] = df.index
        dfs = df.loc[gdf[id_column_label]]
        
        gdfo = hb.df_merge(gdf, dfs, how='outer', left_on=id_column_label, right_on=id_column_label, supress_warnings=True)

        if csv_output_path is not None:
            df = gdfo[[i for i in gdfo.columns if i != 'geometry']]
            df.to_csv(csv_output_path, index=None)

        if vector_output_path is not None:
            gdfo.to_file(vector_output_path, driver='GPKG')
            
    else:
        # Make a new column that copys the index value
        df['id_created'] = df.index
        
        # Keep only where the id is greater than zero
        if output_column_prefix + '_sums' in df.columns and output_column_prefix + '_counts' in df.columns:
            # If the sums and counts are both zero, then remove the row.
            df = df[(df[output_column_prefix + '_sums'] > 0) | (df[output_column_prefix + '_counts'] > 0)]
        elif output_column_prefix + '_sums' in df.columns:
            # If the sums are zero, then remove the row.
            df = df[df[output_column_prefix + '_sums'] > 0]
        else: # Then it is an enumeration
            df = df[~(df[[i for i in df.columns if i != 'id']] == 0).all(axis=1)]
            
        if csv_output_path is not None:
           
           
            
            hb.create_directories(csv_output_path)
            # Save the df but make everything a float
            df = df.astype(float)
            df.to_csv(csv_output_path, index=None)
        

    return df


def zonal_statistics_merge(
        input_raster_paths,
        zones_vector_path,
        id_column_label=None,
        zone_ids_raster_path=None,
        stats_to_retrieve='sums',
        enumeration_classes=None,
        enumeration_labels=None,
        multiply_raster_path=None,
        output_column_prefix=None,
        csv_output_path=None,
        vector_output_path=None,
        zones_ndv=None,
        zones_raster_data_type=None,
        unique_zone_ids=None,  # CAUTION on changing this one. Cython code is optimized by assuming a continuous set of integers of the right bit size that covers all value possibilities and zero and the NDV.
        assert_projections_same=False,
        values_ndv=-9999,
        max_enumerate_value=20000,
        use_pygeoprocessing_version=False,
        remove_zone_ids_raster_path=False,
        verbose=False,
):

    # Only generate zone_ids_raster_path once then reuse.
    if zone_ids_raster_path is None:
        zone_ids_raster_path = hb.ruri(os.path.join(os.path.split(zones_vector_path)[0], 'zone_ids.tif'))

    df = None
    for input_raster_path in input_raster_paths:
        if verbose:
            L.info('Running zonal statistics on ' + str(input_raster_path) + ' (called from zonal_statistics_merge)')
        current_df = hb.raster_vector_interface.zonal_statistics(
            input_raster_path,
            zones_vector_path,
            id_column_label=id_column_label,
            zone_ids_raster_path=zone_ids_raster_path,
            zones_ndv=zones_ndv,
            assert_projections_same=assert_projections_same,
            verbose=verbose,
        )

        if df is None:
            df = current_df
        else:
            df = hb.df_merge(df, current_df, supress_warnings=True)

    if remove_zone_ids_raster_path:
        hb.remove_at_exit(zone_ids_raster_path)
    return df


def replace_label_via_correspondence(input_label, correspondence_df, output='name'):
    
    # Get the names of the _label and output names
    potential_input_columns = [i for i in correspondence_df.columns if i.endswith('_label')]
    if len(potential_input_columns) != 1:
        raise NameError('correspondence_df must have exactly one column ending in _label.')
    input_column = potential_input_columns[0]
    
    potential_output_columns = [i for i in correspondence_df.columns if i.endswith('_' + output)]
    if len(potential_output_columns) != 1:
        raise NameError('correspondence_df must have exactly one column ending in _' + output + '.')
    output_column = potential_output_columns[0]
    
    
    # Select the row where the input_label is in the 'input' column
    row = correspondence_df[correspondence_df[input_column] == input_label]
    return row[output_column].values[0]
    

def extract_correspondence_and_categories_dicts_from_df_cols(input_df, broad_col, narrow_col):
    set_differences = hb.compare_sets_as_dict(input_df[broad_col], input_df[narrow_col], return_amount='all')

    correspondence = {}
    categories = {}
    for i in set_differences['right_set']:
        categories[i] = []
    for i in set_differences['left_set']:
        correspondence[i] = input_df[input_df[broad_col] == i][narrow_col].values[0]
        categories[input_df[input_df[broad_col] == i][narrow_col].values[0]].append(i)
    return correspondence, categories

def convert_id_raster_to_polygons(input_raster_path, output_vector_path, dst_layer_name='id', raster_band=1):
    # TODOO THIS IS TOTALLY BROKEN. Not sure why. Would be good to include.
    # Use raster_to_polygon isntead
    
    # this allows GDAL to throw Python Exceptions
    gdal.UseExceptions()
    hb.path_assert_exists(input_raster_path)
    
    src_ds = gdal.Open(input_raster_path)
    src_band = src_ds.GetRasterBand(raster_band)


    drv = ogr.GetDriverByName("GPKG")
    dst_ds = drv.CreateDataSource(dst_layer_name + ".gpkg")
    dst_layer = dst_ds.CreateLayer(dst_layer_name, srs = None )
    
    def progress_callback(complete, message, unknown):
        hb.log('Complete: ' + str(complete) + '% ' + ' from convert_id_raster_to_polygons on ' + str(input_raster_path))
        return 1

    # gdal.Polygonize(src_band, None, dst_layer, -1, [], callback=progress_callback)
    
#     { 'BAND' : 1, 'EIGHT_CONNECTEDNESS' : False, 'EXTRA' : '', 'FIELD' : 'id', 'INPUT' : 'C:/Users/jajohns/Files/gtap_invest/projects/test_cwon/intermediate/base_data_generation/joined_region_vectors/gtap_invest/region_boundaries/gtapaez11_aezregions.tif', 'OUTPUT' : 'C:/Users/jajohns/Files/gtap_invest/projects/test_cwon/intermediate/base_data_generation/joined_region_vectors/gtap_invest/region_boundaries/gtapaez11_aezregions.gpkg' }
    # raw command: gdal_polygonize.bat C:/Users/jajohns/Files/gtap_invest/projects/test_cwon/intermediate/base_data_generation/joined_region_vectors/gtap_invest/region_boundaries/gtapaez11_aezregions.tif -b 1 -f "GPKG" C:/Users/jajohns/Files/gtap_invest/projects/test_cwon/intermediate/base_data_generation/joined_region_vectors/gtap_invest/region_boundaries/gtapaez11_aezregions.gpkg gtapaez11_aezregions id
    gdal_command = 'gdal_polygonize.bat ' + input_raster_path + " -b 1 -f \"GPKG\" " + output_vector_path + " gtapaez11_aezregions id"

    os.system(gdal_command)
    
    
    
    
def vector_super_simplify(input_vector_path, id_column_label, blur_size, output_path, remove_temp_files=True):
    """
    Simplify a vector file by rasterizing it on the id_column, then blurring it with mode_resampling, then vectorizing it back
    """

    gdf = gpd.read_file(input_vector_path)
    
    match_raster_refpath = hb.get_path(hb.ha_per_cell_ref_paths[blur_size])
    
    
    processing_size_arcseconds = 10.0
    
    
    base_data_dir = 'data'
    match_raster_path = os.path.join(base_data_dir, match_raster_refpath)
    cloud_utils.download_gdrive_refpath(match_raster_path, base_data_dir)
    
    # Rasterize on id_column
    output_raster_path = os.path.splitext(output_path)[0] + '_raster_ids.tif'
    convert_polygons_to_id_raster(input_vector_path, output_raster_path, match_raster_path,
                                  id_column_label, data_type=None, ndv=None, all_touched=None, compress=True)


    raster_blurred_path = os.path.splitext(output_path)[0] + '_raster_blurred.tif'
    




    # Polygonize output_raster_path
    output_vector_path = os.path.splitext(output_raster_path)[0] + '_vectorized.gpkg'
    raster_to_polygon(output_raster_path, output_vector_path, id_column_label)
    
    smoothed_vector_path = os.path.splitext(output_raster_path)[0] + 'smoothed.gpkg'
    input_vector_path = output_vector_path
    gdf = gpd.read_file(input_vector_path).to_crs(epsg=3857)
    gdf['geometry'] = gdf['geometry'].buffer(5000).buffer(-5000)
    gdf.to_file(smoothed_vector_path, driver='GPKG')
    
    
    
    
    
    
    
    