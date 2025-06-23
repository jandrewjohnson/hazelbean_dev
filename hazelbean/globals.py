"""Research-specific globals for frequently used data sets, along with file operating system globals."""

import os
# import numpy as np
from collections import OrderedDict

# TODOO Consider getting rid of all-caps globals notation.
# TODOO Write file object protocol that actually does the data downloading via permissions on google drive.



TINY_MEMORY_ARRAY_SIZE = 1e+04
SMALL_MEMORY_ARRAY_SIZE = 1e+05
MEDIUM_MEMORY_ARRAY_SIZE = 1e+06
LARGE_MEMORY_ARRAY_SIZE = 1e+07
MAX_IN_MEMORY_ARRAY_SIZE = 1e+011

# FROM Pygeoprocessing 06
LOGGING_PERIOD = 1.0  # min 5.0 seconds per update log message for the module
MAX_TIMEOUT = 60.0
DEFAULT_GTIFF_CREATION_OPTIONS = ['TILED=YES', 'BIGTIFF=YES', 'COMPRESS=ZSTD', 'BLOCKXSIZE=512', 'BLOCKYSIZE=512']
DEFAULT_GTIFF_NO_COMPRESS_CREATION_OPTIONS = ['TILED=YES', 'BIGTIFF=YES', 'BLOCKXSIZE=256', 'BLOCKYSIZE=256']
DEFAULT_GTIFF_STRIPED_CREATION_OPTIONS = ['TILED=NO', 'BIGTIFF=YES', 'COMPRESS=ZSTD']
DEFAULT_GTIFF_MANUAL_STRIPED_CREATION_OPTIONS = ['TILED=YES', 'BIGTIFF=YES', 'COMPRESS=ZSTD']
DEFAULT_GTIFF_STRIPED_NO_COMPRESS_CREATION_OPTIONS = ['TILED=NO', 'BIGTIFF=YES']


DEFAULT_GTIFF_CREATION_TUPLE_OPTIONS_HB = (
    'GTIFF',
    (
        'TILED=YES',
        'BIGTIFF=YES',
        'COMPRESS=ZSTD',
        'BLOCKXSIZE=512',
        'BLOCKYSIZE=512',
    ),
)

# Define creation options for COG
PRECOG_GTIFF_CREATION_OPTIONS_LIST = [
    "COMPRESS=ZSTD",
    "BLOCKXSIZE=512",  
    "BLOCKYSIZE=512",  
    "BIGTIFF=YES", 
    'TILED=YES',
]
COG_CREATION_OPTIONS_LIST = [
    'COMPRESS=ZSTD',
    'BLOCKSIZE=512',
    'BIGTIFF=YES',
    # 'TILED=YES', # TILED is actually not a valid cog driver creation option because it requries it. however, you  need to have the precog option specify it.
    # 'OVERVIEWS=IGNORE_EXISTING'
]



# Define creation options for COG
PRECOG_GTIFF_CREATION_OPTIONS_TUPLE = (
    'GTIFF', 
    (
        "COMPRESS=ZSTD",
        "BLOCKXSIZE=512",  
        "BLOCKYSIZE=512",  
        "BIGTIFF=YES", 
        'TILED=YES',
    )
)
COG_CREATION_OPTIONS_TUPLE = (
    'COG', 
    (
        'COMPRESS=ZSTD',
        'BLOCKSIZE=512',
        'BIGTIFF=YES',
        # 'TILED=YES', # TILED is actually not a valid cog driver creation option because it requries it. however, you  need to have the precog option specify it.
        # 'OVERVIEWS=IGNORE_EXISTING'
    )
)





LARGEST_ITERBLOCK = 2 ** 20  # largest block for iterblocks to read in cells

LAST_TIME_CHECK = 0.0
# A dictionary to map the resampling method input string to the gdal type




start_of_numerals_ascii_int = 48
start_of_uppercase_letters_ascii_int = 65
start_of_lowercase_letters_ascii_int = 97
alphanumeric_ascii_ints = list(range(start_of_numerals_ascii_int, start_of_numerals_ascii_int + 10)) + list(range(start_of_uppercase_letters_ascii_int, start_of_uppercase_letters_ascii_int + 26)) + list(range(start_of_lowercase_letters_ascii_int, start_of_lowercase_letters_ascii_int + 26))
alphanumeric_lowercase_ascii_ints = list(range(start_of_numerals_ascii_int, start_of_numerals_ascii_int + 10)) + list(range(start_of_lowercase_letters_ascii_int, start_of_lowercase_letters_ascii_int + 26))
alphanumeric_ascii_symbols = [chr(i) for i in alphanumeric_ascii_ints]
alphanumeric_lowercase_ascii_symbols = [chr(i) for i in alphanumeric_lowercase_ascii_ints]  # numbers are lowercase i assume...


common_epsg_codes_by_name = OrderedDict()
common_epsg_codes_by_name['wgs84'] = 4326
common_epsg_codes_by_name['wec'] = 54002
common_epsg_codes_by_name['world_eckert_iv'] = 54012
common_epsg_codes_by_name['robinson'] = 54030
# common_epsg_codes_by_name['mollweide'] =  54009
common_epsg_codes_by_name['plate_carree'] = 32662
# common_epsg_codes_by_name['mercator'] =  3857
# common_epsg_codes_by_name[]# '] = wec_old': 32663,
# common_epsg_codes_by_name[]# '] = wec_sphere': 3786,

common_projected_epsg_codes_by_name = OrderedDict()
# common_projected_epsg_codes_by_name['wgs84'] =  4326
common_projected_epsg_codes_by_name['wec'] = 54002
common_projected_epsg_codes_by_name['world_eckert_iv'] = 54012
common_projected_epsg_codes_by_name['robinson'] = 54030
# common_projected_epsg_codes_by_name['mollweide'] =  54009
common_projected_epsg_codes_by_name['plate_carree'] = 32662
# common_projected_epsg_codes_by_name['mercator'] =  3857

# Based on WGS84 (G1762)'
wgs_84_wkt = """GEOGCS["WGS 84", DATUM["WGS_1984", SPHEROID["WGS 84", 6378137, 298.257223563, AUTHORITY["EPSG", "7030"]], AUTHORITY["EPSG", "6326"]], PRIMEM["Greenwich", 0, AUTHORITY["EPSG", "8901"]], UNIT["degree", 0.0174532925199433, AUTHORITY["EPSG", "9122"]], AUTHORITY["EPSG", "4326"]]"""
mollweide_wkt = """PROJCS["World_Mollweide", GEOGCS["GCS_WGS_1984", DATUM["WGS_1984", SPHEROID["WGS_1984", 6378137, 298.257223563]], PRIMEM["Greenwich", 0], UNIT["Degree", 0.017453292519943295]], PROJECTION["Mollweide"], PARAMETER["False_Easting", 0], PARAMETER["False_Northing", 0], PARAMETER["Central_Meridian", 0], UNIT["Meter", 1], AUTHORITY["EPSG", "54009"]]"""

