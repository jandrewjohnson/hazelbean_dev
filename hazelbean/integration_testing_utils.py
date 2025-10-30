"""
Integration Testing Utilities for Hazelbean

Story 5: Integration Testing - Task 5.1 Implementation
Provides utilities for creating dummy rasters and tiling operations for integration testing.
"""

import os
import numpy as np
from osgeo import gdal, osr
import math
from typing import List, Tuple, Optional, Union
from datetime import datetime
import hazelbean as hb


def _import_epsg_with_fallback(srs, epsg_code):
    """
    Safely import EPSG code with WGS84 fallback.
    
    For EPSG:4326 (WGS84), uses SetWellKnownGeogCS() as fallback which doesn't 
    require proj.db. This provides resilience if proj.db is missing or inaccessible.
    
    Args:
        srs: osr.SpatialReference object
        epsg_code: EPSG code as int or string (e.g., 4326 or '4326')
        
    Raises:
        RuntimeError: If EPSG code cannot be imported and no fallback available
    """
    # Normalize to int
    if isinstance(epsg_code, str):
        if epsg_code.startswith('EPSG:'):
            epsg_int = int(epsg_code.split(':')[1])
        else:
            epsg_int = int(epsg_code)
    else:
        epsg_int = int(epsg_code)
    
    # Try standard import first
    try:
        srs.ImportFromEPSG(epsg_int)
        return
    except RuntimeError as e:
        # If proj.db error and WGS84, use fallback
        if "proj.db" in str(e) and epsg_int == 4326:
            srs.SetWellKnownGeogCS("WGS84")
            return
        # Otherwise re-raise
        raise


def create_dummy_raster(output_path: str, 
                       width: int, 
                       height: int, 
                       cell_size: float,
                       data_type: int = gdal.GDT_Float32,
                       fill_value: float = 0.0,
                       nodata_value: Optional[float] = None,
                       projection: str = 'EPSG:4326',
                       origin_x: float = -180.0,
                       origin_y: float = 90.0) -> str:
    """
    Create a dummy raster with uniform fill values for testing purposes.
    
    Args:
        output_path: Path where the raster will be saved
        width: Width in pixels
        height: Height in pixels  
        cell_size: Size of each pixel in projection units
        data_type: GDAL data type (default: Float32)
        fill_value: Value to fill all pixels with
        nodata_value: NoData value (if None, no NoData is set)
        projection: Spatial reference system (default: WGS84)
        origin_x: X coordinate of top-left corner
        origin_y: Y coordinate of top-left corner
        
    Returns:
        Path to created raster file
    """
    # Create the output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Create the dataset
    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(output_path, width, height, 1, data_type, 
                           options=['COMPRESS=DEFLATE', 'TILED=YES'])
    
    if dataset is None:
        raise RuntimeError(f"Could not create raster at {output_path}")
    
    # Set geotransform (origin_x, pixel_width, 0, origin_y, 0, -pixel_height)
    geotransform = (origin_x, cell_size, 0, origin_y, 0, -cell_size)
    dataset.SetGeoTransform(geotransform)
    
    # Set projection
    srs = osr.SpatialReference()
    epsg_code = 4326 if projection == 'EPSG:4326' else int(projection.split(':')[1])
    _import_epsg_with_fallback(srs, epsg_code)
    dataset.SetProjection(srs.ExportToWkt())
    
    # Get the band and set nodata value if specified
    band = dataset.GetRasterBand(1)
    if nodata_value is not None:
        band.SetNoDataValue(nodata_value)
    
    # Create array with fill values
    array = np.full((height, width), fill_value, dtype=np.float32 if data_type == gdal.GDT_Float32 else np.float64)
    
    # Write the array to the band
    band.WriteArray(array)
    
    # Calculate statistics
    band.ComputeStatistics(False)
    
    # Clean up
    band = None
    dataset = None
    
    return output_path


