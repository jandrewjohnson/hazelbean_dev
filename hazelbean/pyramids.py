import os, logging, math, time, sys
import hazelbean as hb
from decimal import Decimal
import multiprocessing
import difflib
from rasterio.transform import rowcol
import rasterio

# Note, these four imports add about 1 second. but they're so universally used it's hard to avoid it
from osgeo import gdal, osr, ogr
import numpy as np
import pandas as pd
import geopandas as gpd
import tempfile
import subprocess

from hazelbean import cog
from hazelbean import config as hb_config

L = hb_config.get_logger('pyramids', logging_level='info')

# Define the resolutions compatible with pyramid calculation as key = arcseconds, value = resolution in 64 bit notation, precisely defined with the right amount of significant digits.
pyramid_compatible_arcseconds = [
    1.0,
    10.0,
    30.0,
    150.0,
    300.0,
    900.0,
    1800.0,
    3600.0,
    7200.0,
    14400.0,
    36000.0,
    ]
for i in pyramid_compatible_arcseconds.copy():
    pyramid_compatible_arcseconds.append(str(i))
    pyramid_compatible_arcseconds.append(int(i))
    pyramid_compatible_arcseconds.append(str(float(i)))   
    
    
pyramid_compatible_arcseconds_old = [
    10.0,
    30.0,
    300.0,
    900.0,
    1800.0,
    3600.0,
    7200.0,
    14400.0,
    36000.0,
    ]
for i in pyramid_compatible_arcseconds_old.copy():
    pyramid_compatible_arcseconds_old.append(str(i))
    pyramid_compatible_arcseconds_old.append(int(i))
    pyramid_compatible_arcseconds_old.append(str(float(i)))


pyramid_ha_per_cell_ref_paths = {}
pyramid_ha_per_cell_ref_paths[1.0] = os.path.join('pyramids', 'ha_per_cell_1sec.tif')
pyramid_ha_per_cell_ref_paths[10.0] = os.path.join('pyramids', 'ha_per_cell_10sec.tif')
pyramid_ha_per_cell_ref_paths[30.0] = os.path.join('pyramids', 'ha_per_cell_30sec.tif')
pyramid_ha_per_cell_ref_paths[150.0] = os.path.join('pyramids', 'ha_per_cell_150sec.tif')
pyramid_ha_per_cell_ref_paths[300.0] = os.path.join('pyramids', 'ha_per_cell_300sec.tif')
pyramid_ha_per_cell_ref_paths[900.0] = os.path.join('pyramids', 'ha_per_cell_900sec.tif')
pyramid_ha_per_cell_ref_paths[1800.0] = os.path.join('pyramids', 'ha_per_cell_1800sec.tif')
pyramid_ha_per_cell_ref_paths[3600.0] = os.path.join('pyramids', 'ha_per_cell_3600sec.tif')
pyramid_ha_per_cell_ref_paths[7200.0] = os.path.join('pyramids', 'ha_per_cell_7200sec.tif')
pyramid_ha_per_cell_ref_paths[14400.0] = os.path.join('pyramids', 'ha_per_cell_14400sec.tif')
pyramid_ha_per_cell_ref_paths[36000.0] = os.path.join('pyramids', 'ha_per_cell_36000sec.tif')
for k, v in pyramid_ha_per_cell_ref_paths.copy().items():
    pyramid_ha_per_cell_ref_paths[str(k)] = v
    pyramid_ha_per_cell_ref_paths[int(k)] = v
    pyramid_ha_per_cell_ref_paths[str(int(k))] = v


pyramid_match_ref_paths = {}
pyramid_match_ref_paths[1.0] = os.path.join('pyramids', 'match_1sec.tif')
pyramid_match_ref_paths[10.0] = os.path.join('pyramids', 'match_10sec.tif')
pyramid_match_ref_paths[30.0] = os.path.join('pyramids', 'match_30sec.tif')
pyramid_match_ref_paths[150.0] = os.path.join('pyramids', 'match_150sec.tif')
pyramid_match_ref_paths[300.0] = os.path.join('pyramids', 'match_300sec.tif')
pyramid_match_ref_paths[900.0] = os.path.join('pyramids', 'match_900sec.tif')
pyramid_match_ref_paths[1800.0] = os.path.join('pyramids', 'match_1800sec.tif')
pyramid_match_ref_paths[3600.0] = os.path.join('pyramids', 'match_3600sec.tif')
pyramid_match_ref_paths[7200.0] = os.path.join('pyramids', 'match_7200sec.tif')
pyramid_match_ref_paths[14400.0] = os.path.join('pyramids', 'match_14400sec.tif')
pyramid_match_ref_paths[36000.0] = os.path.join('pyramids', 'match_36000sec.tif')
for k, v in pyramid_match_ref_paths.copy().items():
    pyramid_match_ref_paths[str(k)] = v
    pyramid_match_ref_paths[int(k)] = v
    pyramid_match_ref_paths[str(int(k))] = v


ha_per_cell_column_1sec_ref_path = os.path.join('pyramids', 'ha_per_cell_column_1sec.tif')
ha_per_cell_column_10sec_ref_path = os.path.join('pyramids', 'ha_per_cell_column_10sec.tif')
ha_per_cell_column_30sec_ref_path = os.path.join('pyramids', 'ha_per_cell_column_30sec.tif')
ha_per_cell_column_150sec_ref_path = os.path.join('pyramids', 'ha_per_cell_column_150sec.tif')
ha_per_cell_column_300sec_ref_path = os.path.join('pyramids', 'ha_per_cell_column_300sec.tif')
ha_per_cell_column_900sec_ref_path = os.path.join('pyramids', 'ha_per_cell_column_900sec.tif')
ha_per_cell_column_1800sec_ref_path = os.path.join('pyramids', 'ha_per_cell_column_1800sec.tif')
ha_per_cell_column_3600sec_ref_path = os.path.join('pyramids', 'ha_per_cell_column_3600sec.tif')
ha_per_cell_column_7200sec_ref_path = os.path.join('pyramids', 'ha_per_cell_column_7200sec.tif')
ha_per_cell_column_14400sec_ref_path = os.path.join('pyramids', 'ha_per_cell_column_14400sec.tif')
ha_per_cell_column_36000sec_ref_path = os.path.join('pyramids', 'ha_per_cell_column_36000sec.tif')


pyramid_compatible_resolution_to_arcseconds = {}
pyramid_compatible_resolution_to_arcseconds[0.0002777777777777778] =    1.0
pyramid_compatible_resolution_to_arcseconds[0.002777777777777778] =    10.0
pyramid_compatible_resolution_to_arcseconds[0.008333333333333333] =    30.0
pyramid_compatible_resolution_to_arcseconds[0.008333333333333333 * 5] =    150.0
pyramid_compatible_resolution_to_arcseconds[0.08333333333333333] =   300.0
pyramid_compatible_resolution_to_arcseconds[0.25] =   900.0
pyramid_compatible_resolution_to_arcseconds[0.5] =  1800.0
pyramid_compatible_resolution_to_arcseconds[1.0] =  3600.0
pyramid_compatible_resolution_to_arcseconds[2.0] =  7200.0
pyramid_compatible_resolution_to_arcseconds[4.0] = 14400.0
pyramid_compatible_resolution_to_arcseconds[10.0] = 36000.0
for k, v in pyramid_compatible_resolution_to_arcseconds.copy().items():
    pyramid_compatible_resolution_to_arcseconds[str(k)] = v
    pyramid_compatible_resolution_to_arcseconds[int(k)] = v
    pyramid_compatible_resolution_to_arcseconds[str(int(k))] = v


pyramid_compatible_resolutions = {}
pyramid_compatible_resolutions[1.0] =     0.0002777777777777778 # 0002777777777777778, 0002777777777777777775
pyramid_compatible_resolutions[10.0] =    0.002777777777777778
pyramid_compatible_resolutions[30.0] =    0.008333333333333333
pyramid_compatible_resolutions[150.0] =   0.008333333333333333 * 5
pyramid_compatible_resolutions[300.0] =   0.08333333333333333
pyramid_compatible_resolutions[900.0] =   0.25
pyramid_compatible_resolutions[1800.0] =  0.5
pyramid_compatible_resolutions[3600.0] =  1.0
pyramid_compatible_resolutions[7200.0] =  2.0
pyramid_compatible_resolutions[14400.0] = 4.0
pyramid_compatible_resolutions[36000.0] = 10.0
for k, v in pyramid_compatible_resolutions.copy().items():
    pyramid_compatible_resolutions[str(k)] = v
    pyramid_compatible_resolutions[int(k)] = v
    pyramid_compatible_resolutions[str(int(k))] = v


# Define the bounds of what should raise an assertion that the file is close but not exactly matching one of the supported resolutions.
pyramid_compatible_resolution_bounds = {}
pyramid_compatible_resolution_bounds[1.0] =    (0.0002777777, 0.0002777778)
pyramid_compatible_resolution_bounds[10.0] =    (0.0027777, 0.00277778)
pyramid_compatible_resolution_bounds[30.0] =    (0.0083333, 0.00833334)
pyramid_compatible_resolution_bounds[150.0] =    (0.0083333*5, 0.00833334*5)
pyramid_compatible_resolution_bounds[300.0] =   (0.08333, 0.08334)
pyramid_compatible_resolution_bounds[900.0] =   (0.24999, 0.25001)
pyramid_compatible_resolution_bounds[1800.0] =  (0.4999, 0.5001)
pyramid_compatible_resolution_bounds[3600.0] =  (0.999, 1.001)
pyramid_compatible_resolution_bounds[7200.0] =  (1.999, 2.001)
pyramid_compatible_resolution_bounds[14400.0] = (3.999, 4.001)
pyramid_compatible_resolution_bounds[36000.0] = (9.999, 10.001)
for k, v in pyramid_compatible_resolution_bounds.copy().items():
    pyramid_compatible_resolution_bounds[str(k)] = v
    pyramid_compatible_resolution_bounds[int(k)] = v
    pyramid_compatible_resolution_bounds[str(int(k))] = v


pyramid_compatable_shapes = {}
pyramid_compatable_shapes[1.0] = [1296000, 648000]
pyramid_compatable_shapes[10.0] = [129600, 64800]
pyramid_compatable_shapes[30.0] = [43200, 21600]
pyramid_compatable_shapes[150.0] = [8640, 4320]
pyramid_compatable_shapes[300.0] = [4320, 2160]
pyramid_compatable_shapes[600.0] = [2160, 1080]
pyramid_compatable_shapes[900.0] = [1440, 720]
pyramid_compatable_shapes[1800.0] = [720, 360]
pyramid_compatable_shapes[3600.0] = [360, 180]
pyramid_compatable_shapes[7200.0] = [180, 90]
pyramid_compatable_shapes[14400.0] = [90, 45]
pyramid_compatable_shapes[36000.0] = [36, 18]
for k, v in pyramid_compatable_shapes.copy().items():
    pyramid_compatable_shapes[str(k)] = v
    pyramid_compatable_shapes[int(k)] = v
    pyramid_compatable_shapes[str(int(k))] = v


pyramid_compatable_shapes_to_arcseconds = {}
pyramid_compatable_shapes_to_arcseconds[(1296000, 648000)] = 1.0
pyramid_compatable_shapes_to_arcseconds[(129600, 64800)] = 10.0
pyramid_compatable_shapes_to_arcseconds[(43200, 21600)] = 30.0
pyramid_compatable_shapes_to_arcseconds[(8640, 4320)] = 150.0
pyramid_compatable_shapes_to_arcseconds[(4320, 2160)] = 300.0
pyramid_compatable_shapes_to_arcseconds[(2160, 1080)] = 600.0
pyramid_compatable_shapes_to_arcseconds[(1440, 720)] = 900.0
pyramid_compatable_shapes_to_arcseconds[(720, 360)] = 1800
pyramid_compatable_shapes_to_arcseconds[(360, 180)] = 3600
pyramid_compatable_shapes_to_arcseconds[(180, 90)] = 7200
pyramid_compatable_shapes_to_arcseconds[(90, 45)] = 14400
pyramid_compatable_shapes_to_arcseconds[(36, 18)] = 36000

geotransform_global_36600sec = (-180.0, 10.0, 0.0, 90.0, 0.0, -10.0)
geotransform_global_14400sec = (-180.0, 4.0, 0.0, 90.0, 0.0, -4.0)
geotransform_global_7200sec = (-180.0, 2.0, 0.0, 90.0, 0.0, -2.0)
geotransform_global_3600sec = (-180.0, 1.0, 0.0, 90.0, 0.0, -1.0)
geotransform_global_1800sec = (-180.0, 0.5, 0.0, 90.0, 0.0, -0.5)
geotransform_global_900sec= (-180.0, 0.25, 0.0, 90.0, 0.0, -0.25)
geotransform_global_300sec = (-180.0, 0.08333333333333333, 0.0, 90.0, 0.0, -0.08333333333333333)  # NOTE, the 0.08333333333333333 is defined very precisely as the answer a 64 bit compiled python gives from the answer 1/12 (i.e. 5 arc minutes)
geotransform_global_150sec = (-180.0, 0.008333333333333333 * 5, 0.0, 90.0, 0.0, -0.008333333333333333 * 5)  # NOTE, the 0.08333333333333333 is defined very precisely as the answer a 64 bit compiled python gives from the answer 1/12 (i.e. 5 arc minutes)
geotransform_global_30sec = (-180.0, 0.008333333333333333, 0.0, 90.0, 0.0, -0.008333333333333333)  # NOTE, the 0.008333333333333333 is defined very precisely as the answer a 64 bit compiled python gives from the answer 1/120 (i.e. 30 arc seconds) Note that this has 1 more digit than 1/12 due to how floating points are stored in computers via exponents.
geotransform_global_10ssec = (-180.0, 0.002777777777777778, 0.0, 90.0, 0.0, -0.002777777777777778)  # NOTE, the 0.002777777777777778 is defined very precisely
geotransform_global_1sec = (-180.0, 0.0002777777777777778, 0.0, 90.0, 0.0, -0.0002777777777777778)  # NOTE, the 0.0002777777777777778 is defined very precisely, in this case from the gdal C library

pyramid_compatible_geotransforms = {}
pyramid_compatible_geotransforms[1.0] = (-180.0, 0.0002777777777777778, 0.0, 90.0, 0.0, -0.0002777777777777778)
pyramid_compatible_geotransforms[10.0] = (-180.0, 0.002777777777777778, 0.0, 90.0, 0.0, -0.002777777777777778)
pyramid_compatible_geotransforms[30.0] = (-180.0, 0.008333333333333333, 0.0, 90.0, 0.0, -0.008333333333333333)
pyramid_compatible_geotransforms[150.0] = (-180.0, 0.008333333333333333*5, 0.0, 90.0, 0.0, -0.008333333333333333*5)
pyramid_compatible_geotransforms[300.0] = (-180.0, 0.08333333333333333, 0.0, 90.0, 0.0, -0.08333333333333333)
pyramid_compatible_geotransforms[900.0] = (-180.0, 0.25, 0.0, 90.0, 0.0, -0.25)
pyramid_compatible_geotransforms[1800.0] = (-180.0, 0.5, 0.0, 90.0, 0.0, -0.5)
pyramid_compatible_geotransforms[3600.0] = (-180.0, 1.0, 0.0, 90.0, 0.0, -1.0)
pyramid_compatible_geotransforms[7200.0] = (-180.0, 2.0, 0.0, 90.0, 0.0, -2.0)
pyramid_compatible_geotransforms[14400.0] = (-180.0, 4.0, 0.0, 90.0, 0.0, -4.0)
pyramid_compatible_geotransforms[36000.0] = (-180.0, 10.0, 0.0, 90.0, 0.0, -10.0)
for k, v in pyramid_compatible_geotransforms.copy().items():
    pyramid_compatible_geotransforms[str(k)] = v
    pyramid_compatible_geotransforms[int(k)] = v
    pyramid_compatible_geotransforms[str(int(k))] = v


# I decided that there are two types of supported pyramid levels:
# Main: 1, 3, 10, 300, 900, 1800 arc seconds (soon to add 333msec). All main and secondary must have overviews that represent all of the coarser set of these main levels
# Secondary: 30, 150. Common as an input, but overviews of OTHER levels aren't generated for these.
pyramid_compatible_overview_levels = {}
pyramid_compatible_overview_levels[1.0] = [3, 10, 30, 150, 300, 900, 1800, 3600]
pyramid_compatible_overview_levels[10.0] = [3, 15, 30, 90, 180, 360]
pyramid_compatible_overview_levels[30.0] = [5, 10, 30, 60, 120] 
pyramid_compatible_overview_levels[150.0] = [2, 6, 12, 24]
pyramid_compatible_overview_levels[300.0] = [3, 6, 12]
pyramid_compatible_overview_levels[900.0] = [2, 4]
pyramid_compatible_overview_levels[1800.0] = [2, 4] # Technically to make it to 3600sec (1deg) you would only need 2, however, the cog spec requires higher, so we keep the additional ones even tho they're not necessary for pyramid spec.
pyramid_compatible_overview_levels[3600.0] = [2, 4]
pyramid_compatible_overview_levels[7200.0] = [2, 4]
pyramid_compatible_overview_levels[14400.0] = [2, 4]
pyramid_compatible_overview_levels[36000.0] = [2, 4]
for k, v in pyramid_compatible_overview_levels.copy().items():
    pyramid_compatible_overview_levels[str(k)] = v
    pyramid_compatible_overview_levels[int(k)] = v
    pyramid_compatible_overview_levels[str(int(k))] = v


