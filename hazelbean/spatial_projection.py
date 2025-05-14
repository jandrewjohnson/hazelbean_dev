import os, sys, shutil, random, math, atexit, time, json

from osgeo import gdal, ogr, osr
import numpy as np

import hazelbean as hb
import hazelbean.geoprocessing_extension

import functools
from functools import reduce
from osgeo import gdal
# gdal.SetConfigOption("IGNORE_COG_LAYOUT_BREAK", "YES") 
# gdal.PushErrorHandler('CPLQuietErrorHandler')
L = hb.get_logger('spatial_projection')

def get_wkt_from_epsg_code(epsg_code):
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(int(epsg_code))
    wkt = srs.ExportToWkt()

    return wkt


def get_datasource_srs_uri(dataset_uri):
    driver = ogr.GetDriverByName('ESRI Shapefile')
    dataset = driver.Open(dataset_uri)
    layer = dataset.GetLayer()
    spatialRef = layer.GetSpatialRef()
    return spatialRef


def get_dataset_projection_wkt_uri(dataset_uri):
    """Get the projection of a GDAL dataset as well known text (WKT).

    Args:
        dataset_uri (string): a URI for the GDAL dataset

    Returns:
        proj_wkt (string): WKT describing the GDAL dataset project
    """
    dataset = gdal.Open(dataset_uri)
    proj_wkt = dataset.GetProjection()
    gdal.Dataset.__swig_destroy__(dataset)
    dataset = None
    return proj_wkt



def get_linear_unit(input_uri):
    input_ds = gdal.Open(input_uri)
    geo_t = input_ds.GetGeoTransform()
    resolution = geo_t[1]

    return resolution


def get_linear_unit_from_other_projection(input_uri, projected_uri, also_return_size=False):
    input_ds = gdal.Open(input_uri)
    projected_wkt = hb.get_dataset_projection_wkt_uri(projected_uri)

    # Create a virtual raster that is projected based on the output WKT. This
    # vrt does not save to disk and is used to get the proper projected
    # bounding box and size.
    vrt = gdal.AutoCreateWarpedVRT(
        input_ds, None, projected_wkt, gdal.GRA_Bilinear)

    geo_t = vrt.GetGeoTransform()
    x_size = vrt.RasterXSize  # Raster xsize
    y_size = vrt.RasterYSize  # Raster ysize

    resolution = geo_t[1]

    if also_return_size:
        return resolution, x_size, y_size
    else:
        return resolution


def get_area_of_pixel_from_center_lat(pixel_size, center_lat):
    """Calculate m^2 area of a wgs84 square pixel.

    Adapted from: https://gis.stackexchange.com/a/127327/2397

    Parameters:
        pixel_size (float): length of side of pixel in degrees.
        center_lat (float): latitude of the center of the pixel. Note this
            value +/- half the `pixel-size` must not exceed 90/-90 degrees
            latitude or an invalid area will be calculated.

    Returns:
        Area of square pixel of side length `pixel_size` centered at
        `center_lat` in m^2.

    """
    a = 6378137  # meters
    b = 6356752.3142  # meters
    e = math.sqrt(1 - (b / a) ** 2)
    area_list = []
    for f in [center_lat + pixel_size / 2, center_lat - pixel_size / 2]:
        zm = 1 - e * math.sin(math.radians(f))
        zp = 1 + e * math.sin(math.radians(f))
        area_list.append(
            math.pi * b ** 2 * (
                    math.log(zp / zm) / (2 * e) +
                    math.sin(math.radians(f)) / (zp * zm)))
    return pixel_size / 360. * (area_list[0] - area_list[1])


def get_area_of_pixel_column_from_center_lats(pixel_size, center_lat_column):
    """Calculate a column of ha per cell in wgs84 of square pixel in a vertical column.

    Adapted from: https://gis.stackexchange.com/a/127327/2397

    This replicates the authalic size of earth almost exactly:
    4 * pi * (6371.0071809)^2 = 510065621.721 km2

    Earth's authalic ("equal area") radius is the radius of a hypothetical perfect sphere
    that has the same surface area as the reference ellipsoid.

    returns a column of m2 per gridcell at that latitude.

    """
    output_column = np.zeros(len(center_lat_column))
    a = 6378137  # meters
    b = 6356752.3142  # meters
    e = math.sqrt(1 - (b / a) ** 2)

    i = 0
    for center_lat in center_lat_column:
        area_list = []
        for f in [center_lat + pixel_size / 2, center_lat - pixel_size / 2]:
            zm = 1 - e * math.sin(math.radians(f))
            zp = 1 + e * math.sin(math.radians(f))
            area_list.append(
                math.pi * b ** 2 * (
                        math.log(zp / zm) / (2 * e) +
                        math.sin(math.radians(f)) / (zp * zm)))
        output_column[i] = pixel_size / 360. * (area_list[0] - area_list[1])
        i += 1
    return output_column

