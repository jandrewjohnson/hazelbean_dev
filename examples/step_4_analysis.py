"""
Step 4: Spatial Analysis and Multi-Raster Operations
Learning Time: 20 minutes
Prerequisites: Completed steps 1-3

Learn advanced spatial analysis including combining multiple rasters,
spatial calculations, and using Hazelbean's raster calculator for 
complex geospatial modeling workflows.
"""

import os
import hazelbean as hb
import numpy as np
from osgeo import gdal

def main():
    """
    Demonstrates spatial analysis and multi-raster operations.
    """
    
    # Initialize project (builds on previous steps)
    p = hb.ProjectFlow('hazelbean_tutorial')
    
    print("=== Hazelbean Spatial Analysis Demo ===")
    print()
    
    # Try to find multiple sample rasters for analysis
    raster_paths = []
    for filename in ['tests/ee_r264_ids_900sec.tif', 'pyramids/ha_per_cell_900sec.tif']:
        try:
            path = p.get_path(filename)
            if hb.path_exists(path):
                raster_paths.append(path)
                print(f"✓ Found: {os.path.basename(path)}")
            else:
                print(f"✗ Not found: {filename} (path located but file missing)")
        except:
            print(f"✗ Not found: {filename}")
    
    if len(raster_paths) >= 2:
        print()
        print("=== Multi-Raster Analysis ===")
        
        # Load multiple rasters as arrays
        array1 = hb.as_array(raster_paths[0])
        array2 = hb.as_array(raster_paths[1])
        
        print(f"Raster 1 shape: {array1.shape}")
        print(f"Raster 2 shape: {array2.shape}")
        
        # If shapes don't match, work with a subset
        if array1.shape != array2.shape:
            print("Shapes don't match - using smaller common area")
            min_rows = min(array1.shape[0], array2.shape[0])
            min_cols = min(array1.shape[1], array2.shape[1])
            array1 = array1[:min_rows, :min_cols]
            array2 = array2[:min_rows, :min_cols]
            print(f"Cropped to shape: {array1.shape}")
        
        # Spatial operations between rasters
        print()
        print("=== Raster Calculations ===")
        
        # Addition
        sum_array = array1 + array2
        print(f"Sum - Min: {np.nanmin(sum_array):.2f}, Max: {np.nanmax(sum_array):.2f}")
        
        # Ratio (with division by zero protection)
        with np.errstate(divide='ignore', invalid='ignore'):
            ratio_array = np.divide(array1, array2, 
                                  out=np.zeros_like(array1), 
                                  where=(array2 != 0))
        print(f"Ratio - Min: {np.nanmin(ratio_array):.2f}, Max: {np.nanmax(ratio_array):.2f}")
        
        # Conditional analysis
        overlap_mask = (array1 > 0) & (array2 > 0)
        overlap_pixels = np.sum(overlap_mask)
        print(f"Overlapping pixels: {overlap_pixels} ({overlap_pixels/array1.size*100:.1f}%)")
        
    else:
        print()
        print("=== Single Raster Analysis (Synthetic Data) ===")
        
        # Create synthetic landscape for analysis
        rows, cols = 100, 100
        
        # Elevation-like surface
        x = np.linspace(0, 10, cols)
        y = np.linspace(0, 10, rows)
        X, Y = np.meshgrid(x, y)
        elevation = 100 + 50 * np.sin(X) + 30 * np.cos(Y) + np.random.normal(0, 5, (rows, cols))
        
        # Land cover categories
        landcover = np.random.choice([1, 2, 3, 4, 5], size=(rows, cols), 
                                   p=[0.3, 0.2, 0.2, 0.2, 0.1])
        
        print(f"Created synthetic landscape: {elevation.shape}")
        print(f"Elevation range: {elevation.min():.1f} to {elevation.max():.1f}")
        
        array1, array2 = elevation, landcover
    
    # Spatial analysis calculations
    print()
    print("=== Spatial Analysis Calculations ===")
    
    # Zone-based statistics
    if array2 is not None:
        unique_zones = np.unique(array2)
        print(f"Analysis zones: {len(unique_zones)} unique values")
        
        for zone in unique_zones[:5]:  # Show first 5 zones
            mask = array2 == zone
            zone_values = array1[mask]
            if len(zone_values) > 0:
                print(f"  Zone {zone}: {len(zone_values)} pixels, "
                      f"mean={np.mean(zone_values):.2f}")
    
    # Distance and neighborhood analysis (simplified)
    print()
    print("=== Neighborhood Analysis ===")
    
    # Simple moving window (3x3) mean
    from scipy import ndimage
    window_mean = ndimage.uniform_filter(array1.astype(float), size=3)
    
    print(f"Original mean: {np.nanmean(array1):.2f}")
    print(f"Smoothed mean: {np.nanmean(window_mean):.2f}")
    print(f"Smoothing effect: {np.nanmean(np.abs(array1 - window_mean)):.2f}")
    
    # Hot spot identification (values > 2 std dev above mean)
    threshold = np.nanmean(array1) + 2 * np.nanstd(array1)
    hotspots = array1 > threshold
    n_hotspots = np.sum(hotspots)
    
    print()
    print("=== Spatial Pattern Analysis ===")
    print(f"Hot spot threshold: {threshold:.2f}")
    print(f"Hot spot pixels: {n_hotspots} ({n_hotspots/array1.size*100:.1f}%)")
    
    # Save analysis results to intermediate directory
    # Ensure intermediate directory exists
    os.makedirs(p.intermediate_dir, exist_ok=True)
    output_path = os.path.join(p.intermediate_dir, 'analysis_summary.txt')
    with open(output_path, 'w') as f:
        f.write("Spatial Analysis Summary\n")
        f.write("========================\n")
        f.write(f"Input shape: {array1.shape}\n")
        f.write(f"Value range: {np.nanmin(array1):.2f} to {np.nanmax(array1):.2f}\n")
        f.write(f"Mean: {np.nanmean(array1):.2f}\n")
        f.write(f"Hot spots: {n_hotspots} pixels\n")
    
    print(f"✓ Analysis summary saved: {output_path}")
    
    print()
    print("🎉 Spatial analysis complete!")
    print("Next: Run step_5_export_results.py to learn about saving outputs")


if __name__ == "__main__":
    main()
