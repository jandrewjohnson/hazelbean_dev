"""Hazelbean relies on pygeoprocessing, but there are some cases where an optimal change requires duplicating some code. To minimize upgrading challenges
Hazelbean offers a few functions that reimplement pgp and by convention keep a similar funciton name with the change listed after the matched function name."""

import os, sys, time, math, logging
import hazelbean as hb

from osgeo import gdal
from osgeo import osr
from osgeo import ogr
import numpy as np
import numpy as numpy
from collections import OrderedDict

from decimal import Decimal
import functools
import queue
import threading
import json
import pygeoprocessing


from osgeo import gdal
# gdal.SetConfigOption("IGNORE_COG_LAYOUT_BREAK", "YES") 
# gdal.PushErrorHandler('CPLQuietErrorHandler')

# pgp takes about 1 sec to import.
# HACK I am just not importing this because stat_worker was written in the C and I want to update pgp before I start using that stuff.
# import pygeoprocessing.geoprocessing_core as gpc

# # Key lines here: for convenience and cross-compatibility, I import pgp into the hb namespace
# import pygeoprocessing as pgp
# import pygeoprocessing.geoprocessing_core as gpc
# from pygeoprocessing.geoprocessing import *
# from pygeoprocessing.geoprocessing_core import *

L = hb.get_logger('geoprocessing_extension')
L.setLevel(logging.INFO)

def align_and_resize_raster_stack_ensuring_fit(
        base_raster_path_list, target_raster_path_list, resample_method_list,
        target_pixel_size, bounding_box_mode, base_vector_path_list=None,
        raster_align_index=None, ensure_fits=False, all_touched=False,
        gtiff_creation_options=hb.globals.DEFAULT_GTIFF_CREATION_OPTIONS,
        output_data_type=None,
        src_ndv=None,
        dst_ndv=None,
):
    # WARNING!! ('DEPRECATED!!! align_and_resize_raster_stack_ensuring_fit is deprecated. Use resample_to_match')




    """Generate rasters from a base such that they align geospatially.

    This function resizes base rasters that are in the same geospatial
    projection such that the result is an aligned stack of rasters that have
    the same cell size, dimensions, and bounding box. This is achieved by
    clipping or resizing the rasters to intersected, unioned, or equivocated
    bounding boxes of all the raster and vector input.

    Parameters:
        base_raster_path_list (list): a list of base raster paths that will
            be transformed and will be used to determine the target bounding
            box.
        target_raster_path_list (list): a list of raster paths that will be
            created to one-to-one map with `base_raster_path_list` as aligned
            versions of those original rasters.
        resample_method_list (list): a list of resampling methods which
            one to one map each path in `base_raster_path_list` during
            resizing.  Each element must be one of
            "nearest|bilinear|cubic|cubic_spline|lanczos|mode".
        target_pixel_size (tuple): the target raster's x and y pixel size
            example: [30, -30].
        bounding_box_mode (string): one of "union", "intersection", or
            a list of floats of the form [minx, miny, maxx, maxy].  Depending
            on the value, output extents are defined as the union,
            intersection, or the explicit bounding box.
        base_vector_path_list (list): a list of base vector paths whose
            bounding boxes will be used to determine the final bounding box
            of the raster stack if mode is 'union' or 'intersection'.  If mode
            is 'bb=[...]' then these vectors are not used in any calculation.
        raster_align_index (int): indicates the index of a
            raster in `base_raster_path_list` that the target rasters'
            bounding boxes pixels should align with.  This feature allows
            rasters whose raster dimensions are the same, but bounding boxes
            slightly shifted less than a pixel size to align with a desired
            grid layout.  If `None` then the bounding box of the target
            rasters is calculated as the precise intersection, union, or
            bounding box.
        gtiff_creation_options (list): list of strings that will be passed
            as GDAL "dataset" creation options to the GTIFF driver, or ignored
            if None.

    Returns:
        None
    """
    last_time = time.time()

    # make sure that the input lists are of the same length
    list_lengths = [
        len(base_raster_path_list), len(target_raster_path_list),
        len(resample_method_list)]
    if len(set(list_lengths)) != 1:
        raise ValueError(
            "base_raster_path_list, target_raster_path_list, and "
            "resample_method_list must be the same length "
            " current lengths are %s" % (str(list_lengths)))

    # we can accept 'union', 'intersection', or a 4 element list/tuple
    if bounding_box_mode not in ["union", "intersection"] and (
            not isinstance(bounding_box_mode, (list, tuple)) or
            len(bounding_box_mode) != 4):
        raise ValueError("Unknown bounding_box_mode %s" % (
            str(bounding_box_mode)))

    if ((raster_align_index is not None) and
            ((raster_align_index < 0) or
             (raster_align_index >= len(base_raster_path_list)))):
        raise ValueError(
            "Alignment index is out of bounds of the datasets index: %s"
            " n_elements %s" % (
                raster_align_index, len(base_raster_path_list)))

    raster_info_list = [
        hb.get_raster_info_hb(path) for path in base_raster_path_list]

    if base_vector_path_list is not None:
        vector_info_list = [
            hb.get_vector_info_hb(path) for path in base_vector_path_list]
    else:
        vector_info_list = []

    # get the literal or intersecting/unioned bounding box
    if isinstance(bounding_box_mode, (list, tuple)):
        target_bounding_box = bounding_box_mode
    else:
        # either intersection or union
        target_bounding_box = functools.reduce(
            functools.partial(hb.merge_bounding_boxes, mode=bounding_box_mode),
            [info['bounding_box'] for info in
             (raster_info_list + vector_info_list)])

    if bounding_box_mode == "intersection" and (
            target_bounding_box[0] > target_bounding_box[2] or
            target_bounding_box[1] > target_bounding_box[3]):
        raise ValueError("The rasters' and vectors' intersection is empty "
                         "(not all rasters and vectors touch each other).")

    if raster_align_index is not None:
        if raster_align_index >= 0:
            # bounding box needs alignment
            align_bounding_box = (
                raster_info_list[raster_align_index]['bounding_box'])
            align_pixel_size = (
                raster_info_list[raster_align_index]['pixel_size'])
            # adjust bounding box so lower left corner aligns with a pixel in
            # raster[raster_align_index]
            target_rc = [
                math.ceil((target_bounding_box[2] - target_bounding_box[0]) / target_pixel_size[0]),
                math.floor((target_bounding_box[3] - target_bounding_box[1]) / target_pixel_size[1])
            ]

            original_bounding_box = list(target_bounding_box)

            for index in [0, 1]:
                n_pixels = int((target_bounding_box[index] - align_bounding_box[index]) / float(align_pixel_size[index]))

                target_bounding_box[index] = align_bounding_box[index] + (n_pixels * align_pixel_size[index])
                target_bounding_box[index + 2] = target_bounding_box[index] + target_rc[index] * target_pixel_size[index]

            if ensure_fits:
                # This addition to the core geoprocessing code was to fix the case where the alignment moved the target tif
                # up and to the left, but in a way that then trunkated 1 row/col on the bottom right, causing wrong-shape
                # raster_math errors.z
                if original_bounding_box[2] > target_bounding_box[2]:
                    target_bounding_box[2] += target_pixel_size[0]

                if original_bounding_box[3] > target_bounding_box[3]:
                    target_bounding_box[3] -= target_pixel_size[1]


    option_list = list(gtiff_creation_options)
    if all_touched:
        option_list.append("ALL_TOUCHED=TRUE")

    for index, (base_path, target_path, resample_method) in enumerate(zip(
            base_raster_path_list, target_raster_path_list,
            resample_method_list)):
        last_time = hb.invoke_timed_callback(
            last_time, lambda: L.info(
                "align_dataset_list aligning dataset %d of %d",
                index, len(base_raster_path_list)), hb.LOGGING_PERIOD)
        option_list = []

        # WTF Second one works but not first one?

        # # # My replacement call to the older version
        # hb.warp_raster_hb(
        #     str(base_path), target_pixel_size, target_path,
        #     resample_method=resample_method, target_bb=None, base_sr_wkt=None, target_sr_wkt=None,
        #     gtiff_creation_options=DEFAULT_GTIFF_CREATION_OPTIONS,
        #     n_threads=None, vector_mask_options=None,
        #     output_data_type=output_data_type,
        #     src_ndv=src_ndv,
        #     dst_ndv=dst_ndv)
        #
        # My replacement call to the older version
        hb.warp_raster_HAZELBEAN_REPLACEMENT(
            base_path, target_pixel_size,
            target_path, resample_method,
            target_bb=target_bounding_box,
            gtiff_creation_options=option_list)

