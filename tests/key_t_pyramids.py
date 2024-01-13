import hazelbean as hb
import os
import numpy as np


delete_on_finish = True

global_1deg_raster_path = 'data/global_1deg_floats.tif'
zones_vector_path = "data/countries_iso3.gpkg"
zone_ids_raster_path = "data/country_ids_300sec.tif"
zone_values_path = "data/ha_per_cell_300sec.tif"
change_in_carbon_path = "data/change_in_carbon_300sec.tif"

output_dir = 'data'


hb.load_geotiff_chunk_by_cr_size(global_1deg_raster_path, (1, 2, 5, 5))

input_path = zone_values_path
left_lat = -40
bottom_lon = -25
lat_size = .2
lon_size = 1
bb = [left_lat,
        bottom_lon,
        left_lat + lat_size,
        bottom_lon + lon_size]

hb.load_geotiff_chunk_by_bb(input_path, bb)

incomplete_array = hb.load_geotiff_chunk_by_bb(global_1deg_raster_path, [-180, -80, 180, 70])
temp_path = hb.temp('.tif', 'test_add_rows_or_cols_to_geotiff', delete_on_finish, output_dir)


geotransform_override = hb.get_raster_info_hb(global_1deg_raster_path)['geotransform']
geotransform_override = [-180, 1, 0, 80, 0, -1]
n_rows_override = 150

hb.save_array_as_geotiff(incomplete_array, temp_path, global_1deg_raster_path, geotransform_override=geotransform_override, n_rows_override=n_rows_override)
r_above, r_below, c_above, c_below = 10, 20, 0, 0


incomplete_array = hb.load_geotiff_chunk_by_bb(global_1deg_raster_path, [-180, -80, 180, 70])
# TODO Here is an interesting starting point to assess the question of how to generalize AF as flex inputs. For now it is path based.


temp_path = hb.temp('.tif', 'test_add_rows_or_cols_to_geotiff', delete_on_finish, output_dir)
geotransform_override = hb.get_raster_info_hb(global_1deg_raster_path)['geotransform']
geotransform_override = [-180, 1, 0, 80, 0, -1]
n_rows_override = 150

hb.save_array_as_geotiff(incomplete_array, temp_path, global_1deg_raster_path, geotransform_override=geotransform_override, n_rows_override=n_rows_override)


temp_path = hb.temp('.tif', 'expand_to_bounding_box', delete_on_finish, output_dir)




incomplete_array = hb.load_geotiff_chunk_by_bb(global_1deg_raster_path, [-180, -80, 180, 70])
# TODO Here is an interesting starting point to assess the question of how to generalize AF as flex inputs. For now it is path based.

temp_path = hb.temp('.tif', 'test_add_rows_or_cols_to_geotiff', delete_on_finish, output_dir)

geotransform_override = hb.get_raster_info_hb(global_1deg_raster_path)['geotransform']
geotransform_override = [-180, 1, 0, 80, 0, -1]
n_rows_override = 150

hb.save_array_as_geotiff(incomplete_array, temp_path, global_1deg_raster_path, geotransform_override=geotransform_override, n_rows_override=n_rows_override)

temp2_path = hb.temp('.tif', 'expand_to_bounding_box', delete_on_finish, output_dir)

hb.fill_to_match_extent(temp_path, global_1deg_raster_path, temp2_path)



        # hb.make_path_global_pyramid(r"C:\Files\Research\hazelbean\hazelbean_dev\tests\data\crop_harvested_area_fraction.tif", verbose=False)
hb.make_path_global_pyramid(global_1deg_raster_path, verbose=False)


# Remove auxiliary files so that we can test regenerating them.
hb.remove_path(zone_values_path + '.aux.xml')
hb.remove_path(zone_values_path + '.ovr')
# Remove auxiliary files so that we can test regenerating them.
hb.remove_path(global_1deg_raster_path + '.aux.xml')
hb.remove_path(global_1deg_raster_path + '.ovr')

print('Test complete.')