robinson_wkt = """PROJCS["World_Robinson",
    GEOGCS["GCS_WGS_1984",
        DATUM["WGS_1984",
            SPHEROID["WGS_1984",6378137,298.257223563]],
        PRIMEM["Greenwich",0],
        UNIT["Degree",0.017453292519943295]],
    PROJECTION["Robinson"],
    PARAMETER["False_Easting",0],
    PARAMETER["False_Northing",0],
    PARAMETER["Central_Meridian",0],
    UNIT["Meter",1],
    AUTHORITY["EPSG","54030"]]"""

wgs_84_wkt = """GEOGCS["WGS 84",
    DATUM["WGS_1984",
        SPHEROID["WGS 84",6378137,298.257223563,
            AUTHORITY["EPSG","7030"]],
        AUTHORITY["EPSG","6326"]],
    PRIMEM["Greenwich",0,
        AUTHORITY["EPSG","8901"]],
    UNIT["degree",0.01745329251994328,
        AUTHORITY["EPSG","9122"]],
    AUTHORITY["EPSG","4326"]]"""

cylindrical_wkt = """PROJCS["WGS 84 / World Equidistant Cylindrical",
    GEOGCS["WGS 84",
        DATUM["WGS_1984",
            SPHEROID["WGS 84",6378137,298.257223563,
                AUTHORITY["EPSG","7030"]],
            AUTHORITY["EPSG","6326"]],
        PRIMEM["Greenwich",0,
            AUTHORITY["EPSG","8901"]],
        UNIT["degree",0.01745329251994328,
            AUTHORITY["EPSG","9122"]],
        AUTHORITY["EPSG","4326"],
        AXIS["Latitude",NORTH],
        AXIS["Longitude",EAST]],
    UNIT["metre",1,
        AUTHORITY["EPSG","9001"]]]"""

plate_carree_wkt = """PROJCS["WGS 84 / Plate Carree (deprecated)",
    GEOGCS["WGS 84",
        DATUM["WGS_1984",
            SPHEROID["WGS 84",6378137,298.257223563,
                AUTHORITY["EPSG","7030"]],
            AUTHORITY["EPSG","6326"]],
        PRIMEM["Greenwich",0,
            AUTHORITY["EPSG","8901"]],
        UNIT["degree",0.01745329251994328,
            AUTHORITY["EPSG","9122"]],
        AUTHORITY["EPSG","4326"]],
    UNIT["metre",1,
        AUTHORITY["EPSG","9001"]],
    PROJECTION["Equirectangular"],
    PARAMETER["latitude_of_origin",0],
    PARAMETER["central_meridian",0],
    PARAMETER["false_easting",0],
    PARAMETER["false_northing",0],
    AUTHORITY["EPSG","32662"],
    AXIS["X",EAST],
    AXIS["Y",NORTH]]"""

# Not used in WGS84 standard
more_precise_degree_measurement = 0.01745329251994328

#### DEPRECATED BY PYRAMIDS.py data but kept for compatibility. TODOOO clean.
geotransform_global_4deg = (-180.0, 2, 0.0, 90.0, 0.0, -4)
geotransform_global_2deg = (-180.0, 2, 0.0, 90.0, 0.0, -2)
geotransform_global_1deg = (-180.0, 1, 0.0, 90.0, 0.0, -1)
geotransform_global_30m = (-180.0, 0.5, 0.0, 90.0, 0.0, -0.5) # DEPRECATED
geotransform_global_30min = (-180.0, 0.5, 0.0, 90.0, 0.0, -0.5)
geotransform_global_15m = (-180.0, 0.25, 0.0, 90.0, 0.0, -0.25)
geotransform_global_15min = (-180.0, 0.25, 0.0, 90.0, 0.0, -0.25)
geotransform_global_5m = (-180.0, 0.08333333333333333, 0.0, 90.0, 0.0, -0.08333333333333333)  # NOTE, the 0.08333333333333333 is defined very precisely as the answer a 64 bit compiled python gives from the answer 1/12 (i.e. 5 arc minutes)
geotransform_global_5min = (-180.0, 0.08333333333333333, 0.0, 90.0, 0.0, -0.08333333333333333)  # NOTE, the 0.08333333333333333 is defined very precisely as the answer a 64 bit compiled python gives from the answer 1/12 (i.e. 5 arc minutes)
geotransform_global_30s = (-180.0, 0.008333333333333333, 0.0, 90.0, 0.0, -0.008333333333333333)  # NOTE, the 0.008333333333333333 is defined very precisely as the answer a 64 bit compiled python gives from the answer 1/120 (i.e. 30 arc seconds) Note that this has 1 more digit than 1/12 due to how floating points are stored in computers via exponents.
geotransform_global_30sec = (-180.0, 0.008333333333333333, 0.0, 90.0, 0.0, -0.008333333333333333)  # NOTE, the 0.008333333333333333 is defined very precisely as the answer a 64 bit compiled python gives from the answer 1/120 (i.e. 30 arc seconds) Note that this has 1 more digit than 1/12 due to how floating points are stored in computers via exponents.
geotransform_global_10s = (-180.0, 0.002777777777777778, 0.0, 90.0, 0.0, -0.002777777777777778)  # NOTE, the 0.002777777777777778 is defined very precisely
geotransform_global_10sec = (-180.0, 0.002777777777777778, 0.0, 90.0, 0.0, -0.002777777777777778)  # NOTE, the 0.002777777777777778 is defined very precisely
geotransform_global_1sec = (-180.0, 0.0002777777777777777775, 0.0, 90.0, 0.0, -0.0002777777777777777775)  # WTF, the 77775 comes from QGIS after gdal, but this number in python goes down in precision to 7778 NOTE, the 0.0002777777777777777775 is defined very precisely, in this case from the gdal C library

#### DEPRECATED BY PYRAMIDS.py data but kept for compatibility. TODOOO clean.
common_geotransforms = {
    'global_5m': geotransform_global_5min,
    'global_30s': geotransform_global_30sec, 
} # Maybe deprecate?

global_cr_1sec = (1296000, 648000)

size_of_one_arcdegree_at_equator_in_meters = 111319.49079327358  # Based on (2 * math.pi * 6378.137*1000) / 360  # old 111319

