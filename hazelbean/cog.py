import os.path
import struct
import sys
import pathlib
import hazelbean as hb

from osgeo import gdal




def make_path_cog(input_raster_path, output_raster_path=None, output_data_type=None, overview_resampling_method=None, ndv=None, compression="ZSTD", blocksize=512, verbose=False):
    """ Create a Pog (pyramidal cog) from input_raster_path. Writes in-place if output_raster_path is not set. Chooses correct values for 
    everything else if not set."""
    
    # Check if input exists
    if not hb.path_exists(input_raster_path, verbose=verbose):
        raise FileNotFoundError(f"Input raster does not exist: {input_raster_path} at abs path {hb.path_abs(input_raster_path)}")
    
    if is_path_pog(input_raster_path, verbose) and verbose:
        hb.log(f"Raster is already a COG: {input_raster_path}")
        
    # Make a local copy at a temp file to process on to avoid corrupting the original
    temp_copy_path = hb.temp('.tif', 'copy', True, tag_along_file_extensions=['.aux.xml'])
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(temp_copy_path), exist_ok=True)       
    
    if output_data_type is None:
        output_data_type = input_data_type 

    input_data_type = hb.get_datatype_from_uri(input_raster_path)
    if output_data_type is not None:
        if output_data_type != input_data_type:
            gdal.Translate(temp_copy_path, input_raster_path, outputType=hb.gdal_number_to_gdal_type[output_data_type])
        else:
            hb.path_copy(input_raster_path, temp_copy_path) # Can just copy it direclty without accessing the raster.        
    
    # Get the resolution from the src_ds
    degrees = hb.get_cell_size_from_path(temp_copy_path)
    arcseconds = hb.get_cell_size_from_path_in_arcseconds(temp_copy_path)
    
    original_output_raster_path = output_raster_path
    if output_raster_path is None:        
        output_raster_path = hb.temp('.tif', hb.file_root(input_raster_path) + '_displacement_io_by_make_path_cog', remove_at_exit=False, folder=os.path.dirname(input_raster_path), tag_along_file_extensions=['.aux.xml'])
    
    if output_data_type is None:
        input_data_type = hb.get_datatype_from_uri(temp_copy_path)
        output_data_type = input_data_type       
        
    ndv = hb.no_data_values_by_gdal_type[output_data_type][0] # NOTE AWKWARD INCLUSINO OF zero as second option to work with faster_zonal_stats
        
    # Open the source raster in UPDATE MODE so it writes the overviews as internal
    src_ds = gdal.OpenEx(temp_copy_path, gdal.GA_Update)
    if not src_ds:
        raise ValueError(f"Unable to open raster: {input_raster_path}")
    
    # I'm not sure why, but getting the stats from the src_ds, then building overviews, then reassigning it keeps COG compliance.
    add_stats_to_geotiff_with_gdal(input_raster_path, approx_ok=False, force=True, verbose=verbose)
    stats_dict = get_stats_from_geotiff(input_raster_path)    
    
    # Remove existing overviews (if any)
    src_ds.BuildOverviews(None, [])     
    resampling_algorithm = hb.pyramid_resampling_algorithms_by_data_type[output_data_type] 
    if overview_resampling_method is None:           
        overview_resampling_method = resampling_algorithm
    
    # Set the overview levels based on the pyramid arcseconds
    overview_levels = hb.pyramid_compatible_overview_levels[arcseconds]
    src_ds.BuildOverviews(overview_resampling_method.upper(), overview_levels, hb.make_gdal_callback(f'Building overviews for {temp_copy_path}'))

    # Close the dataset to ensure overviews are saved
    del src_ds    
    
    add_stats_to_geotiff_from_dict(temp_copy_path, stats_dict)  
    
    # Reopen it to use it as a copy target
    src_ds = gdal.OpenEx(temp_copy_path, gdal.GA_ReadOnly)
    
    # Define creation options for COG
    creation_options = [
        f"COMPRESS={compression}",
        f"BLOCKSIZE={blocksize}",  
        f"BIGTIFF=YES", 
        f"OVERVIEW_COMPRESS={compression}",        
        f"RESAMPLING={resampling_algorithm}",
        # f"OVERVIEWS=IGNORE_EXISTING", 
        f"OVERVIEW_RESAMPLING={overview_resampling_method}",
    ]

    cog_driver = gdal.GetDriverByName('COG')
    if cog_driver is None:
        raise RuntimeError("COG driver is not available in this GDAL build.")    
    
    if ndv is not None and src_ds is not None:
        for i in range(1, src_ds.RasterCount + 1):
            band = src_ds.GetRasterBand(i)
            band.SetNoDataValue(ndv)
            
              
            
    # Actually create the COG
    dst_ds = cog_driver.CreateCopy(
        output_raster_path,
        src_ds,
        strict=0,  # set to 1 to fail on any “creation option not recognized”
        options=creation_options,
        callback=hb.make_gdal_callback(f'cog_driver creating copy at {output_raster_path}')
    )        
    dst_ds = None
    
    # add_stats_to_geotiff_from_dict(output_raster_path, stats_dict)
    
    if original_output_raster_path is None:
        hb.swap_filenames(output_raster_path, input_raster_path)        

    if not is_path_cog(output_raster_path, verbose=verbose) and verbose:
        hb.log(f"Failed to create COG: {output_raster_path} at abs path {hb.path_abs(output_raster_path)}")