def transform_bounding_box(
        bounding_box, base_ref_wkt, new_ref_wkt, edge_samples=11):
    """Transform input bounding box to output projection.

    This transform accounts for the fact that the reprojected square bounding
    box might be warped in the new coordinate system.  To account for this,
    the function samples points along the original bounding box edges and
    attempts to make the largest bounding box around any transformed point
    on the edge whether corners or warped edges.

    Parameters:
        bounding_box (list): a list of 4 coordinates in `base_epsg` coordinate
            system describing the bound in the order [xmin, ymin, xmax, ymax]
        base_ref_wkt (string): the spatial reference of the input coordinate
            system in Well Known Text.
        new_ref_wkt (string): the EPSG code of the desired output coordinate
            system in Well Known Text.
        edge_samples (int): the number of interpolated points along each
            bounding box edge to sample along. A value of 2 will sample just
            the corners while a value of 3 will also sample the corners and
            the midpoint.

    Returns:
        A list of the form [xmin, ymin, xmax, ymax] that describes the largest
        fitting bounding box around the original warped bounding box in
        `new_epsg` coordinate system.
    """
    base_ref = osr.SpatialReference()
    base_ref.ImportFromWkt(base_ref_wkt)

    new_ref = osr.SpatialReference()
    new_ref.ImportFromWkt(new_ref_wkt)

    transformer = osr.CoordinateTransformation(base_ref, new_ref)

    def _transform_point(point):
        """Transform an (x,y) point tuple from base_ref to new_ref."""
        trans_x, trans_y, _ = (transformer.TransformPoint(*point))
        return (trans_x, trans_y)

    # The following list comprehension iterates over each edge of the bounding
    # box, divides each edge into `edge_samples` number of points, then
    # reduces that list to an appropriate `bounding_fn` given the edge.
    # For example the left edge needs to be the minimum x coordinate so
    # we generate `edge_samples` number of points between the upper left and
    # lower left point, transform them all to the new coordinate system
    # then get the minimum x coordinate "min(p[0] ...)" of the batch.
    # points are numbered from 0 starting upper right as follows:
    # 0--3
    # |  |
    # 1--2
    p_0 = numpy.array((bounding_box[0], bounding_box[3]))
    p_1 = numpy.array((bounding_box[0], bounding_box[1]))
    p_2 = numpy.array((bounding_box[2], bounding_box[1]))
    p_3 = numpy.array((bounding_box[2], bounding_box[3]))
    transformed_bounding_box = [
        bounding_fn(
            [_transform_point(
                p_a * v + p_b * (1 - v)) for v in numpy.linspace(
                0, 1, edge_samples)])
        for p_a, p_b, bounding_fn in [
            (p_0, p_1, lambda p_list: min([p[0] for p in p_list])),
            (p_1, p_2, lambda p_list: min([p[1] for p in p_list])),
            (p_2, p_3, lambda p_list: max([p[0] for p in p_list])),
            (p_3, p_0, lambda p_list: max([p[1] for p in p_list]))]]
    return transformed_bounding_box



def warp_raster_HAZELBEAN_REPLACEMENT(
        base_raster_path, target_pixel_size, target_raster_path,
        resample_method, target_bb=None, target_sr_wkt=None,
        gtiff_creation_options=hb.globals.DEFAULT_GTIFF_CREATION_OPTIONS):
    """Resize/resample raster to desired pixel size, bbox and projection.

    Parameters:
        base_raster_path (string): path to base raster.
        target_pixel_size (list): a two element list or tuple indicating the
            x and y pixel size in projected units.
        target_raster_path (string): the location of the resized and
            resampled raster.
        resample_method (string): the resampling technique, one of
            "nearest|bilinear|cubic|cubic_spline|lanczos|mode"
        target_bb (list): if None, target bounding box is the same as the
            source bounding box.  Otherwise it's a list of float describing
            target bounding box in target coordinate system as
            [minx, miny, maxx, maxy].
        target_sr_wkt (string): if not None, desired target projection in Well
            Known Text format.
        gtiff_creation_options (list or tuple): list of strings that will be
            passed as GDAL "dataset" creation options to the GTIFF driver.

    Returns:
        None
    """

    # WARNING print ('DEPRECATED!!! warp_raster_HAZELBEAN_REPLACEMENT isdeprecated. use resample_list_to_match')



    base_raster = gdal.OpenEx(base_raster_path)
    base_sr = osr.SpatialReference()
    base_sr.ImportFromWkt(base_raster.GetProjection())

    if target_bb is None:
        target_bb = hb.get_raster_info_hb(base_raster_path)['bounding_box']
        # transform the target_bb if target_sr_wkt is not None
        if target_sr_wkt is not None:
            target_bb = transform_bounding_box(
                hb.get_raster_info_hb(base_raster_path)['bounding_box'],
                hb.get_raster_info_hb(base_raster_path)['projection'],
                target_sr_wkt)

    target_geotransform = [
        target_bb[0], target_pixel_size[0], 0.0, target_bb[1], 0.0,
        target_pixel_size[1]]

    # this handles a case of a negative pixel size in which case the raster
    # row will increase downward
    if target_pixel_size[0] < 0:
        target_geotransform[0] = target_bb[2]
    if target_pixel_size[1] < 0:
        target_geotransform[3] = target_bb[3]
    target_x_size = abs((target_bb[2] - target_bb[0]) / target_pixel_size[0])
    target_y_size = abs((target_bb[3] - target_bb[1]) / target_pixel_size[1])

    if target_x_size - int(target_x_size) > 0:
        # target_x_size = int(target_x_size) + 1
        target_x_size = int(target_x_size) + 1
    else:
        target_x_size = int(target_x_size)

    if target_y_size - int(target_y_size) > 0:
        target_y_size = int(target_y_size) + 1
    else:
        target_y_size = int(target_y_size)

    if target_x_size == 0:
        L.warn(
            "bounding_box is so small that x dimension rounds to 0; "
            "clamping to 1.")
        target_x_size = 1
    if target_y_size == 0:
        L.warn(
            "bounding_box is so small that y dimension rounds to 0; "
            "clamping to 1.")
        target_y_size = 1

    local_gtiff_creation_options = list(gtiff_creation_options)
    # PIXELTYPE is sometimes used to define signed vs. unsigned bytes and
    # the only place that is stored is in the IMAGE_STRUCTURE metadata
    # copy it over if it exists; get this info from the first band since
    # all bands have the same datatype
    base_band = base_raster.GetRasterBand(1)
    metadata = base_band.GetMetadata('IMAGE_STRUCTURE')
    if 'PIXELTYPE' in metadata:
        local_gtiff_creation_options.append(
            'PIXELTYPE=' + metadata['PIXELTYPE'])

    # make directory if it doesn't exist
    try:
        os.makedirs(os.path.dirname(target_raster_path))
    except OSError:
        pass
    gdal_driver = gdal.GetDriverByName('GTiff')

    target_raster = gdal_driver.Create(
        target_raster_path, target_x_size, target_y_size,
        base_raster.RasterCount, base_band.DataType,
        options=local_gtiff_creation_options)
    base_band = None

    for index in range(target_raster.RasterCount):
        base_nodata = base_raster.GetRasterBand(1 + index).GetNoDataValue()
        if base_nodata is not None:
            target_band = target_raster.GetRasterBand(1 + index)
            target_band.SetNoDataValue(base_nodata)
            target_band = None

    # Set the geotransform
    target_raster.SetGeoTransform(target_geotransform)
    if target_sr_wkt is None:
        target_sr_wkt = base_sr.ExportToWkt()
    target_raster.SetProjection(target_sr_wkt)

    # need to make this a closure so we get the current time and we can affect
    # state
    reproject_callback = hb.make_gdal_callback(
        "ReprojectImage %.1f%% complete %s, psz_message '%s'")

    # Perform the projection/resampling

    # NOTE: DO NOT USE REPROJECTiMAGE
    gdal.ReprojectImage(
        base_raster, target_raster, base_sr.ExportToWkt(),
        target_sr_wkt, hb.RESAMPLE_DICT[resample_method], 0, 0,
        reproject_callback, [target_raster_path])

    target_raster = None
    base_raster = None
    # calculate_raster_stats(target_raster_path)