def create_dummy_raster_with_pattern(output_path: str,
                                   width: int,
                                   height: int,
                                   pattern_type: str = 'gradient',
                                   cell_size: float = 1.0,
                                   data_type: int = gdal.GDT_Float32,
                                   nodata_value: Optional[float] = None,
                                   projection: str = 'EPSG:4326',
                                   origin_x: float = -180.0,
                                   origin_y: float = 90.0) -> str:
    """
    Create a dummy raster with mathematical patterns for predictable testing.
    
    Args:
        output_path: Path where the raster will be saved
        width: Width in pixels
        height: Height in pixels
        pattern_type: Type of pattern ('gradient', 'checkerboard', 'concentric', 'random_seed')
        cell_size: Size of each pixel in projection units
        data_type: GDAL data type
        nodata_value: NoData value (if None, no NoData is set)
        projection: Spatial reference system
        origin_x: X coordinate of top-left corner
        origin_y: Y coordinate of top-left corner
        
    Returns:
        Path to created raster file
    """
    # Create the output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Generate pattern array based on type
    if pattern_type == 'gradient':
        # Vertical gradient (row index values)
        array = np.zeros((height, width), dtype=np.float32)
        for i in range(height):
            array[i, :] = i
            
    elif pattern_type == 'checkerboard':
        # Checkerboard pattern
        array = np.zeros((height, width), dtype=np.float32)
        for i in range(height):
            for j in range(width):
                array[i, j] = 1.0 if (i + j) % 2 == 0 else 0.0
                
    elif pattern_type == 'concentric':
        # Concentric circles from center
        center_x, center_y = width // 2, height // 2
        array = np.zeros((height, width), dtype=np.float32)
        for i in range(height):
            for j in range(width):
                distance = math.sqrt((j - center_x)**2 + (i - center_y)**2)
                array[i, j] = distance
                
    elif pattern_type == 'random_seed':
        # Reproducible random pattern using fixed seed
        np.random.seed(42)  # Fixed seed for reproducibility
        array = np.random.rand(height, width).astype(np.float32) * 100
        
    else:
        raise ValueError(f"Unknown pattern type: {pattern_type}")
    
    # Create the dataset
    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(output_path, width, height, 1, data_type,
                           options=['COMPRESS=DEFLATE', 'TILED=YES'])
    
    if dataset is None:
        raise RuntimeError(f"Could not create raster at {output_path}")
    
    # Set geotransform
    geotransform = (origin_x, cell_size, 0, origin_y, 0, -cell_size)
    dataset.SetGeoTransform(geotransform)
    
    # Set projection
    srs = osr.SpatialReference()
    epsg_code = 4326 if projection == 'EPSG:4326' else int(projection.split(':')[1])
    _import_epsg_with_fallback(srs, epsg_code)
    dataset.SetProjection(srs.ExportToWkt())
    
    # Get the band and set nodata value if specified
    band = dataset.GetRasterBand(1)
    if nodata_value is not None:
        band.SetNoDataValue(nodata_value)
    
    # Write the array to the band
    band.WriteArray(array)
    
    # Calculate statistics
    band.ComputeStatistics(False)
    
    # Clean up
    band = None
    dataset = None
    
    return output_path