def calc_cylindrical_geotransform_from_array(input_array):
    """Assume the array is a global cylindrical geotiff. Calculate the geotransform that would make it such."""

    y_size = 180.0 / float(input_array.shape[0])
    x_size = 360.0 / float(input_array.shape[1])

    if x_size != y_size:
        print ('Warning, x_size not same as y_size')

    geotransform = (-180.0, x_size, 0.0, 90.0, 0.0, -y_size)
    return geotransform

def assert_gdal_paths_have_same_geotransform(input_paths_list, return_result=False):
    if not isinstance(input_paths_list, list):
        input_paths_list = [input_paths_list]
    first_geotransform = hb.get_geotransform_uri(input_paths_list[0])
    for path in input_paths_list[1:]:
        geotransform = hb.get_geotransform_uri(path)
        if geotransform == first_geotransform:
            if return_result:
                return True
            else:
                'we good'
        else:
            error_string = 'Two paths do not have the same geotransform, as found by assert_gdal_paths_in_same_projection. \n    ' + input_paths_list[0] + ': ' + str(first_geotransform) + '\n    ' + path + ': ' + str(geotransform)
            if return_result:
                L.critical(error_string)
                return False
            raise NameError(error_string)


def assert_gdal_paths_in_same_projection(input_paths_list, return_result=False, debug=False):
    if not isinstance(input_paths_list, list):
        input_paths_list = [input_paths_list]
    first_srs = hb.get_gdal_srs_path(input_paths_list[0])
    for path in input_paths_list[1:]:
        # ext = os.path.splitext(path)[1]
        # if ext in hb.common_gdal_readable_file_extensions:
        #     info = hb.get_raster_info_hb(path)
        # elif ext in ['.shp']:
        #     info = hb.get_vector_info(path)
        # else:
        #     raise TypeError('input_paths_list given to assert_gdal_paths_in_same_projection was not able to be interpretted on item ' + str(path) + ' from fuller list ' + str(input_paths_list))
        srs = hb.get_gdal_srs_path(path)

        if debug:
            L.info('\n')
            L.info(input_paths_list[0])
            L.info(first_srs)
            L.info(first_srs.GetAttrValue('PROJCS'))
            L.info(first_srs.GetAttrValue('GEOGCS'))
            L.info(first_srs.GetAttrValue('DATUM'))
            L.info(first_srs.GetAttrValue('UNIT'))
            L.info(first_srs.GetAttrValue('UNIT', 1)) # Overriding the defaul 0 gets the VALUE of the value
            L.info(first_srs.IsSameGeogCS(first_srs))
            L.info(first_srs.IsSame(first_srs))

            L.info('\n')
            L.info(path)
            L.info(srs)
            L.info(srs.GetAttrValue('PROJCS'))
            L.info(srs.GetAttrValue('GEOGCS'))
            L.info(srs.GetAttrValue('DATUM'))
            L.info(srs.GetAttrValue('UNIT'))
            L.info(srs.GetAttrValue('UNIT', 1)) # Overriding the defaul 0 gets the VALUE of the value
            L.info(srs.IsSameGeogCS(first_srs))
            L.info(srs.IsSame(first_srs))

        if hb.assert_two_srs_equivilent(first_srs, srs, True):
            if return_result:
                return True
            else:
                'we good'
        else:
            error_string = 'The path ' + str(path) + ' is not the same projection as the other paths in the list given to assert_gdal_paths_in_same_projection. \n  First srs: ' + str(first_srs) + '\n  Second srs: ' + str(srs)
            if return_result:
                return False
            raise NameError(error_string)

