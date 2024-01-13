import os, logging
import hazelbean as hb
import numpy as np
from osgeo import gdal, osr, ogr
import numpy

# L = hb.get_logger('watershed_processing', 'warning')

def merge_hydrosheds_data_by_tile_ids(hydrosheds_dir, output_tif_uri, furthest_west_id, furthest_east_id, furthest_south_id, furthest_north_id):
    furthest_west_id = str(furthest_west_id)
    furthest_east_id = str(furthest_east_id)
    furthest_south_id = str(furthest_south_id)
    furthest_north_id = str(furthest_north_id)

    if furthest_west_id[0] == 'w':
        horizontal_min_id = int(furthest_west_id[1:4]) * -1
    else:
        horizontal_min_id = int(furthest_west_id[1:4])

    if furthest_east_id[0] == 'w':
        horizontal_max_id = int(furthest_east_id[1:4]) * -1
    else:
        horizontal_max_id = int(furthest_east_id[1:4])

    if furthest_south_id[0] == 's':
        vertical_min_id = int(furthest_south_id[1:4]) * -1
    else:
        vertical_min_id = int(furthest_south_id[1:4])

    if furthest_north_id[0] == 's':
        vertical_max_id = int(furthest_north_id[1:4]) * -1
    else:
        vertical_max_id = int(furthest_north_id[1:4])


    filenames = ''
    filenames_list = []
    for horizontal_id in range(horizontal_min_id, horizontal_max_id + 5, 5):
        for vertical_id in range(vertical_min_id, vertical_max_id + 5, 5):
            horizontal_corrected_key = str(abs(horizontal_id)).zfill(3)
            if horizontal_id < 0:
                horizontal_corrected_key = 'w' + horizontal_corrected_key
            else:
                horizontal_corrected_key = 'e' + horizontal_corrected_key
            vertical_corrected_key = str(abs(vertical_id)).zfill(2)
            if vertical_id < 0:
                vertical_corrected_key = 's' + vertical_corrected_key
            else:
                vertical_corrected_key = 'n' + vertical_corrected_key
            current_filename = hydrosheds_dir + '/' + vertical_corrected_key + horizontal_corrected_key + '_con_bil/' + vertical_corrected_key + horizontal_corrected_key + '_con.bil'

            if os.path.isfile(current_filename):
                filenames += ' ' + current_filename
                filenames_list.append(current_filename)
                print(('Adding', current_filename))
            else:
                print(('   SKIPPING', current_filename))
    print('output_tif_uri', output_tif_uri)
    file_list_uri = os.path.join(os.path.split(output_tif_uri)[0], 'virt_file_list.txt')
    with open(file_list_uri, 'w') as f:
        for line in filenames_list:
            f.write(line + '\n')

    gdal_command = 'gdalbuildvrt '
    gdal_command += '-input_file_list ' + file_list_uri + ' '
    srcnodata = None
    if srcnodata:
        gdal_command += '-srcnodata ' + str(srcnodata) + ' '
    # if shifted_extent:
    #     gdal_command += '-a_srs EPSG:4326 -te ' + shifted_extent[0] + ' '  + shifted_extent[1] + ' ' + shifted_extent[2] + ' ' + shifted_extent[3] + ' '

    temporary_virt_filename = output_tif_uri.replace('.tif', '.vrt')

    gdal_command += temporary_virt_filename

    # + ' ' + filenames

    # L.warn('Running external gdal command: ' + gdal_command)
    os.system(gdal_command)

    gdal_command = 'gdalwarp -overwrite ' + temporary_virt_filename + ' ' + output_tif_uri

    # L.warn('Running external gdal command: ' + gdal_command)
    os.system(gdal_command)

def clip_hydrosheds_dem_from_aoi(output_uri, aoi_uri, match_uri):
    hydrosheds_dir = os.path.join(hb.BULK_DATA_DIR, 'hydrosheds/3s/hydrologically_conditioned_dem')
    temp_uri = hb.temp('.tif', remove_at_exit=True)
    merge_hydrosheds_by_aoi(hydrosheds_dir, temp_uri, aoi_uri)

    hb.clip_dataset_uri(temp_uri, aoi_uri, output_uri, assert_datasets_projected=False)
    #
    # resolution = hb.get_linear_unit(match_uri)
    #
    # srs = hb.get_datasource_srs_uri(aoi_uri)
    # output_wkt = srs.ExportToWkt()
    #
    # print('starting reproject to resolution of ' + str(resolution))
    # print(temp2_uri, resolution, output_wkt, 'near', output_uri)
    # hb.reproject_dataset_uri(temp2_uri, resolution, output_wkt, 'bilinear', output_uri)