def add_stats_to_geotiff_with_gdal(geotiff_path, approx_ok=False, force=True, verbose=True):
    """
    Computes raster statistics and embeds them into GeoTIFF internal metadata
    without creating .aux.xml files when opened in QGIS.

    Parameters:
        geotiff_path (str): Path to GeoTIFF.
        approx_ok (bool): Allow approximate stats computation.
        force (bool): Force recomputation of statistics.
        verbose (bool): Print detailed statistics per band.
    """
    ds = gdal.Open(geotiff_path, gdal.GA_Update)

    if not ds:
        raise ValueError(f"Could not open {geotiff_path}")

    for band_index in range(1, ds.RasterCount + 1):
        band = ds.GetRasterBand(band_index)  
        band.SetMetadataItem("STATISTICS_MINIMUM", None)
        band.SetMetadataItem("STATISTICS_MAXIMUM", None)
        band.SetMetadataItem("STATISTICS_MEAN", None)
        band.SetMetadataItem("STATISTICS_STDDEV", None)                    
        stats = band.ComputeStatistics(approx_ok=approx_ok, callback=hb.make_gdal_callback('Calculating stats.') if verbose else None)

        if verbose:
            print(
                f"\nBand {band_index} stats: "
                f"min={stats[0]:.4f}, max={stats[1]:.4f}, mean={stats[2]:.4f}, stddev={stats[3]:.4f}"
            )

        band.FlushCache()

    ds = None 
    
def get_stats_from_geotiff(geotiff_path):
    """
    Returns a dictionary of statistics (min, max, mean, stddev) for each band in the GeoTIFF.
    
    Args:
        geotiff_path (str): Path to the input GeoTIFF file.
    
    Returns:
        dict: A dictionary where keys are band numbers (1-based) and values are dicts of statistics.
    """
    ds = gdal.Open(geotiff_path, gdal.GA_ReadOnly)
    if ds is None:
        raise FileNotFoundError(f"Could not open file: {geotiff_path}")
    
    stats_by_band = {}
    for i in range(1, ds.RasterCount + 1):
        band = ds.GetRasterBand(i)
        stats = band.GetStatistics(True, True)  # (min, max, mean, stddev)
        if stats is not None:
            stats_by_band[i] = {
                'min': stats[0],
                'max': stats[1],
                'mean': stats[2],
                'stddev': stats[3]
            }
        else:
            stats_by_band[i] = None  # or handle missing stats as needed
    
    ds = None  # Close the dataset
    return stats_by_band

def add_stats_to_geotiff_from_dict(geotiff_path, stats_dict, ignore_cog_warning=True):
    """
    Adds per-band statistics to a GeoTIFF file using the given stats dictionary.

    Args:
        geotiff_path (str): Path to the GeoTIFF file to update.
        stats_dict (dict): Dictionary with keys as band numbers (1-based) and values as
                           dicts containing 'min', 'max', 'mean', 'stddev'.
    """
    
    open_options = ["IGNORE_COG_LAYOUT_BREAK=YES"] if ignore_cog_warning else []
    
    ds = gdal.OpenEx(geotiff_path, gdal.OF_UPDATE, open_options=open_options) # LEARNING POINT, OF_UPDATE is for openex whereas GA_Update is for open
    if ds is None:
        raise FileNotFoundError(f"Could not open file for update: {geotiff_path}")

    for band_num, stats in stats_dict.items():
        if stats is None:
            continue
        band = ds.GetRasterBand(band_num)
        band.SetStatistics(
            stats['min'],
            stats['max'],
            stats['mean'],
            stats['stddev']
        )

    ds.FlushCache()
    ds = None  # Close and save
    