from osgeo import gdal, gdalconst


pyramid_resampling_algorithms_by_data_type = {}
pyramid_resampling_algorithms_by_data_type[1] = 'mode'
pyramid_resampling_algorithms_by_data_type[2] = 'mode'
pyramid_resampling_algorithms_by_data_type[3] = 'mode'
pyramid_resampling_algorithms_by_data_type[4] = 'mode'
pyramid_resampling_algorithms_by_data_type[5] = 'mode'
pyramid_resampling_algorithms_by_data_type[6] = 'average'
pyramid_resampling_algorithms_by_data_type[7] = 'average'
pyramid_resampling_algorithms_by_data_type[12] = 'average'
pyramid_resampling_algorithms_by_data_type[13] = 'average'
pyramid_resampling_algorithms_by_data_type[gdalconst.GDT_Byte] = 'mode'
pyramid_resampling_algorithms_by_data_type[gdalconst.GDT_UInt16] = 'mode'
pyramid_resampling_algorithms_by_data_type[gdalconst.GDT_Int16] = 'mode'
pyramid_resampling_algorithms_by_data_type[gdalconst.GDT_UInt32] = 'mode'
pyramid_resampling_algorithms_by_data_type[gdalconst.GDT_Int32] = 'mode'
pyramid_resampling_algorithms_by_data_type[gdalconst.GDT_Float32] = 'average'
pyramid_resampling_algorithms_by_data_type[gdalconst.GDT_Float64] = 'average'
pyramid_resampling_algorithms_by_data_type[gdalconst.GDT_UInt64] = 'average'
pyramid_resampling_algorithms_by_data_type[gdalconst.GDT_Int64] = 'average'
pyramid_resampling_algorithms_by_data_type[np.uint8] = 'mode'
pyramid_resampling_algorithms_by_data_type[np.uint16] = 'mode'
pyramid_resampling_algorithms_by_data_type[np.int16] = 'mode'
pyramid_resampling_algorithms_by_data_type[np.uint32] = 'mode'
pyramid_resampling_algorithms_by_data_type[np.int32] = 'mode'
pyramid_resampling_algorithms_by_data_type[np.float32] = 'average'
pyramid_resampling_algorithms_by_data_type[np.float64] = 'average'
pyramid_resampling_algorithms_by_data_type[np.uint64] = 'average'
pyramid_resampling_algorithms_by_data_type[np.int64] = 'average'



### It is it ref_path NOT refpath. These are correct
ha_per_cell_1sec_ref_path = os.path.join('pyramids', "ha_per_cell_1sec.tif")
ha_per_cell_10sec_ref_path = os.path.join('pyramids', "ha_per_cell_10sec.tif")
ha_per_cell_30sec_ref_path = os.path.join('pyramids', "ha_per_cell_30sec.tif")
ha_per_cell_150sec_ref_path = os.path.join('pyramids', "ha_per_cell_150sec.tif")
ha_per_cell_300sec_ref_path = os.path.join('pyramids', "ha_per_cell_300sec.tif")
ha_per_cell_900sec_ref_path = os.path.join('pyramids', "ha_per_cell_900sec.tif")
ha_per_cell_1800sec_ref_path = os.path.join('pyramids', "ha_per_cell_1800sec.tif")
ha_per_cell_3600sec_ref_path = os.path.join('pyramids', "ha_per_cell_3600sec.tif")
ha_per_cell_7200sec_ref_path = os.path.join('pyramids', "ha_per_cell_7200sec.tif")
ha_per_cell_14400sec_ref_path = os.path.join('pyramids', "ha_per_cell_14400sec.tif")
ha_per_cell_36000sec_ref_path = os.path.join('pyramids', "ha_per_cell_3600s0ec.tif")


ha_per_cell_ref_paths = {}
ha_per_cell_ref_paths[1.0] = ha_per_cell_1sec_ref_path
ha_per_cell_ref_paths[10.0] = ha_per_cell_10sec_ref_path
ha_per_cell_ref_paths[30.0] = ha_per_cell_30sec_ref_path
ha_per_cell_ref_paths[150.0] = ha_per_cell_150sec_ref_path
ha_per_cell_ref_paths[300.0] = ha_per_cell_300sec_ref_path
ha_per_cell_ref_paths[900.0] = ha_per_cell_900sec_ref_path
ha_per_cell_ref_paths[1800.0] = ha_per_cell_1800sec_ref_path
ha_per_cell_ref_paths[3600.0] = ha_per_cell_3600sec_ref_path
ha_per_cell_ref_paths[7200.0] = ha_per_cell_7200sec_ref_path
ha_per_cell_ref_paths[14400.0] = ha_per_cell_14400sec_ref_path
ha_per_cell_ref_paths[36000.0] = ha_per_cell_36000sec_ref_path
for k, v in ha_per_cell_ref_paths.copy().items():
    ha_per_cell_ref_paths[str(k)] = v
    ha_per_cell_ref_paths[int(k)] = v
    ha_per_cell_ref_paths[str(int(k))] = v



ha_per_cell_column_ref_paths = {}
ha_per_cell_column_ref_paths[10.0] = ha_per_cell_column_10sec_ref_path
ha_per_cell_column_ref_paths[30.0] = ha_per_cell_column_30sec_ref_path
ha_per_cell_column_ref_paths[150.0] = ha_per_cell_column_150sec_ref_path
ha_per_cell_column_ref_paths[300.0] = ha_per_cell_column_300sec_ref_path
ha_per_cell_column_ref_paths[900.0] = ha_per_cell_column_900sec_ref_path
ha_per_cell_column_ref_paths[1800.0] = ha_per_cell_column_1800sec_ref_path
ha_per_cell_column_ref_paths[3600.0] = ha_per_cell_column_3600sec_ref_path
ha_per_cell_column_ref_paths[7200.0] = ha_per_cell_column_7200sec_ref_path
ha_per_cell_column_ref_paths[14400.0] = ha_per_cell_column_14400sec_ref_path
ha_per_cell_column_ref_paths[36000.0] = ha_per_cell_column_36000sec_ref_path
for k, v in ha_per_cell_column_ref_paths.copy().items():
    ha_per_cell_column_ref_paths[str(k)] = v
    ha_per_cell_column_ref_paths[int(k)] = v
    ha_per_cell_column_ref_paths[str(int(k))] = v


global_bounding_box = [-180.0, -90.0, 180.0, 90.0]

mollweide_compatible_resolutions = {}
mollweide_compatible_resolutions[10.0] = 309.2208077590933 # calculated via hb.size_of_one_arcdegree_at_equator_in_meters / (60 * 6)
mollweide_compatible_resolutions[30.0] = 309.2208077590933 * (30.0 / 10.0)
mollweide_compatible_resolutions[300.0] = 309.2208077590933 * (300.0 / 10.0)
mollweide_compatible_resolutions[900.0] = 309.2208077590933 * (900.0 / 10.0)
mollweide_compatible_resolutions[1800.0] = 309.2208077590933 * (1800.0 / 10.0)
mollweide_compatible_resolutions[3600.0] = 309.2208077590933 * (3600.0 / 10.0)
mollweide_compatible_resolutions[7200.0] = 309.2208077590933 * (7200.0 / 10.0)
mollweide_compatible_resolutions[14400.0] = 309.2208077590933 * (14400.0 / 10.0)



def df_compare_column_labels_as_dict(left_input, right_input):
    
    if type(left_input) == str:
        left_df = pd.read_csv(left_input)
    else:   
        left_df = left_input
        
    if type(right_input) == str:
        right_df = pd.read_csv(right_input)
    else:
        right_df = right_input
        
    comparison_dict = hb.compare_sets_as_dict(left_df.columns, right_df.columns,  return_amount='partial')
    return comparison_dict
        
def df_compare_column_contents_as_dict(left_column, right_column):
    if type(left_column) == pd.DataFrame:
        raise NameError('left_column should be a column, not a dataframe.')
    if type(right_column) == pd.DataFrame:
        raise NameError('right_column should be a column, not a dataframe.')
        
    left_unique = pd.unique(left_column)
    right_unique = pd.unique(right_column)
    comparison_dict = hb.compare_sets_as_dict(left_unique, right_unique,  return_amount='partial')  
    return comparison_dict
    
def compare_sets_as_dict(left_input, right_input, return_amount='partial', output_csv_path=None):
    left_set = set(left_input)
    right_set = set(right_input)

    union = left_set | right_set # union.
    intersection = left_set & right_set # intersection.
    left_difference = left_set - right_set # difference
    right_difference = right_set - left_set# difference
    symmetric_difference = left_set ^ right_set # symmetric difference



    if return_amount == 'all':
        
        output_dict = {}
        output_dict['left_set'] = list(left_set)
        output_dict['right_set'] = list(right_set)
        output_dict['union'] = list(union)
        output_dict['intersection'] = list(intersection)
        output_dict['left_only'] = list(left_difference)
        output_dict['right_only'] = list(right_difference)
        output_dict['symmetric_difference'] = list(symmetric_difference)

        # hb.log('Set 1: ' + str(len(left_set)) + ' ' + str(left_set))
        # hb.log('Set 2: ' + str(len(right_set)) + ' ' + str(right_set))
        # hb.log('union: ' + str(len(union)), union)
        # hb.log('intersection: ' + str(len(intersection)), intersection)
        # hb.log('left_only: ' + str(len(left_difference)), left_difference)
        # hb.log('right_only: ' + str(len(right_difference)), right_difference)
        # hb.log('symmetric_difference: ' + str(len(symmetric_difference)), symmetric_difference)

    elif return_amount == 'partial':
        output_dict = {}
        output_dict['intersection'] = list(intersection)
        output_dict['left_only'] = list(left_difference)
        output_dict['right_only'] = list(right_difference)

        # hb.log('intersection: ' + str(len(intersection)), intersection)
        # hb.log('left_only: ' + str(len(left_difference)), left_difference)
        # hb.log('right_only: ' + str(len(right_difference)), right_difference)

    longest_element = max([len(output_dict[i]) for i in output_dict.keys()])

    to_write = ','.join(list(output_dict.keys())) + '\n'
    for r in range(longest_element):
        for c in list(output_dict.keys()):
            if r < len(output_dict[c]):

                to_write += '\"' + str(output_dict[c][r]) + '\"' + ','
            else:
                to_write += ','
        to_write += '\n'


    if output_csv_path:
        hb.write_to_file(to_write, output_csv_path)
        comparison_df = pd.read_csv(output_csv_path)
    else:
        from io import StringIO
        df_string = StringIO(to_write)

        comparison_df = pd.read_csv(df_string)
        # comparison_df = pd.read_csv(to_write)


    return output_dict


def fuzzy_merge(left_df, right_df, left_on, right_on, how='inner', cutoff=0.6):
    report = {}
    def get_closest_match(x, other, cutoff, report):
        matches = difflib.get_close_matches(x, other, n=20, cutoff=cutoff)

        if len(matches) > 0:
            if x != matches[0]:
                pass
                if x not in report:

                    report[x] = [matches[0], matches]
                    print ('   found matches for ', x, ': ', matches)
                return matches[0]
            else:
                L.debug('   found EXACT match for ', x, ': ', matches)
                report[x] = [matches[0], matches]
                return matches[0]
        else:
            L.debug('    found NO matches for ' , x)
            report[x] = ''
            return x

    left_uniques = pd.unique(left_df[left_on])
    right_uniques = pd.unique(right_df[right_on])

    right_df['original_right'] = right_df[right_on]
    right_df_copy = right_df.copy()

    # print('right_df', right_df)
    # print('right_dfr', right_df[right_on])

    replace_dict = {}
    for right_unique in right_uniques:
        # print('right_unique', right_unique)
        possible_matches = get_closest_match(right_unique, left_uniques, cutoff, report)
        # print('possible_matches', possible_matches)
        replace_dict[right_unique] = possible_matches
    # hb.print_dict('replace_dict', replace_dict)
    # print('right_df111', right_df)
    # print('replace_dict', replace_dict)
    right_df[right_on].replace(replace_dict, inplace=True)
    # print('right_df1112', right_df)

    # # Apply the get_closest_match for each x in right_df merge column.
    # # This is VERY unoptimized but meh for now.
    # # Save it in a new left_on column in the right_df df.
    # right_df_copy[left_on] = [get_closest_match(x, left_df[left_on], cutoff, report)
    #                      for x in right_df_copy[right_on]]


    # Return the merged output along with a report on what happened.
    merged = hb.df_merge(left_df, right_df, left_on=left_on, right_on=right_on, supress_warnings=True)
    
    return merged, report
    # return left_df.merge(right_df, on=left_on, how=how), report



def get_blocksize_from_path(input_path):
    ds = gdal.OpenEx(input_path)
    blocksize = ds.GetRasterBand(1).GetBlockSize()
    return blocksize

def get_compression_type_from_path(input_path):
    ds = gdal.OpenEx(input_path)
    image_structure = ds.GetMetadata('IMAGE_STRUCTURE')
    if "COMPRESSION" in image_structure:
        return image_structure['COMPRESSION']
    else:
        return 'Didnt detect compression.'

def rewrite_array_with_new_blocksize(input_path, output_path, desired_blocksize):
    if desired_blocksize == 'full_stripe':
        output_blocksize = [hb.get_shape_from_dataset_path(input_path)[1], 1]
        dst_options = ['TILED=NO', 'BIGTIFF=YES', 'COMPRESS=DEFLATE']  # NO tiling cause striding. They're all in a stripe!
    elif desired_blocksize == 'block_default':
        dst_options = hb.globals.DEFAULT_GTIFF_CREATION_OPTIONS
    elif type(desired_blocksize) is list:
        if len(desired_blocksize) == 2:
            if desired_blocksize[0] > 1 and desired_blocksize[1] > 1:
                dst_options = ['TILED=YES', 'BIGTIFF=YES', 'COMPRESS=DEFLATE', 'BLOCKXSIZE=' + str(desired_blocksize[0]), 'BLOCKYSIZE=' + str(desired_blocksize[1])]
            else:
                dst_options = ['TILED=NO', 'BIGTIFF=YES', 'COMPRESS=DEFLATE', 'BLOCKXSIZE=' + str(desired_blocksize[0]), 'BLOCKYSIZE=' + str(desired_blocksize[1])]
        else:
            raise NameError('Unable to interpret inputs for ', input_path)
    else:
        raise NameError('Unable to interpret inputs for rewrite_array_with_new_blocksize on ', input_path)

    swap_filenames_at_end = False
    if input_path == output_path:
        swap_filenames_at_end = True
        output_path = hb.rsuri(output_path, 'pre_swap')


    input_blocksize = get_blocksize_from_path(input_path)
    input_compression_type = get_compression_type_from_path(input_path)

    ds = gdal.Open(input_path)
    band = ds.GetRasterBand(1)

    read_callback = hb.make_logger_callback("ReadAsArray percent complete:")
    input_array = band.ReadAsArray(callback=read_callback, callback_data=[input_path])

    data_type = hb.get_datatype_from_uri(input_path)
    geotransform = hb.get_geotransform_path(input_path)
    projection = hb.get_dataset_projection_wkt_uri(input_path)
    ndv = hb.get_ndv_from_path(input_path)



    driver = gdal.GetDriverByName('GTiff')
    dst_ds = driver.Create(output_path, input_array.shape[1], input_array.shape[0], 1, data_type, dst_options)
    dst_ds.SetGeoTransform(geotransform)
    dst_ds.SetProjection(projection)
    ndv = -9999.0
    dst_ds.GetRasterBand(1).SetNoDataValue(ndv)

    write_callback = hb.make_logger_callback("WriteArray percent complete:")
    dst_ds.GetRasterBand(1).WriteArray(input_array, callback=write_callback, callback_data=[output_path])

    dst_ds = None # Necessary for filename swap
    ds = None # Necessary for filename swap

    if swap_filenames_at_end:
        hb.swap_filenames(output_path, input_path)

def get_global_block_list_indices_from_block_size(block_size):
    block_indices = []
    n_h_blocks = int(360.0 / float(block_size))
    n_v_blocks = int(180.0 / float(block_size))

    for h_b in range(n_h_blocks):
        for v_b in range(n_v_blocks):
            block_indices.append([int(h_b), int(v_b)])

    return block_indices


