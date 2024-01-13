import hazelbean as hb
import os, sys, time

# NOTE Awkward inclusion heere so that I don't have to run the test via a setup config each  time
sys.path.extend(['../..'])

import hazelbean as hb
import pandas as pd
import numpy as np

delete_on_finish = False


global_1deg_raster_path = 'data/global_1deg_floats.tif'
zones_vector_path = "data/countries_iso3.gpkg"
zone_ids_raster_path = "data/country_ids_300sec.tif"
zone_values_path = "data/ha_per_cell_300sec.tif"

output_dir = 'data'
output_path = hb.temp('.tif', 'resampled', delete_on_finish, output_dir)

hb.resample_to_match(zone_values_path, 
                     global_1deg_raster_path, 
                     output_path, 
                     resample_method='near',
                     output_data_type=6, 
                     src_ndv=None, 
                     ndv=None, 
                     compress=True,
                     calc_raster_stats=False,
                     add_overviews=False,
                     pixel_size_override=None)


output2_path = hb.temp('.tif', 'mask', delete_on_finish, output_dir)
hb.create_valid_mask_from_vector_path(zones_vector_path, global_1deg_raster_path, output2_path,
                                all_touched=True)

output3_path = hb.temp('.tif', 'masked', delete_on_finish, output_dir)
hb.set_ndv_by_mask_path(output_path, output2_path, output_path=output3_path, ndv=-9999.)







print('test comlete')