def get_tile_names_and_degrees_from_aoi(shapefile_uri, tile_increment):
    """Get a list of strings representing tile names under the nsew-degree structure ie
    ['n10w90', 'n10w85', 'n15w90', 'n15w85', 'n20w90', 'n20w85']
    """
    temp_uri = hb.temp(ext='.shp', remove_at_exit=True)
    print('shapefile_uri', shapefile_uri)
    hb.reproject_datasource_uri(shapefile_uri, hb.wgs_84_wkt, temp_uri)

    tile_names = []

    bb = hb.get_datasource_bounding_box(temp_uri)

    degrees = [0,0,0,0]

    degrees[0] = hb.round_to_nearest_containing_increment(bb[1], tile_increment, 'up')
    degrees[1] = hb.round_to_nearest_containing_increment(bb[0], tile_increment, 'down')
    degrees[2] = hb.round_to_nearest_containing_increment(bb[3], tile_increment, 'down')
    degrees[3] = hb.round_to_nearest_containing_increment(bb[2], tile_increment, 'up')

    ns_degree_increments = list(range(degrees[2], degrees[0] + tile_increment, tile_increment))
    ew_degree_increments = list(range(degrees[1], degrees[3] + tile_increment, tile_increment))

    for c1, ns in enumerate(ns_degree_increments):
        for c2, ew in enumerate(ew_degree_increments):
            to_append = ''
            if ns < 0:
                to_append += 's' + str(ns).replace('-', '').zfill(2)
            else:
                to_append += 'n' + str(ns).replace('-', '').zfill(2)
            if ew < 0:
                to_append += 'w' + str(ew).replace('-', '').zfill(3)
            else:
                to_append += 'e' + str(ew).replace('-', '').zfill(3)

            tile_names.append(to_append)

    return tile_names, degrees




def merge_hydrosheds_by_aoi(hydrosheds_dir, output_tif_uri, aoi_uri):
    tile_names, degrees = hb.get_tile_names_and_degrees_from_aoi(aoi_uri, 5)

    filenames = ''
    filenames_list = []
    for tile in tile_names:
        #n00e040_con_bil
        to_append = os.path.join(hydrosheds_dir, tile + '_con_bil', tile + '_con.bil')
        filenames_list.append(to_append)

    file_list_uri = os.path.join(os.path.split(output_tif_uri)[0], 'virt_file_list.txt')
    with open(file_list_uri, 'w') as f:
        for line in filenames_list:
            f.write(line + '\n')

    gdal_command = 'gdalbuildvrt '
    gdal_command += '-input_file_list ' + file_list_uri + ' '
    srcnodata = None
    if srcnodata:
        gdal_command += '-srcnodata ' + str(srcnodata) + ' '
    # if shifted_extent:
    #     gdal_command += '-a_srs EPSG:4326 -te ' + shifted_extent[0] + ' '  + shifted_extent[1] + ' ' + shifted_extent[2] + ' ' + shifted_extent[3] + ' '

    temporary_virt_filename = output_tif_uri.replace('.tif', '.vrt')

    gdal_command += temporary_virt_filename

    # + ' ' + filenames

    # L.warn('Running external gdal command: ' + gdal_command)
    os.system(gdal_command)

    gdal_command = 'gdalwarp -overwrite ' + temporary_virt_filename + ' ' + output_tif_uri

    # L.warn('Running external gdal command: ' + gdal_command)

    os.system(gdal_command)


def calculate_topographic_stats_from_dem(dem_path, output_dir, stats_to_calculate=None, output_suffix=None):
    if not os.path.exists(output_dir):
        # L.warning(output_dir + ' did not exist. Creating it.')
        hb.create_directories(output_dir)

    if not stats_to_calculate:
        stats_to_calculate = ['slope', 'hillshade', 'aspect', 'TRI', 'TPI', 'roughness']

        """TRI outputs a single-band raster with values computed from the elevation. TRI stands for Terrain Ruggedness Index, 
        which is defined as the mean difference between a central pixel and its surrounding cells (see Wilson et al 2007, Marine Geodesy 30:3-35)."""

        """This command outputs a single-band raster with values computed from the elevation. TPI stands for Topographic Position Index, which is 
        defined as the difference between a central pixel and the mean of its surrounding cells (see Wilson et al 2007, Marine Geodesy 30:3-35)."""

        """ROUGHNESS outputs a single-band raster with values computed from the elevation. Roughness is the largest inter-cell difference
         of a central pixel and its surrounding cell, as defined in Wilson et al (2007, Marine Geodesy 30:3-35)."""

    for stat in stats_to_calculate:
        if output_suffix:
            stat_path = os.path.join(output_dir, stat + '_' + output_suffix + '.tif')
        else:
            stat_path = os.path.join(output_dir, stat + '.tif')
        command = 'gdaldem ' + stat + ' '  + dem_path + ' ' + stat_path
        os.system(command)