def assert_two_srs_equivilent(first_srs, second_srs, return_result=False):

    result = True
    if first_srs.GetAttrValue('PROJCS') != second_srs.GetAttrValue('PROJCS'):
        L.critical('Mismatch in projections:\n' + str(first_srs.GetAttrValue('PROJCS')) + '\n' + str(second_srs.GetAttrValue('PROJCS')) )
        result = False
    if first_srs.GetAttrValue('GEOGCS') != second_srs.GetAttrValue('GEOGCS'):
        L.critical('Mismatch in projections:\n' + str(first_srs.GetAttrValue('GEOGCS')) + '\n' + str(second_srs.GetAttrValue('GEOGCS')) )
        result = False
    if first_srs.GetAttrValue('DATUM') != second_srs.GetAttrValue('DATUM'):
        L.critical('Mismatch in projections:\n' + str(first_srs.GetAttrValue('DATUM')) + '\n' + str(second_srs.GetAttrValue('DATUM')) )
        result = False
    if first_srs.GetAttrValue('UNIT') != second_srs.GetAttrValue('UNIT'):
        L.critical('Mismatch in projections:\n' + str(first_srs.GetAttrValue('UNIT')) + '\n' + str(second_srs.GetAttrValue('UNIT')) )
        result = False
    if first_srs.GetAttrValue('UNIT', 1) != second_srs.GetAttrValue('UNIT', 1):
        L.critical('Mismatch in projections:\n' + str(first_srs.GetAttrValue('UNIT')) + '\n' + str(second_srs.GetAttrValue('UNIT')) )
        result = False
    if first_srs.GetAttrValue('DATUM|SPHEROID', 1) != second_srs.GetAttrValue('DATUM|SPHEROID', 1):
        L.critical('Mismatch in projections:\n' + str(first_srs.GetAttrValue('DATUM|SPHEROID')) + '\n' + str(second_srs.GetAttrValue('DATUM|SPHEROID')) )
        result = False
    if first_srs.GetAttrValue('DATUM|SPHEROID', 2) != second_srs.GetAttrValue('DATUM|SPHEROID', 2):
        L.critical('Mismatch in projections:\n' + str(first_srs.GetAttrValue('DATUM|SPHEROID')) + '\n' + str(second_srs.GetAttrValue('DATUM|SPHEROID')) )
        result = False

    # LEARNING POINT: To get deeper leverls of srs attributes use pipe character: srs.GetAttrValue("PROJCS|GEOGCS|AUTHORITY", 1)

    if result:
        if return_result:
            return True
        else:
            'we good'
    else:
        error_string = 'The first srs is not the same projection as the other srs. \n  First srs:'
        if return_result:
            return False
        raise NameError(error_string)
  # First srs: GEOGCS["WGS84",DATUM["WGS_1984",SPHEROID["WGS84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]
  # Secondsrs: GEOGCS["WGS84",DATUM["WGS_1984",SPHEROID["WGS84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]


def assert_gdal_paths_have_same_bb(input_paths_list, return_result=False):
    if not isinstance(input_paths_list, list):
        input_paths_list = [input_paths_list]
    first_bb = hb.get_bounding_box(input_paths_list[0])
    for path in input_paths_list[1:]:
        bb = hb.get_bounding_box(path)
        if bb == first_bb:
            if return_result:
                return True
            else:
                'we good'
        else:
            error_string = 'Two paths do not have the same bounding boxes, as found by assert_gdal_paths_have_same_bb. \n    ' + input_paths_list[0] + ': ' + str(first_bb) + '\n    ' + path + ': ' + str(bb)
            if return_result:
                L.critical(error_string)
                return False
            raise NameError(error_string)


def assert_datasets_in_same_projection(dataset_uri_list):
    """Assert that provided datasets are all in the same projection.

    Tests if datasets represented by their uris are projected and in
    the same projection and raises an exception if not.

    Args:
        dataset_uri_list (list): (description)

    Returns:
        is_true (boolean): True (otherwise exception raised)

    Raises:
        DatasetUnprojected: if one of the datasets is unprojected.
        DifferentProjections: if at least one of the datasets is in
            a different projection
    """
    dataset_list = [gdal.Open(dataset_uri) for dataset_uri in dataset_uri_list]
    dataset_projections = []

    unprojected_datasets = set()
    for dataset in dataset_list:
        projection_as_str = dataset.GetProjection()
        dataset_sr = osr.SpatialReference()
        dataset_sr.ImportFromWkt(projection_as_str)
        if not dataset_sr.IsProjected():
            unprojected_datasets.add(dataset.GetFileList()[0])
        dataset_projections.append((dataset_sr, dataset.GetFileList()[0]))



    for index in range(len(dataset_projections)-1):
        if not dataset_projections[index][0].IsSame(
                dataset_projections[index+1][0]):
            L.warn(
                "These two datasets might not be in the same projection."
                " The different projections are:\n\n'filename: %s'\n%s\n\n"
                "and:\n\n'filename:%s'\n%s\n\n",
                dataset_projections[index][1],
                dataset_projections[index][0].ExportToPrettyWkt(),
                dataset_projections[index+1][1],
                dataset_projections[index+1][0].ExportToPrettyWkt())

    for dataset in dataset_list:
        # Close and clean up dataset
        gdal.Dataset.__swig_destroy__(dataset)
    dataset_list = None
    return True


def get_unaligned_raster_paths(input_paths_list, match_raster_path=None):
    """
    Return True if all rasters in input_paths_list are perfectly compatible. This is tested by checking if all paths in list
    match match_raster (if provided) or the first raster in the list if not provided. If any dont match, returns a list
    of with paths that dont match
    :param input_paths_list:
    :param match_raster:
    :return:
    """

    return_list = []
    starting_element = 0
    if match_raster_path is None:
        match_raster_path = input_paths_list[0]
        starting_element = 1
    for path in input_paths_list[starting_element:]:
        a = hb.assert_gdal_paths_have_same_geotransform([path, match_raster_path], return_result=True)
        b = hb.assert_gdal_paths_in_same_projection([path, match_raster_path], return_result=True)
        c = hb.assert_gdal_paths_have_same_bb([path, match_raster_path], return_result=True)

        overall_result = all([a, b, c])
        if not overall_result:
            return_list.append(path)

    return return_list