def get_global_block_list_from_resolution(processing_block_size, raster_resolution, verbose=False):
    """Get list of 6-length lists that define tiles of the world, based only on coarse and fine resolutions. Returns list of lists.

    Return: [ul fine col, ul fine row, fine width, fine height, coarse col, coarse row]
    """
    n_h_blocks = int(360.0 / float(processing_block_size))
    n_v_blocks = int(180.0 / float(processing_block_size))
    n_blocks = n_h_blocks * n_v_blocks

    block_list = []
    block_size = processing_block_size / raster_resolution
    for h_b in range(n_h_blocks):

        for v_b in range(n_v_blocks):
            block_list.append([int(h_b * block_size), int(v_b * block_size), int(block_size), int(block_size), int(h_b), int(v_b)])

    if verbose:
        print("get_global_block_list_from_resolution_and_bb", processing_block_size, raster_resolution)
        print(block_list)

    return block_list

def get_global_block_list_from_resolution_and_bb(processing_block_size, raster_resolution, bb, verbose=False):
    """Get list of 6-length lists that define tiles that iterate over the bounding box. Note that the bounds of the BB must be a multiple of
    the coarse resolution, based only on coarse and fine resolutions. Returns list of lists.

    Return: [ul fine col, ul fine row, fine width, fine height, coarse col, coarse row]
    """


    x_min_deg = bb[0]
    y_min_deg = bb[1]
    x_max_deg = bb[2]
    y_max_deg = bb[3]
    hb.round_to_nearest_containing_increment
    # Here is the problem. This assumes the procesing block size is 1.
    n_h_blocks = math.ceil((hb.round_up_to_nearest_base(x_max_deg, processing_block_size) - hb.round_down_to_nearest_base(x_min_deg, processing_block_size)) / float(processing_block_size))
    n_v_blocks = math.ceil((hb.round_up_to_nearest_base(y_max_deg, processing_block_size) - hb.round_down_to_nearest_base(y_min_deg, processing_block_size)) / float(processing_block_size))
    
    n_h_blocks = int(round((x_max_deg - x_min_deg) / float(processing_block_size)))
    n_v_blocks = int(round((y_max_deg - y_min_deg) / float(processing_block_size)))
    n_blocks = n_h_blocks * n_v_blocks

    block_size = processing_block_size / raster_resolution

    left_offset_h_blocks = int((180. + x_min_deg) / float(processing_block_size))
    left_offset_h_pixels = left_offset_h_blocks * block_size
    top_offset_v_blocks = int((90. - y_max_deg) / float(processing_block_size))
    top_offset_v_pixels = top_offset_v_blocks * block_size
    block_list = []
    for h_b in range(n_h_blocks):

        for v_b in range(n_v_blocks):
            block_list.append([int((h_b * block_size) + left_offset_h_pixels), int((v_b * block_size) + top_offset_v_pixels), int(block_size), int(block_size), int(h_b), int(v_b)])


    if verbose:
        print("get_global_block_list_from_resolution_and_bb", processing_block_size, raster_resolution, bb)
        print(block_list)

    return block_list

def get_subglobal_block_list_from_resolution_and_bb(processing_block_size, raster_resolution, bb, verbose=False):
    """Get list of 6-length lists that define tiles that iterate over the bounding box. Note that the bounds of the BB must be a multiple of
    the coarse resolution, based only on coarse and fine resolutions. Returns list of lists.

    Return: [ul fine col, ul fine row, fine width, fine height, coarse col, coarse row]
    """
    x_min_deg = bb[0]
    y_min_deg = bb[1]
    x_max_deg = bb[2]
    y_max_deg = bb[3]


    a = hb.round_up_to_nearest_base(x_max_deg, processing_block_size)
    b = hb.round_down_to_nearest_base(x_min_deg, processing_block_size)
    c = hb.round_up_to_nearest_base(y_max_deg, processing_block_size)
    d = hb.round_down_to_nearest_base(y_min_deg, processing_block_size)
    e = (hb.round_up_to_nearest_base(y_max_deg, processing_block_size) - hb.round_down_to_nearest_base(y_min_deg, processing_block_size)) / float(processing_block_size)
    n_h_blocks = math.ceil((hb.round_up_to_nearest_base(x_max_deg, processing_block_size) - hb.round_down_to_nearest_base(x_min_deg, processing_block_size)) / float(processing_block_size))
    n_v_blocks = math.ceil((hb.round_up_to_nearest_base(y_max_deg, processing_block_size) - hb.round_down_to_nearest_base(y_min_deg, processing_block_size)) / float(processing_block_size))
 
    n_h_blocks = int(round((x_max_deg - x_min_deg) / float(processing_block_size)))
    n_v_blocks = int(round((y_max_deg - y_min_deg) / float(processing_block_size)))
 
    # n_h_blocks = int((math.ceil(x_max_deg) - math.floor(x_min_deg)) / float(processing_block_size))
    # n_v_blocks = int((math.ceil(y_max_deg) - math.floor(y_min_deg)) / float(processing_block_size))
    # n_blocks = n_h_blocks * n_v_blocks

    block_size = processing_block_size / raster_resolution

    # TODOO actually eliminate rather than set as zero
    left_offset_h_blocks = 0
    left_offset_h_pixels = left_offset_h_blocks * block_size
    top_offset_v_blocks = 0
    top_offset_v_pixels = top_offset_v_blocks * block_size
    block_list = []
    for h_b in range(n_h_blocks):

        for v_b in range(n_v_blocks):
            block_list.append([int((h_b * block_size) + left_offset_h_pixels), int((v_b * block_size) + top_offset_v_pixels), int(block_size), int(block_size), int(h_b), int(v_b)])

    if verbose:
        print("get_subglobal_block_list_from_resolution_and_bb", processing_block_size, raster_resolution, bb)
        print(block_list)


    return block_list

def determine_pyramid_resolution(input_path):
    """ Check if input_path has a resolution the is exactly equal or close to a pyramid-supported resolution.

    Return the input resolution if correct, the snapped-to resolution if close enough. Otherwise raise exception."""
    ds = gdal.OpenEx(input_path)
    if ds is None:
        raise Exception('Could not open ' + str(input_path) + ' at abspath ' + str(os.path.abspath(input_path)))
    gt = ds.GetGeoTransform()
    ulx, xres, _, uly, _, yres = gt[0], gt[1], gt[2], gt[3], gt[4], gt[5]
    # (-180.0, 0.0002777777777777778, 0.0, 90.0, 0.0, -0.0002777777777777778)
    resolution = None
    if xres in pyramid_compatible_resolutions.keys():
        resolution = xres
    else:
        for k, v in pyramid_compatible_resolution_bounds.items():
            if v[0] < xres < v[1]:
                resolution = pyramid_compatible_resolutions[k]
                if resolution != xres:
                    L.info('Input res was ' + str(xres) + ' for ' + str(input_path) + ' but should have been ' + str(resolution) + ' to make pyramid-ready.')

    if resolution is None:

        L.warning('determine_pyramid_resolution found no suitably close resolution for ' + str(input_path) + ' with ulx, xres, uly, yres of ' + str(ulx) + ' ' + str(xres) + ' ' + str(uly) + ' ' + str(yres) + ' ')
        return None
    ds = None
    return resolution
def make_paths_list_global_pyramid(
        input_paths_list,
        output_paths_list=None,
        make_overviews=True,
        overwrite_overviews=False,
        calculate_stats=True,
        overwrite_stats=False,
        clean_temporary_files=False,
        raise_exception=False,
        make_overviews_external=True,
        set_ndv_below_value=None,
        verbose=False
):

    num_workers = max(min(multiprocessing.cpu_count() - 1, len(input_paths_list)), 1)

    if verbose:
        L.info('Creating multiprocessing worker pool of size ' + str(num_workers))
    worker_pool = multiprocessing.Pool(num_workers)  # NOTE, worker pool and results are LOCAL variabes so that they aren't pickled when we pass the project object.

    initial_test = []
    for path in input_paths_list:
        initial_test.append(hb.is_path_global_pyramid(path))
    if verbose:
        L.info('Tested input_paths list and the following were not globally pyramidal: ' + str([i for c, i in enumerate(input_paths_list) if not initial_test[c]]))

    if not all(initial_test):
        input_paths_list = [i for c, i in enumerate(input_paths_list) if not initial_test[c]]
        finished_results = []
        if output_paths_list is None:
            output_paths_list = [None for i in input_paths_list]
        parsed_iterable = [(input_paths_list[c],
                            output_paths_list[c],
                            make_overviews,
                            overwrite_overviews,
                            calculate_stats,
                            overwrite_stats,
                            clean_temporary_files,
                            raise_exception,
                            make_overviews_external,
                            set_ndv_below_value,
                            verbose)
                                for c, i in enumerate(input_paths_list)]

        if verbose:
            L.info('About to launch parallel process on the following parsed_iterable:\n' + hb.pp(parsed_iterable, return_as_string=True))
        result = worker_pool.starmap_async(make_path_global_pyramid, parsed_iterable)
        for i in result.get():
            finished_results.append(i)
        worker_pool.close()
        worker_pool.join()
    # FOR REFERENCE. here is the old apply_async approach
    # results = []
    # finished_results = []
    # num_simultaneous = 80
    # starting_c = 0
    # for w in range(num_simultaneous):
    #     for c in range(starting_c, starting_c + num_simultaneous):
    #         if c < len(input_paths_list):
    #
    #             path = input_paths_list[c]
    #
    #             if output_paths_list is not None:
    #                 output_path = output_paths_list[c]
    #             else:
    #                 output_path = None
    #             L.info('Running make_paths_list_global_pyramid in parallel for ' + path)
    #
    #
    #             result = worker_pool.apply_async(func=make_path_global_pyramid, args=(path,
    #                                                                                   output_path,
    #                                                                                   make_overviews,
    #                                                                                   overwrite_overviews,
    #                                                                                   calculate_stats,
    #                                                                                   overwrite_stats,
    #                                                                                   clean_temporary_files,
    #                                                                                   raise_exception,
    #                                                                                   make_overviews_external,
    #                                                                                   set_ndv_below_value,
    #                                                                                   verbose)
    #                                              )
    #
    #         # Note this keeps it in memory, and can hit limits.
    #         results.append(result)
    #     starting_c = starting_c + num_simultaneous
    #
    #     for i in results:
    #         finished_results.append(i.get())
    #         del i
    #         # print ('i', i, i.get())
    #         #
    #         # for j in i.get():
    #         #     if j is not None:
    #         #         finished_results.append(j)
    #
    # worker_pool.close()
    # worker_pool.join()


def resample_to_match_pyramid(input_path,
                      match_path,
                      output_path,
                      resample_method='bilinear',
                      output_data_type=None,
                      src_ndv=None,
                      ndv=None,
                      s_srs_wkt=None,
                      compress=True,
                      ensure_fits=False,
                      gtiff_creation_options=hb.globals.DEFAULT_GTIFF_CREATION_OPTIONS,
                      calc_raster_stats=False,
                      add_overviews=False,
                      pixel_size_override=None,
                      remove_intermediate_files=False,
                      is_id_raster=False,
                      verbose=False,
                      ):

    if verbose:
        original_level = L.getEffectiveLevel()
        L.setLevel(logging.DEBUG)

    if hb.assert_paths_same_pyramid(input_path, match_path):
        L.debug('Both input and match are same pyramids already.')
        return

    # if not hb.is_path_global_pyramid(input_path):
    #     raise NameError('Non-pyramidal path given to match_path for resample_to_match_pyramid: ' + str(match_path))

    if hb.assert_gdal_paths_have_same_geotransform(input_path):
        requires_resample = False
    else:
        requires_resample = True

    if requires_resample:

        temp_resample_path = hb.temp('.tif', 'temp_resample', remove_intermediate_files, os.path.split(output_path)[0])

        hb.resample_to_match(input_path,
                             match_path,
                             output_path,
                             resample_method=resample_method,
                             output_data_type=output_data_type,
                             src_ndv=src_ndv,
                             ndv=ndv,
                             s_srs_wkt=s_srs_wkt,
                             compress=compress,
                             ensure_fits=ensure_fits,
                             gtiff_creation_options=gtiff_creation_options,
                             calc_raster_stats=calc_raster_stats,
                             add_overviews=add_overviews,
                             pixel_size_override=pixel_size_override,
                             verbose=verbose,
                             )

        # if hb.is_path_global_pyramid(temp_resample_path):
        #     L.debug('Path was pyramidal after resample. Renaming to ' + str(output_path))
        #     hb.rename_with_overwrite(temp_resample_path, output_path)
        # else:
        hb.make_path_global_pyramid(output_path, is_id_raster=is_id_raster)
    else:

        hb.make_path_global_pyramid(input_path, output_path=output_path, is_id_raster=is_id_raster)

    if verbose:
        L.setLevel(original_level)

def assert_path_global_pyramid(input_path):
    try:
        result = is_path_global_pyramid(input_path)
    except Exception as e:
        raise NameError('assert_path_global_pyramid failed on ', input_path, 'with exception', e)
    if not result:
        raise NameError('assert_path_global_pyramid failed on ', input_path)

def is_path_global_pyramid(input_path, verbose=False):
    """Fast method for testing if path is pyramidal."""
    to_return = True
    if verbose:
        L.info('Testing if path is global pyramid: ' + str(input_path))
    res = hb.determine_pyramid_resolution(input_path)

    if res is None:
        if verbose:
            hb.log('Not pyramid because no suitable resolution was found: ' + str(input_path))
        return False
    
    shape = hb.get_shape_from_dataset_path(input_path)
    gt = hb.get_geotransform_path(input_path)

    if not pyramid_compatible_geotransforms[pyramid_compatible_resolution_to_arcseconds[res]] == gt:
        if verbose:
            hb.log('Not pyramid because geotransform was not pyramidal. Found ' + str(gt) + ' which was not equal to ' + str(pyramid_compatible_geotransforms[pyramid_compatible_resolution_to_arcseconds[res]]) + ' for: '  + str(input_path))
        to_return = False
        
    # Interesting bug: If statistics are exact and stored internally to the geotiff but there is ALSO an external .aux.xml file with approximate statistics, 
    # the gdal driver will return approximate statistics. To ensure this doesn't happen, first remove any .aux.xml file that may exist.
    aux_path = input_path + '.aux.xml'
    if hb.path_exists(aux_path):
        if verbose:
            hb.log('Removing aux file: ' + str(aux_path))
        hb.remove_path(aux_path)        

    ds = gdal.OpenEx(input_path)
    image_structure = ds.GetMetadata('IMAGE_STRUCTURE')
    compression = image_structure.get('COMPRESSION', None)

    # Check if compressed (pyramidal file standards require compression)
    if str(compression).lower() not in ['zstd', 'lzw']:
        if verbose:
            hb.log('Not a global pyramid because compression was not zstd/lzw: ' + str(input_path))
        to_return = False

    data_type = ds.GetRasterBand(1).DataType
    ndv = ds.GetRasterBand(1).GetNoDataValue()
    
    correct_ndv = hb.get_correct_ndv_from_dtype_flex(data_type)
    if ndv != correct_ndv:
        if verbose:
            hb.log('Not pyramid because ndv was not correct for datatype: ' + str(input_path))
        to_return = False

    # Check if the overview levels are correct
    levels = []
    band = ds.GetRasterBand(1)
    overview_count = band.GetOverviewCount()
    for i in range(overview_count):
        ovr = band.GetOverview(i)
        if verbose:
            hb.log(f"Overview {i+1}: {ovr.XSize} x {ovr.YSize}")
        levels.append(shape[1] / ovr.XSize)
        
    correct_levels = hb.pyramid_compatible_overview_levels[pyramid_compatible_resolution_to_arcseconds[res]]
    if levels != correct_levels:
        if verbose:
            hb.log(f'Not pyramid because overview levels were not correct: {levels} {correct_levels }' + str(input_path))
        to_return = False



    metadata = band.GetMetadata()
    approx = metadata.get('STATISTICS_APPROXIMATE', 'YES')
    if approx != 'NO':
        if verbose:
            hb.log('Not pyramid because statistics were either approximate or not present: ' + str(input_path))
        to_return = False

        
    if to_return:
        if verbose:
            L.info('Path is a global pyramid: ' + str(input_path))
        return True
    else:
        if verbose:
            L.info('Path is NOT a global pyramid: ' + str(input_path))
        return False
    


