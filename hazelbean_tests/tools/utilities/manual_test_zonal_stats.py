

import os
import hazelbean as hb
import numpy as np
from hazelbean.raster_vector_interface import *
import pygeoprocessing as pgp
from hazelbean.calculation_core import cython_functions
print('This test file also compares pgp performance against hazelbean. '
        'Zonal_stats is WAY faster in HB, reclassify flex is slightly faster '
        'when read/write is considered, but when run just as an array function is much faster.')

L = hb.get_logger('manual_t_zonal_stats_logger')

data_dir = os.path.join(os.path.dirname(__file__), "../data")
test_data_dir = os.path.join(data_dir, "tests")
cartographic_data_dir = os.path.join(data_dir, "cartographic/ee")        
pyramid_data_dir = os.path.join(data_dir, "pyramids")
ee_r264_ids_900sec_path = os.path.join(cartographic_data_dir, "ee_r264_ids_900sec.tif")
global_1deg_raster_path = os.path.join(pyramid_data_dir, "ha_per_cell_3600sec.tif")        
ee_r264_correspondence_vector_path = os.path.join(cartographic_data_dir, "ee_r264_simplified900sec.gpkg")
ee_r264_correspondence_csv_path = os.path.join(cartographic_data_dir, "ee_r264_correspondence.csv")        
maize_calories_path = os.path.join(data_dir, "crops/johnson/crop_calories/maize_calories_per_ha_masked.tif")
ha_per_cell_column_900sec_path = hb.get_path(hb.ha_per_cell_column_ref_paths[900])
ha_per_cell_900sec_path = hb.get_path(hb.ha_per_cell_ref_paths[900])
pyramid_match_900sec_path = hb.get_path(hb.pyramid_match_ref_paths[900])    


test_zonal_statistics_merge_sum = 0
if test_zonal_statistics_merge_sum:
    # First confirm that all spam data are present in pyramids and are actually in pyramid form

    input_paths_list = [ee_r264_ids_900sec_path, ha_per_cell_900sec_path]
    L.info(input_paths_list)
    hb.make_paths_list_global_pyramid(input_paths_list,
                                        output_paths_list=None,
                                        make_overviews=True,
                                        overwrite_overviews=False,
                                        calculate_stats=True,
                                        overwrite_stats=False,
                                        clean_temporary_files=True,
                                        raise_exception=False,
                                        make_overviews_external=True,
                                        set_ndv_below_value=None,
                                        verbose=True)

    returned_dfs = zonal_statistics_merge(
        input_raster_paths=input_paths_list,
        zones_vector_path=ee_r264_correspondence_vector_path,
        verbose=False, remove_zone_ids_raster_path=True)
    
    L.info(returned_dfs)



test_all = 1
if test_all:
    # TODOO Manual_t_x refers to a test that I was too lazy to setup the test environment (but also didn't want nose finding it)
    zone_ids_raster_path = ee_r264_ids_900sec_path
    zone_values_path = ha_per_cell_900sec_path
    zones_vector_path = ee_r264_correspondence_vector_path
    
    zone_ids = hb.as_array(zone_ids_raster_path).astype(np.int64)
    values_array = hb.as_array(zone_values_path).astype(np.float64)
    unique_zone_ids = np.append([0], np.unique(zone_ids).astype(np.int64))
    zones_ndv = np.int64(255)
    values_ndv = np.float64(9999.)
    L = hb.get_logger('manual_t_zonal_stats')

    L.debug('zonal_stats_cythonized directly.')
    hb.timer('Cython fasterrasterstats starting')
    r = cython_functions.zonal_stats_cythonized(
        zone_ids,
        values_array,
        unique_zone_ids,
        zones_ndv,
        values_ndv)
    hb.timer('zonal_stats_cythonized')

    base_raster_path_band = (zone_values_path, 1)
    aggregate_vector_path = zones_vector_path

    # aggregate_vector_path = "data\countries_iso3_just_code_and_names.gpkg"
    pgp.geoprocessing.zonal_statistics(base_raster_path_band, aggregate_vector_path,
            ignore_nodata=True,
            polygons_might_overlap=False)
    hb.timer('pgp.geoprocessing.zonal_statistics')

    zone_ids_raster_temp_path = hb.temp('.tif', 'zone_ids', remove_at_exit=True)
    csv_output_path = hb.temp('.csv', 'df_output', remove_at_exit=True)
    hb.raster_vector_interface.zonal_statistics(zone_values_path, aggregate_vector_path, zone_ids_raster_path=zone_ids_raster_temp_path, csv_output_path=csv_output_path, output_column_prefix='prefixed_value')
    hb.timer('zonal_statistics_flex with values read and rasterization of vector.')

    zone_ids_raster_temp_path = hb.temp('.tif', 'zone_ids', remove_at_exit=True)
    values_temp_path = hb.temp('.tif', 'values', remove_at_exit=True)
    csv_output_path = hb.temp('.csv', 'df_output', remove_at_exit=True)

    hb.save_array_as_geotiff(np.random.randint(1, 4, hb.get_shape_from_dataset_path(zone_ids_raster_path)), values_temp_path, zone_ids_raster_path)
    hb.raster_vector_interface.zonal_statistics(values_temp_path,
                                aggregate_vector_path,
                                zone_ids_raster_path=zone_ids_raster_temp_path,
                                stats_to_retrieve='enumeration',
                                csv_output_path=csv_output_path,
                                output_column_prefix='enumerated',
                                enumeration_labels=['this', 'is', 'labels!'])
    hb.timer('zonal_statistics_flex ENUMERATION with values read and rasterization of vector.')