def make_path_pog(input_raster_path, output_raster_path=None, output_data_type=None, ndv=None, overview_resampling_method=None, compression="ZSTD", blocksize=512, verbose=False):
    """ Create a Pog (pyramidal cog) from input_raster_path. Writes in-place if output_raster_path is not set. Chooses correct values for 
    everything else if not set."""
    
    # Check if input exists
    if not hb.path_exists(input_raster_path, verbose=verbose):
        raise FileNotFoundError(f"Input raster does not exist: {input_raster_path} at abs path {hb.path_abs(input_raster_path)}")
    
    if is_path_pog(input_raster_path, verbose) and verbose:
        hb.log(f"Raster is already a POG: {input_raster_path}")
        
    # Make a local copy at a temp file to process on to avoid corrupting the original
    temp_copy_path = hb.temp('.tif', 'copy', True, tag_along_file_extensions=['.aux.xml'])
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(temp_copy_path), exist_ok=True)       
    
    input_data_type = hb.get_datatype_from_uri(input_raster_path)
    if output_data_type == 'auto':
        if input_data_type in [1, 2, 3, 4, 5, 12, 13]:
            output_data_type = 13
        elif input_data_type in [6]:
            output_data_type = 6
        elif input_data_type in [7, 8, 9, 10, 11]:
            output_data_type = 7
    
    if output_data_type is None:
        output_data_type = input_data_type 

    
    if output_data_type is not None:
        if output_data_type != input_data_type:
            gdal.Translate(temp_copy_path, input_raster_path, outputType=hb.gdal_number_to_gdal_type[output_data_type], callback=hb.make_gdal_callback(f"Translating to expand to global extent on {temp_copy_path}"))
        else:
            hb.path_copy(input_raster_path, temp_copy_path) # Can just copy it direclty without accessing the raster.        
    
    # Get the resolution from the src_ds
    degrees = hb.get_cell_size_from_path(temp_copy_path)
    arcseconds = hb.get_cell_size_from_path_in_arcseconds(temp_copy_path)
    
    original_output_raster_path = output_raster_path
    if output_raster_path is None:        
        output_raster_path = hb.temp('.tif', hb.file_root(input_raster_path), remove_at_exit=False, folder=os.path.dirname(input_raster_path), tag_along_file_extensions=['.aux.xml'])
        
    ndv = hb.no_data_values_by_gdal_type[output_data_type][0] # NOTE AWKWARD INCLUSINO OF zero as second option to work with faster_zonal_stats
    
    gt = hb.get_geotransform_path(input_raster_path)    
    gt_pyramid = hb.get_global_geotransform_from_resolution(degrees)
    
    user_dir = pathlib.Path.home()
    match_path = os.path.join(user_dir, 'Files', 'base_data', hb.ha_per_cell_ref_paths[arcseconds])
    if gt != gt_pyramid:
        resample_temp_path = hb.temp('.tif', 'resample', True, tag_along_file_extensions=['.aux.xml'])

        hb.resample_to_match(
            temp_copy_path,
            match_path,
            resample_temp_path,
            resample_method='bilinear',
            output_data_type=output_data_type,
            src_ndv=None,
            ndv=None,
            s_srs_wkt=None,
            compress=True,
            ensure_fits=False,
            gtiff_creation_options=hb.globals.PRECOG_GTIFF_CREATION_OPTIONS_LIST,
            calc_raster_stats=False,
            add_overviews=False,
            pixel_size_override=None,
            target_aligned_pixels=True,
            bb_override=None,
            verbose=False, 
        )
        hb.swap_filenames(resample_temp_path, temp_copy_path)
        
        
    add_stats_to_geotiff_with_gdal(temp_copy_path, approx_ok=False, force=True, verbose=verbose)
    
    # Open the source raster in UPDATE MODE so it writes the overviews as internal
    src_ds = gdal.OpenEx(temp_copy_path, gdal.GA_Update)
    if not src_ds:
        raise ValueError(f"Unable to open raster: {temp_copy_path}")



    # Remove existing overviews (if any)
    src_ds.BuildOverviews(None, [])     
        
    if overview_resampling_method is None:
        overview_resampling_method = hb.pyramid_resampling_algorithms_by_data_type[output_data_type] 
    
    # Set the overview levels based on the pyramid arcseconds
    overview_levels = hb.pyramid_compatible_overview_levels[arcseconds]
    src_ds.BuildOverviews(overview_resampling_method.upper(), overview_levels)

    # Close the dataset to ensure overviews are saved
    del src_ds    
    
    # Reopen it to use it as a copy target
    src_ds = gdal.OpenEx(temp_copy_path, gdal.GA_ReadOnly)
    
    # Define creation options for COG
    creation_options = [
        f"COMPRESS={compression}",
        f"BLOCKSIZE={blocksize}",  
        f"BIGTIFF=YES", 
        f"OVERVIEW_COMPRESS={compression}",        
        f"RESAMPLING={overview_resampling_method}",
        # f"OVERVIEWS=IGNORE_EXISTING",
        f"OVERVIEW_RESAMPLING={overview_resampling_method}",
    ]

    cog_driver = gdal.GetDriverByName('COG')
    if cog_driver is None:
        raise RuntimeError("COG driver is not available in this GDAL build.")    
    
    if ndv is not None and src_ds is not None:
        for i in range(1, src_ds.RasterCount + 1):
            band = src_ds.GetRasterBand(i)
            band.SetNoDataValue(ndv)
            
    # Actually create the COG
    dst_ds = cog_driver.CreateCopy(
        output_raster_path,
        src_ds,
        strict=0,  # set to 1 to fail on any “creation option not recognized”
        options=creation_options
    )        
    dst_ds = None
    
    if original_output_raster_path is None:
        hb.swap_filenames(output_raster_path, input_raster_path)        

    if not is_path_cog(output_raster_path, verbose=verbose) and verbose:
        hb.log(f"Failed to create COG: {output_raster_path} at abs path {hb.path_abs(output_raster_path)}")