esacci_standard_classes = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210, 220, ]

esacci_standard_class_descriptions = OrderedDict()
esacci_standard_class_descriptions[0] = 'No Data'
esacci_standard_class_descriptions[10] = 'Cropland, rainfed'
esacci_standard_class_descriptions[20] = 'Cropland, irrigated or post-flooding'
esacci_standard_class_descriptions[30] = 'Mosaic cropland (>50%) / natural vegetation (tree, shrub, herbaceous cover)(<50%)'
esacci_standard_class_descriptions[40] = 'Mosaic natural vegetation (tree, shrub, herbaceous cover) (>50%) / cropland(<50%)'
esacci_standard_class_descriptions[50] = 'Tree cover, broadleaved, evergreen, closed to open (>15%)'
esacci_standard_class_descriptions[60] = 'Tree cover, broadleaved, deciduous, closed to open (>15%)'
esacci_standard_class_descriptions[70] = 'Tree cover, needleleaved, evergreen, closed to open (>15%)'
esacci_standard_class_descriptions[80] = 'Tree cover, needleleaved, deciduous, closed to open (>15%)'
esacci_standard_class_descriptions[90] = 'Tree cover, mixed leaf type (broadleaved and needleleaved)'
esacci_standard_class_descriptions[100] = 'Mosaic tree and shrub (>50%) / herbaceous cover (<50%)'
esacci_standard_class_descriptions[110] = 'Mosaic herbaceous cover (>50%) / tree and shrub (<50%)'
esacci_standard_class_descriptions[120] = 'Shrubland'
esacci_standard_class_descriptions[130] = 'Grassland'
esacci_standard_class_descriptions[140] = 'Lichens and mosses'
esacci_standard_class_descriptions[150] = 'Sparse vegetation (tree, shrub, herbaceous cover) (<15%)'
esacci_standard_class_descriptions[160] = 'Tree cover, flooded, fresh or brakish water'
esacci_standard_class_descriptions[170] = 'Tree cover, flooded, saline water'
esacci_standard_class_descriptions[180] = 'Shrub or herbaceous cover, flooded, fresh/saline/brakish water'  # Underestimates wetland GIEMS might be able to improve this (lehner et al.)
esacci_standard_class_descriptions[190] = 'Urban areas'
esacci_standard_class_descriptions[200] = 'Bare areas'
esacci_standard_class_descriptions[210] = 'Water bodies'
esacci_standard_class_descriptions[220] = 'Permanent snow and ice'

esacci_extended_classes = [0, 10, 11, 12, 20, 30, 40, 50, 60, 61, 62, 70, 71, 72, 80, 81, 82, 90, 100, 110, 120, 121, 122, 130, 140, 150, 151, 152, 153, 160, 170, 180, 190, 200, 201, 202, 210, 220]
esacci_extended_class_descriptions = OrderedDict()
esacci_extended_class_descriptions[0] = 'No Data'
esacci_extended_class_descriptions[10] = 'Cropland, rainfed'
esacci_extended_class_descriptions[11] = 'Cropland, rainfed, herbaceous cover'
esacci_extended_class_descriptions[12] = 'Cropland, rainfed, tree or shrub cover'
esacci_extended_class_descriptions[20] = 'Cropland, irrigated or post-flooding'
esacci_extended_class_descriptions[30] = 'Mosaic cropland (>50%) / natural vegetation (tree, shrub, herbaceous cover)(<50%)'
esacci_extended_class_descriptions[40] = 'Mosaic natural vegetation (tree, shrub, herbaceous cover) (>50%) / cropland(<50%)'
esacci_extended_class_descriptions[50] = 'Tree cover, broadleaved, evergreen, closed to open (>15%)'
esacci_extended_class_descriptions[60] = 'Tree cover, broadleaved, deciduous, closed to open (>15%)'
esacci_extended_class_descriptions[61] = 'Tree cover, broadleaved, deciduous, closed (>40%)'
esacci_extended_class_descriptions[62] = 'Tree cover, broadleaved, deciduous, open (15-40%)'
esacci_extended_class_descriptions[70] = 'Tree cover, needleleaved, evergreen, closed to open (>15%)'
esacci_extended_class_descriptions[71] = 'Tree cover, needleleaved, evergreen, closed to open (>15%)'
esacci_extended_class_descriptions[72] = 'Tree cover, needleleaved, evergreen, open (15-40%)'
esacci_extended_class_descriptions[80] = 'Tree cover, needleleaved, deciduous, closed to open (>15%)'
esacci_extended_class_descriptions[81] = 'Tree cover, needleleaved, deciduous, closed (>40%)'
esacci_extended_class_descriptions[82] = 'Tree cover, needleleaved, deciduous, open (15-40%)'
esacci_extended_class_descriptions[90] = 'Tree cover, mixed leaf type (broadleaved and needleleaved)'
esacci_extended_class_descriptions[100] = 'Mosaic tree and shrub (>50%) / herbaceous cover (<50%)'
esacci_extended_class_descriptions[110] = 'Mosaic herbaceous cover (>50%) / tree and shrub (<50%)'
esacci_extended_class_descriptions[120] = 'Shrubland'
esacci_extended_class_descriptions[121] = 'Evergreen shrubland'
esacci_extended_class_descriptions[122] = 'Deciduous shrubland '
esacci_extended_class_descriptions[130] = 'Grassland'
esacci_extended_class_descriptions[140] = 'Lichens and mosses'
esacci_extended_class_descriptions[150] = 'Sparse vegetation (tree, shrub, herbaceous cover) (<15%)'
esacci_extended_class_descriptions[151] = 'Sparse tree (<15%)'
esacci_extended_class_descriptions[152] = 'Sparse shrub (<15%)'
esacci_extended_class_descriptions[153] = 'Sparse herbaceous cover (<15%)'
esacci_extended_class_descriptions[160] = 'Tree cover, flooded, fresh or brakish water'
esacci_extended_class_descriptions[170] = 'Tree cover, flooded, saline water'
esacci_extended_class_descriptions[180] = 'Shrub or herbaceous cover, flooded, fresh/saline/brakish water'
esacci_extended_class_descriptions[190] = 'Urban areas'
esacci_extended_class_descriptions[200] = 'Bare areas'
esacci_extended_class_descriptions[201] = 'Consolidated bare areas'
esacci_extended_class_descriptions[202] = 'Unconsolidated bare areas'
esacci_extended_class_descriptions[210] = 'Water bodies'
esacci_extended_class_descriptions[220] = 'Permanent snow and ice'