def get_bounding_box(input_path, return_in_basemap_order=False, return_in_old_order=False):
    """

    WARNING, This changed notation from UL LR to xmin ymin xmax ymax and may not have back\ward compatibility.
     from the bounding box reported by pygeoprocessing insofar as it is UL, LR (but PGP is LL, UR)
    Get bounding box where coordinates are in projected units.

    Args:
        input_path (string): a uri to a GDAL dataset

    Returns:
        bounding_box (list):
            [upper_left_x, upper_left_y, lower_right_x, lower_right_y] in
            projected coordinates
    """
    if os.path.splitext(input_path)[1].lower() == '.shp' or os.path.splitext(input_path)[1].lower() == '.gpkg':
        bounding_box = hb.geoprocessing_extension.get_vector_info_hb(input_path)['bounding_box']
    else:
        bounding_box = hb.get_raster_info_hb(input_path)['bounding_box']

    if return_in_basemap_order:
        dataset = gdal.Open(input_path)

        geotransform = dataset.GetGeoTransform()
        n_cols = dataset.RasterXSize
        n_rows = dataset.RasterYSize

        bounding_box = [geotransform[0],
                        geotransform[3],
                        geotransform[0] + n_cols * geotransform[1],
                        geotransform[3] + n_rows * geotransform[5]]

        # Close and cleanup dataset
        gdal.Dataset.__swig_destroy__(dataset)
        dataset = None


        bounding_box = [
            bounding_box[3], # llcrnrlat
            bounding_box[1], # urcrnrlat
            bounding_box[0], # llcrnrlon
            bounding_box[2], # urcrnrlon
        ]
        return bounding_box

    if return_in_old_order:
        dataset = gdal.Open(input_path)

        geotransform = dataset.GetGeoTransform()
        n_cols = dataset.RasterXSize
        n_rows = dataset.RasterYSize

        bounding_box = [geotransform[0],
                        geotransform[3],
                        geotransform[0] + n_cols * geotransform[1],
                        geotransform[3] + n_rows * geotransform[5]]

        # Close and cleanup dataset
        gdal.Dataset.__swig_destroy__(dataset)
        dataset = None


        return bounding_box

    return bounding_box

def get_datasource_bounding_box(datasource_uri, return_in_old_order=False):
    """
    Returns a bounding box where coordinates are in projected units.

    Args:
        dataset_uri (string): a uri to a GDAL dataset

    Returns:
        bounding_box (list):
            [upper_left_x, upper_left_y, lower_right_x, lower_right_y] in
            projected coordinates

    """
    print ('DEPRECATED for get_bounding_box()')
    datasource = ogr.Open(datasource_uri)
    layer = datasource.GetLayer(0)
    extent = layer.GetExtent()
    #Reindex datasource extents into the upper left/lower right coordinates
    bounding_box = [extent[0],
                    extent[3],
                    extent[1],
                    extent[2]]
    if return_in_old_order:
        bounding_box = hb.get_vector_info_hb(datasource_uri)
        return bounding_box


    return bounding_box



if 0:
    # STEP 1, identify how resample_to_match is different than resample_to_match_ensuring_fit and
    # if minimal, make into 1 eqn with an option
    # STEP 2, veryfiy/improve warp_raster_hb make it supported and clarify how it's different than warp_raster pgp
    # STEP 3: make resample_list_to_match
    # STEP 4: clarify if warb_raster_hb is sufficiently different than resample_to_match

    hb.resample_list_to_match_ensuring_fit()
    hb.resample_to_match()
    hb.warp_raster_hb
    gdal.Warp

    hb.resample_to_match()
    hb.warp_raster_hb
    gdal.Warp

    hb.resample_to_match_ensuring_fit()
    hb.warp_raster_hb()
    gdal.Warp

    # DEPRECATED
    hb.align_list_of_datasets_to_match()
    hb.align_and_resize_raster_stack_ensuring_fit()
    hb.warp_raster_HAZELBEAN_REPLACEMENT()
    gdal.ReprojectImage

    # DOESNT EXIST
    hb.resample()  #


