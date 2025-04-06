import os
import pathlib
from osgeo import gdal
import numpy as np
import tqdm

import hazelbean as hb
from hazelbean.pog import *


def is_path_pog(path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False):
    
    is_pyramid = hb.is_path_global_pyramid(path, verbose=True)
    is_cog = hb.is_path_cog(path, check_tiled=check_tiled, full_check=full_check, raise_exceptions=raise_exceptions, verbose=verbose)

    return is_pyramid and is_cog

  
def make_path_pog(input_raster_path, output_raster_path=None, output_data_type=None, ndv=None, overview_resampling_method=None, compression="ZSTD", blocksize=512, verbose=False):
    """ Create a Pog (pyramidal cog) from input_raster_path. Writes in-place if output_raster_path is not set. Chooses correct values for 
    everything else if not set."""
    
    # Check if input exists
    if not hb.path_exists(input_raster_path, verbose=verbose):
        raise FileNotFoundError(f"Input raster does not exist: {input_raster_path} at abs path {hb.path_abs(input_raster_path)}")
    
    if is_path_pog(input_raster_path, verbose):
        hb.log(f"Raster is already a POG: {input_raster_path}")
        
        return
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
    degrees = hb.get_cell_size_from_path(temp_copy_path, force_to_pyramid=True)

    arcseconds = hb.get_cell_size_from_path_in_arcseconds(temp_copy_path, force_to_pyramid=True)
    
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
        
    if not hb.raster_path_has_stats(temp_copy_path, approx_ok=False):
        hb.add_stats_to_geotiff_with_gdal(temp_copy_path, approx_ok=False, force=True, verbose=verbose)
    
    # Open the source raster in UPDATE MODE so it writes the overviews as internal
    # gdal.PushErrorHandler('CPLQuietErrorHandler')
    src_ds = gdal.OpenEx(temp_copy_path, gdal.GA_Update)
    # gdal.PopErrorHandler()
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

    if not is_path_pog(output_raster_path, verbose=verbose) and verbose:
        hb.log(f"Failed to create COG: {output_raster_path} at abs path {hb.path_abs(output_raster_path)}")


    
def write_pog_of_value_from_scratch(output_path, value, arcsecond_resolution, output_data_type, ndv=None, overview_resampling_method=None, compression='ZSTD', blocksize='512', verbose=False):
    # Define creation options for COG
    precog_gtiff_creation_options = [
        f"COMPRESS={compression}",
        f"BLOCKXSIZE={str(blocksize)}",  
        f"BLOCKYSIZE={str(blocksize)}",  
        f"BIGTIFF=YES", 
        "TILED=YES",
    ]

        
    if ndv is None:
        ndv = hb.no_data_values_by_gdal_type[output_data_type][0] 

    if overview_resampling_method is None:
            overview_resampling_method = hb.pyramid_resampling_algorithms_by_data_type[output_data_type] 

    geotransform = hb.pyramid_compatible_geotransforms[float(arcsecond_resolution)]
    projection = hb.wgs_84_wkt
    x_size = hb.pyramid_compatable_shapes[float(arcsecond_resolution)][0]
    y_size = hb.pyramid_compatable_shapes[float(arcsecond_resolution)][1]

    
    # Make a temp geotiff based on match
    temp_path = hb.temp('.tif', filename_start='temp_gtiff_b4_cog', remove_at_exit=True)
    driver = gdal.GetDriverByName('GTiff')
    tmp_ds = driver.Create(temp_path, x_size, y_size, 1, output_data_type, options=precog_gtiff_creation_options)
    tmp_ds.SetGeoTransform(geotransform)
    tmp_ds.SetProjection(projection)    
    
    # Memory safe (hopefully) way to write the value to the raster, row by row
    value_row = np.full((1, x_size), value, dtype=hb.gdal_number_to_numpy_type[output_data_type])

    # Initialize accumulators for statistics
    total_sum = 0.0
    total_sq_sum = 0.0
    total_count = 0
    global_min = np.inf
    global_max = -np.inf        
    
    band = tmp_ds.GetRasterBand(1)
    for row in tqdm.tqdm(range(y_size)):
        # hb.print_in_place('Writing row ' + str(row) + ' of ' + str(y_size))
        band.WriteArray(value_row, xoff=0, yoff=row)
      
        # Update statistics incrementally
        total_sum += value_row.sum()
        total_sq_sum += np.square(value_row).sum()
        total_count += value_row.size
        global_min = min(global_min, np.min(value_row))
        global_max = max(global_max, np.max(value_row))    

    mean = total_sum / total_count if total_count else 0
    variance = (total_sq_sum / total_count - mean ** 2) if total_count else 0
    variance = max(variance, 0)  # safeguard against negative variance
    stddev = np.sqrt(variance)

    # Set statistics directly
    # bTODOO ensure this works with ints   
    band.SetStatistics(float(global_min), float(global_max), float(mean), float(stddev))
        
    # Build Overviews
    tmp_ds.GetRasterBand(1).SetNoDataValue(ndv)    
    tmp_ds.BuildOverviews(None, []) # Remove existing overviews (if any) 
    
    resampling_algorithm = hb.pyramid_resampling_algorithms_by_data_type[output_data_type]    
    if overview_resampling_method is None:
        overview_resampling_method = resampling_algorithm
    
    # Set the overview levels based on the pyramid arcseconds
    overview_levels = hb.pyramid_compatible_overview_levels[arcsecond_resolution]
    tmp_ds.BuildOverviews(overview_resampling_method.upper(), overview_levels, callback=hb.make_gdal_callback('Building overviews for ' + str(output_path)))
    
    tmp_ds.FlushCache()
    del tmp_ds  # Close temp dataset

    # Step 2: Convert temporary GTiff to COG using CreateCopy
    cog_driver = gdal.GetDriverByName('COG')
    cog_creation_options = [
        f'COMPRESS={compression}',
        f'BLOCKSIZE={blocksize}',
        'BIGTIFF=YES',
        # 'OVERVIEWS=IGNORE_EXISTING'
    ]

    tmp_ds = gdal.Open(temp_path)
    cog_ds = cog_driver.CreateCopy(output_path, tmp_ds, options=cog_creation_options)

    if cog_ds is None:
        raise RuntimeError('Failed to create COG dataset.')

    # Cleanup
    del cog_ds
    del tmp_ds