esacci_extended_short_class_descriptions = OrderedDict()
esacci_extended_short_class_descriptions[0] = 'ndv'
esacci_extended_short_class_descriptions[10] = 'crop_rainfed'
esacci_extended_short_class_descriptions[11] = 'crop_rainfed_herb'
esacci_extended_short_class_descriptions[12] = 'crop_rainfed_tree'
esacci_extended_short_class_descriptions[20] = 'crop_irrigated'
esacci_extended_short_class_descriptions[30] = 'crop_natural_mosaic'
esacci_extended_short_class_descriptions[40] = 'natural_crop_mosaic'
esacci_extended_short_class_descriptions[50] = 'tree_broadleaved_evergreen'
esacci_extended_short_class_descriptions[60] = 'tree_broadleaved_deciduous_closed_to_open_15'
esacci_extended_short_class_descriptions[61] = 'tree_broadleaved_deciduous_closed_40'
esacci_extended_short_class_descriptions[62] = 'tree_broadleaved_deciduous_open_15_40'
esacci_extended_short_class_descriptions[70] = 'tree_needleleaved_evergreen_closed_to_open_15'
esacci_extended_short_class_descriptions[71] = 'tree_needleleaved_evergreen_closed_to_open_15_extended'
esacci_extended_short_class_descriptions[72] = 'tree_needleleaved_evergreen_open_15_40'
esacci_extended_short_class_descriptions[80] = 'tree_needleleaved_deciduous_closed_to_open_15'
esacci_extended_short_class_descriptions[81] = 'tree_needleleaved_deciduous_closed_40'
esacci_extended_short_class_descriptions[82] = 'tree_needleleaved_deciduous_open_15_40'
esacci_extended_short_class_descriptions[90] = 'tree_mixed_type'
esacci_extended_short_class_descriptions[100] = 'mosaic_tree_and_shrub_50_herbaceous_cover_50'
esacci_extended_short_class_descriptions[110] = 'mosaic_herbaceous_cover_50_tree_and_shrub_50'
esacci_extended_short_class_descriptions[120] = 'shrubland'
esacci_extended_short_class_descriptions[121] = 'evergreen_shrubland'
esacci_extended_short_class_descriptions[122] = 'deciduous_shrubland'
esacci_extended_short_class_descriptions[130] = 'grassland'
esacci_extended_short_class_descriptions[140] = 'lichens_and_mosses'
esacci_extended_short_class_descriptions[150] = 'sparse_vegetation_tree_shrub_herbaceous_cover_15'
esacci_extended_short_class_descriptions[151] = 'sparse_tree_15'
esacci_extended_short_class_descriptions[152] = 'sparse_shrub_15'
esacci_extended_short_class_descriptions[153] = 'sparse_herbaceous_cover_15'
esacci_extended_short_class_descriptions[160] = 'tree_cover_flooded_fresh_or_brakish_water'
esacci_extended_short_class_descriptions[170] = 'tree_cover_flooded_saline_water'
esacci_extended_short_class_descriptions[180] = 'shrub_or_herbaceous_cover_flooded_fresh_saline_brakish_water'
esacci_extended_short_class_descriptions[190] = 'urban_areas'
esacci_extended_short_class_descriptions[200] = 'bare_areas'
esacci_extended_short_class_descriptions[201] = 'consolidated_bare_areas'
esacci_extended_short_class_descriptions[202] = 'unconsolidated_bare_areas'
esacci_extended_short_class_descriptions[210] = 'water_bodies'
esacci_extended_short_class_descriptions[220] = 'permanent_snow_and_ice'

# Decided this is the preferred method for storing the correspondence data and then also making it into a rules dict.
esacci_to_seals_simplified_correspondence = OrderedDict()
esacci_to_seals_simplified_correspondence[0] = [0, 'ndv', 'ndv']
esacci_to_seals_simplified_correspondence[10] = [2, 'crop_rainfed', 'crop']
esacci_to_seals_simplified_correspondence[11] = [2, 'crop_rainfed_herb', 'crop']
esacci_to_seals_simplified_correspondence[12] = [2, 'crop_rainfed_tree', 'crop']
esacci_to_seals_simplified_correspondence[20] = [2, 'crop_irrigated', 'crop']
esacci_to_seals_simplified_correspondence[30] = [2, 'crop_natural_mosaic', 'crop']
esacci_to_seals_simplified_correspondence[40] = [2, 'natural_crop_mosaic', 'crop']
esacci_to_seals_simplified_correspondence[50] = [4, 'tree_broadleaved_evergreen', 'forest']
esacci_to_seals_simplified_correspondence[60] = [4, 'tree_broadleaved_deciduous_closed_to_open_15', 'forest']
esacci_to_seals_simplified_correspondence[61] = [4, 'tree_broadleaved_deciduous_closed_40', 'forest']
esacci_to_seals_simplified_correspondence[62] = [4, 'tree_broadleaved_deciduous_open_15_40', 'forest']
esacci_to_seals_simplified_correspondence[70] = [4, 'tree_needleleaved_deciduous_closed_to_open_15', 'forest']
esacci_to_seals_simplified_correspondence[71] = [4, 'tree_needleleaved_evergreen_closed_to_open_15_extended', 'forest']
esacci_to_seals_simplified_correspondence[72] = [4, 'tree_needleleaved_evergreen_open_15_40', 'forest']
esacci_to_seals_simplified_correspondence[80] = [4, 'tree_needleleaved_deciduous_closed_to_open_15', 'forest']
esacci_to_seals_simplified_correspondence[81] = [4, 'tree_needleleaved_deciduous_closed_40', 'forest']
esacci_to_seals_simplified_correspondence[82] = [4, 'tree_needleleaved_deciduous_open_15_40', 'forest']
esacci_to_seals_simplified_correspondence[90] = [4, 'tree_mixed_type', 'forest']
esacci_to_seals_simplified_correspondence[100] = [4, 'mosaic_tree_and_shrub_50_herbaceous_cover_50', 'forest']
esacci_to_seals_simplified_correspondence[110] = [5, 'mosaic_herbaceous_cover_50_tree_and_shrub_50', 'shrubland']
esacci_to_seals_simplified_correspondence[120] = [5, 'shrubland', 'shrubland']
esacci_to_seals_simplified_correspondence[121] = [5, 'evergreen_shrubland', 'shrubland']
esacci_to_seals_simplified_correspondence[122] = [5, 'deciduous_shrubland', 'shrubland']
esacci_to_seals_simplified_correspondence[130] = [3, 'grassland', 'grassland']
esacci_to_seals_simplified_correspondence[140] = [5, 'lichens_and_mosses', 'shrubland']
esacci_to_seals_simplified_correspondence[150] = [5, 'sparse_vegetation_tree_shrub_herbaceous_cover_15', 'shrubland']
esacci_to_seals_simplified_correspondence[151] = [4, 'sparse_tree_15', 'forest']
esacci_to_seals_simplified_correspondence[152] = [5, 'sparse_shrub_15', 'shrubland']
esacci_to_seals_simplified_correspondence[153] = [5, 'sparse_herbaceous_cover_15', 'shrubland']
esacci_to_seals_simplified_correspondence[160] = [4, 'tree_cover_flooded_fresh_or_brakish_water', 'forest']
esacci_to_seals_simplified_correspondence[170] = [4, 'tree_cover_flooded_saline_water', 'forest']
esacci_to_seals_simplified_correspondence[180] = [5, 'shrub_or_herbaceous_cover_flooded_fresh_saline_brakish_water', 'shrubland']
esacci_to_seals_simplified_correspondence[190] = [1, 'urban_areas', 'urban']
esacci_to_seals_simplified_correspondence[200] = [7, 'bare_areas', 'other']
esacci_to_seals_simplified_correspondence[201] = [7, 'consolidated_bare_areas', 'other']
esacci_to_seals_simplified_correspondence[202] = [7, 'unconsolidated_bare_areas', 'other']
esacci_to_seals_simplified_correspondence[210] = [6, 'water_bodies', 'water']
esacci_to_seals_simplified_correspondence[220] = [7, 'permanent_snow_and_ice', 'other']