def is_path_cog(path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False):
    """Check if a file is a (Geo)TIFF with cloud optimized compatible structure."""
    if not hb.path_exists(path):
        if verbose:
            hb.log(f"Path {path} does not exist at abspath {hb.path_abs(path)}")
        if raise_exceptions:
            raise FileNotFoundError(f"Path {path} does not exist at abspath {hb.path_abs(path)}")
        return False
    if os.path.splitext(path)[1].lower() != ".tif":
        if verbose:
            hb.log(f"Path {path} at abspath {hb.path_abs(path)} is not a GeoTIFF")
        if raise_exceptions:
            raise ValueError(f"Path {path} at abspath {hb.path_abs(path)} is not a GeoTIFF")
        return False
    
    try: 
        ds = gdal.OpenEx(path, gdal.OF_RASTER)    
    except:
        if verbose:
            hb.log(f"Unable to open {path} at abspath {hb.path_abs(path)}")
        if raise_exceptions:
            raise ValueError(f"Unable to open {path} at abspath {hb.path_abs(path)}")
        return False
    
    result = validate(ds, check_tiled=check_tiled, full_check=full_check)

    
    # Check if any element of the list result is longer than 1
    if any(len(item) > 0 for item in result[:-1]):
        if verbose:
            hb.log(f"Path {path} at abspath {hb.path_abs(path)} is not a valid COG. It raised the following errors: \n " + '\n'.join([str(i) for i in result]))
        if raise_exceptions:
            raise ValueError(f"Path {path} at abspath {hb.path_abs(path)} is not a valid COG. It raised the following errors: \n " + '\n'.join(result))
        return False

    return True



def is_path_pog(path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False):
    
    is_pyramid = hb.is_path_global_pyramid(path)
    is_cog = is_path_cog(path, check_tiled=check_tiled, full_check=full_check, raise_exceptions=raise_exceptions, verbose=verbose)

    return is_pyramid and is_cog


    

import numpy as np
from osgeo import gdal, osr

def write_random_cog(output_path, xsize=256, ysize=256, epsg=4326):
    """
    Creates a single-band random raster in-memory and writes it as a COG.
    
    Args:
        output_path (str): Path to the output .tif file
        xsize       (int): Width of the raster
        ysize       (int): Height of the raster
        epsg        (int): EPSG code for the spatial reference (default 4326)
    """
    
    from osgeo import gdal
    driver = gdal.GetDriverByName('COG')
    if driver is None:
        print("COG driver not available in this GDAL build.")
    else:
        print("COG driver is available.")

    # 1. Create random data (8-bit range 0-255)
    arr = np.random.randint(0, 256, size=(ysize, xsize), dtype=np.uint8)

    # 2. Create an in-memory dataset
    mem_driver = gdal.GetDriverByName('MEM')
    mem_ds = mem_driver.Create('', xsize, ysize, bands=1, eType=gdal.GDT_Byte)

    # 3. Set a simple GeoTransform (top-left at (0,0), 1 pixel = 1 degree/meters, etc.)
    mem_ds.SetGeoTransform([0, 1, 0, 0, 0, -1])  
    # For example, the above transform means:
    #   origin_x = 0
    #   pixel_width = 1
    #   rotation_x = 0
    #   origin_y = 0
    #   rotation_y = 0
    #   pixel_height = -1 (y goes "down")

    # 4. Assign a projection (e.g., EPSG:4326 for WGS84 lat/lon)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)
    mem_ds.SetProjection(srs.ExportToWkt())

    # 5. Write the random array to the band
    mem_ds.GetRasterBand(1).WriteArray(arr)

    # 6. Define creation options for the COG driver
    creation_options = [
        "COMPRESS=DEFLATE",
        "PREDICTOR=2",
        "BLOCKSIZE=512",
        "OVERVIEW_COMPRESS=DEFLATE",
        "OVERVIEW_LEVELS=2,4,8,16"
        # You can also specify RESAMPLING=AVERAGE, etc.
    ]

    # 7. Use gdal.Translate to produce the COG
    gdal.Translate(
        destName=output_path,
        srcDS=mem_ds,
        format="COG",  # Critical: ensures we use the COG driver
        options=gdal.TranslateOptions(creationOptions=creation_options)
    )

    # 8. Clean up
    mem_ds = None
    print(f"COG created at: {output_path}")

    # Optional: Print out some info on the resulting file
    info_str = gdal.Info(output_path)
    print(info_str)
    
    result = is_path_cog(output_path, verbose=True)
    print(result)
    return result