def create_dummy_raster_with_known_sum(output_path: str,
                                     width: int,
                                     height: int,
                                     target_sum: float,
                                     cell_size: float = 1.0,
                                     data_type: int = gdal.GDT_Float32,
                                     nodata_value: Optional[float] = None,
                                     distribution: str = 'uniform',
                                     projection: str = 'EPSG:4326',
                                     origin_x: float = -180.0,
                                     origin_y: float = 90.0) -> str:
    """
    Create a dummy raster with a predetermined total sum for validation testing.
    
    Args:
        output_path: Path where the raster will be saved
        width: Width in pixels
        height: Height in pixels
        target_sum: Desired total sum of all pixel values
        cell_size: Size of each pixel in projection units
        data_type: GDAL data type
        nodata_value: NoData value (if None, no NoData is set)
        distribution: How to distribute values ('uniform', 'linear', 'exponential')
        projection: Spatial reference system
        origin_x: X coordinate of top-left corner
        origin_y: Y coordinate of top-left corner
        
    Returns:
        Path to created raster file
    """
    # Create the output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    total_pixels = width * height
    
    # Generate value distribution based on type
    if distribution == 'uniform':
        # All pixels have same value
        value_per_pixel = target_sum / total_pixels
        array = np.full((height, width), value_per_pixel, dtype=np.float32)
        
    elif distribution == 'linear':
        # Linear distribution from 1 to some max value
        # Sum of 1,2,3,...,n = n(n+1)/2
        # We want sum = target_sum, so scale accordingly
        indices = np.arange(1, total_pixels + 1, dtype=np.float32)
        natural_sum = np.sum(indices)
        scale_factor = target_sum / natural_sum
        values = indices * scale_factor
        array = values.reshape((height, width))
        
    elif distribution == 'exponential':
        # Exponential distribution scaled to target sum
        # Use fixed seed for reproducibility
        np.random.seed(123)
        raw_values = np.random.exponential(1.0, (height, width)).astype(np.float32)
        current_sum = np.sum(raw_values)
        scale_factor = target_sum / current_sum
        array = raw_values * scale_factor
        
    else:
        raise ValueError(f"Unknown distribution type: {distribution}")
    
    # Verify sum is correct (within floating point precision)
    actual_sum = np.sum(array)
    if abs(actual_sum - target_sum) > 1e-6:
        # Adjust the last pixel to ensure exact sum
        correction = target_sum - actual_sum
        array[-1, -1] += correction
    
    # Create the dataset
    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(output_path, width, height, 1, data_type,
                           options=['COMPRESS=DEFLATE', 'TILED=YES'])
    
    if dataset is None:
        raise RuntimeError(f"Could not create raster at {output_path}")
    
    # Set geotransform
    geotransform = (origin_x, cell_size, 0, origin_y, 0, -cell_size)
    dataset.SetGeoTransform(geotransform)
    
    # Set projection
    srs = osr.SpatialReference()
    epsg_code = 4326 if projection == 'EPSG:4326' else int(projection.split(':')[1])
    _import_epsg_with_fallback(srs, epsg_code)
    dataset.SetProjection(srs.ExportToWkt())
    
    # Get the band and set nodata value if specified
    band = dataset.GetRasterBand(1)
    if nodata_value is not None:
        band.SetNoDataValue(nodata_value)
    
    # Write the array to the band
    band.WriteArray(array)
    
    # Calculate statistics
    band.ComputeStatistics(False)
    
    # Clean up
    band = None
    dataset = None
    
    return output_path


