"""
Step 2: Data Loading and File Discovery
Learning Time: 10 minutes
Prerequisites: Completed step_1_project_setup.py

Learn how to use Hazelbean's intelligent file discovery system (get_path) 
and load geospatial data for analysis.
"""

import hazelbean as hb
import numpy as np

def main():
    """
    Demonstrates intelligent file location and basic raster loading.
    """
    
    # Initialize project (builds on step 1)
    p = hb.ProjectFlow('hazelbean_tutorial')
    
    print("=== Hazelbean Data Loading Demo ===")
    print()
    
    # Demonstrate get_path() - Hazelbean's intelligent file finder
    print("=== Intelligent File Discovery with get_path() ===")
    
    # Try to find a test raster (get_path searches multiple locations)
    try:
        raster_path = p.get_path('tests/ee_r264_ids_900sec.tif')
        # Verify the file actually exists
        if hb.path_exists(raster_path):
            print(f"✓ Found raster: {raster_path}")
            found_raster = True
        else:
            raise FileNotFoundError("Path found but file doesn't exist")
    except:
        print("✗ Test raster not found, using alternative...")
        # Fallback to any available data
        try:
            raster_path = p.get_path('pyramids/ha_per_cell_900sec.tif')
            if hb.path_exists(raster_path):
                print(f"✓ Found alternative raster: {raster_path}")
                found_raster = True
            else:
                raise FileNotFoundError("Alternative path found but file doesn't exist")
        except:
            print("✗ No sample raster found in data directories")
            found_raster = False
    
    if found_raster:
        print()
        print("=== Loading and Examining Raster Data ===")
        
        # Load raster information without reading full data
        raster_info = hb.get_raster_info_hb(raster_path)
        
        print(f"Raster size: {raster_info['raster_size']} (width x height)")
        print(f"Pixel size: {raster_info['pixel_size']}")
        print(f"Number of bands: {raster_info['n_bands']}")
        print(f"Data type: {raster_info.get('datatype', 'Unknown')}")
        print(f"NoData value: {raster_info['ndv']}")
        
        # Load raster data as numpy array
        print()
        print("=== Loading Raster as Array ===")
        raster_array = hb.as_array(raster_path)
        
        print(f"Array shape: {raster_array.shape}")
        print(f"Array data type: {raster_array.dtype}")
        print(f"Min value: {np.nanmin(raster_array):.2f}")
        print(f"Max value: {np.nanmax(raster_array):.2f}")
        print(f"Mean value: {np.nanmean(raster_array):.2f}")
        
    else:
        print()
        print("=== Alternative: Create Sample Data ===")
        print("When sample data isn't available, you can create test arrays:")
        
        # Create a simple test array
        test_array = np.random.rand(100, 100) * 1000
        print(f"Created test array shape: {test_array.shape}")
        print(f"Test array range: {test_array.min():.1f} to {test_array.max():.1f}")
    
    print()
    print("🎉 Data loading complete!")
    print("Next: Run step_3_basic_processing.py to learn raster operations")


if __name__ == "__main__":
    main()