# Drawn from https://github.com/OSGeo/gdal/blob/master/swig/python/gdal-utils/osgeo_utils/samples/validate_cloud_optimized_geotiff.py

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# *****************************************************************************
#
#  Project:  GDAL
#  Purpose:  Validate Cloud Optimized GeoTIFF file structure
#  Author:   Even Rouault, <even dot rouault at spatialys dot com>
#
# *****************************************************************************
#  Copyright (c) 2017, Even Rouault
#
# SPDX-License-Identifier: MIT
# *****************************************************************************

def Usage():
    print(
        "Usage: validate_cloud_optimized_geotiff.py [-q] [--full-check=yes/no/auto] test.tif"
    )
    print("")
    print("Options:")
    print("-q: quiet mode")
    print(
        "--full-check=yes/no/auto: check tile/strip leader/trailer bytes. auto=yes for local files, and no for remote files"
    )
    return 2


class ValidateCloudOptimizedGeoTIFFException(Exception):
    pass


def full_check_band(
    f,
    interleave,
    band_name,
    band,
    errors,
    block_order_row_major,
    block_leader_size_as_uint4,
    block_trailer_last_4_bytes_repeated,
    mask_interleaved_with_imagery,
    last_offset,
):

    block_size = band.GetBlockSize()
    mask_band = None
    if mask_interleaved_with_imagery:
        mask_band = band.GetMaskBand()
        mask_block_size = mask_band.GetBlockSize()
        if block_size != mask_block_size:
            errors += [
                band_name + ": mask block size is different from its imagery band"
            ]
            mask_band = None

    yblocks = (band.YSize + block_size[1] - 1) // block_size[1]
    xblocks = (band.XSize + block_size[0] - 1) // block_size[0]
    for y in range(yblocks):
        for x in range(xblocks):

            offset = band.GetMetadataItem("BLOCK_OFFSET_%d_%d" % (x, y), "TIFF")
            offset = int(offset) if offset is not None else 0
            bytecount = band.GetMetadataItem("BLOCK_SIZE_%d_%d" % (x, y), "TIFF")
            bytecount = int(bytecount) if bytecount is not None else 0

            if offset > 0:
                if block_order_row_major and offset < last_offset:
                    errors += [
                        band_name
                        + ": offset of block (%d, %d) is smaller than previous block"
                        % (x, y)
                    ]

                if block_leader_size_as_uint4:
                    gdal.VSIFSeekL(f, offset - 4, 0)
                    leader_size = struct.unpack("<I", gdal.VSIFReadL(4, 1, f))[0]
                    if leader_size != bytecount:
                        errors += [
                            band_name
                            + ": for block (%d, %d), size in leader bytes is %d instead of %d"
                            % (x, y, leader_size, bytecount)
                        ]

                if block_trailer_last_4_bytes_repeated:
                    if bytecount >= 4:
                        gdal.VSIFSeekL(f, offset + bytecount - 4, 0)
                        last_bytes = gdal.VSIFReadL(8, 1, f)
                        if last_bytes[0:4] != last_bytes[4:8]:
                            errors += [
                                band_name
                                + ": for block (%d, %d), trailer bytes are invalid"
                                % (x, y)
                            ]

            if mask_band and (
                interleave == "PIXEL"
                or (
                    interleave == "TILE"
                    and band.GetBand() == band.GetDataset().RasterCount
                )
            ):
                offset_mask = mask_band.GetMetadataItem(
                    "BLOCK_OFFSET_%d_%d" % (x, y), "TIFF"
                )
                offset_mask = int(offset_mask) if offset_mask is not None else 0
                if offset > 0 and offset_mask > 0:
                    # bytecount_mask = int(mask_band.GetMetadataItem('BLOCK_SIZE_%d_%d' % (x,y), 'TIFF'))
                    expected_offset_mask = (
                        offset
                        + bytecount
                        + (4 if block_leader_size_as_uint4 else 0)
                        + (4 if block_trailer_last_4_bytes_repeated else 0)
                    )
                    if offset_mask != expected_offset_mask:
                        errors += [
                            "Mask of "
                            + band_name
                            + ": for block (%d, %d), offset is %d, whereas %d was expected"
                            % (x, y, offset_mask, expected_offset_mask)
                        ]
                elif offset == 0 and offset_mask > 0:
                    if block_order_row_major and offset_mask < last_offset:
                        errors += [
                            "Mask of "
                            + band_name
                            + ": offset of block (%d, %d) is smaller than previous block"
                            % (x, y)
                        ]

                    offset = offset_mask

            last_offset = offset

    return last_offset