def tile_raster_into_grid(input_raster_path: str,
                         output_dir: str,
                         tile_size: int,
                         overlap: int = 0,
                         nodata_value: Optional[float] = None) -> List[str]:
    """
    Tile a raster into a grid of smaller rasters for parallel processing and validation.
    
    Args:
        input_raster_path: Path to input raster to be tiled
        output_dir: Directory where tiles will be saved
        tile_size: Size of tiles in pixels (square tiles)
        overlap: Overlap between tiles in pixels
        nodata_value: NoData value for output tiles (auto-detected if None)
        
    Returns:
        List of paths to created tile files
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Open input raster
    dataset = gdal.Open(input_raster_path, gdal.GA_ReadOnly)
    if dataset is None:
        raise RuntimeError(f"Could not open input raster: {input_raster_path}")
    
    # Get raster properties
    width = dataset.RasterXSize
    height = dataset.RasterYSize
    geotransform = dataset.GetGeoTransform()
    projection = dataset.GetProjection()
    band = dataset.GetRasterBand(1)
    
    # Auto-detect nodata if not provided
    if nodata_value is None:
        nodata_value = band.GetNoDataValue()
    
    data_type = band.DataType
    
    # Calculate number of tiles
    tiles_x = math.ceil(width / tile_size)
    tiles_y = math.ceil(height / tile_size)
    
    tile_paths = []
    
    # Generate tiles
    for tile_y in range(tiles_y):
        for tile_x in range(tiles_x):
            # Calculate tile boundaries
            x_offset = tile_x * tile_size
            y_offset = tile_y * tile_size
            
            # Handle edge tiles that might be smaller
            tile_width = min(tile_size, width - x_offset)
            tile_height = min(tile_size, height - y_offset)
            
            if tile_width <= 0 or tile_height <= 0:
                continue
            
            # Read tile data
            tile_array = band.ReadAsArray(x_offset, y_offset, tile_width, tile_height)
            if tile_array is None:
                continue
            
            # Create tile filename
            tile_filename = f"tile_{tile_y:04d}_{tile_x:04d}.tif"
            tile_path = os.path.join(output_dir, tile_filename)
            
            # Create tile dataset
            driver = gdal.GetDriverByName('GTiff')
            tile_dataset = driver.Create(tile_path, tile_width, tile_height, 1, data_type,
                                       options=['COMPRESS=DEFLATE', 'TILED=YES'])
            
            if tile_dataset is None:
                continue
            
            # Calculate tile geotransform
            tile_origin_x = geotransform[0] + x_offset * geotransform[1]
            tile_origin_y = geotransform[3] + y_offset * geotransform[5]
            tile_geotransform = (tile_origin_x, geotransform[1], geotransform[2],
                               tile_origin_y, geotransform[4], geotransform[5])
            
            tile_dataset.SetGeoTransform(tile_geotransform)
            tile_dataset.SetProjection(projection)
            
            # Write tile data
            tile_band = tile_dataset.GetRasterBand(1)
            if nodata_value is not None:
                tile_band.SetNoDataValue(nodata_value)
            
            tile_band.WriteArray(tile_array)
            tile_band.ComputeStatistics(False)
            
            # Clean up tile
            tile_band = None
            tile_dataset = None
            
            tile_paths.append(tile_path)
    
    # Clean up
    band = None
    dataset = None
    
    return tile_paths


def validate_tiling_sum_conservation(original_raster_path: str,
                                   tile_paths: List[str],
                                   tolerance: float = 1e-6) -> dict:
    """
    Validate that tiling operation conserved the total sum of pixel values.
    
    Args:
        original_raster_path: Path to original raster
        tile_paths: List of tile file paths
        tolerance: Acceptable difference between original and tiled sums
        
    Returns:
        Dictionary with validation results
    """
    # Get original sum
    original_array = hb.as_array(original_raster_path)
    original_nodata = hb.get_ndv_from_path(original_raster_path)
    
    if original_nodata is not None:
        valid_original = original_array[original_array != original_nodata]
    else:
        valid_original = original_array.flatten()
    
    original_sum = np.sum(valid_original)
    
    # Calculate sum from tiles
    tiles_sum = 0.0
    valid_tiles = 0
    invalid_tiles = []
    
    for tile_path in tile_paths:
        if not os.path.exists(tile_path):
            invalid_tiles.append(tile_path)
            continue
            
        try:
            tile_array = hb.as_array(tile_path)
            tile_nodata = hb.get_ndv_from_path(tile_path)
            
            if tile_nodata is not None:
                valid_tile_data = tile_array[tile_array != tile_nodata]
            else:
                valid_tile_data = tile_array.flatten()
            
            tiles_sum += np.sum(valid_tile_data)
            valid_tiles += 1
            
        except Exception as e:
            invalid_tiles.append(f"{tile_path}: {str(e)}")
    
    # Calculate validation metrics
    sum_difference = abs(tiles_sum - original_sum)
    relative_error = sum_difference / original_sum if original_sum != 0 else float('inf')
    is_valid = sum_difference <= tolerance
    
    return {
        'original_sum': float(original_sum),
        'tiles_sum': float(tiles_sum),
        'sum_difference': float(sum_difference),
        'relative_error': float(relative_error),
        'tolerance': float(tolerance),
        'is_valid': bool(is_valid),
        'valid_tiles': int(valid_tiles),
        'total_tiles': len(tile_paths),
        'invalid_tiles': invalid_tiles,
        'original_pixels': len(valid_original),
        'validation_timestamp': datetime.now().isoformat()
    }