def warp_raster_hb(
        base_raster_path,
        target_pixel_size,
        target_raster_path,
        resample_method='bilinear',
        target_bb=None,
        base_sr_wkt=None,
        target_sr_wkt=None,
        gtiff_creation_options=hb.globals.DEFAULT_GTIFF_CREATION_OPTIONS,
        n_threads=None,
        vector_mask_options=None,
        output_data_type=None,
        src_ndv=None,
        dst_ndv=None,
        calc_raster_stats=False,
        add_overviews=False,
        specific_overviews_to_add=None,
        target_aligned_pixels=True
):
    """Resize/resample raster to desired pixel size, bbox and projection.

    Parameters:
        base_raster_path (string): path to base raster.
        target_pixel_size (list): a two element list or tuple indicating the
            x and y pixel size in projected units.
        target_raster_path (string): the location of the resized and
            resampled raster.
        resample_method (string): the resampling technique, one of
            "near|bilinear|cubic|cubicspline|lanczos|average|mode|max"
            "min|med|q1|q3"
        target_bb (list): if None, target bounding box is the same as the
            source bounding box.  Otherwise it's a list of float describing
            target bounding box in target coordinate system as
            [minx, miny, maxx, maxy].
        base_sr_wkt (string): if not None, interpret the projection of
            `base_raster_path` as this.
        target_sr_wkt (string): if not None, desired target projection in Well
            Known Text format.
        gtiff_creation_options (list or tuple): list of strings that will be
            passed as GDAL "dataset" creation options to the GTIFF driver.
        n_threads (int): optional, if not None this sets the `N_THREADS`
            option for `gdal.Warp`.
        vector_mask_options (dict): optional, if not None, this is a
            dictionary of options to use an existing vector's geometry to
            mask out pixels in the target raster that do not overlap the
            vector's geometry. Keys to this dictionary are:
                'mask_vector_path': (str) path to the mask vector file. This
                    vector will be automatically projected to the target
                    projection if its base coordinate system does not match
                    the target.
                'mask_layer_name': (str) the layer name to use for masking,
                    if this key is not in the dictionary the default is to use
                    the layer at index 0.
                'mask_vector_where_filter': (str) an SQL WHERE string that can
                    be used to filter the geometry in the mask. Ex:
                    'id > 10' would use all features whose field value of
                    'id' is > 10.

    Returns:
        None

    """

    # EXTENSION allow either tuple or float specification of resolution
    if isinstance(target_pixel_size, (float, int)):
        target_pixel_size = (target_pixel_size, -target_pixel_size)

    base_raster_info = hb.get_raster_info_hb(base_raster_path)
    if target_sr_wkt is None:
        target_sr_wkt = base_raster_info['projection']

    if target_bb is None:
        working_bb = base_raster_info['bounding_box']
        # transform the working_bb if target_sr_wkt is not None
        if target_sr_wkt is not None:
            L.debug(
                "transforming bounding box from %s ", working_bb)

            working_bb = transform_bounding_box(
                base_raster_info['bounding_box'],
                base_raster_info['projection'], target_sr_wkt)

            L.debug(
                "transforming bounding to %s ", working_bb)
    else:
        working_bb = target_bb[:]

    if output_data_type is None:
        output_data_type = base_raster_info['datatype']

    if src_ndv is None:
        src_ndv = base_raster_info['nodata']

    if dst_ndv is None:
        dst_ndv = base_raster_info['datatype']
        if dst_ndv is None:
            if output_data_type < 5:
                dst_ndv = 255
            else:
                dst_ndv = -9999.0

    # determine the raster size that bounds the input bounding box and then
    # adjust the bounding box to be that size
    target_x_size = int(abs(
        float(working_bb[2] - working_bb[0]) / target_pixel_size[0]))
    target_y_size = int(abs(
        float(working_bb[3] - working_bb[1]) / target_pixel_size[1]))

    # sometimes bounding boxes are numerically perfect, this checks for that
    x_residual = (
            abs(target_x_size * target_pixel_size[0]) -
            (working_bb[2] - working_bb[0]))
    if not numpy.isclose(x_residual, 0.0):
        target_x_size += 1
    y_residual = (
            abs(target_y_size * target_pixel_size[1]) -
            (working_bb[3] - working_bb[1]))
    if not numpy.isclose(y_residual, 0.0):
        target_y_size += 1

    if target_x_size == 0:
        L.warning(
            "bounding_box is so small that x dimension rounds to 0; "
            "clamping to 1.")
        target_x_size = 1
    if target_y_size == 0:
        L.warning(
            "bounding_box is so small that y dimension rounds to 0; "
            "clamping to 1.")
        target_y_size = 1

    # this ensures the bounding boxes perfectly fit a multiple of the target
    # pixel size. EXTENSION: includes using Decimal object to ensure no funny floating point imprecision.
    # Note the input of str object to Decimal. Otherwise we would get a very long precision float that is not exactly the intention.
    working_bb[2] = float(Decimal(str(working_bb[0])) + abs(Decimal(str(target_pixel_size[0])) * Decimal(str(target_x_size))))
    working_bb[3] = float(Decimal(str(working_bb[1])) + abs(Decimal(str(target_pixel_size[1])) * Decimal(str(target_y_size))))


    reproject_callback = hb.make_gdal_callback("Warp %.1f%% complete %s for %s")

    warp_options = []
    if n_threads:
        warp_options.append('NUM_THREADS=%d' % n_threads)
        
    warp_options.append('targetAlignedPik')
    # warp_options = None # Changed to see if fix gdal warp options error

    mask_vector_path = None
    mask_layer_name = None
    mask_vector_where_filter = None
    if vector_mask_options or mask_vector_path:
        # translate pygeoprocessing terminology into GDAL warp options.
        if 'mask_vector_path' not in vector_mask_options:
            raise ValueError(
                'vector_mask_options passed, but no value for '
                '"mask_vector_path": %s', vector_mask_options)
        mask_vector_path = vector_mask_options['mask_vector_path']
        if not os.path.exists(mask_vector_path):
            raise ValueError(
                'The mask vector at %s was not found.', mask_vector_path)
        if 'mask_layer_name' in vector_mask_options:
            mask_layer_name = vector_mask_options['mask_layer_name']
        if 'mask_vector_where_filter' in vector_mask_options:
            mask_vector_where_filter = (
                vector_mask_options['mask_vector_where_filter'])

    base_raster = gdal.OpenEx(base_raster_path, gdal.OF_RASTER)

    gdal.Warp(
        target_raster_path, base_raster,
        outputBounds=working_bb,
        xRes=abs(target_pixel_size[0]),
        yRes=abs(target_pixel_size[1]),
        resampleAlg=resample_method,
        outputBoundsSRS=target_sr_wkt,
        srcSRS=base_sr_wkt,
        dstSRS=target_sr_wkt,
        multithread=True if warp_options else False,
        warpOptions=warp_options,
        creationOptions=gtiff_creation_options,
        callback=reproject_callback,
        callback_data=[target_raster_path],
        cutlineDSName=mask_vector_path,
        cutlineLayer=mask_layer_name,
        cutlineWhere=mask_vector_where_filter,
        outputType=output_data_type,
        srcNodata=src_ndv,
        dstNodata=dst_ndv,
        targetAlignedPixels=target_aligned_pixels,
    )
    # TODOO decided not to implement parallel calculation of unique values list when making pyramids, but might be a nice optional addon.
    if calc_raster_stats:
        # TODO, see below, but the value of the non hb version is that it calculates simultaneously. however i hit an error on it once i couldn't fix
        hb.calculate_raster_stats(target_raster_path)
        # hb.calculate_raster_stats_hb(target_raster_path)

    if specific_overviews_to_add is not None:
        hb.add_overviews_to_path(target_raster_path, specific_overviews_to_add=specific_overviews_to_add)
    elif add_overviews:
        hb.add_overviews_to_path(target_raster_path)