esacci_to_seals_simplified_mosaic_is_natural_correspondence = OrderedDict()
esacci_to_seals_simplified_mosaic_is_natural_correspondence[0] = [0, 'ndv', 'ndv']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[10] = [2, 'crop_rainfed', 'crop']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[11] = [2, 'crop_rainfed_herb', 'crop']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[12] = [2, 'crop_rainfed_tree', 'crop']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[20] = [2, 'crop_irrigated', 'crop']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[30] = [5, 'crop_natural_mosaic', 'shrubland'] # DIFF IS HERE
esacci_to_seals_simplified_mosaic_is_natural_correspondence[40] = [4, 'natural_crop_mosaic', 'forest'] # DIFF IS HERE
esacci_to_seals_simplified_mosaic_is_natural_correspondence[50] = [4, 'tree_broadleaved_evergreen', 'forest']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[60] = [4, 'tree_broadleaved_deciduous_closed_to_open_15', 'forest']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[61] = [4, 'tree_broadleaved_deciduous_closed_40', 'forest']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[62] = [4, 'tree_broadleaved_deciduous_open_15_40', 'forest']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[70] = [4, 'tree_needleleaved_deciduous_closed_to_open_15', 'forest']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[71] = [4, 'tree_needleleaved_evergreen_closed_to_open_15_extended', 'forest']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[72] = [4, 'tree_needleleaved_evergreen_open_15_40', 'forest']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[80] = [4, 'tree_needleleaved_deciduous_closed_to_open_15', 'forest']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[81] = [4, 'tree_needleleaved_deciduous_closed_40', 'forest']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[82] = [4, 'tree_needleleaved_deciduous_open_15_40', 'forest']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[90] = [4, 'tree_mixed_type', 'forest']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[100] = [4, 'mosaic_tree_and_shrub_50_herbaceous_cover_50', 'forest']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[110] = [5, 'mosaic_herbaceous_cover_50_tree_and_shrub_50', 'shrubland']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[120] = [5, 'shrubland', 'shrubland']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[121] = [5, 'evergreen_shrubland', 'shrubland']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[122] = [5, 'deciduous_shrubland', 'shrubland']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[130] = [3, 'grassland', 'grassland']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[140] = [5, 'lichens_and_mosses', 'shrubland']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[150] = [5, 'sparse_vegetation_tree_shrub_herbaceous_cover_15', 'shrubland']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[151] = [4, 'sparse_tree_15', 'forest']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[152] = [5, 'sparse_shrub_15', 'shrubland']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[153] = [5, 'sparse_herbaceous_cover_15', 'shrubland']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[160] = [4, 'tree_cover_flooded_fresh_or_brakish_water', 'forest']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[170] = [4, 'tree_cover_flooded_saline_water', 'forest']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[180] = [5, 'shrub_or_herbaceous_cover_flooded_fresh_saline_brakish_water', 'shrubland']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[190] = [1, 'urban_areas', 'urban']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[200] = [7, 'bare_areas', 'other']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[201] = [7, 'consolidated_bare_areas', 'other']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[202] = [7, 'unconsolidated_bare_areas', 'other']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[210] = [6, 'water_bodies', 'water']
esacci_to_seals_simplified_mosaic_is_natural_correspondence[220] = [7, 'permanent_snow_and_ice', 'other']