def resample_to_match(input_path,
                      match_path,
                      output_path,
                      resample_method='bilinear',
                      output_data_type=None,
                      src_ndv=None,
                      ndv=None,
                      s_srs_wkt=None,
                      compress=True,
                      ensure_fits=False,
                      gtiff_creation_options=hb.globals.DEFAULT_GTIFF_CREATION_OPTIONS,
                      calc_raster_stats=False,
                      add_overviews=False,
                      pixel_size_override=None,
                      target_aligned_pixels=True,
                      bb_override=None,
                      verbose=False,
                      ):
    if pixel_size_override is None:
        target_pixel_size = (hb.get_cell_size_from_uri(match_path), -hb.get_cell_size_from_uri(match_path))
    elif not isinstance(pixel_size_override, (tuple, list)):
        target_pixel_size = (pixel_size_override, -pixel_size_override)

    target_sr_wkt = hb.get_raster_info_hb(match_path)['projection']

    if bb_override is None:
        target_bb = hb.get_raster_info_hb(match_path)['bounding_box']
    else:
        target_bb = bb_override
        
    if output_data_type is None:
        output_data_type = hb.get_datatype_from_uri(match_path)

    if src_ndv is None:
        src_ndv = hb.get_ndv_from_path(match_path)

    if ndv is None:
        dst_ndv = hb.get_ndv_from_path(match_path)
    else:
        dst_ndv = ndv
        # correct_ndv = hb.get_correct_ndv_from_dtype_flex(output_data_type, is_id=True)
        # if output_data_type < 5:
        #     dst_ndv = 255
        # else:
        #     dst_ndv = -9999.0

    if ensure_fits:
        # This addition to the core geoprocessing code was to fix the case where the alignment moved the target tif
        # up and to the left, but in a way that then trunkated 1 row/col on the bottom right, causing wrong-shape
        # raster_math errors.z
        pass
        # target_bounding_box = reduce(
        #     functools.partial(hb.merge_bounding_boxes, mode=bounding_box_mode),
        #     [info['bounding_box'] for info in
        #      (raster_info_list + vector_info_list)])
        #
        # if original_bounding_box[2] > target_bounding_box[2]:
        #     target_bounding_box[2] += target_pixel_size[0]
        #
        # if original_bounding_box[3] > target_bounding_box[3]:
        #     target_bounding_box[3] -= target_pixel_size[1]

        target_bb[2] += target_pixel_size[0]
        target_bb[3] += target_pixel_size[1]
    if compress is True or compress == 'ZSTD':
        gtiff_creation_options = (
            'TILED=YES',
            'BIGTIFF=YES',
            'COMPRESS=ZSTD',
            'BLOCKXSIZE=512',
            'BLOCKYSIZE=512',
        )
    elif compress:
        gtiff_creation_options = (
            'TILED=YES',
            'BIGTIFF=YES',
            'BLOCKXSIZE=512',
            'BLOCKYSIZE=512',
            compress.upper(),
        )
    else:
        gtiff_creation_options = (
            'TILED=YES',
            'BIGTIFF=YES',
            'BLOCKXSIZE=512',
            'BLOCKYSIZE=512',
        )
    hb.warp_raster_hb(input_path, target_pixel_size, output_path,
                      resample_method, target_bb=target_bb, base_sr_wkt=s_srs_wkt, target_sr_wkt=target_sr_wkt,
                      gtiff_creation_options=gtiff_creation_options,
                      n_threads=None, vector_mask_options=None,
                      output_data_type=output_data_type,
                      src_ndv=src_ndv,
                      dst_ndv=dst_ndv,
                      calc_raster_stats=calc_raster_stats,
                      add_overviews=add_overviews,
                      target_aligned_pixels=target_aligned_pixels,
    )


def resample_in_memory(input_path, match_path, resamping_method):
    # NYI flex. still uses paths
    # input_flex = hb.parse_input_flex(input_flex)

    input_ds = gdal.OpenEx(input_path)
    # input_ds = gdal.OpenEx(input_flex.path)
    match_ds = gdal.OpenEx(match_path)

    # TODOOO
    input_raster_info = hb.get_raster_info_hb(input_path)
    # input_raster_info = hb.get_raster_info_hb(input_flex.path)
    match_raster_info = hb.get_raster_info_hb(match_path)

    input_wkt = input_raster_info['projection']
    match_wkt = match_raster_info['projection']

    input_gt = input_raster_info['geotransform']
    match_gt = match_raster_info['geotransform']

    match_x_size = match_ds.RasterXSize
    match_y_size = match_ds.RasterYSize

    match_ulx = match_gt[0]
    match_uly = match_gt[3]
    match_lrx = match_gt[0] + match_gt[1] * match_x_size
    match_lry = match_gt[3] + match_gt[5] * match_y_size

    pixel_spacing = input_raster_info['pixel_size'][0]

    # tx = osr.CoordinateTransformation(wgs84, osng)
    # (ulx, uly, ulz) = tx.TransformPoint(geo_t[0], geo_t[3])
    # (lrx, lry, lrz) = tx.TransformPoint(geo_t[0] + geo_t[1] * x_size, \
    #                                     geo_t[3] + geo_t[5] * y_size)
    #
    # Get the Geotransform vector
    mem_drv = gdal.GetDriverByName('MEM')

    output_ds = mem_drv.Create('', match_x_size, match_y_size, 1, gdal.GDT_Float32)

    # new_geo = (ulx, pixel_spacing, geo_t[2], uly, geo_t[4], -pixel_spacing)
    output_ds.SetGeoTransform(match_gt)
    output_ds.SetProjection(match_wkt)

    # Perform the projection/resampling
    gdal.ReprojectImage(input_ds, output_ds, input_wkt, match_wkt, hb.resampling_methods[resamping_method])
    return output_ds