def calculate_raster_stats_hb(raster_path):
    # WARNING not sure if memory safe.
    ds = gdal.OpenEx(raster_path)
    ds.GetRasterBand(1).ComputeStatistics(False)  # False here means approx NOT okay
    ds.GetRasterBand(1).GetHistogram(approx_ok=0)

    # TODO Ensure this is memory safe and determine how is different from regular calc below.



def read_raster_stats(raster_path):
    ds = gdal.OpenEx(raster_path)
    gdal_json_info = gdal.Info(ds, options=['-json'])
    gdal_info_dict = gdal_json_info
    # gdal_info_dict = json.loads(str(gdal_json_info))

    # NOTE, currently only works for single band opperations
    if len(gdal_info_dict['bands']) == 1:
        band_info = gdal_info_dict['bands'][0]
    else:
        raise NameError('currently only works for single band opperations')
    return band_info

    # gdal.GDAL_GCP_Info_get()
    # ds.GetRasterBand(1).ComputeStatistics(False)  # False here means approx NOT okay
    # ds.GetRasterBand(1).GetHistogram(approx_ok=0)

    # TODO Ensure this is memory safe and determine how is different from regular calc below.

def calculate_raster_stats(raster_path, return_unique_values_list=False):
    """Calculate and set min, max, stdev, and mean for all bands in raster.
    optionally return also a list of unique values
    Parameters:
        raster_path (string): a path to a GDAL raster raster that will be
            modified by having its band statistics set

    Returns:
        None
    """
    raster = gdal.OpenEx(raster_path, gdal.GA_Update)
    raster_properties = hb.get_raster_info_hb(raster_path)
    for band_index in range(raster.RasterCount):
        target_min = None
        target_max = None
        target_n = 0
        target_sum = 0.0
        for _, target_block in hb.iterblocks(
                (raster_path, 1)):
            nodata_target = raster_properties['nodata'][band_index]
            # guard against an undefined nodata target
            valid_mask = numpy.ones(target_block.shape, dtype=bool)
            if nodata_target is not None:
                valid_mask[:] = target_block != nodata_target
            valid_block = target_block[valid_mask]
            if valid_block.size == 0:
                continue
            if target_min is None:
                # initialize first min/max
                target_min = target_max = valid_block[0]
            target_sum += numpy.sum(valid_block)
            target_min = min(numpy.min(valid_block), target_min)
            target_max = max(numpy.max(valid_block), target_max)
            target_n += valid_block.size

        if target_min is not None:
            target_mean = target_sum / float(target_n)
            stdev_sum = 0.0
            for _, target_block in hb.iterblocks(
                    (raster_path, 1)):
                # guard against an undefined nodata target
                valid_mask = numpy.ones(target_block.shape, dtype=bool)
                if nodata_target is not None:
                    valid_mask = target_block != nodata_target
                valid_block = target_block[valid_mask]
                stdev_sum += numpy.sum((valid_block - target_mean) ** 2)
            target_stddev = (stdev_sum / float(target_n)) ** 0.5

            target_band = raster.GetRasterBand(band_index + 1)
            target_band.SetStatistics(
                float(target_min), float(target_max), float(target_mean),
                float(target_stddev))
            target_band = None
        else:
            L.warn(
                "Stats not calculated for %s band %d since no non-nodata "
                "pixels were found.", raster_path, band_index + 1)
    raster = None


def iterblocks_hb(
        raster_path_band, largest_block=hb.globals.LARGEST_ITERBLOCK,
        offset_only=False):
    """Iterate across all the memory blocks in the input raster.

    Result is a generator of block location information and numpy arrays.

    This is especially useful when a single value needs to be derived from the
    pixel values in a raster, such as the sum total of all pixel values, or
    a sequence of unique raster values.  In such cases, ``raster_local_op``
    is overkill, since it writes out a raster.

    As a generator, this can be combined multiple times with itertools.izip()
    to iterate 'simultaneously' over multiple rasters, though the user should
    be careful to do so only with prealigned rasters.

    Args:
        raster_path_band (tuple): a path/band index tuple to indicate
            which raster band iterblocks should iterate over.
        largest_block (int): Attempts to iterate over raster blocks with
            this many elements.  Useful in cases where the blocksize is
            relatively small, memory is available, and the function call
            overhead dominates the iteration.  Defaults to 2**20.  A value of
            anything less than the original blocksize of the raster will
            result in blocksizes equal to the original size.
        offset_only (boolean): defaults to False, if True ``iterblocks`` only
            returns offset dictionary and doesn't read any binary data from
            the raster.  This can be useful when iterating over writing to
            an output.

    Yields:
        If ``offset_only`` is false, on each iteration, a tuple containing a
        dict of block data and a 2-dimensional numpy array are
        yielded. The dict of block data has these attributes:

        * ``data['xoff']`` - The X offset of the upper-left-hand corner of the
          block.
        * ``data['yoff']`` - The Y offset of the upper-left-hand corner of the
          block.
        * ``data['win_xsize']`` - The width of the block.
        * ``data['win_ysize']`` - The height of the block.

        If ``offset_only`` is True, the function returns only the block offset
        data and does not attempt to read binary data from the raster.

    """
    if not _is_raster_path_band_formatted(raster_path_band):
        raise ValueError(
            "`raster_path_band` not formatted as expected.  Expects "
            "(path, band_index), received %s" % repr(raster_path_band))
    raster = gdal.OpenEx(raster_path_band[0], gdal.OF_RASTER)
    if raster is None:
        raise ValueError(
            "Raster at %s could not be opened." % raster_path_band[0])
    band = raster.GetRasterBand(raster_path_band[1])
    block = band.GetBlockSize()
    cols_per_block = block[0]
    rows_per_block = block[1]

    n_cols = raster.RasterXSize
    n_rows = raster.RasterYSize

    block_area = cols_per_block * rows_per_block
    
    # HACK I decided to overwrite this logic because it was making funny blocksizes, but this may be necessary for non pyramidal rasters.hb    
    # try to make block wider                                                                                                                                                           
    if int(largest_block / block_area) > 0:
        width_factor = int(largest_block / block_area)
        cols_per_block *= width_factor
        if cols_per_block > n_cols:
            cols_per_block = n_cols
        block_area = cols_per_block * rows_per_block
    # try to make block taller
    if int(largest_block / block_area) > 0:
        height_factor = int(largest_block / block_area)
        rows_per_block *= height_factor
        if rows_per_block > n_rows:
            rows_per_block = n_rows

    n_col_blocks = int(math.ceil(n_cols / float(cols_per_block)))
    n_row_blocks = int(math.ceil(n_rows / float(rows_per_block)))

    for row_block_index in range(n_row_blocks):
        row_offset = row_block_index * rows_per_block
        row_block_width = n_rows - row_offset
        if row_block_width > rows_per_block:
            row_block_width = rows_per_block
        for col_block_index in range(n_col_blocks):
            col_offset = col_block_index * cols_per_block
            col_block_width = n_cols - col_offset
            if col_block_width > cols_per_block:
                col_block_width = cols_per_block

            offset_dict = {
                'xoff': col_offset,
                'yoff': row_offset,
                'win_xsize': col_block_width,
                'win_ysize': row_block_width,
            }
            if offset_only:
                yield offset_dict
            else:
                yield (offset_dict, band.ReadAsArray(**offset_dict))

    band = None
    raster = None