def make_vector_path_global_pyramid(input_path, output_path=None, pyramid_index_columns=None, drop_columns=False,
                                    clean_temporary_files=False, verbose=False):
    """A pyramidal vector file requires that it have bb information (optionall minx, miny separate), a pyramid_id that is composed of name-id pairs of potential zones.

    pyramid_id may be large, hence also have pyramid_id which starts at 1

    If specifying pyramid_index_columns, it will smartly create an index according to the following logic:
        if the column type is int64able, it is an unnamed int pyramid_index
        if the column is not int64able, it is a named pyramid index and also generates a <name>_as_id column that is int64

    """
    if not hb.path_exists(input_path):
        raise NameError('Unable to find input_path ' + str(input_path))
    
    if drop_columns is False:
        drop_columns = []

    if os.path.splitext(input_path)[1] != 'gpkg':
        input_is_not_gpkg = True

    try:
        if os.path.splitext(input_path)[1].lower() == '.gpkg':
            gdf = gpd.read_file(input_path, driver='GPKG')
        elif os.path.splitext(input_path)[1].lower() == '.shp':
            gdf = gpd.read_file(input_path, driver='ESRI Shapefile')
        else:
            gdf = gpd.read_file(input_path)
    except NameError as exception:
        raise NameError('Unable to read GPKG at ' + str(input_path) + ' and encountered exception: ' + str(exception))

    rewrite_necessary = False
    dissolved_gdf = None

    if 'bb' not in gdf.columns:
        if verbose:
            L.info('bb not in vector attributes so rewriting.')
        gdf['bb'] = gdf.bounds.minx.astype(str) + ',' + gdf.bounds.miny.astype(str) + ',' + gdf.bounds.maxx.astype(str) + ',' + gdf.bounds.maxy.astype(str)
        gdf['minx'] = gdf.bounds.minx.astype(float)
        gdf['miny'] = gdf.bounds.miny.astype(float)
        gdf['maxx'] = gdf.bounds.maxx.astype(float)
        gdf['maxy'] = gdf.bounds.maxy.astype(float)
        rewrite_necessary = True

    if 'pyramid_id' not in gdf.columns or pyramid_index_columns is not None:
        rewrite_necessary = True
        if verbose:
            L.info('pyramid_id not in vector so rewriting.')
        if pyramid_index_columns is None:
            raise NameError('Unable to make vector file a global pyramid because there was no preexisting pyramid_id column and no pyramid_index_columns argument was given.')

        # First sanitize names:
        rename_dict = {}
        for name in pyramid_index_columns:
            if name.lower() != name:
                rename_dict[name] = name.lower()
        # pyramid_index_columns = list(rename_dict.values())
        pyramid_index_columns = [i.lower() for i in pyramid_index_columns]
        gdf.rename(columns=rename_dict, inplace=True)

        updated_pyramid_index_columns = []
        updated_pyramid_names_columns = []
        columns_to_add_ids = []

        gdf = gdf.dropna(subset=pyramid_index_columns)

        # Iterate through the columns that will define the pyramidal structure in REVERSE because the first listed is the final sort.
        for column_name in pyramid_index_columns:
            try:
                gdf[column_name] = gdf[column_name].fillna(0).astype(np.int64)
                column_intable = True
            except Exception as e:
                L.debug('In try, came accross exception ' + str(e))
                column_intable = False


            # For intable indices, only need to rename and move them.
            if column_intable is True:
                validated_column_id =  column_name.lower() + '_pyramid_id'
                updated_pyramid_index_columns.append(validated_column_id)
                gdf.rename(columns={column_name: validated_column_id}, inplace=True)

                # Sort the by the new column id
                gdf = gdf.iloc[gdf[validated_column_id].sort_values().index.values] #.astype(np.int64)



            # But for columns that are not ints, need to add a new name after a complex sort.
            else:
                validated_column_name = column_name.lower() + '_pyramid_name'
                updated_pyramid_names_columns.append(validated_column_name)
                columns_to_add_ids.append(column_name.lower())
                validated_column_id = column_name.lower() + '_pyramid_id'
                updated_pyramid_index_columns.append(validated_column_id)

                # LEARNING POINT WTF, underscore comes between capital and lowercase letters. Sorting thus is borked. Best fix is to replace understcores with something that does sort right. WTFingF.

                unique_values = list(np.unique(gdf[column_name][gdf[column_name].notnull()]))
                ascii_fixed_unique_values = [str(i).replace('_', '%') for i in unique_values]
                unique_sorted_values = [str(i).replace('%', '_') for i in sorted(ascii_fixed_unique_values)]

                replacement_dict = {v: c + 1 for c, v in enumerate(unique_sorted_values)}

                L.info('Generated replacement dict for pyramid id on ' + str(column_name) + ': ' + str(replacement_dict))
                # gdf[validated_column_name] = gdf[column_name]
                gdf.rename(columns={column_name: validated_column_name}, inplace=True)
                gdf[validated_column_id] = gdf[validated_column_name].replace(replacement_dict).astype(np.int64)
                # Sort the by the new column id
                gdf = gdf.iloc[gdf[validated_column_id].sort_values().index.values]


        # Generate a concatenation of all pyramids in int form

        # Generate actual pyramid id
        for c, column_name in enumerate(updated_pyramid_index_columns):
            if column_name.endswith('_pyramid_id'):
                if 'pyramid_ids_concatenated' not in gdf.columns:
                    gdf['pyramid_ids_concatenated'] = gdf[column_name].map(np.int64).map(str)
                else:
                    gdf['pyramid_ids_concatenated'] = gdf['pyramid_ids_concatenated'].map(str) + '_' + gdf[column_name].map(np.int64).map(str)

                if 'pyramid_ids_multiplied' not in gdf.columns:
                    gdf['pyramid_ids_multiplied'] = gdf[column_name].map(np.int64)
                else:
                    gdf['pyramid_ids_multiplied'] = gdf['pyramid_ids_multiplied'].map(np.int64) * 1000 + gdf[column_name].map(np.int64)

        # Check to see if the resultant pyramid_ids are unique. If not, write a secondary file *_dissolved that combines these polygons to make it unique
        unique_pyramid_ids = np.unique(gdf['pyramid_ids_multiplied'])
        pyramid_ordered_ids_dict = {v: c + 1 for c, v in enumerate(list(unique_pyramid_ids))}
        gdf['pyramid_id'] = gdf['pyramid_ids_multiplied'].apply(lambda x: pyramid_ordered_ids_dict[x])
        # gdf['pyramid_id'] = gdf['pyramid_id'].apply(lambda x: pyramid_ordered_ids_dict[x])

        # Reorder to put pyramid cols first.
        drop_columns.append('dissolve_col')
        updated_pyramid_index_columns = ['pyramid_id'] + ['pyramid_ids_concatenated'] + ['pyramid_ids_multiplied'] + updated_pyramid_index_columns + updated_pyramid_names_columns
        columns_ordered = updated_pyramid_index_columns + [i for i in gdf.columns if i not in updated_pyramid_index_columns and i not in drop_columns]
        gdf = gdf[columns_ordered]

        from shapely.geometry.polygon import Polygon
        from shapely.geometry.multipolygon import MultiPolygon

        # Learning point, I encountered an error with invalid geometries. I fixed it by both converting to Multipolygons AND running feature.buffer().
        # the above worked, this is fraught if there's invalid geometry. It
        # appears there is no good way of fixing invalid geometry cause each case is different.
        try:
            gdf["geometry"] = [MultiPolygon([feature.buffer(0)]) if type(feature) == Polygon else feature.buffer(0) for feature in gdf["geometry"]]
        except:
            print ('Tried the bugger and multipolygon trick but that didnt work. Miiiiight not matter but be cautious.')

        if len(unique_pyramid_ids) < len(gdf['pyramid_id']):
            L.info('Found non-unique pyramid_id, so creating new geopackage with dissolved_gdf polygons.')

            # Add copy of column to be dissolved on cause it disappears on dissolve.
            gdf['dissolve_col'] = gdf['pyramid_id']

            # Save it as gtap_aez_dissolved
            dissolved_gdf = gdf.dissolve(by='dissolve_col')

            dissolved_gdf_path = hb.suri(output_path, 'dissolved')

            # Need to rewrite BB info cause disolving changed this.
            dissolved_gdf['bb'] = dissolved_gdf.bounds.minx.astype(str) + ',' + dissolved_gdf.bounds.miny.astype(str) + ',' + dissolved_gdf.bounds.maxx.astype(str) + ',' + dissolved_gdf.bounds.maxy.astype(str)
            dissolved_gdf['minx'] = dissolved_gdf.bounds.minx.astype(float)
            dissolved_gdf['miny'] = dissolved_gdf.bounds.miny.astype(float)
            dissolved_gdf['maxx'] = dissolved_gdf.bounds.maxx.astype(float)
            dissolved_gdf['maxy'] = dissolved_gdf.bounds.maxy.astype(float)

        gdf = gdf.sort_values('pyramid_id')
        if dissolved_gdf is not None:
            dissolved_gdf = dissolved_gdf.sort_values('pyramid_id')

        # Reorder to put pyramid cols first.
        # updated_pyramid_index_columns = ['pyramid_id', 'pyramid_ids_concatenated'] + updated_pyramid_index_columns
        columns_ordered = updated_pyramid_index_columns + [i for i in gdf.columns if i not in updated_pyramid_index_columns and i not in drop_columns]
        gdf = gdf[columns_ordered]

        if dissolved_gdf is not None:
            dissolved_gdf = dissolved_gdf[columns_ordered]


    if rewrite_necessary is True:

        # Rename files to displace old input. This has to be done before external-file operations are completed.
        displacement_path = hb.temp('.gpkg', filename_start=hb.file_root(input_path) + '_displaced_' + hb.random_string(), folder=os.path.split(input_path)[0], remove_at_exit=clean_temporary_files)
        temp_write_path = hb.temp('.gpkg', filename_start=hb.file_root(input_path) + '_temp_write_' + hb.random_string(), folder=os.path.split(input_path)[0], remove_at_exit=clean_temporary_files)

        if output_path:
            layer_name = hb.file_root(output_path)
        else:
            layer_name = hb.file_root(input_path)

        # LEARNING POINT, when importing a shapefile that had a float-style fid, which is interpretted by fiona as the SQL primary key, there was a
        # File "fiona/ogrext.pyx", line 1173, in fiona.ogrext.WritingSession.start
        # fiona.errors.SchemaError: Wrong field type for fid
        # error that arose. Solution for now was to rewrite fids as ints64.
        for current_gdf in [gdf, dissolved_gdf]:
            if current_gdf is not None:
                if 'fid' in current_gdf.columns:
                    if current_gdf['fid'].dtype != np.int64:
                        current_gdf['fid'] = current_gdf['fid'].astype(np.int64)

        # gdf = gdf.drop('dissolve_col', 1)
        # dissolved_gdf = dissolved_gdf.drop('dissolve_col', 1)
        # if 'dissolve_col' in gdf.columns:
        #     gdf = gdf.drop('dissolve_col', 1)
        if dissolved_gdf is not None:
            # LEARNING POINT, I messed up dropping dissolve_col because it was the INDEX, and thus was not in dissolved_gdf.columns
            # dissolved_gdf = dissolved_gdf[[i for i in dissolved_gdf.columns if i != 'dissolve_col']]
            dissolved_gdf.set_index('pyramid_id', inplace=True)

        # Writing logic: if no output path given, rename input path to displacement path then write on input path.
        if output_path:
            hb.create_directories(os.path.split(str(output_path))[0])

            if dissolved_gdf is not None:
                try:
                    dissolved_gdf = dissolved_gdf[[i for i in dissolved_gdf.columns if i != 'dissolve_col']]
                    dissolved_gdf.to_file(str(output_path), driver='GPKG')
                except NameError as e:
                    raise NameError('Unable to write GPKG. Encountered exception: ' + str(e))

                try:
                    gdf.to_file(hb.suri(str(output_path), 'pre_dissolve'), driver='GPKG')
                except NameError as e:
                    raise NameError('Unable to write GPKG. Encountered exception: ' + str(e))
            else:

                try:
                    gdf.to_file(str(output_path), driver='GPKG')
                except NameError as e:
                    raise NameError('Unable to write GPKG. Encountered exception: ' + str(e))

        else:
            if dissolved_gdf is not None:
                try:
                    dissolved_gdf.to_file(temp_write_path, driver='GPKG')
                except NameError as e:
                    raise NameError('Unable to write GPKG. Encountered exception: ' + str(e))

                try:
                    gdf.to_file(hb.suri(input_path, 'pre_dissolve'), driver='GPKG')
                except NameError as e:
                    raise NameError('Unable to write GPKG. Encountered exception: ' + str(e))
            else:
                try:
                    gdf.to_file(temp_write_path, driver='GPKG')
                except NameError as e:
                    raise NameError('Unable to write GPKG. Encountered exception: ' + str(e))

            if os.path.exists(temp_write_path):
                os.rename(input_path, displacement_path)
                os.rename(temp_write_path, input_path)

def resample_via_pyramid_overviews(input_path, output_resolution, output_path, force_overview_rewrite=False, overview_resampling_algorithm=None, new_ndv=None,
                                   overview_data_types=None, assert_pyramids=True, scale_array_by_resolution_change=False):
    if assert_pyramids:
        hb.assert_path_global_pyramid(input_path)
    output_shape = hb.pyramid_compatable_shapes[output_resolution]
    raster_statistics = hb.read_raster_stats(input_path)
    input_deg_resolution = hb.get_cell_size_from_path(input_path)
    input_resolution = hb.pyramid_compatible_resolution_to_arcseconds[input_deg_resolution]

    input_resolution = hb.determine_pyramid_resolution(input_path)
    input_resolution_in_arcseconds = hb.pyramid_compatible_resolution_to_arcseconds[input_resolution]
    overview_level = None
    if overview_data_types is None:
        overview_data_types = hb.get_datatype_from_uri(input_path)

    if 'overviews' in raster_statistics:
        for c, i in enumerate(raster_statistics['overviews']):
            if output_shape == i['size']:
                overview_level = c

    if overview_level is None or force_overview_rewrite:
        L.info('resample_via_pyramid_overviews triggered rewrite of overviews. overview_level', overview_level, 'force_overview_rewrite', force_overview_rewrite)

        if output_resolution not in hb.pyramid_compatible_overview_levels:
            raise NameError('resample_via_pyramid_overviews on', input_path, 'did not seem to need overviews. Is it already low res?')

        if new_ndv is not None:

            old_ndv = hb.get_ndv_from_path(input_path)
            temp_path = hb.temp()

            # TODOOO, the binary data type wasn't working on this type of data because it was still in byte format and thus the average failed.
            hb.raster_calculator_flex(input_path, lambda x: np.where(x == old_ndv, new_ndv, x), temp_path, datatype=overview_data_types)
            hb.set_ndv_in_raster_header(input_path, new_ndv)
            hb.swap_filenames(input_path, temp_path)

        hb.add_overviews_to_path(input_path, specific_overviews_to_add=hb.pyramid_compatible_overview_levels[input_resolution_in_arcseconds],
                                 overview_resampling_algorithm=overview_resampling_algorithm, make_pyramid_compatible=True)

        # Get the specific overview_level from where they output resolution was in the dictionary.
        # NOTE the cool but confusing method by which i get the position in the resample list via the ratio of arcescond resolutions.
        # this works because overview levels are defined as multiples of the input resolution.
        overview_level =  list(hb.pyramid_compatible_overview_levels[input_resolution_in_arcseconds]).index(int(output_resolution / input_resolution_in_arcseconds))


        L.info('Rewrote overviews and set overview_level to', overview_level)
    ds = gdal.OpenEx(input_path)
    band = ds.GetRasterBand(1)
    overview_band = band.GetOverview(overview_level)
    overview_array = overview_band.ReadAsArray()

    if scale_array_by_resolution_change:
        scaler = (output_resolution / input_resolution_in_arcseconds) ** 2
        L.info('Multiplying resampled output by ', scaler, 'based on difference in resolutions. This means you are multiplying something that is in a fixed areal, like hectares, which will change when the resolution changes.')
        overview_array *= scaler

    n_rows, n_cols = overview_array.shape
    hb.save_array_as_geotiff(overview_array, output_path, input_path, n_cols=n_cols, n_rows=n_rows, geotransform_override=hb.pyramid_compatible_geotransforms[output_resolution])



    # if output_resolution in [i['size'] for i in raster_statistics['overviews']]:

def make_path_global_pyramid(
        input_path,
        output_path=None,
        make_overviews=True,
        overwrite_overviews=False,
        calculate_stats=True,
        overwrite_stats=False,
        fill_to_global_extent=False, # NYI and BROKEN!
        clean_temporary_files=False,
        raise_exception=False,
        make_overviews_external=True,
        set_ndv_below_value=None,
        write_unique_values_list=False,
        overview_resample_method=None,
        is_id_raster=False,
        verbose=False
):
    ### TODO Make this identical to the relevant part of make_path_pog
    print('CONSIDER ALSO make_paths_cog or pog.')
    """Throw exception if input_path is not pyramid-ready. This requires that the file be global, geographic projection, and with resolution
    that is a factor/multiple of arcdegrees.

    If output_path is specified, write to that location. Otherwise, make changes in-place but saving a temporary backup file of the input.

    # LEARNING POINT: Able to access specific overview bands!
    # ovr_band = src_ds.GetRasterBand(i).GetOverview(1)

    write_unique_values_list = True makes it write to the xml stats file a comma separated list of unique values
    """

    # TODOO write_unique_values_list unimplemented but good idea for fasterstats.
    if verbose:
        L.info('Running make_path_global_pyramid on ' + str(input_path))

    resolution = hb.determine_pyramid_resolution(input_path)
    arcseconds = pyramid_compatible_resolution_to_arcseconds[resolution]

    ds = gdal.OpenEx(input_path)
    n_c, n_r = ds.RasterXSize, ds.RasterYSize
    orginal_n_c, orginal_n_r = ds.RasterXSize, ds.RasterYSize
    gt = ds.GetGeoTransform()

    orginal_gt = gt
    ulx, xres, _, uly, _, yres = gt[0], gt[1], gt[2], gt[3], gt[4], gt[5]
    orginal_ulx, orginal_xres, _, orginal_uly, _, orginal_yres = gt[0], gt[1], gt[2], gt[3], gt[4], gt[5]
    if verbose:
        L.info('   ulx: ' + str(ulx) + ', uly: ' + str(uly) + ', xres: ' + str(xres) + ', yres: ' + str(yres) + ', n_c: ' + str(n_c) + ', n_r: ' + str(n_r))

    if fill_to_global_extent:
        if verbose:
            L.info('Filling to global extent with value ' + str(fill_to_global_extent))
        ulx = -180.0
        uly = 90.0
        


    if -180.001 < ulx < -179.999:
        ulx = -180.0
    if 90.001 > uly > 89.999:
        uly = 90.0

    if ulx != -180.0 or uly != 90.0:
        result_string = 'Input path not pyramid ready because UL not at -180 90 (or not close enough): ' + str(input_path) +'. \n    Instead they were: ' + str(ulx) + ', ' + str(uly)
        if raise_exception:
            raise NameError(result_string)
        else:
            L.info(result_string)
            return False
    
    changed_extent = False
    if fill_to_global_extent:
        lrx = 180.0
        lry = -90.0
        n_c = int((lrx - ulx) / resolution)
        n_r = int((uly - lry) / resolution)
        changed_extent = True
    else:        
        lrx = ulx + resolution * n_c
        lry = uly + -1.0 * resolution * n_r

    if lrx != 180.0 or lry != -90.0:

        result_string = 'Input path not pyramid ready because its not the right size: ' + str(input_path) + '\n    ulx ' + str(ulx) + ', xres ' + str(xres) + ', uly ' + str(uly) + ', yres ' + str(yres) + ', lrx ' + str(lrx) + ', lry ' + str(lry)
        if raise_exception:
            raise NameError(result_string)
        else:
            L.warning(result_string)
            return False

    output_geotransform = pyramid_compatible_geotransforms[arcseconds]
    ds = None

    if output_geotransform != gt and fill_to_global_extent is None:
        L.warning('Changing geotransform of ' + str(input_path) + ' to ' + str(output_geotransform) + ' from ' + str(gt))

    # hb.set_geotransform_to_tuple(input_path, output_geotransform)
    if not hb.path_exists(input_path):
        raise NameError('Unable to find input_path ' + str(input_path) + ' with absolute path ' + str(os.path.abspath(input_path)))
    ds = gdal.OpenEx(input_path, gdal.OF_RASTER)
    md = ds.GetMetadata()
    image_structure = ds.GetMetadata('IMAGE_STRUCTURE')
    compression = image_structure.get('COMPRESSION', None)
    if verbose:
        L.info('Compression of ' + str(input_path) + ': ' + str(compression))

    # Consider operations that may need rewriting the underlying data
    rewrite_array = False

    # Check if compressed (pyramidal file standards require compression)
    if str(compression).lower() not in  ['zstd']:
        L.critical('rewrite_array triggered because compression was not deflate.')
        rewrite_array = True

    data_type = ds.GetRasterBand(1).DataType
    ndv = ds.GetRasterBand(1).GetNoDataValue()

    if 6 <= data_type < 12:
        options = (
            'TILED=YES',
            'BIGTIFF=YES',
            'COMPRESS=ZSTD',
            'BLOCKXSIZE=512',
            'BLOCKYSIZE=512',
        )
    else:
        options = hb.globals.DEFAULT_GTIFF_CREATION_OPTIONS

    new_ndv = False
    below_ndv = False
    if verbose:
        L.info('input data_type: ' + str(data_type) + ', input ndv: ' + str(ndv))
        
    correct_ndv = hb.get_correct_ndv_from_dtype_flex(data_type, is_id=is_id_raster)
    if float(ndv) != float(correct_ndv):
        old_ndv = ndv
        ndv = correct_ndv
        L.critical('rewrite_array triggered because ndv was not 255 and datatype was 1.')
        rewrite_array = True
        new_ndv = True
    else:
        # rewrite_array = False
        new_ndv = False
                

            
    if set_ndv_below_value is not None:
        rewrite_array = True

                
    if changed_extent:
        L.info('Changed extent of ' + str(input_path) + ' to global extent. New extent is ' + str(ulx) + ', ' + str(uly) + ', ' + str(lrx) + ', ' + str(lry))
        rewrite_array = True

    if verbose:
        L.info('output data_type: ' + str(data_type) + ', output ndv: ' + str(ndv))

    # ds.SetMetadataItem('last_processing_on', str(time.time()))

    ds = None
    if verbose:
        L.info('rewrite_array ' + str(rewrite_array))

    displacement_path = hb.temp('.tif', filename_start='displaced_by_make_path_global_pyramid_on_' + str(hb.file_root(input_path)), folder=os.path.split(input_path)[0], remove_at_exit=clean_temporary_files)
    temp_write_path = hb.temp('.tif', filename_start='temp_write_' + str(hb.file_root(input_path)), folder=os.path.split(input_path)[0], remove_at_exit=clean_temporary_files)

    if rewrite_array:
        L.info('make_path_global_pyramid triggered rewrite_array for ' + str(input_path))
        if changed_extent:
            dst_size = (n_c, n_r)
            # Create a raster with just the fill value but with a global extent
            if fill_to_global_extent == 'ndv':
                final_fill_to_global_extent_value = ndv
            else:
                final_fill_to_global_extent_value = fill_to_global_extent
            warp_add_padding(input_path, displacement_path, output_geotransform, dst_size, final_fill_to_global_extent_value)
            input_path = displacement_path
            
        def sanitize_array(x):
            x = x.astype(hb.gdal_number_to_numpy_type[data_type])

            if new_ndv is True:
                x = np.where(np.isclose(x, old_ndv), ndv, x)
            if set_ndv_below_value is not None:
                x[x < set_ndv_below_value] = ndv
            return x

        hb.raster_calculator_flex(input_path, sanitize_array, temp_write_path, datatype=data_type, ndv=ndv, gtiff_creation_options=options)
 

    # Rename files to displace old input. This has to be done before external-file operations are completed.
    if output_path:
        if rewrite_array:
            hb.create_directories(os.path.split(output_path)[0])
            os.rename(temp_write_path, output_path)
            processed_path = output_path
        else:
            processed_path = output_path
            hb.path_copy(input_path, processed_path)
    else:
        if os.path.exists(temp_write_path):
            os.rename(input_path, displacement_path)
            os.rename(temp_write_path, input_path)
        processed_path = input_path

   # Do metadata and compression tasks
    if make_overviews_external:
        ds = gdal.OpenEx(processed_path)
    else:
        ds = gdal.OpenEx(processed_path, gdal.GA_Update)

    # make_rat = False  # Arcaic form from ESRI, KEPT FOR REFERENCE ONLY. And hilarity.
    # if make_rat:
    #     rat = gdal.RasterAttributeTable()
    #
    #     attr_dict = {0: 0, 1: 11, 2: 22}
    #     column_name = 'values'
    #
    #     rat.SetRowCount(len(attr_dict))
    #
    #     # create columns
    #     rat.CreateColumn('Value', gdal.GFT_Integer, gdal.GFU_MinMax)
    #     rat.CreateColumn(column_name, gdal.GFT_String, gdal.GFU_Name)
    #
    #     row_count = 0
    #     for key in sorted(attr_dict.keys()):
    #         rat.SetValueAsInt(row_count, 0, int(key))
    #         rat.SetValueAsString(row_count, 1, attr_dict[key])
    #         row_count += 1
    #
    #     ds.GetRasterBand(1).SetDefaultRAT(rat)

    gdal.SetConfigOption('COMPRESS_OVERVIEW', 'DEFLATE')
    # gdal.SetConfigOption('USE_RRD', 'YES')  # FORCE EXTERNAL ,possibly as ovr? # USE_RRD is outdated (saves x.aux file). If you want external, just make sure you open the DS in read only.

    if overview_resample_method is None:
        if data_type <= 5 or data_type in [12, 13]:
            overview_resample_method = 'NEAREST'
        else:
            overview_resample_method = 'AVERAGE'

    #TODOO FEATURE IDEA, have multiple types of overviews, mean, min, max, nearest for extremely quick reference to statistics at different scales.
    if make_overviews or overwrite_overviews:
        if not os.path.exists(processed_path + '.ovr') or overwrite_overviews:
            if verbose:
                L.info('Starting to make overviews for ' + str(processed_path))

            band = ds.GetRasterBand(1)
            callback = hb.make_logger_callback("Creation of overviews in hb.spatial_utils.make_path_global_pyramid() %.1f%% complete %s for%s")

            ds.BuildOverviews(overview_resample_method, pyramid_compatible_overview_levels[arcseconds], callback, [input_path])  # Based on commonly used data shapes

    if calculate_stats or overwrite_stats:
        if not os.path.exists(processed_path + '.aux.xml') or overwrite_overviews:
            if verbose:
                L.info('Starting to calculate stats for ' + str(processed_path))
            ds.GetRasterBand(1).ComputeStatistics(False)  # False here means approx NOT okay
            ds.GetRasterBand(1).GetHistogram(approx_ok=0)
    ds = None
    return True


def warp_add_padding(input_path, output_path, dst_geotransform, dst_columns_rows_tuple, fill_value, resample_method='near'):
    # dst_size is in number of pixels
    
    dataset = gdal.Open(input_path)
    geotransform = dataset.GetGeoTransform()
    
    dataset.SetGeoTransform(dst_geotransform)
    width = dst_columns_rows_tuple[0] * dst_geotransform[1]
    height = dst_columns_rows_tuple[1] * dst_geotransform[1]

    # Calculate new bounds based on the padding
    xmin = dst_geotransform[0]
    ymax = dst_geotransform[3]
    xmax = xmin + width
    ymin = ymax - height 


    # def progress_callback(complete, message, user_data):
    #     """ Reports progress more frequently during a GDAL operation. """
    #     global last_reported
    #     fine_grained_progress = int(complete * 10000)  # Scale up to report 100x more

    #     if fine_grained_progress > last_reported:  # Only report new progress values
    #         last_reported = fine_grained_progress
    #         print(f"\rProgress: {complete*100:.3f}% completed.", end="", flush=True)

    #     return 1          
    def progress_callback(complete, message, user_data):
        """ Reports progress of a GDAL operation. """
        print(f"Progress: {complete*100:.3f}% completed.", end="")
        return 1  # Returning 1 continues, 0 would cancel the operation

    # Execute gdalwarp with the new bounds
    make_it_cog = True
    if make_it_cog:
        
        # warp_options = gdal.WarpOptions(
        #     format="COG",  # Directly create a Cloud Optimized GeoTIFF
        #     outputBounds=[xmin, ymin, xmax, ymax],
        #     creationOptions=[
        #         "COMPRESS=DEFLATE",  # Efficient compression
        #         "PREDICTOR=2",       # Optimized for floating point data
        #         "BIGTIFF=YES"        # Ensure large file support
        #     ],
        #     dstNodata=fill_value,
        #     callback=progress_callback
        # )

        warp_options = gdal.WarpOptions(
            format='GTiff',
            outputBounds=[xmin, ymin, xmax, ymax],
            resampleAlg=resample_method,
            creationOptions=[
                "TILED=YES",
                "COMPRESS=DEFLATE",
                "PREDICTOR=2",
                "BIGTIFF=YES",
                "NUM_THREADS=ALL_CPUS",
                # "COPY_SRC_OVERVIEWS=NO"
            ],
            dstNodata=fill_value,
            callback=progress_callback
        )

    else:
        warp_options = gdal.WarpOptions(format='GTiff', outputBounds=[xmin, ymin, xmax, ymax], creationOptions=hb.DEFAULT_GTIFF_CREATION_OPTIONS, dstNodata=fill_value, callback=progress_callback)


    gdal.Warp(output_path, dataset, options=warp_options)

    dataset = None  # Close the dataset


def make_dir_global_pyramid(input_dir, output_path=None, make_overviews=True, calculate_stats=True, clean_temporary_files=False,
                            resolution=None, raise_exception=False, make_overviews_external=True, verbose=True):
    """Throw exception if input_path is not pyramid-ready. This requires that the file be global, geographic projection, and with resolution
    that is a factor/multiple of arcdegrees.

    If output_path is specified, write to that location. Otherwise, make changes in-place but saving a temporary backup file of the input.

    # LEARNING POINT
    # ovr_band = src_ds.GetRasterBand(i).GetOverview(1)
    """
    L.critical('A bit outdated because doesnt use parallel approach found in make_paths_list_global_pyramid')
    for file_path in hb.list_filtered_paths_nonrecursively(input_dir, include_extensions='.tif'):
        hb.make_path_global_pyramid(file_path, output_path=output_path, make_overviews=make_overviews, calculate_stats=calculate_stats, clean_temporary_files=clean_temporary_files,
                                    raise_exception=raise_exception, make_overviews_external=make_overviews_external, verbose=verbose)


def make_path_spatially_clean(input_path,
                              output_path=None,
                              make_overviews=True,
                              overwrite_overviews=False,
                              calculate_stats=True,
                              overwrite_stats=False,
                              clean_temporary_files=False,
                              raise_exception=False,
                              make_overviews_external=True,
                              set_ndv_below_value=None,
                              write_unique_values_list=False,
                              overview_resample_method=None,
                              verbose=False
                              ):
    L.critical('DEPRECATED because hasnt been updated with newest things from make_path_global_pyramid. MOREOVER ')

    """Similar to make_path_global_pyramid, except doesnt change anything that would alter the data.
    Specifically, it only changes (optionally) compression, overviews, and NDV (based on observed data_type."""
    ds = gdal.OpenEx(input_path, gdal.GA_Update)
    n_c, n_r = ds.RasterXSize, ds.RasterYSize
    output_geotransform = ds.GetGeoTransform()
    # TODO This is outdated compared to advances made in make_path_global_pyramid.
    md = ds.GetMetadata()
    image_structure = ds.GetMetadata('IMAGE_STRUCTURE')
    compression = image_structure.get('COMPRESSION', None)

    # Consider operations that may need rewriting the underlying data
    rewrite_array = False
    compression_method = 'ZSTD'
    # Check if compressed (pyramidal file standards require compression)
    if str(compression).lower() != compression_method.lower():
        rewrite_array = True

    L.info('Running make_path_spatially_clean on ' + str(input_path))
    data_type = ds.GetRasterBand(1).DataType
    ndv = ds.GetRasterBand(1).GetNoDataValue()
    ds.SetMetadataItem('last_processing_on', str(time.time()))
    # ds = None

    if 6 <= data_type < 12:
        options = (
            'BIGTIFF=YES',
            'COMPRESS=' + str(compression_method).upper(),
            'BLOCKXSIZE=256',
            'BLOCKYSIZE=256',
            'TILED=YES',
            # 'PREDICTOR=3', #
        )
    else:
        options = hb.globals.DEFAULT_GTIFF_CREATION_OPTIONS


    new_ndv = False
    below_ndv = False
    if verbose:
        L.info('input data_type: ' + str(data_type) + ', input ndv: ' + str(ndv))
    correct_ndv = 'fix'
    if float(ndv) != float(correct_ndv):
        old_ndv = ndv
        ndv = correct_ndv
        L.critical('rewrite_array triggered because ndv was not 255 and datatype was 1.')
        rewrite_array = True
        new_ndv = True
    else:
        rewrite_array = False
        new_ndv = False
                

    L.info('output data_type: ' + str(data_type) + ', output ndv: ' + str(ndv))



    ds = None

    L.info('rewrite_array ' + str(rewrite_array))
    temp_write_path = hb.temp('.tif', filename_start='temp_write_' + str(hb.file_root(input_path)), remove_at_exit=clean_temporary_files)
    displacement_path = hb.temp('.tif', filename_start='displaced_by_make_path_global_pyramid_on_' + str(hb.file_root(input_path)), remove_at_exit=clean_temporary_files)

    if rewrite_array:

        input_ds = gdal.OpenEx(input_path)

        driver = gdal.GetDriverByName('GTiff')
        new_ds = driver.Create(temp_write_path, n_c, n_r, 1, data_type, options=options)
        new_ds.SetGeoTransform(output_geotransform)
        new_ds.SetProjection(hb.wgs_84_wkt)
        new_ds.GetRasterBand(1).SetNoDataValue(ndv)
        read_callback = hb.make_logger_callback("ReadAsArray percent complete:")
        write_callback = hb.make_logger_callback("WriteArray percent complete:")
        array = input_ds.ReadAsArray(callback=read_callback, callback_data=[output_path]).astype(hb.gdal_number_to_numpy_type[data_type])

        if new_ndv and  set_ndv_below_value is None:
            np.where(np.isclose(array, old_ndv), ndv, array)
            # array[array == old_ndv] = ndv

        if set_ndv_below_value is not None:
            # array = np.where(array < set_ndv_below_value, ndv, array)
            array[array < set_ndv_below_value] = ndv


        new_ds.GetRasterBand(1).WriteArray(array, callback=write_callback, callback_data=[output_path])

        input_ds = None
        new_ds = None

        # Rename files to displace old input. This has to be done before external-file operations are completed.
        os.rename(input_path, displacement_path)
        os.rename(temp_write_path, input_path)
    # Rename files to displace old input. This has to be done before external-file operations are completed.
    if output_path:
        hb.create_directories(os.path.split(output_path)[0])
        os.rename(temp_write_path, output_path)
        processed_path = output_path
    else:
        if os.path.exists(temp_write_path):
            os.rename(input_path, displacement_path)
            os.rename(temp_write_path, input_path)
        processed_path = input_path

    # Do metadata and compression tasks
    if make_overviews_external:
        ds = gdal.OpenEx(input_path)
    else:
        ds = gdal.OpenEx(input_path, gdal.GA_Update)

    gdal.SetConfigOption('COMPRESS_OVERVIEW', 'DEFLATE')
    # gdal.SetConfigOption('USE_RRD', 'YES')  # FORCE EXTERNAL ,possibly as ovr? # USE_RRD is outdated (saves x.aux file). If you want external, just make sure you open the DS in read only.

    if make_overviews or overwrite_overviews:
        if not os.path.exists(processed_path + '.ovr') or overwrite_overviews:
            if verbose:
                L.info('Starting to make overviews for ' + str(processed_path))
            ds.BuildOverviews('nearest', [2, 4, 8, 16, 32])  # Based on commonly used data shapes

    if calculate_stats or overwrite_stats:
        if not os.path.exists(processed_path + '.aux.xml') or overwrite_overviews:
            if verbose:
                L.info('Starting to calculate stats for ' + str(processed_path))
            ds.GetRasterBand(1).ComputeStatistics(False)  # False here means approx NOT okay
            ds.GetRasterBand(1).GetHistogram(approx_ok=0)

 
    ds = None
    return True