def resize_and_resample_dataset_uri(
        original_dataset_uri, bounding_box, out_pixel_size, output_uri,
        resample_method, output_datatype=None):


    L.critical('DEPRECATED!!!'
               ''
               'resize_and_resample_dataset_uri is deprecated. use hb.resample_to_match (Which is a wrapper).')
    """
    A function to  a datsaet to larger or smaller pixel sizes

    Args:
        original_dataset_uri (string): a GDAL dataset
        bounding_box (list): [upper_left_x, upper_left_y, lower_right_x,
            lower_right_y]
        out_pixel_size (?): the pixel size in projected linear units
        output_uri (string): the location of the new resampled GDAL dataset
        resample_method (string): the resampling technique, one of
            "nearest|bilinear|cubic|cubic_spline|lanczos"

    Returns:
        nothing

    """

    resample_dict = {
        "nearest": gdal.GRA_NearestNeighbour,
        "near": gdal.GRA_NearestNeighbour,
        "nearest_neighbor": gdal.GRA_NearestNeighbour,
        "bilinear": gdal.GRA_Bilinear,
        "cubic": gdal.GRA_Cubic,
        "cubicspline": gdal.GRA_CubicSpline,
        "lanczos": gdal.GRA_Lanczos,
        "average": gdal.GRA_Average
    }


    original_dataset = gdal.Open(original_dataset_uri)
    original_band = original_dataset.GetRasterBand(1)
    original_nodata = original_band.GetNoDataValue()
    #gdal python doesn't handle unsigned nodata values well and sometime returns
    #negative numbers.  this guards against that
    if original_band.DataType == gdal.GDT_Byte:
        original_nodata %= 2**8
    if original_band.DataType == gdal.GDT_UInt16:
        original_nodata %= 2**16
    if original_band.DataType == gdal.GDT_UInt32:
        original_nodata %= 2**32

    if not output_datatype:
        output_datatype = original_band.DataType

    if original_nodata is None:
        L.debug('Nodata not defined in resize_and_resample_dataset_uri on ' + str(original_dataset_uri) + '. This can be correct but is dangerous because you might have the no_data_value contribute to the resampled values.')
        original_nodata = -9999

    original_sr = osr.SpatialReference()
    original_sr.ImportFromWkt(original_dataset.GetProjection())

    output_geo_transform = [
        bounding_box[0], out_pixel_size, 0.0, bounding_box[1], 0.0,
        -out_pixel_size]
    new_x_size = abs(
        int(np.round((bounding_box[2] - bounding_box[0]) / out_pixel_size)))
    new_y_size = abs(
        int(np.round((bounding_box[3] - bounding_box[1]) / out_pixel_size)))

    #create the new x and y size
    block_size = original_band.GetBlockSize()
    #If the original band is tiled, then its x blocksize will be different than
    #the number of columns
    if block_size[0] != original_band.XSize and original_band.XSize > 256 and original_band.YSize > 256:
        #it makes sense for a wad of invest functions to use 256x256 blocks, lets do that here
        block_size[0] = 256
        block_size[1] = 256
        gtiff_creation_options = [
            'TILED=YES', 'BIGTIFF=IF_SAFER', 'BLOCKXSIZE=%d' % block_size[0],
                                             'BLOCKYSIZE=%d' % block_size[1]]
    else:
        #this thing is so small or strangely aligned, use the default creation options
        gtiff_creation_options = []

    hb.create_directories([os.path.dirname(output_uri)])
    gdal_driver = gdal.GetDriverByName('GTiff')

    output_dataset = gdal_driver.Create(
        output_uri, new_x_size, new_y_size, 1, output_datatype,
        options=gtiff_creation_options)
    output_band = output_dataset.GetRasterBand(1)
    if original_nodata is None:
        original_nodata = float(
            -9999.)

    output_band.SetNoDataValue(original_nodata)

    # Set the geotransform
    output_dataset.SetGeoTransform(output_geo_transform)
    output_dataset.SetProjection(original_sr.ExportToWkt())

    #need to make this a closure so we get the current time and we can affect
    #state
    def reproject_callback(df_complete, psz_message, p_progress_arg):
        """The argument names come from the GDAL API for callbacks."""
        try:
            current_time = time.time()
            if ((current_time - reproject_callback.last_time) > 5.0 or
                    (df_complete == 1.0 and reproject_callback.total_time >= 5.0)):
                # LOGGER.info(
                #     "ReprojectImage %.1f%% complete %s, psz_message %s",
                #     df_complete * 100, p_progress_arg[0], psz_message)
                print ("ReprojectImage for resize_and_resample_dataset_uri " + str(df_complete * 100) + " percent complete")
                reproject_callback.last_time = current_time
                reproject_callback.total_time += current_time
        except AttributeError:
            reproject_callback.last_time = time.time()
            reproject_callback.total_time = 0.0

    # Perform the projection/resampling
    gdal.ReprojectImage(
        original_dataset, output_dataset, original_sr.ExportToWkt(),
        original_sr.ExportToWkt(), resample_dict[resample_method], 0, 0,
        reproject_callback, [output_uri])

    #Make sure the dataset is closed and cleaned up
    original_band = None
    gdal.Dataset.__swig_destroy__(original_dataset)
    original_dataset = None

    output_dataset.FlushCache()
    gdal.Dataset.__swig_destroy__(output_dataset)
    output_dataset = None
    hb.calculate_raster_stats_uri(output_uri)