def check_tile_interleave(ds, ds_name, block_order_row_major, errors):

    block_size = ds.GetRasterBand(1).GetBlockSize()
    yblocks = (ds.RasterYSize + block_size[1] - 1) // block_size[1]
    xblocks = (ds.RasterXSize + block_size[0] - 1) // block_size[0]
    last_offset = 0
    for y in range(yblocks):
        for x in range(xblocks):
            for band_idx in range(ds.RasterCount):
                offset = ds.GetRasterBand(band_idx + 1).GetMetadataItem(
                    "BLOCK_OFFSET_%d_%d" % (x, y), "TIFF"
                )
                offset = int(offset) if offset is not None else 0

                if offset > 0:
                    if block_order_row_major and offset < last_offset:
                        errors += [
                            ds_name
                            + ": offset of block (%d, %d) is smaller than previous block"
                            % (x, y)
                        ]

                    last_offset = offset


def validate(ds, check_tiled=True, full_check=False):
    """Check if a file is a (Geo)TIFF with cloud optimized compatible structure.

    Args:
      ds: GDAL Dataset for the file to inspect.
      check_tiled: Set to False to ignore missing tiling.
      full_check: Set to TRUe to check tile/strip leader/trailer bytes. Might be slow on remote files

    Returns:
      A tuple, whose first element is an array of error messages
      (empty if there is no error), and the second element, a dictionary
      with the structure of the GeoTIFF file.

    Raises:
      ValidateCloudOptimizedGeoTIFFException: Unable to open the file or the
        file is not a Tiff.
    """

    if int(gdal.VersionInfo("VERSION_NUM")) < 2020000:
        raise ValidateCloudOptimizedGeoTIFFException("GDAL 2.2 or above required")

    unicode_type = type("".encode("utf-8").decode("utf-8"))
    if isinstance(ds, (str, unicode_type)):
        gdal.PushErrorHandler()
        ds = gdal.Open(ds)
        gdal.PopErrorHandler()
        if ds is None:
            raise ValidateCloudOptimizedGeoTIFFException(
                "Invalid file : %s" % gdal.GetLastErrorMsg()
            )
        if ds.GetDriver().ShortName not in ("GTiff", "LIBERTIFF"):
            raise ValidateCloudOptimizedGeoTIFFException("The file is not a GeoTIFF")

    details = {}
    errors = []
    warnings = []
    filename = ds.GetDescription()
    main_band = ds.GetRasterBand(1)
    ovr_count = main_band.GetOverviewCount()
    filelist = ds.GetFileList()
    if filelist is not None and filename + ".ovr" in filelist:
        errors += ["Overviews found in external .ovr file. They should be internal"]

    if main_band.XSize > 512 or main_band.YSize > 512:
        if check_tiled:
            block_size = main_band.GetBlockSize()
            if block_size[0] == main_band.XSize and block_size[0] > 1024:
                errors += ["The file is greater than 512xH or Wx512, but is not tiled"]

        if ovr_count == 0:
            warnings += [
                "The file is greater than 512xH or Wx512, it is recommended "
                "to include internal overviews"
            ]

    ifd_offset = int(main_band.GetMetadataItem("IFD_OFFSET", "TIFF"))
    ifd_offsets = [ifd_offset]

    block_order_row_major = False
    block_leader_size_as_uint4 = False
    block_trailer_last_4_bytes_repeated = False
    mask_interleaved_with_imagery = False

    if ifd_offset not in (8, 16):

        # Check if there is GDAL hidden structural metadata
        f = gdal.VSIFOpenL(filename, "rb")
        if not f:
            raise ValidateCloudOptimizedGeoTIFFException("Cannot open file")
        signature = struct.unpack("B" * 4, gdal.VSIFReadL(4, 1, f))
        bigtiff = signature in ((0x49, 0x49, 0x2B, 0x00), (0x4D, 0x4D, 0x00, 0x2B))
        if bigtiff:
            expected_ifd_pos = 16
        else:
            expected_ifd_pos = 8
        gdal.VSIFSeekL(f, expected_ifd_pos, 0)
        pattern = "GDAL_STRUCTURAL_METADATA_SIZE=%06d bytes\n" % 0
        got = gdal.VSIFReadL(len(pattern), 1, f).decode("LATIN1")
        if len(got) == len(pattern) and got.startswith(
            "GDAL_STRUCTURAL_METADATA_SIZE="
        ):
            size = int(got[len("GDAL_STRUCTURAL_METADATA_SIZE=") :][0:6])
            extra_md = gdal.VSIFReadL(size, 1, f).decode("LATIN1")
            block_order_row_major = "BLOCK_ORDER=ROW_MAJOR" in extra_md
            block_leader_size_as_uint4 = "BLOCK_LEADER=SIZE_AS_UINT4" in extra_md
            block_trailer_last_4_bytes_repeated = (
                "BLOCK_TRAILER=LAST_4_BYTES_REPEATED" in extra_md
            )
            mask_interleaved_with_imagery = (
                "MASK_INTERLEAVED_WITH_IMAGERY=YES" in extra_md
            )
            if "KNOWN_INCOMPATIBLE_EDITION=YES" in extra_md:
                errors += ["KNOWN_INCOMPATIBLE_EDITION=YES is declared in the file"]
            expected_ifd_pos += len(pattern) + size
            expected_ifd_pos += (
                expected_ifd_pos % 2
            )  # IFD offset starts on a 2-byte boundary
        gdal.VSIFCloseL(f)

        if expected_ifd_pos != ifd_offsets[0]:
            errors += [
                "The offset of the main IFD should be %d. It is %d instead"
                % (expected_ifd_pos, ifd_offsets[0])
            ]

    details["ifd_offsets"] = {}
    details["ifd_offsets"]["main"] = ifd_offset

    for i in range(ovr_count):
        # Check that overviews are by descending sizes
        ovr_band = ds.GetRasterBand(1).GetOverview(i)
        if i == 0:
            if ovr_band.XSize > main_band.XSize or ovr_band.YSize > main_band.YSize:
                errors += ["First overview has larger dimension than main band"]
        else:
            prev_ovr_band = ds.GetRasterBand(1).GetOverview(i - 1)
            if (
                ovr_band.XSize > prev_ovr_band.XSize
                or ovr_band.YSize > prev_ovr_band.YSize
            ):
                errors += [
                    "Overview of index %d has larger dimension than "
                    "overview of index %d" % (i, i - 1)
                ]

        if check_tiled:
            block_size = ovr_band.GetBlockSize()
            if block_size[0] == ovr_band.XSize and block_size[0] > 1024:
                errors += ["Overview of index %d is not tiled" % i]

        # Check that the IFD of descending overviews are sorted by increasing
        # offsets
        ifd_offset = int(ovr_band.GetMetadataItem("IFD_OFFSET", "TIFF"))
        ifd_offsets.append(ifd_offset)
        details["ifd_offsets"]["overview_%d" % i] = ifd_offset
        if ifd_offsets[-1] < ifd_offsets[-2]:
            if i == 0:
                errors += [
                    "The offset of the IFD for overview of index %d is %d, "
                    "whereas it should be greater than the one of the main "
                    "image, which is at byte %d" % (i, ifd_offsets[-1], ifd_offsets[-2])
                ]
            else:
                errors += [
                    "The offset of the IFD for overview of index %d is %d, "
                    "whereas it should be greater than the one of index %d, "
                    "which is at byte %d" % (i, ifd_offsets[-1], i - 1, ifd_offsets[-2])
                ]

    # Check that the imagery starts by the smallest overview and ends with
    # the main resolution dataset

    def get_block_offset(band):
        blockxsize, blockysize = band.GetBlockSize()
        for y in range(int((band.YSize + blockysize - 1) / blockysize)):
            for x in range(int((band.XSize + blockxsize - 1) / blockxsize)):
                block_offset = band.GetMetadataItem(
                    "BLOCK_OFFSET_%d_%d" % (x, y), "TIFF"
                )
                if block_offset:
                    return int(block_offset)
        return 0

    block_offset = get_block_offset(main_band)
    data_offsets = [block_offset]
    details["data_offsets"] = {}
    details["data_offsets"]["main"] = block_offset
    for i in range(ovr_count):
        ovr_band = ds.GetRasterBand(1).GetOverview(i)
        block_offset = get_block_offset(ovr_band)
        data_offsets.append(block_offset)
        details["data_offsets"]["overview_%d" % i] = block_offset

    if data_offsets[-1] != 0 and data_offsets[-1] < ifd_offsets[-1]:
        if ovr_count > 0:
            errors += [
                "The offset of the first block of the smallest overview "
                "should be after its IFD"
            ]
        else:
            errors += [
                "The offset of the first block of the image should " "be after its IFD"
            ]
    for i in range(len(data_offsets) - 2, 0, -1):
        if data_offsets[i] != 0 and data_offsets[i] < data_offsets[i + 1]:
            errors += [
                "The offset of the first block of overview of index %d should "
                "be after the one of the overview of index %d" % (i - 1, i)
            ]
    if (
        len(data_offsets) >= 2
        and data_offsets[0] != 0
        and data_offsets[0] < data_offsets[1]
    ):
        errors += [
            "The offset of the first block of the main resolution image "
            "should be after the one of the overview of index %d" % (ovr_count - 1)
        ]

    interleave = ds.GetMetadataItem("INTERLEAVE", "IMAGE_STRUCTURE")

    if full_check and (
        block_order_row_major
        or block_leader_size_as_uint4
        or block_trailer_last_4_bytes_repeated
        or mask_interleaved_with_imagery
    ):
        f = gdal.VSIFOpenL(filename, "rb")
        if not f:
            raise ValidateCloudOptimizedGeoTIFFException("Cannot open file")

        if interleave == "PIXEL":
            full_check_band(
                f,
                interleave,
                "Main resolution image",
                main_band,
                errors,
                block_order_row_major,
                block_leader_size_as_uint4,
                block_trailer_last_4_bytes_repeated,
                mask_interleaved_with_imagery,
                0,
            )
        else:
            last_offset = 0
            for band_idx in range(ds.RasterCount):
                if interleave != "BAND":
                    last_offset = 0
                last_offset = full_check_band(
                    f,
                    interleave,
                    "Band %d of main resolution image" % (band_idx + 1),
                    ds.GetRasterBand(band_idx + 1),
                    errors,
                    block_order_row_major,
                    block_leader_size_as_uint4,
                    block_trailer_last_4_bytes_repeated,
                    mask_interleaved_with_imagery,
                    last_offset,
                )

        if interleave == "TILE":
            check_tile_interleave(
                ds, "Main resolution image", block_order_row_major, errors
            )

        if (
            main_band.GetMaskFlags() == gdal.GMF_PER_DATASET
            and (filename + ".msk") not in ds.GetFileList()
        ):
            full_check_band(
                f,
                interleave,
                "Mask band of main resolution image",
                main_band.GetMaskBand(),
                errors,
                block_order_row_major,
                block_leader_size_as_uint4,
                block_trailer_last_4_bytes_repeated,
                False,
                0,
            )
        for i in range(ovr_count):
            ovr_band = ds.GetRasterBand(1).GetOverview(i)
            if interleave == "PIXEL":
                full_check_band(
                    f,
                    interleave,
                    "Overview %d" % i,
                    ovr_band,
                    errors,
                    block_order_row_major,
                    block_leader_size_as_uint4,
                    block_trailer_last_4_bytes_repeated,
                    mask_interleaved_with_imagery,
                    0,
                )
            else:
                last_offset = 0
                for band_idx in range(ds.RasterCount):
                    if interleave != "BAND":
                        last_offset = 0
                    last_offset = full_check_band(
                        f,
                        interleave,
                        "Band %d of overview %d" % (band_idx + 1, i),
                        ds.GetRasterBand(band_idx + 1).GetOverview(i),
                        errors,
                        block_order_row_major,
                        block_leader_size_as_uint4,
                        block_trailer_last_4_bytes_repeated,
                        mask_interleaved_with_imagery,
                        last_offset,
                    )

            if interleave == "TILE":
                check_tile_interleave(
                    ds.GetRasterBand(1).GetDataset(),
                    "Overview %d" % i,
                    block_order_row_major,
                    errors,
                )

            if (
                ovr_band.GetMaskFlags() == gdal.GMF_PER_DATASET
                and (filename + ".msk") not in ds.GetFileList()
            ):
                full_check_band(
                    f,
                    interleave,
                    "Mask band of overview %d" % i,
                    ovr_band.GetMaskBand(),
                    errors,
                    block_order_row_major,
                    block_leader_size_as_uint4,
                    block_trailer_last_4_bytes_repeated,
                    False,
                    0,
                )
        gdal.VSIFCloseL(f)

    return warnings, errors, details