def raster_calculator_hb(
        base_raster_path_band_const_list, local_op, target_raster_path,
        datatype_target, nodata_target, read_datatype=None,
        gtiff_creation_options=hb.globals.DEFAULT_GTIFF_CREATION_OPTIONS,
        calc_raster_stats=False, invoke_full_callback=True,
        largest_block=hb.globals.LARGEST_ITERBLOCK):
    """Apply local a raster operation on a stack of rasters.

    This function applies a user defined function across a stack of
    rasters' pixel stack. The rasters in `base_raster_path_band_list` must be
    spatially aligned and have the same cell sizes.

    Parameters:
        base_raster_path_band_const_list (list): a list containing either
            (str, int) tuples, `numpy.ndarray`s of up to two
            dimensions, or an (object, 'raw') tuple.  A `(str, int)`
            tuple refers to a raster path band index pair to use as an input.
            The `numpy.ndarray`s must be broadcastable to each other AND the
            size of the raster inputs. Values passed by  `(object, 'raw')`
            tuples pass `object` directly into the `local_op`. All rasters
            must have the same raster size. If only arrays are input, numpy
            arrays must be broadcastable to each other and the final raster
            size will be the final broadcast array shape. A value error is
            raised if only "raw" inputs are passed.
        local_op (function) a function that must take in as many parameters as
            there are elements in `base_raster_path_band_const_list`. The
            parameters in `local_op` will map 1-to-1 in order with the values
            in `base_raster_path_band_const_list`. `raster_calculator` will
            call `local_op` to generate the pixel values in `target_raster`
            along memory block aligned processing windows. Note any
            particular call to `local_op` will have the arguments from
            `raster_path_band_const_list` sliced to overlap that window.
            If an argument from `raster_path_band_const_list` is a raster/path
            band tuple, it will be passed to `local_op` as a 2D numpy array of
            pixel values that align with the processing window that `local_op`
            is targeting. A 2D or 1D array will be sliced to match
            the processing window and in the case of a 1D array tiled in
            whatever dimension is flat. If an argument is a scalar it is
            passed as as scalar.
            The return value must be a 2D array of the same size as any of the
            input parameter 2D arrays and contain the desired pixel values
            for the target raster.
        target_raster_path (string): the path of the output raster.  The
            projection, size, and cell size will be the same as the rasters
            in `base_raster_path_const_band_list` or the final broadcast size
            of the constant/ndarray values in the list.
        datatype_target (gdal datatype; int): the desired GDAL output type of
            the target raster.
        nodata_target (numerical value): the desired nodata value of the
            target raster.
        gtiff_creation_options (list): this is an argument list that will be
            passed to the GTiff driver.  Useful for blocksizes, compression,
            and more.
        calc_raster_stats (boolean): If True, calculates and sets raster
            statistics (min, max, mean, and stdev) for target raster.
        largest_block (int): Attempts to internally iterate over raster blocks
            with this many elements.  Useful in cases where the blocksize is
            relatively small, memory is available, and the function call
            overhead dominates the iteration.  Defaults to 2**20.  A value of
            anything less than the original blocksize of the raster will
            result in blocksizes equal to the original size.

    Returns:
        None

    Raises:
        ValueError: invalid input provided

    """
    if not base_raster_path_band_const_list:
        raise ValueError(
            "`base_raster_path_band_const_list` is empty and "
            "should have at least one value.")

    # It's a common error to not pass in path/band tuples, so check for that
    # and report error if so
    bad_raster_path_list = False
    if not isinstance(base_raster_path_band_const_list, (list, tuple, dict, OrderedDict)):
        bad_raster_path_list = True
    else:
        for value in base_raster_path_band_const_list:
            if (not _is_raster_path_band_formatted(value) and
                    not isinstance(value, numpy.ndarray) and
                    not (isinstance(value, tuple) and len(value) == 2 and
                         value[1] == 'raw')):
                bad_raster_path_list = True
                break
    if bad_raster_path_list:
        raise ValueError(
            "Expected a list of path / integer band tuples, "
            "ndarrays, or (value, 'raw') pairs for "
            "`base_raster_path_band_const_list`, instead got: " +  str(base_raster_path_band_const_list))

    # check that any rasters exist on disk and have enough bands
    not_found_paths = []
    gdal.PushErrorHandler('CPLQuietErrorHandler')
    base_raster_path_band_list = [
        path_band for path_band in base_raster_path_band_const_list
        if _is_raster_path_band_formatted(path_band)]
    for value in base_raster_path_band_list:
        if gdal.OpenEx(value[0], gdal.OF_RASTER) is None:
            not_found_paths.append(value[0])
    gdal.PopErrorHandler()
    if not_found_paths:
        raise ValueError(
            "The following files were expected but do not exist on the "
            "filesystem: " + str(not_found_paths))

    # check that band index exists in raster
    invalid_band_index_list = []
    for value in base_raster_path_band_list:
        raster = gdal.OpenEx(value[0], gdal.OF_RASTER)
        if not (1 <= value[1] <= raster.RasterCount):
            invalid_band_index_list.append(value)
        raster = None
    if invalid_band_index_list:
        raise ValueError(
            "The following rasters do not contain requested band "
            "indexes: %s" % invalid_band_index_list)

    # check that the target raster is not also an input raster
    if target_raster_path in [x[0] for x in base_raster_path_band_list]:
        raise ValueError(
            "%s is used as a target path, but it is also in the base input "
            "path list %s" % (
                target_raster_path, str(base_raster_path_band_const_list)))

    # check that raster inputs are all the same dimensions
    raster_info_list = [
        hb.get_raster_info_hb(path_band[0])
        for path_band in base_raster_path_band_const_list
        if _is_raster_path_band_formatted(path_band)]
    geospatial_info_set = set()
    for raster_info in raster_info_list:
        geospatial_info_set.add(raster_info['raster_size'])

    if len(geospatial_info_set) > 1:
        raise ValueError(
            "Input Rasters are not the same dimensions. The "
            "following raster are not identical %s" % str(
                geospatial_info_set))

    numpy_broadcast_list = [
        x for x in base_raster_path_band_const_list
        if isinstance(x, numpy.ndarray)]
    stats_worker_thread = None
    try:
        # numpy.broadcast can only take up to 32 arguments, this loop works
        # around that restriction:
        while len(numpy_broadcast_list) > 1:
            numpy_broadcast_list = (
                    [numpy.broadcast(*numpy_broadcast_list[:32])] +
                    numpy_broadcast_list[32:])
        if numpy_broadcast_list:
            numpy_broadcast_size = numpy_broadcast_list[0].shape
    except ValueError:
        # this gets raised if numpy.broadcast fails
        raise ValueError(
            "Numpy array inputs cannot be broadcast into a single shape %s" %
            numpy_broadcast_list)

    if numpy_broadcast_list and len(numpy_broadcast_list[0].shape) > 2:
        raise ValueError(
            "Numpy array inputs must be 2 dimensions or less %s" %
            numpy_broadcast_list)

    # if there are both rasters and arrays, check the numpy shape will
    # be broadcastable with raster shape
    if raster_info_list and numpy_broadcast_list:
        # geospatial lists x/y order and numpy does y/x so reverse size list
        raster_shape = tuple(reversed(raster_info_list[0]['raster_size']))
        invalid_broadcast_size = False
        if len(numpy_broadcast_size) == 1:
            # if there's only one dimension it should match the last
            # dimension first, in the raster case this is the columns
            # because of the row/column order of numpy. No problem if
            # that value is `1` because it will be broadcast, otherwise
            # it should be the same as the raster.
            if (numpy_broadcast_size[0] != raster_shape[1] and
                    numpy_broadcast_size[0] != 1):
                invalid_broadcast_size = True
        else:
            for dim_index in range(2):
                # no problem if 1 because it'll broadcast, otherwise must
                # be the same value
                if (numpy_broadcast_size[dim_index] !=
                        raster_shape[dim_index] and
                        numpy_broadcast_size[dim_index] != 1):
                    invalid_broadcast_size = True
        if invalid_broadcast_size:
            raise ValueError(
                "Raster size %s cannot be broadcast to numpy shape %s" % (
                    raster_shape, numpy_broadcast_size))

    # create a "canonical" argument list that's bands, 2d numpy arrays, or
    # raw values only
    base_canonical_arg_list = []
    base_raster_list = []
    base_band_list = []
    for value in base_raster_path_band_const_list:
        # the input has been tested and value is either a raster/path band
        # tuple, 1d ndarray, 2d ndarray, or (value, 'raw') tuple.
        if _is_raster_path_band_formatted(value):
            # it's a raster/path band, keep track of open raster and band
            # for later so we can __swig_destroy__ them.
            base_raster_list.append(gdal.OpenEx(value[0], gdal.OF_RASTER))
            base_band_list.append(
                base_raster_list[-1].GetRasterBand(value[1]))
            base_canonical_arg_list.append(base_band_list[-1])
        elif isinstance(value, numpy.ndarray):
            if value.ndim == 1:
                # easier to process as a 2d array for writing to band
                base_canonical_arg_list.append(
                    value.reshape((1, value.shape[0])))
            else:  # dimensions are two because we checked earlier.
                base_canonical_arg_list.append(value)
        elif isinstance(value, tuple):
            base_canonical_arg_list.append(value)
        else:
            raise ValueError(
                "An unexpected `value` occurred. This should never happen. "
                "Value: %r" % value)

    # create target raster
    if raster_info_list:
        # if rasters are passed, the target is the same size as the raster
        n_cols, n_rows = raster_info_list[0]['raster_size']
    elif numpy_broadcast_list:
        # numpy arrays in args and no raster result is broadcast shape
        # expanded to two dimensions if necessary
        if len(numpy_broadcast_size) == 1:
            n_rows, n_cols = 1, numpy_broadcast_size[0]
        else:
            n_rows, n_cols = numpy_broadcast_size
    else:
        raise ValueError(
            "Only (object, 'raw') values have been passed. Raster "
            "calculator requires at least a raster or numpy array as a "
            "parameter. This is the input list: " + str(
                base_raster_path_band_const_list))

    # create target raster
    gtiff_driver = gdal.GetDriverByName('GTiff')
    try:
        os.makedirs(os.path.dirname(target_raster_path))
    except OSError:
        pass
    target_raster = gtiff_driver.Create(
        target_raster_path, n_cols, n_rows, 1, hb.gdal_number_to_gdal_type[datatype_target],
        options=gtiff_creation_options)
    target_band = target_raster.GetRasterBand(1)
    if nodata_target is not None:
        target_band.SetNoDataValue(nodata_target)
    if base_raster_list:
        # use the first raster in the list for the projection and geotransform
        target_raster.SetProjection(base_raster_list[0].GetProjection())
        target_raster.SetGeoTransform(base_raster_list[0].GetGeoTransform())
    target_band.FlushCache()
    target_raster.FlushCache()

    try:
        last_time = time.time()

        if calc_raster_stats:
            # if this queue is used to send computed valid blocks of
            # the raster to an incremental statistics calculator worker

            stats_worker_queue = queue.Queue()
            exception_queue = queue.Queue()
        else:
            stats_worker_queue = None
            exception_queue = None

        if calc_raster_stats:
            # To avoid doing two passes on the raster to calculate standard
            # deviation, we implement a continuous statistics calculation
            # as the raster is computed. This computational effort is high
            # and benefits from running in parallel. This queue and worker
            # takes a valid block of a raster and incrementally calculates
            # the raster's statistics. When `None` is pushed to the queue
            # the worker will finish and return a (min, max, mean, std)
            # tuple.
            target = 'fix'
            L.info('starting stats_worker')
            stats_worker_thread = threading.Thread(
                target=target,
                args=(stats_worker_queue, exception_queue))
            stats_worker_thread.daemon = True
            stats_worker_thread.start()
            L.info('started stats_worker %s', stats_worker_thread)

        pixels_processed = 0
        n_pixels = n_cols * n_rows

        # iterate over each block and calculate local_op
        for block_offset in iterblocks_hb(
                (target_raster_path, 1), offset_only=True,
                largest_block=largest_block):
        ### Decide if I am consistent on raster vs path-band
        # for block_offset in iterblocks(
        #         (target_raster_path, 1), offset_only=True,
        #         largest_block=largest_block):
            # read input blocks
            offset_list = (block_offset['yoff'], block_offset['xoff'])
            blocksize = (block_offset['win_ysize'], block_offset['win_xsize'])
            data_blocks = []


            for value in base_canonical_arg_list:
                if isinstance(value, gdal.Band):
                    # HB Modificaiton: allow type reinterpretation at read
                    if read_datatype:
                        data_blocks.append(value.ReadAsArray(**block_offset, buf_type=read_datatype))
                    elif datatype_target:
                        data_blocks.append(value.ReadAsArray(**block_offset, buf_type=datatype_target))
                    else:
                        data_blocks.append(value.ReadAsArray(**block_offset))
                    # I've encountered the following error when a gdal raster
                    # is corrupt, often from multiple threads writing to the
                    # same file. This helps to catch the error early rather
                    # than lead to confusing values of `data_blocks` later.
                    if not isinstance(data_blocks[-1], numpy.ndarray):
                        raise ValueError(
                            "got a %s when trying to read %s at %s",
                            data_blocks[-1], value.GetDataset().GetFileList(),
                            block_offset)
                elif isinstance(value, numpy.ndarray):
                    # must be numpy array and all have been conditioned to be
                    # 2d, so start with 0:1 slices and expand if possible
                    slice_list = [slice(0, 1)] * 2
                    tile_dims = list(blocksize)
                    for dim_index in [0, 1]:
                        if value.shape[dim_index] > 1:
                            slice_list[dim_index] = slice(
                                offset_list[dim_index],
                                offset_list[dim_index] +
                                blocksize[dim_index], )
                            tile_dims[dim_index] = 1
                    data_blocks.append(
                        numpy.tile(value[slice_list], tile_dims))
                # HB EXTENSION, support input as a dict of replacement values for reclassification
                elif type(value) in [dict, OrderedDict]:
                    data_blocks.append(value)
                else:
                    # must be a raw tuple
                    data_blocks.append(value[0])

            # HB EXTENSION, now supports memoryviews, which are faster in cython.

            target_block = np.asarray(local_op(*data_blocks))
            # target_block = local_op(*data_blocks)

            if (not isinstance(target_block, numpy.ndarray) or
                    target_block.shape != blocksize):
                raise ValueError(
                    "Expected `local_op` to return a numpy.ndarray of "
                    "shape %s but got this instead: %s" % (
                        blocksize, target_block))

            # send result to stats calculator
            if stats_worker_queue:
                # guard against an undefined nodata target
                if nodata_target is not None:
                    valid_block = target_block[target_block != nodata_target]
                    if valid_block.size > 0:
                        stats_worker_queue.put(valid_block)
                else:
                    stats_worker_queue.put(target_block.flatten())

            target_band.WriteArray(
                target_block, yoff=block_offset['yoff'],
                xoff=block_offset['xoff'])

            pixels_processed += blocksize[0] * blocksize[1]
            if invoke_full_callback:
                last_time = _invoke_timed_callback(
                    last_time, lambda: L.info(
                        'Raster calculator progress: ' + str(float(pixels_processed) / n_pixels * 100.0) + ' on ' + str(base_raster_path_band_const_list)),
                    hb.LOGGING_PERIOD)
            else:
                last_time = _invoke_timed_callback(
                    last_time, lambda: L.info(
                        'Raster calculator progress: ' + str(float(pixels_processed) / n_pixels * 100.0)), hb.LOGGING_PERIOD)
        L.debug('raster_calculator_hb finished on ' + str(target_raster_path))

        if calc_raster_stats:
            L.info("signaling stats worker to terminate")
            stats_worker_queue.put(None)
            L.info("Waiting for raster stats worker result.")
            stats_worker_thread.join(hb.MAX_TIMEOUT)
            if stats_worker_thread.is_alive():
                raise RuntimeError("stats_worker_thread.join() timed out")
            payload = stats_worker_queue.get(True, hb.MAX_TIMEOUT)
            if payload is not None:
                target_min, target_max, target_mean, target_stddev = payload
                target_band.SetStatistics(
                    float(target_min), float(target_max), float(target_mean),
                    float(target_stddev))
                target_band.FlushCache()
    finally:
        # This block ensures that rasters are destroyed even if there's an
        # exception raised.
        base_band_list[:] = []
        for raster in base_raster_list:
            gdal.Dataset.__swig_destroy__(raster)
        base_raster_list[:] = []
        target_band.FlushCache()
        target_band = None
        target_raster.FlushCache()
        gdal.Dataset.__swig_destroy__(target_raster)
        target_raster = None

        if calc_raster_stats and stats_worker_thread:
            if stats_worker_thread.is_alive():
                stats_worker_queue.put(None, True, hb.MAX_TIMEOUT)
                L.info("Waiting for raster stats worker result.")
                stats_worker_thread.join(hb.MAX_TIMEOUT)
                if stats_worker_thread.is_alive():
                    raise RuntimeError("stats_worker_thread.join() timed out")

            # check for an exception in the workers, otherwise get result
            # and pass to writer
            try:
                exception = exception_queue.get_nowait()
                L.error("Exception encountered at termination.")
                raise exception
            except queue.Empty:
                pass

