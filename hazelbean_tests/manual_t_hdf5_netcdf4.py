import os
import hazelbean as hb
from hazelbean import netcdf
from hazelbean.netcdf import *

import pathlib
usr_dir = pathlib.Path.home()

country_ids_300sec_path = os.path.join(usr_dir, "Files/base_data/pyramids/country_ids_300sec.tif")

input_tif_path = os.path.join(r"C:\OneDrive\Projects\base_data\pyramids\country_ids_5m.tif"

input_nc_path = r"C:\OneDrive\Projects\base_data\luh2\raw_data\RCP26_SSP1\multiple-states_input4MIPs_landState_ScenarioMIP_UofMD-IMAGE-ssp126-2-1-f_gn_2015-2100.nc"
input_2_nc_path = r"C:\OneDrive\Projects\hazelbean\tests\data\tpw_v07r01_200910.nc4.nc.nc4"

output_raster_path = hb.temp('.nc', 'example_nc')
# hb.load_netcdf_as_array(input_nc_path)
# hb.create_netcdf_at_path(output_raster_path)
# hb.show_netcdf(input_2_nc_path)

# hb.dask_test(input_nc_path)

target_dir = r"C:\OneDrive\Projects\base_data\crops\earthstat\crop_production"
input_paths = hb.list_filtered_paths_recursively(target_dir, include_extensions='.tif', include_strings='_HarvestedAreaFraction')

# hb.combine_earthstat_tifs_to_nc(input_paths, output_nc_path)
output_nc_path = hb.temp('.nc', 'earthstat')
# hb.combine_earthstat_tifs_to_nc_new(input_paths, output_nc_path)

output_nc_path = hb.temp('.nc', 'pruned')
# hb.prune_nc_by_vars_list(input_nc_path, output_nc_path, ['primf', 'c3ann'])
output_nc_path = hb.temp('.nc', 'generated')
# hb.generate_nc_from_attributes(output_nc_path)

input_nc_path = r"C:\OneDrive\Projects\base_data\crops\earthstat_area_fraction.nc"
hb.netcdf.read_earthstat_nc_slice(input_nc_path, 'maize')
# hb.write_geotiff_as_netcdf(input_tif_path, output_raster_path)

# import glob
# import numpy as np
# from osgeo import gdal
# from concurrent.futures import ProcessPoolExecutor
#
# # Example file list; filenames should have some numeric date/year
# ordered_files = glob.glob('*.tiff')
# ordered_files.sort()
#
#
# # A function that maps whatever you want to do over each pixel;
# #   needs to be a global function so it can be pickled
# def do_something(array):
#     N = array.shape[0]
#     result = [my_function(array[i, ...]) for i in range(0, N)]
#     return result
#
#
# # Iterate through each file, combining them in order as a single array
# for i, each_file in enumerate(ordered_files):
#     # Open the file, read in as an array
#     ds = gdal.Open(each_file)
#     arr = ds.ReadAsArray()
#     ds = None
#     shp = arr.shape
#     arr_flat = arr.reshape((shp[0] * shp[1], 1))  # Ravel array to 1-D shape
#     if i == 0:
#         base_array = arr_flat  # The very first array is the base
#         continue  # Skip to the next year
#
#     # Stack the arrays from each year
#     base_array = np.concatenate((base_array, arr_flat), axis=1)
#
# # Break up the indices into (roughly) equal parts, e.g.,
# #   partitions = [(0, 1000), (1000, 2000), ..., (9000, 10001)]
# partitions = [...]
#
# # NUM_PROCESSES is however many cores you want to use
# with ProcessPoolExecutor(max_workers=NUM_PROCESSES) as executor:
#     result = executor.map(linear_trend, [
#         base_array[i:j, ...] for i, j in partitions
#     ])
#
# combined_results = list(result)  # List of array chunks...
# final = np.concatenate(regression, axis=0)  # ...Now a single array
# np.array(final).reshape((num_rows, num_cols))  # ...In the original shape