def resize_and_resample_dataset_uri_hb_old(
        original_dataset_uri, bounding_box, out_pixel_size, output_uri,
        resample_method):
    """Resize and resample the given dataset.

    Args:
        original_dataset_uri (string): a GDAL dataset
        bounding_box (list): [upper_left_x, upper_left_y, lower_right_x,
            lower_right_y]
        out_pixel_size: the pixel size in projected linear units
        output_uri (string): the location of the new resampled GDAL dataset
        resample_method (string): the resampling technique, one of
            "nearest|bilinear|cubic|cubic_spline|lanczos"

    Returns:
        None
    """
    resample_dict = {
        "nearest": gdal.GRA_NearestNeighbour,
        "nearest_neighbor": gdal.GRA_NearestNeighbour,
        "bilinear": gdal.GRA_Bilinear,
        "cubic": gdal.GRA_Cubic,
        "cubic_spline": gdal.GRA_CubicSpline,
        "lanczos": gdal.GRA_Lanczos,
        "average": gdal.GRA_Average,
    }

    original_dataset = gdal.Open(original_dataset_uri)
    original_band = original_dataset.GetRasterBand(1)
    original_nodata = original_band.GetNoDataValue()

    if original_nodata is None:
        original_nodata = -9999

    original_sr = osr.SpatialReference()
    original_sr.ImportFromWkt(original_dataset.GetProjection())

    output_geo_transform = [
        bounding_box[0], out_pixel_size, 0.0, bounding_box[1], 0.0,
        -out_pixel_size]
    new_x_size = abs(
        int(np.round((bounding_box[2] - bounding_box[0]) / out_pixel_size)))
    new_y_size = abs(
        int(np.round((bounding_box[3] - bounding_box[1]) / out_pixel_size)))

    if new_x_size == 0:
        print (
            "bounding_box is so small that x dimension rounds to 0; "
            "clamping to 1.")
        new_x_size = 1
    if new_y_size == 0:
        print (
            "bounding_box is so small that y dimension rounds to 0; "
            "clamping to 1.")
        new_y_size = 1

    # create the new x and y size
    block_size = original_band.GetBlockSize()
    # If the original band is tiled, then its x blocksize will be different
    # than the number of columns
    if original_band.XSize > 256 and original_band.YSize > 256:
        # it makes sense for many functions to have 256x256 blocks
        block_size[0] = 256
        block_size[1] = 256
        gtiff_creation_options = [
            'TILED=YES', 'BIGTIFF=IF_SAFER', 'BLOCKXSIZE=%d' % block_size[0],
                                             'BLOCKYSIZE=%d' % block_size[1]]

        metadata = original_band.GetMetadata('IMAGE_STRUCTURE')
        if 'PIXELTYPE' in metadata:
            gtiff_creation_options.append('PIXELTYPE=' + metadata['PIXELTYPE'])
    else:
        # it is so small or strangely aligned, use the default creation options
        gtiff_creation_options = []

    hb.create_directories([os.path.dirname(output_uri)])
    gdal_driver = gdal.GetDriverByName('GTiff')
    output_dataset = gdal_driver.Create(
        output_uri, new_x_size, new_y_size, 1, original_band.DataType,
        options=gtiff_creation_options)
    output_band = output_dataset.GetRasterBand(1)

    output_band.SetNoDataValue(original_nodata)

    # Set the geotransform
    output_dataset.SetGeoTransform(output_geo_transform)
    output_dataset.SetProjection(original_sr.ExportToWkt())

    # need to make this a closure so we get the current time and we can affect
    # state
    def reproject_callback(df_complete, psz_message, p_progress_arg):
        """The argument names come from the GDAL API for callbacks."""
        try:
            current_time = time.time()
            if ((current_time - reproject_callback.last_time) > 5.0 or
                    (df_complete == 1.0 and reproject_callback.total_time >= 5.0)):
                print (
                    "ReprojectImage %.1f%% complete %s, psz_message %s",
                    df_complete * 100, p_progress_arg[0], psz_message)
                reproject_callback.last_time = current_time
                reproject_callback.total_time += current_time
        except AttributeError:
            reproject_callback.last_time = time.time()
            reproject_callback.total_time = 0.0

    # Perform the projection/resampling
    gdal.ReprojectImage(
        original_dataset, output_dataset, original_sr.ExportToWkt(),
        original_sr.ExportToWkt(), resample_dict[resample_method], 0, 0,
        reproject_callback, [output_uri])

    # Make sure the dataset is closed and cleaned up
    original_band = None
    gdal.Dataset.__swig_destroy__(original_dataset)
    original_dataset = None

    output_dataset.FlushCache()
    gdal.Dataset.__swig_destroy__(output_dataset)
    output_dataset = None
    hb.calculate_raster_stats_uri(output_uri)