# INTERNAL FUNCTIONS
# UNLESS OTHERWISE NOTED, all internal functions are copied without modification from pygeoprocessing here so they can be called as internal funcs.

def _invoke_timed_callback(
        reference_time, callback_lambda, callback_period):
    """Invoke callback if a certain amount of time has passed.

    This is a convenience function to standardize update callbacks from the
    module.

    Parameters:
        reference_time (float): time to base `callback_period` length from.
        callback_lambda (lambda): function to invoke if difference between
            current time and `reference_time` has exceeded `callback_period`.
        callback_period (float): time in seconds to pass until
            `callback_lambda` is invoked.

    Returns:
        `reference_time` if `callback_lambda` not invoked, otherwise the time
        when `callback_lambda` was invoked.

    """
    current_time = time.time()
    if current_time - reference_time > callback_period:
        callback_lambda()
        return current_time
    return reference_time


def _is_raster_path_band_formatted(raster_path_band):
    """Return true if raster path band is a (str, int) tuple/list."""
    if not isinstance(raster_path_band, (list, tuple)):
        return False
    elif len(raster_path_band) != 2:
        return False
    elif not isinstance(raster_path_band[0], str):
        return False
    elif not isinstance(raster_path_band[1], int):
        return False

    else:
        return True


# def make_gdal_callback(message):
#     """Build a timed logger callback that prints `message` replaced.