def main(argv=sys.argv):
    """Return 0 in case of success, 1 for failure."""

    i = 1
    filename = None
    quiet = False
    full_check = None
    while i < len(argv):
        if argv[i] == "-q":
            quiet = True
        elif argv[i] == "--full-check=yes":
            full_check = True
        elif argv[i] == "--full-check=no":
            full_check = False
        elif argv[i] == "--full-check=auto":
            full_check = None
        elif argv[i][0] == "-":
            return Usage()
        elif filename is None:
            filename = argv[i]
        else:
            return Usage()

        i += 1

    if filename is None:
        return Usage()

    gdal.UseExceptions()

    if full_check is None:
        full_check = filename.startswith("/vsimem/") or os.path.exists(filename)

    try:
        ret = 0
        warnings, errors, details = validate(filename, full_check=full_check)
        if warnings:
            if not quiet:
                print("The following warnings were found:")
                for warning in warnings:
                    print(" - " + warning)
                print("")
        if errors:
            if not quiet:
                print("%s is NOT a valid cloud optimized GeoTIFF." % filename)
                print("The following errors were found:")
                for error in errors:
                    print(" - " + error)
                print("")
            ret = 1
        else:
            if not quiet:
                print("%s is a valid cloud optimized GeoTIFF" % filename)

        if not quiet and not warnings and not errors:
            headers_size = min(
                details["data_offsets"][k] for k in details["data_offsets"]
            )
            if headers_size == 0:
                headers_size = gdal.VSIStatL(filename).size
            print("\nThe size of all IFD headers is %d bytes" % headers_size)
    except ValidateCloudOptimizedGeoTIFFException as e:
        if not quiet:
            print("%s is NOT a valid cloud optimized GeoTIFF : %s" % (filename, str(e)))
        ret = 1

    return ret


if __name__ == "__main__":
    sys.exit(main(sys.argv))