def add_statistics_to_raster(input_path, verbose=False):
    
    # DEPRECATED in favor of:
    hb.add_stats_to_geotiff_with_gdal
    try:
        ds = gdal.OpenEx(input_path)
    except Exception as e:
        raise NameError('Missing path: ' + str(input_path) + ' raised exception ' + str(e))
    if verbose:
        L.info('Starting to calculate stats for ' + str(input_path))
    ds.GetRasterBand(1).ComputeStatistics(False)  # False here means approx NOT okay
    ds.GetRasterBand(1).GetHistogram(approx_ok=0)

    ds = None

def compress_path(input_path, clean_temporary_files=False):
    hb.make_path_spatially_clean(input_path, make_overviews=False, calculate_stats=False, clean_temporary_files=clean_temporary_files)

def assert_paths_same_pyramid(path_1, path_2, raise_exception=False, surpress_output=False):

    if hb.path_exists(path_1):
        bool_1 = hb.is_path_global_pyramid(path_1)
    else:
        hb.log('Not the same pyramid because path 1 does not exist: ' + str(path_1))
        return False
    if hb.path_exists(path_2):
        bool_2 = hb.is_path_global_pyramid(path_2)
    else:    
        hb.log('Not the same pyramid because path 2 does not exist: ' + str(path_2))
        return False        
    bool_3 = hb.is_path_same_geotransform(path_1, path_2, raise_exception=raise_exception, surpress_output=surpress_output)

    results = [bool_1, bool_2, bool_3]
    if all(results):
        return True
    else:
        result_string = '\nPaths not pyramidal:\n' + str(path_1) + '\n' + str(path_2)
        if raise_exception:
            if raise_exception:
                raise NameError(result_string)
            else:
                L.critical(result_string)
                return False


def set_geotransform_to_tuple(input_path, desired_geotransform, output_path=None):
    """
    FROM CONFIG:
    geotransform_global_5m = (-180.0, 0.08333333333333333, 0.0, 90.0, 0.0, -0.08333333333333333)  # NOTE, the 0.08333333333333333 is defined very precisely as the answer a 64 bit compiled python gives from the answer 1/12 (i.e. 5 arc minutes)
    geotransform_global_30s = (-180.0, 0.008333333333333333, 0.0, 90.0, 0.0, -0.008333333333333333)  # NOTE, the 0.008333333333333333 is defined very precisely as the answer a 64 bit compiled python gives from the answer 1/120 (i.e. 30 arc seconds) Note that this has 1 more digit than 1/12 due to how floating points are stored in computers via exponents.
    geotransform_global_10s = (-180.0, 0.002777777777777778, 0.0, 90.0, 0.0, -0.002777777777777778)  # NOTE, the 0.002777777777777778 is defined very precisely
    """
    
    if output_path is None:
        ds = gdal.OpenEx(input_path, gdal.GA_Update)
        gt = ds.GetGeoTransform()
        ds.SetGeoTransform(desired_geotransform)
        gt = ds.GetGeoTransform()
        ds = None
    else:
        hb.path_copy(input_path, output_path)
        ds = gdal.OpenEx(output_path, gdal.GA_Update)
        gt = ds.GetGeoTransform()
        ds.SetGeoTransform(desired_geotransform)
        gt = ds.GetGeoTransform()
        ds = None
                
        ## LEARNING POINT: INITIALLY TRIED BELOW BUT ABOVE WAS A FASTER OPTION WAS JUST TO COPY AND THEN RESET THE GEOTRANSFORM
        # ds = gdal.OpenEx(input_path)
        # driver = gdal.GetDriverByName('GTiff')
        # new_ds = driver.Create(output_path, ds.RasterXSize, ds.RasterYSize, 1, ds.GetRasterBand(1).DataType, options=hb.DEFAULT_GTIFF_CREATION_OPTIONS)
        # new_ds.SetGeoTransform(desired_geotransform)
        # new_ds.SetProjection(ds.GetProjection())
        # array = ds.GetRasterBand(1).ReadAsArray()
        # new_ds.GetRasterBand(1).WriteArray(array)
        # new_ds = None
        # ds = None

def change_array_datatype_and_ndv(input_path, output_path, data_type, input_ndv=None, output_ndv=None):
    output_data_type_numpy = hb.gdal_number_to_numpy_type[data_type]
    if input_ndv is None:
        input_ndv = hb.get_ndv_from_path(input_path)
    if output_ndv is None:
        output_ndv = hb.no_data_values_by_gdal_number[data_type]
    output_ndv = np.float64(output_ndv)
    hb.raster_calculator_flex(input_path, lambda x: np.where(x == input_ndv, output_ndv, x).astype(output_data_type_numpy), output_path, datatype=data_type, ndv=output_ndv)


def set_projection_to_wkt(input_path, desired_projection_wkt):
    ds = gdal.OpenEx(input_path, gdal.GA_Update)
    ds.SetProjection(desired_projection_wkt)
    ds = None

def load_geotiff(input_path, raise_all_exceptions=False):
    callback = hb.make_logger_callback("load_geotiff %.1f%% complete %s")
    ds = gdal.OpenEx(input_path)
    if ds is None:
        raise NameError("Cannot use gdal.OpenEx on " + str(input_path) + ' in load_geotiff. Probably the file doesnt exist.')

    try:
        a = ds.ReadAsArray(callback=callback, callback_data=[input_path])
    except:
        L.critical('Failed to ReadAsArray in load_geotiff for ' + str(input_path))

    return a

def load_geotiff_chunk_by_cr_size(input_path, cr_size, stride_rate=None, datatype=None, output_path=None, ndv=None, raise_all_exceptions=False):
    """Convenience function to load a chunk of an array given explicit row and column info."""

    ds = gdal.OpenEx(input_path)
    # C:\Users\jajohns\Files\seals\projects\custom_coarse_algorithm_20250418_104912\intermediate\restoration\coarse_simplified_projected_ha_difference_from_previous_year\ssp2\rcp45\luh2-message\bau\2030\urban_2030_2017_ha_diff_ssp2_rcp45_luh2-message_bau.tif
    # C:\Users\jajohns\Files\seals\projects\custom_coarse_algorithm_20250418_104912\intermediate\restoration\coarse_simplified_projected_ha_difference_from_previous_year\ssp2\rcp45\luh2-message\policy\2030\urban_2030_2017_ha_diff_ssp2_rcp45_luh2-message_policy.tif"
    # C:\Users\jajohns\Files\Research\cge\seals\projects\test_seals_magpie\intermediate\magpie_as_seals7_proportion\rcp45_ssp2\2050\SSP2_BiodivPol_ClimPol_NCPpol_LPJmL5\magpie_crop_2050_2015_ha_difference.tif 
    if ds is None:
        mod_path = os.path.split(input_path)[0].replace('/', '\\')
        raise NameError("Cannot find " + str(input_path) + ' in load_geotiff_chunk_by_cr_size.')
        # raise NameError("Cannot find " + str(input_path) + " in dir:\n\tFile \"" + mod_path + "\\\", line 1")
    n_c, n_r = ds.RasterXSize, ds.RasterYSize
    c = int(cr_size[0])
    r = int(cr_size[1])
    c_size = int(cr_size[2])
    r_size = int(cr_size[3])

    if stride_rate:
        if stride_rate > 1:
            L.debug('load_geotiff_chunk_by_cr_size with stride rate ' + str(stride_rate) + ' on ' + input_path)

    if stride_rate is None:
        stride_rate = 1


    if not 0 <= r <= n_r:
        raise NameError('r given to load_geotiff_chunk_by_cr_size didnt fit. r, n_r: ' + str(r) + ' ' + str(n_r) + ' for path ' + input_path)

    if not 0 <= c <= n_c:
        raise NameError('c given to load_geotiff_chunk_by_cr_size didnt fit. c, n_c: ' + str(c) + ' ' + str(n_c) + ' for path ' + input_path)

    if not 0 <= r + r_size / stride_rate <= n_r:
        raise NameError('r_size given to load_geotiff_chunk_by_cr_size didnt fit. r_size, n_r: ' + str(r_size) + ' ' + str(n_r) + ' for path ' + input_path)

    if not 0 <= c + c_size / stride_rate <= n_c:
        raise NameError('c given to load_geotiff_chunk_by_cr_size didnt fit. c, n_c: ' + str(c_size) + ' ' + str(n_c) + ' for path ' + input_path)

    # callback = hb.make_logger_callback("load_geotiff_chunk_by_cr_size %.1f%% complete %s")
    # callback = hb.invoke_timed_callback("load_geotiff_chunk_by_cr_size %.1f%% complete %s")
    # callback = hb.make_simple_gdal_callback("load_geotiff_chunk_by_cr_size %.1f%% complete %s")
    # # hb.load_gdal_ds_as_strided_array()
    # ds = gdal.Open(input_path)
    # band = ds.GetRasterBand(1)
    # array = band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize, buf_xsize=int(ds.RasterXSize / stride_rate), buf_ysize=int(ds.RasterYSize / stride_rate))
    #
    # band = None
    # gdal.Dataset.__swig_destroy__(ds)
    # ds = None
    # return array

    callback = hb.make_logger_callback("load_geotiff_chunk_by_cr_size %.1f%% complete %s")
    buf_xsize = int(c_size / stride_rate)
    buf_ysize = int(r_size / stride_rate)
    if raise_all_exceptions:
        a = ds.ReadAsArray(c, r, c_size, r_size, buf_xsize=buf_xsize,
                           buf_ysize=buf_ysize, buf_type=datatype, callback=callback, callback_data=[input_path])
    else:
        fail = 1
        if fail:
            a = ds.ReadAsArray(c, r, c_size, r_size, buf_xsize=buf_xsize,
                               buf_ysize=buf_ysize, buf_type=datatype, callback=callback, callback_data=[input_path])
        else:
            try:
                a = ds.ReadAsArray(c, r, c_size, r_size, buf_xsize=buf_xsize,
                                   buf_ysize=buf_ysize, buf_type=datatype, callback=callback, callback_data=[input_path])
            except:
                L.critical('Failed to ReadAsArray in load_geotiff_chunk_by_cr_size for ' + str(input_path))

    if output_path is not None:

        if datatype is not None:
            data_type = datatype
        # else:
        #     data_type = hb.get_datatype_from_uri(input_path)

        if not isinstance(datatype, int):
            try:
                data_type = hb.get_datatype_from_uri(input_path)
            except:
                data_type = hb.numpy_type_to_gdal_number[hb.get_datatype_from_uri(input_path)]

        src_ndv = hb.get_ndv_from_path(input_path)
        if ndv is None:
            ndv = hb.get_ndv_from_path(input_path)

        if ndv != src_ndv:
            a = np.where(np.isclose(a, src_ndv), ndv, a)

        gt = list(hb.get_geotransform_uri(input_path))
        lat, lon = hb.rc_path_to_latlon(r, c, input_path)
        gt[0] = lon
        gt[3] = lat
        geotransform_override = gt
        projection_override = hb.get_dataset_projection_wkt_uri(input_path)
        n_cols_override, n_rows_override = (c_size, r_size)

        if output_path is True:
            output_path = hb.temp('.tif')

        hb.save_array_as_geotiff(a, output_path, data_type=data_type, ndv=ndv, geotransform_override=geotransform_override,
                                 projection_override=projection_override, n_cols_override=n_cols_override, n_rows_override=n_rows_override)

    return a

def load_geotiff_chunk_by_bb(input_path, bb, inclusion_behavior='centroid', stride_rate=None, datatype=None, output_path=None, ndv=None, raise_all_exceptions=False):
    """Load a geotiff chunk as a numpy array from input_path. Requires that input_path be pyramid_ready. If datatype given,
    returns the numpy array by GDAL number, defaulting to the type the data was saved as.

    If BB is none, loads the whole array.

    Inclusion_behavior determines how cells that are only partially within the bb are considered. Default is centroid, but can be exclusive or exclusive.

    inclusion_behavior = one of 'centroid', 'inclusive', 'exclusive'

    if given output_path will make it write there (potentially EXTREMELY computaitonally slow)
    if output_path is True and not a string, will save to a atemp file.
     """
     
    if not hb.path_exists(input_path):
        raise NameError('load_geotiff_chunk_by_bb unable to open ' + str(input_path))
    c, r, c_size, r_size = hb.bb_path_to_cr_size(input_path, bb, inclusion_behavior=inclusion_behavior)
    L.debug('bb_path_to_cr_widthheight generated', c, r, c_size, r_size)

    a = hb.load_geotiff_chunk_by_cr_size(input_path, (c, r, c_size, r_size), stride_rate=stride_rate, datatype=datatype, raise_all_exceptions=raise_all_exceptions)

    if output_path is not None:

        data_type = hb.get_datatype_from_uri(input_path)

        src_ndv = hb.get_ndv_from_path(input_path)
        if ndv is None:
            ndv = hb.get_ndv_from_path(input_path)

        if ndv != src_ndv:
            a = np.where(np.isclose(a, src_ndv), ndv, a)

        gt = list(hb.get_geotransform_uri(input_path))
        gt[0] = bb[0]
        gt[3] = bb[3]
        geotransform_override = gt
        projection_override = hb.get_dataset_projection_wkt_uri(input_path)
        n_cols_override, n_rows_override = (c_size, r_size)

        if output_path is True:
            output_path = hb.temp('.tif')

        hb.save_array_as_geotiff(a, output_path, data_type=data_type, ndv=ndv, geotransform_override=geotransform_override,
                                 projection_override=projection_override, n_cols_override=n_cols_override, n_rows_override=n_rows_override)

    return a

def bb_path_to_cr_size(input_path, bb, inclusion_behavior='centroid'):
    """input path of larger file from which bb cuts."""
    # BB must be in lat-lon units (not projected units yet) in xmin, ymin, xmax, ymax order
    # Useful for getting gdal-type cr_widthheight from a subset of a raster via it's bb from path.
    # Note that gdal Open uses col, row, n_cols, n_row notation. This function converts lat lon bb to rc in this order based on the proportional size of the input_path.

    if not os.path.exists(input_path):
        L.warning('bb_path_to_cr_size unable to open ' + str(input_path))
    ds = gdal.OpenEx(input_path)
    n_c, n_r = ds.RasterXSize, ds.RasterYSize
    gt = hb.get_geotransform_uri(input_path)
    lower_lat = bb[1]
    upper_lat = bb[3]
    left_lon = bb[0]
    right_lon = bb[2]

    if inclusion_behavior == 'inclusive':
        r, c = hb.latlon_path_to_rc(upper_lat, left_lon, input_path, r_shift_direction='up', c_shift_direction='left')
        r_right, c_right = hb.latlon_path_to_rc(lower_lat, right_lon, input_path, r_shift_direction='down', c_shift_direction='right')
    elif inclusion_behavior == 'exclusive':
        r, c = hb.latlon_path_to_rc(upper_lat, left_lon, input_path, r_shift_direction='down', c_shift_direction='right')
        r_right, c_right = hb.latlon_path_to_rc(lower_lat, right_lon, input_path, r_shift_direction='up', c_shift_direction='left')
    else:
        r, c = hb.latlon_path_to_rc(upper_lat, left_lon, input_path, r_shift_direction='centered', c_shift_direction='centered')
        r_right, c_right = hb.latlon_path_to_rc(lower_lat, right_lon, input_path, r_shift_direction='centered', c_shift_direction='centered')
    r_size = r_right - r
    c_size = c_right - c

    if c_size == 0 or r_size == 0:
        L.debug('Inputs given result in zero size: ' + str(c) + ' ' + str(r) + ' ' + str(c_size) + ' ' + str(r_size))

    return round(c), round(r), round(c_size), round(r_size)