#     Parameters:
#         message (string): a string that expects 3 placement %% variables,
#             first for % complete from `df_complete`, second `psz_message`
#             and last is `p_progress_arg[0]`.

#     Returns:
#         Function with signature:
#             logger_callback(df_complete, psz_message, p_progress_arg)
#     """

#     def logger_callback(df_complete, psz_message, p_progress_arg):
#         """The argument names come from the GDAL API for callbacks."""
#         try:
#             current_time = time.time()
#             if ((current_time - logger_callback.last_time) > 5.0 or
#                     (df_complete == 1.0 and
#                      logger_callback.total_time >= 5.0)):
#                 L.info(
#                     message, df_complete * 100, psz_message, p_progress_arg[0])
#                 logger_callback.last_time = current_time
#                 logger_callback.total_time += current_time
#         except AttributeError:
#             logger_callback.last_time = time.time()
#             logger_callback.total_time = 0.0

#     return logger_callback

# DUPLICATED Above to make non-internal
def invoke_timed_callback(
        reference_time, callback_lambda, callback_period):
    """Invoke callback if a certain amount of time has passed.

    This is a convenience function to standardize update callbacks from the
    module.

    Parameters:
        reference_time (float): time to base `callback_period` length from.
        callback_lambda (lambda): function to invoke if difference between
            current time and `reference_time` has exceeded `callback_period`.
        callback_period (float): time in seconds to pass until
            `callback_lambda` is invoked.

    Returns:
        `reference_time` if `callback_lambda` not invoked, otherwise the time
        when `callback_lambda` was invoked.

    """
    current_time = time.time()
    if current_time - reference_time > callback_period:
        callback_lambda()
        return current_time
    return reference_time


def is_raster_path_band_formatted(raster_path_band):
    """Return true if raster path band is a (str, int) tuple/list."""
    if not isinstance(raster_path_band, (list, tuple)):
        return False
    elif len(raster_path_band) != 2:
        return False
    elif not isinstance(raster_path_band[0], str):
        return False
    elif not isinstance(raster_path_band[1], int):
        return False

    else:
        return True


def make_logger_callback(message):
    """Build a timed logger callback that prints `message` replaced.

    Parameters:
        message (string): a string that expects 3 placement %% variables,
            first for % complete from `df_complete`, second `psz_message`
            and last is `p_progress_arg[0]`.

    Returns:
        Function with signature:
            logger_callback(df_complete, psz_message, p_progress_arg)
    """

    def logger_callback(df_complete, psz_message, p_progress_arg):
        """The argument names come from the GDAL API for callbacks."""
        try:
            current_time = time.time()
            if ((current_time - logger_callback.last_time) > 3.0 or
                    (df_complete == 1.0 and
                     logger_callback.total_time >= 5.0)):
                # L.info(message + ' ' + str(df_complete * 100) + 'percent complete on ' + str(p_progress_arg[0]), str(psz_message), str(p_progress_arg))
                L.info(message + ' ' + str(df_complete * 100) + 'percent complete on ' + str(p_progress_arg[0]))
                # L.info(message, df_complete * 100, psz_message, p_progress_arg[0])
                logger_callback.last_time = current_time
                logger_callback.total_time += current_time
        except AttributeError:
            logger_callback.last_time = time.time()
            logger_callback.total_time = 0.0

    return logger_callback

def make_blank_gdal_callback():
    # MOVE OUT OF EXTENSION
    """Build a timed logger callback that prints `message` replaced.

    Parameters:
        message (string): a string that expects 3 placement %% variables,
            first for % complete from `df_complete`, second `psz_message`
            and last is `p_progress_arg[0]`.

    Returns:
        Function with signature:
            logger_callback(df_complete, psz_message, p_progress_arg)
    """

    def logger_callback(df_complete, psz_message, p_progress_arg):
        """The argument names come from the GDAL API for callbacks."""
        try:
            current_time = time.time()
            if ((current_time - logger_callback.last_time) > 5.0 or
                    (df_complete == 1.0 and
                     logger_callback.total_time >= 5.0)):
                L.info('GDAL running: ' + str(df_complete))
                logger_callback.last_time = current_time
                logger_callback.total_time += current_time
        except AttributeError:
            logger_callback.last_time = time.time()
            logger_callback.total_time = 0.0

    return logger_callback


