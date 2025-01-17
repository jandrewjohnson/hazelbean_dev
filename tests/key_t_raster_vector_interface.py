import hazelbean as hb
from hazelbean import raster_vector_interface
import os, sys, time

# # NOTE Awkward inclusion heere so that I don't have to run the test via a setup config each  time
# sys.path.extend(['../..'])

import hazelbean as hb
import pandas as pd
import numpy as np

delete_on_finish = False


global_1deg_raster_path = 'data/global_1deg_floats.tif'
zones_vector_path = "data/countries_iso3.gpkg"
zone_ids_raster_path = "data/country_ids_300sec.tif"
zone_values_path = "data/ha_per_cell_300sec.tif"

output_dir = 'data'


# raster_vector_interface.raster_to_polygon(input_raster_path, output_vector_path, id_label, dissolve_on_id=True)
input_vector_path = zones_vector_path
id_column_label = 'id'
blur_size = 300.0 
output_path = 'simplified_vector.gpkg'
raster_vector_interface.vector_super_simplify(input_vector_path, id_column_label, blur_size, output_path, remove_temp_files=True)




print('test comlete')