def force_geotiff_to_match_projection_ndv_and_datatype(input_path, match_path, output_path, output_datatype=None, output_ndv=None):
    """Rather than actually projecting, just change the metadata so it matches exactly. This only will be useful
    if there was a data error and something got a projection defined when the underlying data wasnt actually transofmred
    into that shape.

    NOTE that the output will keep the same geotransform as input, and only the projection, no data and datatype will change.
    """

    if not output_datatype:

        output_datatype = hb.get_datatype_from_uri(match_path)

    if not output_ndv:
        output_ndv = hb.get_ndv_from_path(match_path)
    match_wkt = hb.get_dataset_projection_wkt_uri(match_path)
    input_geotransform  = hb.get_geotransform_uri(input_path)

    # Load the array, but use numpy to convert it to the new datatype
    input_array = hb.as_array(input_path).astype(hb.gdal_number_to_numpy_type[output_datatype])

    if not output_ndv:
        output_ndv = -9999

    hb.save_array_as_geotiff(input_array, output_path,
                             data_type=output_datatype,
                             ndv=output_ndv,
                             geotransform_override=input_geotransform,
                             projection_override=match_wkt)


def force_global_angular_data_to_plate_carree(input_path, output_path):

    output_datatype = hb.get_datatype_from_uri(input_path)
    output_ndv = hb.get_ndv_from_path(input_path)
    match_wkt = hb.get_dataset_projection_wkt_uri(input_path)
    match_wkt = hb.get_wkt_from_epsg_code(32662)

    input_geotransform  = hb.get_geotransform_uri(input_path)

    output_geotransform = list(hb.common_geotransforms['wec_30s'])

    output_geotransform[1] = input_geotransform[1] * hb.size_of_one_arcdegree_at_equator_in_meters
    output_geotransform[5] = input_geotransform[5] * hb.size_of_one_arcdegree_at_equator_in_meters


    # Load the array, but use numpy to convert it to the new datatype
    input_array = hb.as_array(input_path).astype(hb.gdal_number_to_numpy_type[output_datatype])

    if not output_ndv:
        output_ndv = -9999

    hb.save_array_as_geotiff(input_array, output_path,
                             data_type=output_datatype,
                             ndv=output_ndv,
                             geotransform_override=output_geotransform,
                             projection_override=match_wkt)


def force_global_angular_data_to_equal_area_earth_grid(input_path, output_path):

    output_datatype = hb.get_datatype_from_uri(input_path)
    output_ndv = hb.get_ndv_from_path(input_path)
    match_wkt = hb.get_dataset_projection_wkt_uri(input_path)
    match_wkt = hb.get_wkt_from_epsg_code(6933)

    input_geotransform  = hb.get_geotransform_uri(input_path)

    output_geotransform = list(hb.common_geotransforms['wec_30s'])

    output_geotransform[1] = input_geotransform[1] * hb.size_of_one_arcdegree_at_equator_in_meters
    output_geotransform[5] = input_geotransform[5] * hb.size_of_one_arcdegree_at_equator_in_meters


    # Load the array, but use numpy to convert it to the new datatype
    input_array = hb.as_array(input_path).astype(hb.gdal_number_to_numpy_type[output_datatype])

    if not output_ndv:
        output_ndv = -9999

    hb.save_array_as_geotiff(input_array, output_path,
                             data_type=output_datatype,
                             ndv=output_ndv,
                             geotransform_override=output_geotransform,
                             projection_override=match_wkt)