def make_simple_gdal_callback(message):
    # MOVE OUT OF EXTENSION
    """Build a timed logger callback that prints `message` replaced.

    Parameters:
        message (string): a string that expects 3 placement %% variables,
            first for % complete from `df_complete`, second `psz_message`
            and last is `p_progress_arg[0]`.

    Returns:
        Function with signature:
            logger_callback(df_complete, psz_message, p_progress_arg)
    """

    def logger_callback(df_complete, psz_message, p_progress_arg):
        """The argument names come from the GDAL API for callbacks."""
        try:
            current_time = time.time()
            if ((current_time - logger_callback.last_time) > 5.0 or
                    (df_complete == 1.0 and
                     logger_callback.total_time >= 5.0)):
                L.info(message + ': ' + str(df_complete))
                logger_callback.last_time = current_time
                logger_callback.total_time += current_time
        except AttributeError:
            logger_callback.last_time = time.time()
            logger_callback.total_time = 0.0

    return logger_callback

def gdal_progress_callback(complete, message, unknown):
    percent = float(complete * 100)
    if percent % 10 == 0:
        print(f"\r{percent}%", end='', flush=True)
    else:
        print('.', end='', flush=True)
        


def make_gdal_callback(msg=None):
    if msg is None:
        msg = "GDAL running:"
    else:
        msg = str(msg) + ": "

    state = {
        'start_time': None,
        'last_time': 0,
        'last_displayed_percent': -1,
        'buffer': '',
        'printed_header': False,
        'finished': False
    }

    def maybe_flush(now):
        if not state['printed_header'] and (now - state['start_time']) >= 0.5:
            print(msg, end='', flush=True)
            print(state['buffer'], end='', flush=True)
            state['printed_header'] = True
            state['buffer'] = ''  # clear buffer

    def callback(complete, message, unknown):
        percent = int(complete * 100)
        now = time.time()

        if state['start_time'] is None:
            state['start_time'] = now

        output = ''
        if percent % 10 == 0 and percent != state['last_displayed_percent']:
            output = f"{percent}%."
            state['last_displayed_percent'] = percent
        elif now - state['last_time'] >= 3 and percent != state['last_displayed_percent']:
            output = '.'
            state['last_time'] = now

        if output:
            if state['printed_header']:
                print(output, end='', flush=True)
            else:
                state['buffer'] += output

        # Check if it's time to flush
        maybe_flush(now)

        # Final flush at 100%
        if percent == 100 and not state['finished']:
            maybe_flush(now)
            if state['printed_header']:
                print()  # newline
            state['finished'] = True

        return 1

    return callback


# gdal_callback_standard = generate_gdal_callback_standard()


def get_vector_info_hb(vector_path, layer_index=0):
    
    """Get information about an OGR vector (datasource).

    Parameters:
        vector_path (str): a path to a OGR vector.
        layer_index (int): index of underlying layer to analyze.  Defaults to
            0.

    Raises:
        ValueError if `vector_path` does not exist on disk or cannot be opened
        as a gdal.OF_VECTOR.

    Returns:
        raster_properties (dictionary): a dictionary with the following
            properties stored under relevant keys.

            'projection' (string): projection of the vector in Well Known
                Text.
            'bounding_box' (list): list of floats representing the bounding
                box in projected coordinates as [minx, miny, maxx, maxy].

    """
    # hack_path = r"C:\Files\Research\base_data_test\aoi.gpkg"

    vector = gdal.OpenEx(vector_path, gdal.OF_VECTOR)
    if not vector:
        raise ValueError(
            "Could not open %s as a gdal.OF_VECTOR" % vector_path)
    vector_properties = {}
    layer = vector.GetLayer(iLayer=layer_index)
    # projection is same for all layers, so just use the first one
    spatial_ref = layer.GetSpatialRef()
    if spatial_ref:
        vector_sr_wkt = spatial_ref.ExportToWkt()
    else:
        vector_sr_wkt = None
    vector_properties['projection'] = vector_sr_wkt
    layer_bb = layer.GetExtent()
    layer = None
    vector = None
    # convert form [minx,maxx,miny,maxy] to [minx,miny,maxx,maxy]
    vector_properties['bounding_box'] = [layer_bb[i] for i in [0, 2, 1, 3]]
    return vector_properties


def get_raster_info_hb(raster_path, verbose=False):
    """Get information about a GDAL raster (dataset).

    Parameters:
       raster_path (String): a path to a GDAL raster.

    Raises:
        ValueError if `raster_path` is not a file or cannot be opened as a
        gdal.OF_RASTER.

    Returns:
        raster_properties (dictionary): a dictionary with the properties
            stored under relevant keys.
    """
    if not hb.path_exists(raster_path):
        raise ValueError("Raster path %s does not exist" % raster_path)
    raster = gdal.OpenEx(raster_path, gdal.OF_RASTER)
    if not raster:
        raise ValueError(
            "Could not open %s as a gdal.OF_RASTER" % raster_path)
    raster_properties = {}
    projection_wkt = raster.GetProjection()
    if not projection_wkt:
        projection_wkt = None
    raster_properties['projection'] = projection_wkt
    geo_transform = raster.GetGeoTransform()
    raster_properties['geotransform'] = geo_transform
    raster_properties['pixel_size'] = (geo_transform[1], geo_transform[5])
    raster_properties['mean_pixel_size'] = (
            (abs(geo_transform[1]) + abs(geo_transform[5])) / 2.0)
    raster_properties['raster_size'] = (
        raster.GetRasterBand(1).XSize,
        raster.GetRasterBand(1).YSize)
    raster_properties['size'] = raster.GetRasterBand(1).XSize * raster.GetRasterBand(1).YSize
    raster_properties['shape'] = ( # NOTE DIFFERENT ORDER, to match numpy rc notaiton
        raster.GetRasterBand(1).YSize,
        raster.GetRasterBand(1).XSize)
    raster_properties['n_bands'] = raster.RasterCount
    raster_properties['nodata'] = [
        raster.GetRasterBand(index).GetNoDataValue() for index in range(
            1, raster_properties['n_bands'] + 1)]
    raster_properties['ndv'] = raster.GetRasterBand(1).GetNoDataValue() # NOTE this one assumes 1 band.
    # blocksize is the same for all bands, so we can just get the first
    raster_properties['block_size'] = raster.GetRasterBand(1).GetBlockSize()

    # we dont' really know how the geotransform is laid out, all we can do is
    # calculate the x and y bounds, then take the appropriate min/max
    x_bounds = [
        geo_transform[0], geo_transform[0] +
                          raster_properties['raster_size'][0] * geo_transform[1] +
                          raster_properties['raster_size'][1] * geo_transform[2]]
    y_bounds = [
        geo_transform[3], geo_transform[3] +
                          raster_properties['raster_size'][0] * geo_transform[4] +
                          raster_properties['raster_size'][1] * geo_transform[5]]

    raster_properties['bounding_box'] = [
        numpy.min(x_bounds), numpy.min(y_bounds),
        numpy.max(x_bounds), numpy.max(y_bounds)]

    # datatype is the same for the whole raster, but is associated with band
    raster_properties['datatype'] = raster.GetRasterBand(1).DataType
    raster_properties['data_type'] = raster.GetRasterBand(1).DataType # preffered key name
    raster = None

    # ULX ULY LRX LRY
    raster_properties['gdal_win'] = [raster_properties['bounding_box'][0], raster_properties['bounding_box'][3],
                                     raster_properties['bounding_box'][2], raster_properties['bounding_box'][1]]
    raster_properties['minx'] = raster_properties['bounding_box'][0]
    raster_properties['miny'] = raster_properties['bounding_box'][1]
    raster_properties['maxx'] = raster_properties['bounding_box'][2]
    raster_properties['maxy'] = raster_properties['bounding_box'][3]

    if verbose:
        L.info(hb.pp(raster_properties))

    return raster_properties