run_reclassify_raster_hb = 0 # RELIES ON ARRAYFRAMES WTF
if run_reclassify_raster_hb:

    rules = {i: 33 for i in range(0, 256)}
    rules_array = np.asarray(list(rules.values()), dtype=np.uint8)
    zone_ids = zone_ids.astype(np.uint8)


    zone_ids = zone_ids.astype(np.int64)
    rules_array = rules_array.astype(np.int64)

    output_path = hb.temp('.tif', remove_at_exit=True)

    zone_ids = zone_ids.astype(np.uint8)
    rules_array = rules_array.astype(np.uint8)
    hb.reclassify_raster_hb(zone_ids, rules, output_path)
    hb.timer('reclassify_raster_hb from array on dict')
    hb.reclassify_raster_hb(zone_ids, rules_array, output_path)
    hb.timer('reclassify_raster_hb from array on array')

    # Note that for the next two, because it's path based, it has to have an output path
    # TODOO Why is this one so slow?
    # hb.reclassify_raster_hb(zone_ids_raster_path, rules, output_path, array_threshold=1)
    # hb.timer('reclassify_raster_hb from zone_ids_raster_path on dict')
    hb.reclassify_raster_hb(zone_ids_raster_path, rules_array, output_path)
    hb.timer('reclassify_raster_hb from zone_ids_raster_path on array')

    # Test different types
    rules_array = rules_array.astype(np.float32)
    hb.reclassify_raster_hb(zone_ids_raster_path, rules_array, output_path)
    hb.timer('reclassify_raster_hb from zone_ids_raster_path on array but with float32 rules')

    rules_array = rules_array.astype(np.float32)
    a = hb.reclassify_raster_hb(zone_ids, rules_array, output_path)
    hb.timer('reclassify_raster_hb from zone_ids on array')



    # Make some modifications that can be challenging for the algorithm with negative numbers and non-continuity.
    zone_ids_modified_path = hb.temp('.tif', 'zone_ids_modified', True)
    zone_ids_modified = np.where(zone_ids==255, -9999.0, zone_ids).astype(np.int64)
    zone_ids_modified = np.where(zone_ids_modified==12, -44.0, zone_ids).astype(np.int64)
    hb.save_array_as_geotiff(zone_ids_modified, zone_ids_modified_path, zone_ids_raster_path, data_type=5, ndv=-9999.0)

    base_raster_path_band = (zone_ids_modified_path, 1)
    rules[-44] = -3444.
    value_map = rules
    target_raster_path = hb.temp('testing_pgp_reclassify_faster', remove_at_exit=True)
    target_datatype = 6
    target_nodata = -9999
    hb.timer('pgp.geoprocessing.reclassify_raster start')
    pgp.geoprocessing.reclassify_raster(
            base_raster_path_band, value_map, target_raster_path, target_datatype,
            target_nodata)
    hb.timer('pgp.geoprocessing.reclassify_raster time')


    hb.timer('reclassify_raster_hb started')
    zone_ids_modified = hb.as_array(zone_ids_raster_path)
    # zone_ids_modified = hb.as_array(zone_ids_modified_path)
    hb.timer('    reclassify_raster_hb finished read')
    memview = hb.reclassify_raster_hb(zone_ids_modified, rules_array, output_path)
    hb.timer('    reclassify_raster_hb finished array reclassify')
    array = np.asarray(memview)
    target_raster_path = hb.temp('.tif', 'testing_reclassify_raster_hb', remove_at_exit=True)
    hb.save_array_as_geotiff(array, target_raster_path, zone_values_path, data_type=7, ndv=-9999.)
    hb.timer('    reclassify_raster_hb finished write')



print('Tests finished')