def latlon_path_to_rc(lat, lon, input_path, r_shift_direction='centered', c_shift_direction='centered'):
    """Calculate the row and column index from a raster at input_path for a given lat, lon value.
    Because latlon is continuous and rc is integer, specify the behavior for rounding. Default is centered, but can shift in any direction
    for applications that need precision (e.g. clipping country borders and requiring exclusivity.
    """

    ds = gdal.OpenEx(input_path)
    n_c, n_r = Decimal(ds.RasterXSize), Decimal(ds.RasterYSize)
    gt = ds.GetGeoTransform()
    ulx, xres, _, uly, _, yres = Decimal(gt[0]), Decimal(gt[1]), Decimal(gt[2]), Decimal(gt[3]), Decimal(gt[4]), Decimal(gt[5])

    lat = Decimal(lat)
    lon = Decimal(lon)
    gt_xmin_lon = ulx
    gt_ymin_lat = uly + yres * n_r
    gt_xmax_lon = ulx + xres * n_c
    gt_ymax_lat = uly
    prop_r = (gt_ymax_lat - lat) / (gt_ymax_lat - gt_ymin_lat)
    # prop_r = (lat - gt_ymin_lat) / (gt_ymax_lat - gt_ymin_lat)
    prop_c = (lon - gt_xmin_lon) / (gt_xmax_lon - gt_xmin_lon)
    r = prop_r * n_r
    c = prop_c * n_c

    initial_r = r
    initial_c = c

    if r_shift_direction == 'up':
        r = math.floor(r)
    elif r_shift_direction == 'down':
        r = math.ceil(r)
    elif r_shift_direction == 'nearest':
        r = round(r)

    if c_shift_direction == 'left':
        c = math.floor(c)
    elif c_shift_direction == 'right':
        c = math.ceil(c)
    elif c_shift_direction == 'nearest':
        c = round(c)

    verbose = False
    if verbose:
        print ('latlon_path_to_rc generated: lat', lat, 'lon', lon, 'n_c', n_c, 'n_r', n_r, 'ulx', ulx, 'xres', xres, 'uly', uly, 'yres', yres, 'prop_r', prop_r, 'prop_c', prop_c, 'r', r, 'c', c)

    return r, c

def rc_path_to_latlon(r, c, input_path):
    ds = gdal.OpenEx(input_path)
    n_c, n_r = ds.RasterXSize, ds.RasterYSize
    gt = ds.GetGeoTransform()

    ulx, xres, _, uly, _, yres = gt[0], gt[1], gt[2], gt[3], gt[4], gt[5]

    prop_r = r / n_r
    prop_c = c / n_c

    lat = uly - prop_r * (uly - (uly + yres * n_r))
    lon = ulx - prop_c * (ulx - (ulx + xres * n_c))

    # CAUTION: Recall that a geotransform is ul_LON, xres, 0 ul_LAT, 0, yres)
    return lat, lon

def generate_geotransform_of_chunk_from_cr_size_and_larger_path(cr_size, larger_raster_path):
    # gt = [0, 0, 0, 0, 0, 0]
    lat, lon = hb.rc_path_to_latlon(float(cr_size[1]), float(cr_size[0]), larger_raster_path)
    lat, lon = float(lat), float(lon)
    res = hb.get_cell_size_from_uri(larger_raster_path)
    return [lon, res, 0., lat, 0., -res]

def get_pyramid_compatible_bb_from_vector_and_resolution(input_vector, pyramid_resolution):
    """
    get a BB expanded outwards to include all of the input vector up to the nearest bounds of pyramid resolution

    :param input_vector: GPKG pointiing to the AOI or other vector needd to calculate inclusive coarse pyramid tiles.
    :param pyramid_resolution: in arcseconds
    :return: [r, c, r_size, c_size]

    Note that this is cmore challenging than it seems. For example, with a pyramid resolution of 4, the bounds are -2 to 2 near the equator. This 
    Makes ceil floor rounding not make sense. Instead need to convert -90 90 to 0 180+ m. This is implemented in bb2, which is different than the incorrect bb.
    """
    exact_bb = hb.spatial_projection.get_bounding_box(input_vector)

    pyramid_resolution_degrees = pyramid_compatible_resolutions[pyramid_resolution]

    bb = [0, 0, 0, 0]
    # a = exact_bb[0] / pyramid_resolution_degrees
    # b = float(math.floor(exact_bb[0] / pyramid_resolution_degrees))
    # c = pyramid_resolution_degrees * float(math.floor(exact_bb[0] / pyramid_resolution_degrees))
    # d = int(pyramid_resolution_degrees * round(float(exact_bb[0])/pyramid_resolution_degrees))

    bb[0] = pyramid_resolution_degrees * float(math.floor(exact_bb[0] / pyramid_resolution_degrees))
    bb[1] = pyramid_resolution_degrees * float(math.floor(exact_bb[1] / pyramid_resolution_degrees))
    bb[2] = pyramid_resolution_degrees * float(math.ceil(exact_bb[2] / pyramid_resolution_degrees))
    bb[3] = pyramid_resolution_degrees * float(math.ceil(exact_bb[3] / pyramid_resolution_degrees))
    
    shifted_bb = [0, 0, 0, 0]
    shifted_bb[0] = exact_bb[0] + 180
    shifted_bb[1] = -1 * exact_bb[3] + 90
    shifted_bb[2] = exact_bb[2] + 180
    shifted_bb[3] = -1 * exact_bb[1] + 90

    bb2 = [0, 0, 0, 0]
    bb2[0] = pyramid_resolution_degrees * float(math.floor(shifted_bb[0] / pyramid_resolution_degrees)) - 180
    bb2[3] = -1 * (pyramid_resolution_degrees * float(math.floor(shifted_bb[1] / pyramid_resolution_degrees)) - 90)
    bb2[2] = pyramid_resolution_degrees * float(math.ceil(shifted_bb[2] / pyramid_resolution_degrees)) - 180
    bb2[1] = -1 * (pyramid_resolution_degrees * float(math.ceil(shifted_bb[3] / pyramid_resolution_degrees)) - 90)


    return bb2

def is_path_same_geotransform(input_path, match_path, raise_exception=False, surpress_output=False):
    """Throw exception if input_path is not the same geotransform as the match path."""
    if not os.path.exists(input_path):
        result_string = 'Unable to find input path:\n' + str(input_path)
        if raise_exception:
            raise NameError(result_string)
        else:
            if not surpress_output:
                L.warning(result_string)
            return False

    if not os.path.exists(match_path):
        result_string = 'Unable to find match path:\n' + str(match_path)
        if raise_exception:
            raise NameError(result_string)
        else:
            if not surpress_output:
                L.warning(result_string)
            return False

    ds = gdal.OpenEx(input_path)
    try:
        gt = ds.GetGeoTransform()
    except:
        gt = None

    ds_match = gdal.OpenEx(match_path)
    gt_match = ds_match.GetGeoTransform()

    if not gt == gt_match:
        result_string = 'Input path did not have the same geotransform as match path:\n' + str(input_path) + '\n' + str(gt) + '\n' + str(match_path) + '\n' + str(gt_match)
        if raise_exception:
            raise NameError(result_string)
        else:
            if not surpress_output:
                L.warning(result_string)
            return False


    # Passed all the tests
    return True

def convert_ndv_to_alpha_band(input_path, output_path, ndv_replacement_value=0):
    """Take a 1 band geotiff with an ndv value, extract the ndv value, replace it, then write the ndv value as an alpha band.

    Writes a 2 band geotiff to output path."""

    ds = gdal.OpenEx(input_path)
    band = ds.GetRasterBand(1)
    array = band.ReadAsArray()

    ndv = band.GetNoDataValue()
    data_type = band.DataType

    n_cols = array.shape[1]
    n_rows = array.shape[0]
    geotransform = hb.get_geotransform_path(input_path)
    projection = hb.get_dataset_projection_wkt_uri(input_path)

    # For later, make it inherit the right metadata with the following
    metadata = ds.GetMetadata('IMAGE_STRUCTURE')
    metadata = ds.GetMetadata()

    # For now, I just have it use the default gtiff options
    dst_options = hb.globals.DEFAULT_GTIFF_CREATION_OPTIONS

    driver = gdal.GetDriverByName('GTiff')
    dst_ds = driver.Create(output_path, n_cols, n_rows, 2, data_type, dst_options)
    dst_ds.GetRasterBand(2).SetColorInterpretation(gdal.GCI_AlphaBand)
    dst_ds.SetGeoTransform(geotransform)
    dst_ds.SetProjection(projection)

    # dst_ds.GetRasterBand(1).SetNoDataValue(ndv)

    alpha_array = np.where(array == ndv, 0, 255)

    array[array == ndv] = ndv_replacement_value
    dst_ds.GetRasterBand(1).WriteArray(array)
    dst_ds.GetRasterBand(2).WriteArray(alpha_array)

    dst_ds = None
    ds = None

    # From gdal_edit.py script.
    # ds.GetRasterBand(band).SetColorInterpretation(colorinterp[band])
    # gdal.GCI_AlphaBand

def get_aspect_ratio_of_two_arrays(coarse_res_array, fine_res_array):
    # Test that map resolutions are workable multiples of each other
    # assert int(round(fine_res_array.shape[0] / coarse_res_array.shape[0])) == int(
    #     round(fine_res_array.shape[1] / coarse_res_array.shape[1]))
    aspect_ratio = int(round(fine_res_array.shape[0] / coarse_res_array.shape[0]))
    return aspect_ratio


def calc_proportion_of_coarse_res_with_valid_fine_res(coarse_res, fine_res):
    """Useful wehn allocating to border cells."""

    if not isinstance(coarse_res, np.ndarray):
        try:
            coarse_res = hb.as_array(coarse_res).astype(np.float64)
        except:
            raise NameError('Unable to load ' + str(coarse_res) + ' as array in calc_proportion_of_coarse_res_with_valid_fine_res.')

    if not isinstance(fine_res, np.ndarray):
        try:
            fine_res = hb.as_array(fine_res).astype(np.int64)
        except:
            raise NameError('Unable to load ' + str(fine_res) + ' as array in calc_proportion_of_coarse_res_with_valid_fine_res.')

    aspect_ratio = get_aspect_ratio_of_two_arrays(coarse_res, fine_res)

    #
    # coarse_res_proportion_array = np.zeros(coarse_res.shape).astype(np.float64)
    # fine_res_proportion_array = np.zeros(fine_res.shape).astype(np.float64)

    proportion_valid_fine_per_coarse_cell = hb.cython_calc_proportion_of_coarse_res_with_valid_fine_res(coarse_res.astype(np.float64), fine_res.astype(np.int64))

    return proportion_valid_fine_per_coarse_cell

def is_compressed(input_path):
    # Make flex?

    ds = gdal.OpenEx(input_path)
    md = ds.GetMetadata()
    image_structure = ds.GetMetadata('IMAGE_STRUCTURE')
    compression = image_structure.get('COMPRESSION', False)

    if compression:
        return True
    else:
        return False


def add_rows_or_cols_to_geotiff(input_path, r_above, r_below, c_left, c_right, output_path=None, fill_value=None, remove_temporary_files=False):
    # if output_path is None, assume overwriting
    input_ds = gdal.OpenEx(input_path)
    input_gt = input_ds.GetGeoTransform()
    input_projection = input_ds.GetProjection()
    datatype = hb.get_raster_info_hb(input_path)['datatype']

    callback = hb.make_simple_gdal_callback('Reading array')
    input_array = input_ds.ReadAsArray(callback=callback)
    output_gt = list(input_gt)
    output_gt = [input_gt[0] + c_left * input_gt[1], input_gt[1], 0.0, input_gt[3] + r_above * input_gt[1], 0.0, input_gt[5]]

    if fill_value is None:
        fill_value = input_ds.GetRasterBand(1).GetNoDataValue()

    n_rows = int(input_ds.RasterYSize + r_above + r_below)
    n_cols = int(input_ds.RasterXSize + c_left + c_right)

    input_ds = None # Close the dataset so that we can move or overwrite it.

    # If there is no output_path, assume that we are going to be doing the operation in-place. BUT, if remove_temporary_files
    # is not True, simply move the input file to temp as a backup.
    if output_path is None:
        output_dir = os.path.dirname(input_path)
        temp_path = hb.temp('.tif', 'test_add_rows_or_cols_to_geotiff', remove_temporary_files, output_dir)
        # hb.rename_with_overwrite(input_path, temp_path)
        output_path = temp_path
        # input_path = temp_path

    driver = gdal.GetDriverByName('GTiff')

    local_gtiff_creation_options = list(hb.globals.DEFAULT_GTIFF_CREATION_OPTIONS)
    local_gtiff_creation_options.extend(['COMPRESS=DEFLATE'])

    n_bands = 1

    output_raster = driver.Create(output_path, n_cols, n_rows, n_bands, datatype, options=local_gtiff_creation_options)
    output_raster.SetProjection(input_projection)
    output_raster.SetGeoTransform(output_gt)

    output_band = output_raster.GetRasterBand(1)

    output_band.SetNoDataValue(fill_value) # NOTE, this has to happen before WriteArray or it will assume filling with 0.
    output_band.WriteArray(input_array, c_left, r_above)
    output_raster.FlushCache()
    output_raster = None


def fill_to_match_extent(input_path, match_path, output_path=None, fill_value=None, remove_temporary_files=False):

    # gdal.Translate()

    ds = gdal.OpenEx(input_path)
    input_gt = ds.GetGeoTransform()

    match_ds = gdal.OpenEx(match_path)
    match_gt = match_ds.GetGeoTransform()

    c_left = -1 * (match_gt[0] - input_gt[0]) * match_gt[1]
    r_above = (match_gt[3] - input_gt[3]) / match_gt[1]

    c_right = match_ds.RasterXSize - (c_left + ds.RasterXSize)
    r_below = match_ds.RasterYSize - (r_above + ds.RasterYSize)

    n_cols = ds.RasterXSize + c_left + c_right
    n_rows = ds.RasterYSize + r_above + r_below

    ds = None
    match_ds = None

    hb.add_rows_or_cols_to_geotiff(input_path, r_above, r_below, c_left, c_right, output_path=output_path, fill_value=fill_value, remove_temporary_files=remove_temporary_files)



def fill_to_match_extent_using_warp(input_path, match_path, output_path=None, fill_value=None, remove_temporary_files=False):
    # Slower it seems than fill_to_match_extent.
    match_ds = gdal.OpenEx(match_path)
    match_gt = match_ds.GetGeoTransform()
    match_srs = match_ds.GetProjection()
    match_gdal_win = hb.get_raster_info_hb(match_path)['gdal_win']

    if output_path is None:
        output_path = hb.temp('.tif', 'filled', False)

    width = match_ds.RasterXSize
    height = match_ds.RasterYSize
    callback = hb.make_logger_callback(
        "fill_to_match_extent %.1f%% complete %s")
    gdal.Warp(output_path, input_path, width=width, height=height, outputBounds=match_gdal_win,
              callback=callback, callback_data=[output_path])

def snap_bb_points_to_outer_pyramid(input_bb, pyramidal_raster_path):
    """
    Converts a BB to one that has points that preceisly correspond to the Pyramid definition given by Pyramidal_raster_path.
    :param input_bb:
    :param pyramidal_raster_path:
    :return:
    """
    # NOTE INTERESTING BEHAVIOR: exclusive works, centroid does not. it shifts everyone 1 to the right.
    # Is this a bahavior that happens with centroid and coords that precisely hit a pyramid cell edge?
    res = Decimal(determine_pyramid_resolution(pyramidal_raster_path))

    # Convert to decimal types
    input_bb = [Decimal(input_bb[0]), Decimal(input_bb[1]), Decimal(input_bb[2]), Decimal(input_bb[3])]

    snapped_bb = [Decimal(0.0), Decimal(0.0), Decimal(0.0), Decimal(0.0)]
    snapped_bb[0] = input_bb[0] - (Decimal(input_bb[0]) % res)
    snapped_bb[1] = input_bb[1] - (input_bb[1] % res)
    snapped_bb[2] = input_bb[2] + (res - input_bb[2] % res)
    snapped_bb[3] = input_bb[3] + (res - input_bb[3] % res)

    returned_bb = [float(i) for i in snapped_bb]
    return returned_bb