# Decided this is the preferred method for storing the correspondence data and then also making it into a rules dict.
esacci_to_habitat_quality_simplified_correspondence = OrderedDict()
esacci_to_habitat_quality_simplified_correspondence[0] = [0, 'ndv', 'ndv']
esacci_to_habitat_quality_simplified_correspondence[10] = [2, 'crop_rainfed', 'crop']
esacci_to_habitat_quality_simplified_correspondence[11] = [2, 'crop_rainfed_herb', 'crop']
esacci_to_habitat_quality_simplified_correspondence[12] = [2, 'crop_rainfed_tree', 'crop']
esacci_to_habitat_quality_simplified_correspondence[20] = [2, 'crop_irrigated', 'crop']
esacci_to_habitat_quality_simplified_correspondence[30] = [2, 'crop_natural_mosaic', 'crop']
esacci_to_habitat_quality_simplified_correspondence[40] = [4, 'natural_crop_mosaic', 'low_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[50] = [6, 'tree_broadleaved_evergreen', 'high_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[60] = [6, 'tree_broadleaved_deciduous_closed_to_open_15', 'high_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[61] = [6, 'tree_broadleaved_deciduous_closed_40', 'high_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[62] = [6, 'tree_broadleaved_deciduous_open_15_40', 'high_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[70] = [6, 'tree_needleleaved_deciduous_closed_to_open_15', 'high_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[71] = [6, 'tree_needleleaved_evergreen_closed_to_open_15_extended', 'high_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[72] = [6, 'tree_needleleaved_evergreen_open_15_40', 'high_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[80] = [6, 'tree_needleleaved_deciduous_closed_to_open_15', 'high_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[81] = [6, 'tree_needleleaved_deciduous_closed_40', 'high_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[82] = [6, 'tree_needleleaved_deciduous_open_15_40', 'high_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[90] = [6, 'tree_mixed_type', 'high_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[100] = [5, 'mosaic_tree_and_shrub_50_herbaceous_cover_50', 'medium_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[110] = [5, 'mosaic_herbaceous_cover_50_tree_and_shrub_50', 'medium_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[120] = [5, 'shrubland', 'medium_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[121] = [5, 'evergreen_shrubland', 'medium_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[122] = [5, 'deciduous_shrubland', 'medium_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[130] = [4, 'grassland', 'low_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[140] = [4, 'lichens_and_mosses', 'low_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[150] = [4, 'sparse_vegetation_tree_shrub_herbaceous_cover_15', 'low_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[151] = [4, 'sparse_tree_15', 'low_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[152] = [4, 'sparse_shrub_15', 'low_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[153] = [4, 'sparse_herbaceous_cover_15', 'low_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[160] = [6, 'tree_cover_flooded_fresh_or_brakish_water', 'high_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[170] = [6, 'tree_cover_flooded_saline_water', 'high_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[180] = [6, 'shrub_or_herbaceous_cover_flooded_fresh_saline_brakish_water', 'high_cv_habitat']
esacci_to_habitat_quality_simplified_correspondence[190] = [1, 'urban_areas', 'urban']
esacci_to_habitat_quality_simplified_correspondence[200] = [3, 'bare_areas', 'bare']
esacci_to_habitat_quality_simplified_correspondence[201] = [3, 'consolidated_bare_areas', 'bare']
esacci_to_habitat_quality_simplified_correspondence[202] = [3, 'unconsolidated_bare_areas', 'bare']
esacci_to_habitat_quality_simplified_correspondence[210] = [6, 'water_bodies', 'water']
esacci_to_habitat_quality_simplified_correspondence[220] = [3, 'permanent_snow_and_ice', 'bare']

# Decided this is the preferred method for storing the correspondence data and then also making it into a rules dict.
esacci_to_seals_simplified_rules = OrderedDict(zip(esacci_to_seals_simplified_correspondence.keys(), [i[0] for i in esacci_to_seals_simplified_correspondence.values()]))

seals_simplified_to_esacci_correspondence = OrderedDict()
seals_simplified_to_esacci_correspondence[0] = [0, 'ndv', 'ndv']
seals_simplified_to_esacci_correspondence[1] = [190, 'urban', 'urban_areas']
seals_simplified_to_esacci_correspondence[2] = [10, 'crop', 'crop_rainfed']
seals_simplified_to_esacci_correspondence[3] = [130, 'grassland', 'grassland']
seals_simplified_to_esacci_correspondence[4] = [50, 'forest', 'tree_broadleaved_evergreen']
seals_simplified_to_esacci_correspondence[5] = [120, 'shrubland', 'shrubland']
seals_simplified_to_esacci_correspondence[6] = [210, 'water', 'water_bodies']
seals_simplified_to_esacci_correspondence[7] = [200, 'other', 'bare_areas']

seals_simplified_labels = {}
seals_simplified_labels[0] = 'ndv'
seals_simplified_labels[1] = 'urban'
seals_simplified_labels[2] = 'crop'
seals_simplified_labels[3] = 'grassland'
seals_simplified_labels[4] = 'forest'
seals_simplified_labels[5] = 'shrubland'
seals_simplified_labels[6] = 'water'
seals_simplified_labels[7] = 'other'

# Decided this is the preferred method for storing the correspondence data and then also making it into a rules dict.
seals_simplified_to_esa_rules = OrderedDict(zip(seals_simplified_to_esacci_correspondence.keys(), [i[0] for i in seals_simplified_to_esacci_correspondence.values()]))

glc_classes_to_labels = OrderedDict()
glc_classes_to_labels[1] = 'tree_broadleaved_evergreen'
glc_classes_to_labels[2] = 'tree_broadleaved_deciduous_closed'
glc_classes_to_labels[3] = 'tree_broadleaved_deciduous_open'
glc_classes_to_labels[4] = 'tree_needleleaved_evergreen'
glc_classes_to_labels[5] = 'tree_needleleaved_deciduous'
glc_classes_to_labels[6] = 'tree_mixed_type'
glc_classes_to_labels[7] = 'tree_cover_flooded_fresh_or_brakish_water'
glc_classes_to_labels[8] = 'tree_cover_flooded_saline_water'
glc_classes_to_labels[9] = 'mosaic'
glc_classes_to_labels[10] = 'tree_cover_burnt'
glc_classes_to_labels[11] = 'evergreen_shrubland'
glc_classes_to_labels[12] = 'deciduous_shrubland'
glc_classes_to_labels[13] = 'herbaceous'
glc_classes_to_labels[14] = 'sparse_herbaceous_cover'
glc_classes_to_labels[15] = 'shrub_or_herbaceous_cover_flooded_fresh_saline_brakish_water'
glc_classes_to_labels[16] = 'cultivated'
glc_classes_to_labels[17] = 'crop_tree_mosaic'
glc_classes_to_labels[18] = 'crop_shrub_mosaic'
glc_classes_to_labels[19] = 'bare'
glc_classes_to_labels[20] = 'water'
glc_classes_to_labels[21] = 'snow_and_ice'
glc_classes_to_labels[22] = 'artificial_surface'

esacci_to_glc2000_correspondence = OrderedDict()
esacci_to_glc2000_correspondence[0] = [0, 'ndv']
esacci_to_glc2000_correspondence[10] = [16, 'crop_rainfed']
esacci_to_glc2000_correspondence[11] = [16, 'crop_rainfed_herb']
esacci_to_glc2000_correspondence[12] = [16, 'crop_rainfed_tree']
esacci_to_glc2000_correspondence[20] = [16, 'crop_irrigated']
esacci_to_glc2000_correspondence[30] = [17, 'crop_natural_mosaic']
esacci_to_glc2000_correspondence[40] = [17, 'natural_crop_mosaic']
esacci_to_glc2000_correspondence[50] = [1, 'tree_broadleaved_evergreen']
esacci_to_glc2000_correspondence[60] = [2, 'tree_broadleaved_deciduous_closed_to_open_15']
esacci_to_glc2000_correspondence[61] = [2, 'tree_broadleaved_deciduous_closed_40']
esacci_to_glc2000_correspondence[62] = [5, 'tree_broadleaved_deciduous_open_15_40']
esacci_to_glc2000_correspondence[70] = [5, 'tree_needleleaved_deciduous_closed_to_open_15']
esacci_to_glc2000_correspondence[71] = [4, 'tree_needleleaved_evergreen_closed_to_open_15_extended']
esacci_to_glc2000_correspondence[72] = [4, 'tree_needleleaved_evergreen_open_15_40']
esacci_to_glc2000_correspondence[80] = [5, 'tree_needleleaved_deciduous_closed_to_open_15']
esacci_to_glc2000_correspondence[81] = [5, 'tree_needleleaved_deciduous_closed_40']
esacci_to_glc2000_correspondence[82] = [5, 'tree_needleleaved_deciduous_open_15_40']
esacci_to_glc2000_correspondence[90] = [6, 'tree_mixed_type']
esacci_to_glc2000_correspondence[100] = [9, 'mosaic_tree_and_shrub_50_herbaceous_cover_50']
esacci_to_glc2000_correspondence[110] = [9, 'mosaic_herbaceous_cover_50_tree_and_shrub_50']
esacci_to_glc2000_correspondence[120] = [12, 'shrubland']
esacci_to_glc2000_correspondence[121] = [11, 'evergreen_shrubland']
esacci_to_glc2000_correspondence[122] = [12, 'deciduous_shrubland']
esacci_to_glc2000_correspondence[130] = [13, 'grassland']
esacci_to_glc2000_correspondence[140] = [13, 'lichens_and_mosses']
esacci_to_glc2000_correspondence[150] = [13, 'sparse_vegetation_tree_shrub_herbaceous_cover_15']
esacci_to_glc2000_correspondence[151] = [14, 'sparse_tree_15']
esacci_to_glc2000_correspondence[152] = [14, 'sparse_shrub_15']
esacci_to_glc2000_correspondence[153] = [14, 'sparse_herbaceous_cover_15']
esacci_to_glc2000_correspondence[160] = [7, 'tree_cover_flooded_fresh_or_brakish_water']
esacci_to_glc2000_correspondence[170] = [8, 'tree_cover_flooded_saline_water']
esacci_to_glc2000_correspondence[180] = [15, 'shrub_or_herbaceous_cover_flooded_fresh_saline_brakish_water']
esacci_to_glc2000_correspondence[190] = [22, 'urban_areas']
esacci_to_glc2000_correspondence[200] = [19, 'bare_areas']
esacci_to_glc2000_correspondence[201] = [19, 'consolidated_bare_areas']
esacci_to_glc2000_correspondence[202] = [19, 'unconsolidated_bare_areas']
esacci_to_glc2000_correspondence[210] = [20, 'water_bodies']
esacci_to_glc2000_correspondence[220] = [21, 'permanent_snow_and_ice']

soilgrid_variable_names = [
    'ACDWRB',
    'AWCh1',
    'AWCh2',
    'AWCh3',
    'BDRICM',
    'BDRLOG',
    'BDTICM',
    'BLDFIE',
    'CECSOL',
    'CLYPPT',
    'CRFVOL',
    'HISTPR',
    'OCDENS',
    'OCSTHA',
    'ORCDRC',
    'PHIHOX',
    'PHIKCL',
    'SLGWRB',
    'SLTPPT',
    'SNDPPT',
    'TAXOUSDA',
    'TAXNWRB',
    'TEXMHT',
    'WWP',
]

soilgrid_variable_descriptions = OrderedDict()

soilgrid_variable_descriptions['ACDWRB'] = 'Grade of a sub-soil being acid e.g. having a pH < 5 and low BS:'
soilgrid_variable_descriptions['AWCh1'] = 'Available soil water capacity (volumetric fraction) with FC = pF 2.0: grade'
soilgrid_variable_descriptions['AWCh2'] = 'Available soil water capacity (volumetric fraction) with FC = pF 2.3: percentage'
soilgrid_variable_descriptions['AWCh3'] = 'Available soil water capacity (volumetric fraction) with FC = pF 2.5: percentage'
soilgrid_variable_descriptions['BDRICM'] = 'Depth to bedrock (R horizon) up to 200 cm: percentage'
soilgrid_variable_descriptions['BDRLOG'] = 'Probability of occurrence of R horizon: cm'
soilgrid_variable_descriptions['BDTICM'] = 'Absolute depth to bedrock: percentage'
soilgrid_variable_descriptions['BLDFIE'] = 'Bulk density (fine earth): cm'
soilgrid_variable_descriptions['CECSOL'] = 'Cation Exchange Capacity of soil: kg/m3'
soilgrid_variable_descriptions['CLYPPT'] = 'Weight percentage of the clay particles (<0.0002 mm): cmolc/kg'
soilgrid_variable_descriptions['CRFVOL'] = 'Volumetric percentage of coarse fragments (>2 mm): percentage'
soilgrid_variable_descriptions['HISTPR'] = 'Histosols probability cumulative: percentage'
soilgrid_variable_descriptions['OCDENS'] = 'Soil organic carbon density: percentage'
soilgrid_variable_descriptions['OCSTHA'] = 'Soil organic carbon stock: kg/m3'
soilgrid_variable_descriptions['ORCDRC'] = 'Soil organic carbon content: ton/ha'
soilgrid_variable_descriptions['PHIHOX'] = 'pH index measured in water solution: permille'
soilgrid_variable_descriptions['PHIKCL'] = 'pH index measured in KCl solution: pH'
soilgrid_variable_descriptions['SLGWRB'] = 'Sodic soil grade: pH'
soilgrid_variable_descriptions['SLTPPT'] = 'Weight percentage of the silt particles (0.0002–0.05 mm): grade'
soilgrid_variable_descriptions['SNDPPT'] = 'Weight percentage of the sand particles (0.05–2 mm): percentage'
soilgrid_variable_descriptions['TAXOUSDA'] = 'Keys to Soil Taxonomy suborders: percentage'
soilgrid_variable_descriptions['TAXNWRB'] = 'World Reference Base legend: -'
soilgrid_variable_descriptions['TEXMHT'] = 'Texture class (USDA system): -'
soilgrid_variable_descriptions['WWP'] = 'Available soil water capacity (volumetric fraction) until wilting point: -'

nlcd_colors = OrderedDict()
nlcd_colors[0] = [0, 0, 0]
nlcd_colors[1] = [0, 249, 0]
nlcd_colors[11] = [71, 107, 160]
nlcd_colors[12] = [209, 221, 249]
nlcd_colors[21] = [221, 201, 201]
nlcd_colors[22] = [216, 147, 130]
nlcd_colors[23] = [237, 0, 0]
nlcd_colors[24] = [170, 0, 0]
nlcd_colors[31] = [178, 173, 163]
nlcd_colors[32] = [249, 249, 249]
nlcd_colors[41] = [104, 170, 99]
nlcd_colors[42] = [28, 99, 48]
nlcd_colors[43] = [181, 201, 142]
nlcd_colors[51] = [165, 140, 48]
nlcd_colors[52] = [204, 186, 124]
nlcd_colors[71] = [226, 226, 193]
nlcd_colors[72] = [201, 201, 119]
nlcd_colors[73] = [153, 193, 71]
nlcd_colors[74] = [119, 173, 147]
nlcd_colors[81] = [219, 216, 61]
nlcd_colors[82] = [170, 112, 40]
nlcd_colors[90] = [186, 216, 234]
nlcd_colors[91] = [181, 211, 229]
nlcd_colors[92] = [181, 211, 229]
nlcd_colors[93] = [181, 211, 229]
nlcd_colors[94] = [181, 211, 229]
nlcd_colors[95] = [112, 163, 186]

nlcd_category_names = OrderedDict()
nlcd_category_names[0] = 'ndv'
nlcd_category_names[11] = 'Open Water'
nlcd_category_names[12] = 'Perennial Ice/Snow'
nlcd_category_names[21] = 'Developed, Open Space'
nlcd_category_names[22] = 'Developed, Low Intensity'
nlcd_category_names[23] = 'Developed, Medium Intensity'
nlcd_category_names[24] = 'Developed High Intensity'
nlcd_category_names[31] = 'Barren Land (Rock/Sand/Clay)'
nlcd_category_names[41] = 'Deciduous Forest'
nlcd_category_names[42] = 'Evergreen Forest'
nlcd_category_names[43] = 'Mixed Forest'
nlcd_category_names[51] = 'Dwarf Scrub'
nlcd_category_names[52] = 'Shrub/Scrub'
nlcd_category_names[71] = 'Grassland/Herbaceous'
nlcd_category_names[72] = 'Sedge/Herbaceous'
nlcd_category_names[73] = 'Lichens'
nlcd_category_names[74] = 'Moss'
nlcd_category_names[81] = 'Pasture/Hay'
nlcd_category_names[82] = 'Cultivated Crops'
nlcd_category_names[90] = 'Woody Wetlands'
nlcd_category_names[95] = 'Emergent Herbaceous Wetlands'

nlcd_category_descriptions = OrderedDict()
nlcd_category_descriptions[0] = 'ndv'
nlcd_category_descriptions[11] = 'areas of open water, generally with less than 25% cover of vegetation or soil.'
nlcd_category_descriptions[12] = 'areas characterized by a perennial cover of ice and/or snow, generally greater than 25% of total cover.'
nlcd_category_descriptions[21] = 'areas with a mixture of some constructed materials, but mostly vegetation in the form of lawn grasses. Impervious surfaces account for less than 20% of total cover. These areas most commonly include large-lot single-family housing units, parks, golf courses, and vegetation planted in developed settings for recreation, erosion control, or aesthetic purposes.'
nlcd_category_descriptions[22] = 'areas with a mixture of constructed materials and vegetation. Impervious surfaces account for 20% to 49% percent of total cover. These areas most commonly include single-family housing units.'
nlcd_category_descriptions[23] = 'areas with a mixture of constructed materials and vegetation. Impervious surfaces account for 50% to 79% of the total cover. These areas most commonly include single-family housing units.'
nlcd_category_descriptions[24] = 'highly developed areas where people reside or work in high numbers. Examples include apartment complexes, row houses and commercial/industrial. Impervious surfaces account for 80% to 100% of the total cover.'
nlcd_category_descriptions[31] = 'areas of bedrock, desert pavement, scarps, talus, slides, volcanic material, glacial debris, sand dunes, strip mines, gravel pits and other accumulations of earthen material. Generally, vegetation accounts for less than 15% of total cover.'
nlcd_category_descriptions[41] = 'areas dominated by trees generally greater than 5 meters tall, and greater than 20% of total vegetation cover. More than 75% of the tree species shed foliage simultaneously in response to seasonal change.'
nlcd_category_descriptions[42] = 'areas dominated by trees generally greater than 5 meters tall, and greater than 20% of total vegetation cover. More than 75% of the tree species maintain their leaves all year. Canopy is never without green foliage.'
nlcd_category_descriptions[43] = 'areas dominated by trees generally greater than 5 meters tall, and greater than 20% of total vegetation cover. Neither deciduous nor evergreen species are greater than 75% of total tree cover.'
nlcd_category_descriptions[51] = 'Alaska only areas dominated by shrubs less than 20 centimeters tall with shrub canopy typically greater than 20% of total vegetation. This type is often co-associated with grasses, sedges, herbs, and non-vascular vegetation.'
nlcd_category_descriptions[52] = 'areas dominated by shrubs; less than 5 meters tall with shrub canopy typically greater than 20% of total vegetation. This class includes true shrubs, young trees in an early successional stage or trees stunted from environmental conditions.'
nlcd_category_descriptions[71] = 'areas dominated by gramanoid or herbaceous vegetation, generally greater than 80% of total vegetation. These areas are not subject to intensive management such as tilling, but can be utilized for grazing.'
nlcd_category_descriptions[72] = 'Alaska only areas dominated by sedges and forbs, generally greater than 80% of total vegetation. This type can occur with significant other grasses or other grass like plants, and includes sedge tundra, and sedge tussock tundra.'
nlcd_category_descriptions[73] = 'Alaska only areas dominated by fruticose or foliose lichens generally greater than 80% of total vegetation.'
nlcd_category_descriptions[74] = 'Alaska only areas dominated by mosses, generally greater than 80% of total vegetation.'
nlcd_category_descriptions[81] = 'areas of grasses, legumes, or grass-legume mixtures planted for livestock grazing or the production of seed or hay crops, typically on a perennial cycle. Pasture/hay vegetation accounts for greater than 20% of total vegetation.'
nlcd_category_descriptions[82] = 'areas used for the production of annual crops, such as corn, soybeans, vegetables, tobacco, and cotton, and also perennial woody crops such as orchards and vineyards. Crop vegetation accounts for greater than 20% of total vegetation. This class also includes all land being actively tilled.'
nlcd_category_descriptions[90] = 'areas where forest or shrubland vegetation accounts for greater than 20% of vegetative cover and the soil or substrate is periodically saturated with or covered with water.'
nlcd_category_descriptions[95] = 'Areas where perennial herbaceous vegetation accounts for greater than 80% of vegetative cover and the soil or substrate is periodically saturated with or covered with water.'

e = 2.71828182845904523536028747135266249775724709369995
pi = 3.14159265358979323846264338327950288419716939937510