def write_pog_of_value_from_match(output_path, match_path, value, output_data_type=None, ndv=None, overview_resampling_method=None, compression='ZSTD', blocksize='512', verbose=False):
    
    # Define creation options for COG
    precog_gtiff_creation_options = [
        f"COMPRESS={compression}",
        f"BLOCKXSIZE={str(blocksize)}",  
        f"BLOCKYSIZE={str(blocksize)}",  
        f"BIGTIFF=YES", 
        f"TILED=YES", 
    ]
    
    # Check if match exists
    if not hb.path_exists(match_path, verbose=verbose):
        raise FileNotFoundError(f"Input raster does not exist: {match_path} at abs path {hb.path_abs(match_path)}")
    
    if output_data_type is None:
        output_data_type = hb.get_datatype_from_uri(match_path)
        
    if ndv is None:
        ndv = hb.no_data_values_by_gdal_type[output_data_type][0] 

    if overview_resampling_method is None:
            overview_resampling_method = hb.pyramid_resampling_algorithms_by_data_type[output_data_type] 
            
    # Open existing raster to match
    src_ds = gdal.Open(match_path)
    geotransform = src_ds.GetGeoTransform()
    projection = src_ds.GetProjection()
    x_size = src_ds.RasterXSize
    y_size = src_ds.RasterYSize
    degrees = hb.get_cell_size_from_path(match_path)
    arcseconds = hb.get_cell_size_from_path_in_arcseconds(match_path)        
    
    # Make a temp geotiff based on match
    temp_path = hb.temp('.tif', filename_start='temp_gtiff_b4_cog', remove_at_exit=True)
    driver = gdal.GetDriverByName('GTiff')
    tmp_ds = driver.Create(temp_path, x_size, y_size, 1, output_data_type, options=precog_gtiff_creation_options)
    tmp_ds.SetGeoTransform(geotransform)
    tmp_ds.SetProjection(projection)    
    
    # Memory safe (hopefully) way to write the value to the raster, row by row
    value_row = np.full((1, x_size), value, dtype=hb.gdal_number_to_numpy_type[output_data_type])

    # Initialize accumulators for statistics
    total_sum = 0.0
    total_sq_sum = 0.0
    total_count = 0
    global_min = np.inf
    global_max = -np.inf        
    
    band = tmp_ds.GetRasterBand(1)
    for row in tqdm.tqdm(range(y_size)):
        # hb.print_in_place('Writing row ' + str(row) + ' of ' + str(y_size))
        band.WriteArray(value_row, xoff=0, yoff=row)
      
        # Update statistics incrementally
        total_sum += value_row.sum()
        total_sq_sum += np.square(value_row).sum()
        total_count += value_row.size
        global_min = min(global_min, np.min(value_row))
        global_max = max(global_max, np.max(value_row))    

    mean = total_sum / total_count if total_count else 0
    variance = (total_sq_sum / total_count - mean ** 2) if total_count else 0
    variance = max(variance, 0)  # safeguard against negative variance
    stddev = np.sqrt(variance)

    # Set statistics directly
    # bTODOO ensure this works with ints   
    band.SetStatistics(float(global_min), float(global_max), float(mean), float(stddev))
        
    # Build Overviews
    tmp_ds.GetRasterBand(1).SetNoDataValue(ndv)    
    tmp_ds.BuildOverviews(None, []) # Remove existing overviews (if any) 
    
    resampling_algorithm = hb.pyramid_resampling_algorithms_by_data_type[output_data_type]    
    if overview_resampling_method is None:
        overview_resampling_method = resampling_algorithm
    
    # Set the overview levels based on the pyramid arcseconds
    overview_levels = hb.pyramid_compatible_overview_levels[arcseconds]
    tmp_ds.BuildOverviews(overview_resampling_method.upper(), overview_levels, callback=hb.make_gdal_callback('Building overviews for ' + str(output_path)))
    
    tmp_ds.FlushCache()
    del tmp_ds  # Close temp dataset

    # Step 2: Convert temporary GTiff to COG using CreateCopy
    cog_driver = gdal.GetDriverByName('COG')
    cog_creation_options = [
        f'COMPRESS={compression}',
        f'BLOCKSIZE={blocksize}',
        'BIGTIFF=YES',
        'NUM_THREADS=ALL_CPUS',
        # 'OVERVIEWS=IGNORE_EXISTING'
    ]

    tmp_ds = gdal.Open(temp_path)
    cog_ds = cog_driver.CreateCopy(output_path, tmp_ds, options=cog_creation_options)

    if cog_ds is None:
        raise RuntimeError('Failed to create COG dataset.')

    # Cleanup
    del cog_ds
    del tmp_ds
    del src_ds