def numpy_dtype_to_gdal(dtype):
    """
    Map a NumPy data type to a corresponding GDAL data type.
    """
    if np.issubdtype(dtype, np.uint8):
        return gdal.GDT_Byte
    elif np.issubdtype(dtype, np.uint16):
        return gdal.GDT_UInt16
    elif np.issubdtype(dtype, np.int16):
        return gdal.GDT_Int16
    elif np.issubdtype(dtype, np.uint32):
        return gdal.GDT_UInt32
    elif np.issubdtype(dtype, np.int32):
        return gdal.GDT_Int32
    elif np.issubdtype(dtype, np.float32):
        return gdal.GDT_Float32
    elif np.issubdtype(dtype, np.float64):
        return gdal.GDT_Int64
    elif np.issubdtype(dtype, np.uint64):
        return gdal.GDT_UInt64
    else:
        raise ValueError("Unsupported NumPy data type: {}".format(dtype))

### DUPLACED SAME FUNCTION BELOW BUT I CANT REMEMBER IF THERE WAS OTHER VALUE TO GET
# def write_geotiff_as_cog(input_path, output_path, match_path, verbose=False):
#     """
#     Write a NumPy array to a Cloud Optimized GeoTIFF (COG) using GDAL.
    
#     This function follows a two‑step process:
#       1. It creates a temporary GTiff file with recommended COG creation options
#          (tiled, compressed, with a fixed block size) and builds internal overviews.
#       2. It then reprojects that file into a final COG using gdal.Translate with the 
#          COPY_SRC_OVERVIEWS option so that the IFD and tile offsets are arranged properly.
    
#     Parameters:
#       output_path (str): Path to the final output COG file.
#       array (np.ndarray): Data array to be written. Use shape (rows, cols) for a single
#                           band or (bands, rows, cols) for multiband data.
#       geotransform (tuple): A 6‑element tuple defining the geotransform.
#       projection (str): The projection in WKT format.
#       nodata (optional): No-data value to assign to each band.
    
#     Raises:
#       RuntimeError: If dataset creation or translation fails.
    
#     Example:
    
#         # For a single‑band array:
#         arr = np.random.randint(0, 255, size=(1024, 1024)).astype(np.uint8)
#         geotrans = (444720, 30, 0, 3751320, 0, -30)
#         proj = osr.SRS_WKT_WGS84  # or load from a proper SRS object
#         write_cog("output_cog.tif", arr, geotrans, proj, nodata=0)
#     """
#     # Determine dimensions and number of bands.
#     if array.ndim == 2:
#         nbands = 1
#         rows, cols = array.shape
#     elif array.ndim == 3:
#         nbands, rows, cols = array.shape
#     else:
#         raise ValueError("Array must be 2D (rows, cols) or 3D (bands, rows, cols).")
    
#     # Map the NumPy dtype to a GDAL type.
#     gdal_dtype = numpy_dtype_to_gdal(array.dtype)
    
#     # Get the GTiff driver.
#     driver = gdal.GetDriverByName('GTiff')
    
#     # Create a temporary file for the intermediate dataset.
#     tmp_fd, tmp_path = tempfile.mkstemp(suffix='.tif')
#     os.close(tmp_fd)  # We let GDAL handle the file.
    
#     # Creation options for the temporary file.
#     tmp_creation_options = [
#         'TILED=YES',
#         'BLOCKXSIZE=512',
#         'BLOCKYSIZE=512',
#         'COMPRESS=ZSTD',
#         'PREDICTOR=2',
#         'BIGTIFF=IF_SAFER',
#         'NUM_THREADS=ALL_CPUS',
#     ]
    
#     # Create the temporary dataset.
#     dataset = driver.Create(tmp_path, cols, rows, nbands, gdal_dtype, options=tmp_creation_options)
#     if dataset is None:
#         raise RuntimeError("Failed to create temporary dataset.")
    
#     # Set georeferencing.
#     dataset.SetGeoTransform(geotransform)
#     dataset.SetProjection(projection)
    
#     # Write the array data.
#     if nbands == 1:
#         band = dataset.GetRasterBand(1)
#         if nodata is not None:
#             band.SetNoDataValue(nodata)
#         band.WriteArray(array)
#     else:
#         for i in range(nbands):
#             band = dataset.GetRasterBand(i+1)
#             if nodata is not None:
#                 band.SetNoDataValue(nodata)
#             band.WriteArray(array[i, :, :])
    
#     # Ensure data is written.
#     dataset.FlushCache()
    
#     # Build overviews.
#     # Choose overview levels until the reduced size is less than ~256 pixels.
#     overview_levels = []
#     factor = 2
#     while (rows // factor >= 256) and (cols // factor >= 256):
#         overview_levels.append(factor)
#         factor *= 2
#     if overview_levels:
#         # Use a resampling method; "AVERAGE" is often appropriate for continuous data.
#         dataset.BuildOverviews("AVERAGE", overview_levels)
#         dataset.FlushCache()
    
#     # Close the temporary dataset.
#     dataset = None
    
#     # Now translate the temporary file into the final COG.
#     # The COPY_SRC_OVERVIEWS option ensures that overviews are copied and that the file
#     # is reorganized so that the primary IFD and tile offsets are optimized.
#     final_creation_options = [
#         'TILED=YES',
#         'COPY_SRC_OVERVIEWS=YES',
#         'COMPRESS=DEFLATE',
#         'PREDICTOR=2',
#         'BIGTIFF=IF_SAFER'
#     ]
    
#     translate_options = gdal.TranslateOptions(creationOptions=final_creation_options)
#     final_ds = gdal.Translate(output_path, tmp_path, options=translate_options)
#     if final_ds is None:
#         os.remove(tmp_path)
#         raise RuntimeError("Failed to translate to final COG.")
#     final_ds = None
    
#     # Remove the temporary file.
#     os.remove(tmp_path)
#     print("COG successfully saved to '{}'.".format(output_path))
    
    
    
    
    
def write_geotiff_as_cog(input_path, output_path, match_path, verbose=False):
    """
    Reads an input GeoTIFF, gets georeference parameters from a matching GeoTIFF,
    and writes out a Cloud Optimized GeoTIFF (COG) at output_path.
    
    Parameters:
      input_path (str): Path to the input (source) GeoTIFF file.
      output_path (str): Path for the final output COG.
      match_path (str): Path to a GeoTIFF file from which to copy required georeference 
                        and projection parameters.
      verbose (bool): If True, prints additional diagnostic messages.
    
    The function performs the following steps:
      1. Reads the data from input_path as a NumPy array.
      2. Reads geotransform and projection from match_path.
      3. Creates a temporary GeoTIFF using recommended COG creation options,
         writes the data, and builds internal overviews.
      4. Uses gdal.Translate with the COPY_SRC_OVERVIEWS option to produce the final file.
    """
    # 1. Open the input dataset.
    in_ds = gdal.Open(input_path, gdal.GA_ReadOnly)
    if in_ds is None:
        raise RuntimeError("Unable to open input file: {}".format(input_path))
    if verbose:
        print("Opened input file: {}".format(input_path))
    
    # Read the input data as a NumPy array.
    data = in_ds.ReadAsArray()
    if data is None:
        in_ds = None
        raise RuntimeError("Failed to read data from input file.")
    
    # Determine the number of bands and image dimensions.
    if data.ndim == 2:
        nbands = 1
        rows, cols = data.shape
    elif data.ndim == 3:
        nbands, rows, cols = data.shape
    else:
        in_ds = None
        raise ValueError("Input data must be 2D (rows, cols) or 3D (bands, rows, cols).")
    
    if verbose:
        print("Input data dimensions: {} x {} with {} band(s)".format(cols, rows, nbands))
    
    # Determine the GDAL data type from the NumPy dtype.
    gdal_dtype = numpy_dtype_to_gdal(data.dtype)
    
    # Get nodata value from the first band of the input.
    in_band = in_ds.GetRasterBand(1)
    nodata = in_band.GetNoDataValue()
    if verbose:
        print("Input nodata value: {}".format(nodata))
    
    # 2. Open the match dataset to obtain georeferencing information.
    match_ds = gdal.Open(match_path, gdal.GA_ReadOnly)
    if match_ds is None:
        in_ds = None
        raise RuntimeError("Unable to open match file: {}".format(match_path))
    geotransform = match_ds.GetGeoTransform()
    projection = match_ds.GetProjection()
    if verbose:
        print("Using geotransform from match file: {}".format(geotransform))
        print("Using projection from match file.")
    match_ds = None  # No longer needed.
    
    # 3. Create a temporary file for the intermediate COG dataset.
    driver = gdal.GetDriverByName('GTiff')
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.tif')
    os.close(tmp_fd)  # Let GDAL manage the file.
    if verbose:
        print("Creating temporary file: {}".format(tmp_path))
    
    tmp_creation_options = [
        'TILED=YES',
        'BLOCKXSIZE=512',
        'BLOCKYSIZE=512',
        'COMPRESS=ZSTD',
        'PREDICTOR=2',
        'BIGTIFF=IF_SAFER',
        'NUM_THREADS=ALL_CPUS',      
    ]
    
    tmp_ds = driver.Create(tmp_path, cols, rows, nbands, gdal_dtype, options=tmp_creation_options)
    if tmp_ds is None:
        in_ds = None
        raise RuntimeError("Failed to create temporary dataset.")
    
    # Set georeferencing using parameters from the match file.
    tmp_ds.SetGeoTransform(geotransform)
    tmp_ds.SetProjection(projection)
    
    # 4. Write the data to the temporary dataset.
    if nbands == 1:
        band = tmp_ds.GetRasterBand(1)
        if nodata is not None:
            band.SetNoDataValue(nodata)
        band.WriteArray(data)
    else:
        for i in range(nbands):
            band = tmp_ds.GetRasterBand(i+1)
            if nodata is not None:
                band.SetNoDataValue(nodata)
            # data is assumed to be in (bands, rows, cols) order.
            band.WriteArray(data[i, :, :])
    
    tmp_ds.FlushCache()
    if verbose:
        print("Wrote data to temporary dataset.")
    
    # Build overviews.
    
    res_in_seconds = hb.pyramid_compatible_resolution_to_arcseconds[geotransform[1]]
    overview_levels = hb.pyramid_compatible_overview_levels[res_in_seconds]
    
    # If the data are any form of ints, make it mode. otherwise make the resampling method be average.
    if data.dtype in [np.int8, np.int16, np.int32, np.int64, np.uint8, np.uint16, np.uint32, np.uint64]:
        resampling_method = 'MODE' # AVERAGE, NEAREST
    else:
        resampling_method = 'AVERAGE' # AVERAGE, NEAREST
    # resampling_method = 'MODE' # AVERAGE, NEAREST
    # overview_levels = []
    # factor = 2
    # while (rows // factor >= 256) and (cols // factor >= 256):
    #     overview_levels.append(factor)
    #     factor *= 2
    if overview_levels:
        if verbose:
            print("Building overviews with levels: {}".format(overview_levels))
        tmp_ds.BuildOverviews(resampling_method, overview_levels)
        tmp_ds.FlushCache()
    
    # Close the temporary dataset.
    tmp_ds = None
    in_ds = None  # Close input dataset.
    
    # 5. Translate the temporary file into the final COG.
    final_creation_options = [
        'TILED=YES',
        'COPY_SRC_OVERVIEWS=YES',
        'BLOCKXSIZE=512',
        'BLOCKYSIZE=512',
        'COMPRESS=ZSTD',
        'PREDICTOR=2',
        'BIGTIFF=IF_SAFER'
    ]
    translate_options = gdal.TranslateOptions(creationOptions=final_creation_options)
    if verbose:
        print("Translating temporary file to final COG: {}".format(output_path))
    final_ds = gdal.Translate(output_path, tmp_path, options=translate_options)
    if final_ds is None:
        os.remove(tmp_path)
        raise RuntimeError("Failed to translate temporary file to final COG.")
    final_ds = None
    
    # Remove the temporary file.
    os.remove(tmp_path)
    if verbose:
        print("Final COG saved to '{}' and temporary file removed.".format(output_path))
 
    

def add_overviews_with_gdaladdo(dataset_path, overview_levels=None, 
                                resampling_method="AVERAGE", verbose=False):
    """
    Uses gdaladdo.exe to add overviews (pyramids) to a GeoTIFF dataset.
    
    Parameters:
      dataset_path (str): Path to the dataset (GeoTIFF) on which to add overviews.
      overview_levels (list of int, optional): A list of integer factors at which
           overviews will be created (e.g., [2, 4, 8, 16]). If None, the levels will be 
           determined automatically based on the dataset dimensions.
      resampling_method (str): Resampling method to use (e.g., "NEAREST", "AVERAGE",
           "CUBIC", "MODE", etc.). Default is "AVERAGE".
      verbose (bool): If True, prints the constructed command and any output/error messages.
      callback (function): Optional callback function taking two parameters (progress, message).
           Progress is a float between 0 and 1.
    
    Returns:
      int: The return code from the gdaladdo.exe command.
    
    Raises:
      FileNotFoundError: If the dataset file does not exist.
      RuntimeError: If there is an error running gdaladdo.exe.
    """
    def callback(progress, message):
        print("Progress: {:.0f}% - {}".format(progress * 100, message))    
    
    # Check if the input dataset exists.
    if not os.path.exists(dataset_path):
        raise FileNotFoundError("Dataset not found: {}".format(dataset_path))
    
    # If no overview levels are provided, compute them automatically.
    if overview_levels is None:
        ds = gdal.Open(dataset_path, gdal.GA_Update) # Update ensures overviews are internal
        if ds is None:
            raise RuntimeError("Failed to open dataset for overview level calculation.")
        cols = ds.RasterXSize
        rows = ds.RasterYSize
        ds = None
        
        overview_levels = []
        factor = 2
        while (rows // factor >= 256) and (cols // factor >= 256):
            overview_levels.append(factor)
            factor *= 2
        
        if verbose:
            print("Automatically determined overview levels: {}".format(overview_levels))
        if callback:
            callback(0.1, "Determined overview levels: {}".format(overview_levels))
    
    # Construct the gdaladdo.exe command.
    # Example: gdaladdo.exe -r AVERAGE dataset_path 2 4 8 16
    command = ["gdaladdo.exe", "-r", resampling_method, dataset_path] + [str(level) for level in overview_levels]
    if verbose:
        print("Executing command: {}".format(" ".join(command)))
    if callback:
        callback(0.2, "Executing gdaladdo command.")
    
    # Run the command.
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                universal_newlines=True)
    except Exception as e:
        if callback:
            callback(1.0, "Error executing gdaladdo: {}".format(e))
        raise RuntimeError("Error executing gdaladdo.exe: {}".format(e))
    
    # Print output if verbose.
    if verbose:
        print("gdaladdo stdout:\n{}".format(result.stdout))
        if result.stderr:
            print("gdaladdo stderr:\n{}".format(result.stderr))
    
    if callback:
        callback(1.0, "gdaladdo finished with return code: {}".format(result.returncode))
    
    return result.returncode

def area_of_pixel(pixel_size, center_lat):
    """Calculate m^2 area of a wgs84 square pixel.

    Adapted from: https://gis.stackexchange.com/a/127327/2397

    Args:
        pixel_size (float): length of side of pixel in degrees.
        center_lat (float): latitude of the center of the pixel. Note this
            value +/- half the `pixel-size` must not exceed 90/-90 degrees
            latitude or an invalid area will be calculated.

    Returns:
        Area of square pixel of side length `pixel_size` centered at
        `center_lat` in m^2.

    """
    a = 6378137  # meters
    b = 6356752.3142  # meters
    e = math.sqrt(1 - (b/a)**2)
    area_list = []
    for f in [center_lat+pixel_size/2, center_lat-pixel_size/2]:
        zm = 1 - e*math.sin(math.radians(f))
        zp = 1 + e*math.sin(math.radians(f))
        area_list.append(
            math.pi * b**2 * (
                math.log(zp/zm) / (2*e) +
                math.sin(math.radians(f)) / (zp*zm)))
    return abs(pixel_size / 360. * (area_list[0] - area_list[1]))

    
def raster_to_area_raster(base_raster_path, target_raster_path):
    """Convert base to a target raster of same shape with per area pixels."""
    base_raster_info = hb.get_raster_info(base_raster_path)

    # create 1D array of pixel size vs. lat
    n_rows = base_raster_info['raster_size'][1]
    pixel_height = abs(base_raster_info['geotransform'][5])
    # the / 2 is to get in the center of the pixel
    miny = base_raster_info['bounding_box'][1] + pixel_height/2
    maxy = base_raster_info['bounding_box'][3] - pixel_height/2
    lat_vals = np.linspace(maxy, miny, n_rows)

    pixel_area_per_lat = 1.0 / 10000.0 * np.array([
        [area_of_pixel(pixel_height, lat_val)] for lat_val in lat_vals])

    # hb.raster_calculator_flex
    # hb.raster_calculator_hb
    hb.raster_calculator(
        [(base_raster_path, 1), pixel_area_per_lat],
        lambda x, y: y, target_raster_path,
        gdal.GDT_Float64, -9999.0, raster_driver_creation_tuple=hb.PRECOG_GTIFF_CREATION_OPTIONS_TUPLE)
    
    
    
    
    
    
    
    