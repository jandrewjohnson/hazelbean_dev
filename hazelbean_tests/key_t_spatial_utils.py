import hazelbean as hb
import os, sys, time

# NOTE Awkward inclusion heere so that I don't have to run the test via a setup config each  time
sys.path.extend(['../..'])

import hazelbean as hb
import pandas as pd
import numpy as np

delete_on_finish = True


global_1deg_raster_path = 'data/global_1deg_floats.tif'
zones_vector_path = "data/countries_iso3.gpkg"
country_vector_path = "data/rwa.gpkg"
zone_ids_raster_path = "data/country_ids_300sec.tif"
zone_values_path = "data/ha_per_cell_300sec.tif"

output_dir = 'data'
output_path = hb.temp('.tif', 'clipped', delete_on_finish, output_dir)

hb.clip_raster_by_vector_simple(zone_values_path, 
                                 output_path, 
                                 country_vector_path, 
                                 output_data_type=6, 
                                 gtiff_creation_options=hb.DEFAULT_GTIFF_CREATION_OPTIONS)

print('Created', output_path)


output_path = hb.temp('.tif', 'clipped_attr', delete_on_finish, output_dir)

hb.clip_raster_by_vector_simple(zone_values_path, 
                                 output_path, 
                                 zones_vector_path, 
                                 output_data_type=6, 
                                 clip_vector_filter='ISO3="RWA"',
                                 
                                 gtiff_creation_options=hb.DEFAULT_GTIFF_CREATION_OPTIONS)

print('Created', output_path)





print('test comlete')
