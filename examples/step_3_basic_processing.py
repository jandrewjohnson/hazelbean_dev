"""
Step 3: Basic Raster Processing
Learning Time: 15 minutes
Prerequisites: Completed step_1_project_setup.py and step_2_data_loading.py

Learn fundamental raster operations including transformations, resampling,
and mathematical operations on geospatial data.
"""

import os
import hazelbean as hb
import numpy as np

def main():
    """
    Demonstrates basic raster processing operations.
    """
    
    # Initialize project (builds on previous steps)
    p = hb.ProjectFlow('hazelbean_tutorial')
    
    print("=== Hazelbean Basic Processing Demo ===")
    print()
    
    # Try to find sample data for processing
    try:
        input_path = p.get_path('tests/ee_r264_ids_900sec.tif')
        if hb.path_exists(input_path):
            has_sample_data = True
            print(f"✓ Using sample raster: {os.path.basename(input_path)}")
        else:
            raise FileNotFoundError("Path found but file doesn't exist")
    except:
        has_sample_data = False
        print("✗ Sample data not found, creating synthetic raster...")
    
    if has_sample_data:
        # Working with real data
        print()
        print("=== Basic Raster Information ===")
        info = hb.get_raster_info_hb(input_path)
        print(f"Original size: {info['raster_size']}")
        print(f"Pixel size: {info['pixel_size']}")
        
        # Create output path in intermediate directory
        processed_path = os.path.join(p.intermediate_dir, 'processed_raster.tif')
        
        print()
        print("=== Resampling Raster ===")
        # Resample to a different resolution (make pixels 2x larger)
        target_pixel_size = (info['pixel_size'][0] * 2, info['pixel_size'][1] * 2)
        
        try:
            hb.warp_raster(
                input_path,
                target_pixel_size,
                processed_path,
                resample_method='nearest'
            )
            
            # Check the result
            new_info = hb.get_raster_info_hb(processed_path)
            print(f"✓ Resampled raster created")
            print(f"New size: {new_info['raster_size']}")
            print(f"New pixel size: {new_info['pixel_size']}")
            
        except Exception as e:
            print(f"✗ Resampling failed: {e}")
            print("Continuing with array operations...")
        
        # Load and process array data
        print()
        print("=== Array-based Processing ===")
        array = hb.as_array(input_path)
        
    else:
        # Create synthetic data for demonstration
        print()
        print("=== Creating Synthetic Data ===")
        array = np.random.rand(50, 50) * 100
        processed_path = os.path.join(p.intermediate_dir, 'synthetic_processed.tif')
        
        print(f"Created {array.shape} array with values 0-100")
    
    # Mathematical operations on arrays
    print()
    print("=== Mathematical Operations ===")
    print(f"Original - Min: {np.nanmin(array):.2f}, Max: {np.nanmax(array):.2f}")
    
    # Apply some transformations
    # Scale values
    scaled_array = array * 2.0
    print(f"Scaled x2 - Min: {np.nanmin(scaled_array):.2f}, Max: {np.nanmax(scaled_array):.2f}")
    
    # Apply threshold
    threshold_array = np.where(array > np.nanmean(array), 1, 0)
    unique_values = np.unique(threshold_array)
    print(f"Threshold (mean={np.nanmean(array):.2f}) - Unique values: {unique_values}")
    
    # Calculate statistics
    print()
    print("=== Statistical Summary ===")
    print(f"Mean: {np.nanmean(array):.2f}")
    print(f"Standard deviation: {np.nanstd(array):.2f}")
    print(f"Non-zero pixels: {np.count_nonzero(array)}")
    print(f"Total pixels: {array.size}")
    
    print()
    print("🎉 Basic processing complete!")
    print("Next: Run step_4_analysis.py to learn spatial analysis workflows")


if __name__ == "__main__":
    main()
