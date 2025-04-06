# coding=utf-8

import os, sys, time
import logging
import traceback
from collections import OrderedDict
import hazelbean as hb
# from hazelbean.globals import *
import inspect

#First check for config file specific to this computer
def list_mounted_drive_paths():
    # Iterate through all possible drives to identify which exist.
    drives_to_analyze = list('abcdefghijklmnopqrstuvwxyz')
    drive_paths = []
    for drive in drives_to_analyze:
        drive_path = drive + ':/'
        if os.path.exists(drive_path):
            drive_paths.append(drive_path)

    return drive_paths

user_path = os.path.expanduser('~')
default_hazelbean_config_uri = os.path.join(user_path, 'Documents\\hazelbean\\config.txt')
local_hazelbean_config_uri = os.path.join(user_path, 'Documents\\hazelbean\\config.txt')
mounted_drives = list_mounted_drive_paths()
# PRIMARY_DRIVE = mounted_drives[0]
# EXTERNAL_BULK_DATA_DRIVE = mounted_drives[0]
if os.path.exists(default_hazelbean_config_uri):
    with open(default_hazelbean_config_uri) as f:
        for line in f:
            if '=' in line:
                line_split = line.split('=')
                if line_split[0] == 'primary_drive_letter':
                    PRIMARY_DRIVE_LETTER = line_split[1][0]
                    PRIMARY_DRIVE = PRIMARY_DRIVE_LETTER + ':/'
                if line_split[0] == 'external_bulk_data_drive':
                    EXTERNAL_BULK_DATA_DRIVE_LETTER = line_split[1][0]
                    EXTERNAL_BULK_DATA_DRIVE = EXTERNAL_BULK_DATA_DRIVE_LETTER + ':/'
                if line_split[0] == 'hazelbean_working_directory':
                    HAZELBEAN_WORKING_DIRECTORY = line_split[1].split('\n')[0]
                if line_split[0] == 'configured_for_cython_compilation':
                    CONFIGURED_FOR_CYTHON_COMPILATION = float(line_split[1])
else:
    mounted_drives = list_mounted_drive_paths()
    if len(mounted_drives) > 0:
        PRIMARY_DRIVE_LETTER = mounted_drives[0][0]
        if len(mounted_drives) > 1:
            EXTERNAL_BULK_DATA_DRIVE_LETTER = mounted_drives[1][0]
        else:
            EXTERNAL_BULK_DATA_DRIVE_LETTER = 'd'
    else:
        PRIMARY_DRIVE_LETTER = 'c'
        EXTERNAL_BULK_DATA_DRIVE_LETTER = 'd'

    PRIMARY_DRIVE = PRIMARY_DRIVE_LETTER + ':/'

    EXTERNAL_BULK_DATA_DRIVE = EXTERNAL_BULK_DATA_DRIVE_LETTER + ':/'
    HAZELBEAN_WORKING_DIRECTORY = PRIMARY_DRIVE + 'Files/Research/hazelbean/hazelbean_dev/hazelbean'
    CONFIGURED_FOR_CYTHON_COMPILATION = 1.0
    w = 'primary_drive_letter=' + PRIMARY_DRIVE_LETTER + '\n' + \
        'external_bulk_data_drive=' + EXTERNAL_BULK_DATA_DRIVE_LETTER + '\n' + \
        'hazelbean_working_directory=' + HAZELBEAN_WORKING_DIRECTORY + '\n' + \
        'configured_for_cython_compilation=' + str(CONFIGURED_FOR_CYTHON_COMPILATION)
    try:
        os.makedirs(os.path.split(default_hazelbean_config_uri)[0])

    except:
        pass

    with open(default_hazelbean_config_uri, 'w', encoding='latin1') as f:
        f.write(w)


# HAZELBEAN SETUP GLOBALS
TEMPORARY_DIR = os.path.join(PRIMARY_DRIVE, 'hazelbean_temp')
BASE_DATA_DIR = os.path.join(PRIMARY_DRIVE, 'files', 'research', 'base_data')
SEALS_BASE_DATA_DIR = os.path.join(PRIMARY_DRIVE, 'files', 'research', 'cge', 'seals', 'base_data')
GTAP_INVEST_BASE_DATA_DIR = os.path.join(PRIMARY_DRIVE, 'files', 'research', 'cge', 'gtap_invest', 'base_data')
BULK_DATA_DIR = os.path.join(PRIMARY_DRIVE, 'bulk_data')
EXTERNAL_BULK_DATA_DIR = os.path.join(EXTERNAL_BULK_DATA_DRIVE, 'bulk_data')
# HAZELBEAN_WORKING_DIRECTORY = 'c:\\OneDrive\\Projects\\hazelbean\\hazelbean'  # TODOO Make this based on config file?
# HAZELBEAN_WORKING_DIRECTORY = os.path.join(PRIMARY_DRIVE, 'OneDrive\\Projects\\hazelbean\\hazelbean')  # TODOO Make this based on config file?
TEST_DATA_DIR = os.path.join(HAZELBEAN_WORKING_DIRECTORY, '../tests/data')
PROJECTS_DIR = os.path.join(PRIMARY_DRIVE, 'OneDrive\\Projects')


class CustomLogger(logging.LoggerAdapter):
    def __init__(self, logger, *args, **kwargs):
        logging.LoggerAdapter.__init__(self, logger, *args, **kwargs)
        self.L = logger
        self.DEBUG_DEEPER_1_NUM = 9
        logging.addLevelName(self.DEBUG_DEEPER_1_NUM, "DEBUG_DEEPER_1")

    def process(self, msg, kwargs):
        return msg, kwargs

    def debug_deeper_1(self, message, *args, **kws):
        # Yes, logger takes its '*args' as 'args'.
        if self.isEnabledFor(self.DEBUG_DEEPER_1_NUM):
            self._log(self.DEBUG_DEEPER_1_NUM, message, args, **kws)

    def debug(self, msg, *args, **kwargs):
        for i in args:
            msg += ', ' + str(i)
        msg, kwargs = self.process(msg, kwargs)
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        msg = str(msg)
        for i in args:
            msg += ', ' + str(i)
        args = []
        msg, kwargs = self.process(msg, kwargs)
        self.logger.info(msg, *args, **kwargs)

    def print(self, msg, *args, **kwargs):
        # Hacky piece of code to report both the names and the values of variables passed to info.
        frame = inspect.currentframe()
        frame = inspect.getouterframes(frame)[1]
        string = inspect.getframeinfo(frame[0]).code_context[0].strip()
        names = string[string.find('(') + 1:-1].split(',')
        names = [i.replace(' ', '') for i in names]

        if type(msg) is not str:
            msg = '\n' + names[0] + ':\t' + str(msg)
        else:
            msg = '\n' + msg
        for c, i in enumerate(args):
            if type(i) is not str:
                msg += '\n' + str(names[c + 1]) + ':\t' + str(i)
            else:
                msg += '\n' + str(i)

        msg = msg.expandtabs(30)

        args = []
        msg, kwargs = self.process(msg, kwargs)

        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        for i in args:
            msg += ', ' + str(i)
        msg, kwargs = self.process(msg, kwargs)
        stack_list = traceback.format_stack()

        key_file_root = hb.file_root(sys.argv[0])

        key_stack_elements = ''
        rest_of_stack = ''
        for i in range(len(stack_list)):
            if key_file_root in stack_list[i]:
                key_stack_elements += stack_list[i].split(', in ')[0]
            rest_of_stack += ' ' + str(stack_list[i].split(', in ')[0])

        if key_stack_elements:
            msg = str(msg) + ' ' + key_stack_elements + '. Rest of stack trace: '+ rest_of_stack
        else:
            msg = str(msg) + ' Stack trace: ' + rest_of_stack
        msg = 'WARNING ' + msg
        self.logger.warning(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        for i in args:
            msg += ', ' + str(i)
        msg, kwargs = self.process(msg, kwargs)
        stack_list = traceback.format_stack()
        warning_string = ''
        # stack_list.reverse()
        for i in range(len(stack_list)):
            warning_string += ' ' + stack_list[i].split(', in ')[0] + '\n'
        msg = str(msg) + ' Stacktrace:\n' + warning_string
        msg = 'CRITICAL ' + msg
        self.logger.critical(msg, *args, **kwargs)

    def set_log_file_uri(self, uri):
        hdlr = logging.FileHandler(uri)
        self.logger.addHandler(hdlr)

CLEAN_FORMAT = "%(message)s"
LONG_FORMAT = "%(message)s              --- %(asctime)s --- %(name)s %(levelname)s"  
FORMAT = "%(message)s"
# FORMAT = "%(message)s"
logging.basicConfig(format=FORMAT)

LOGGING_LEVEL = logging.INFO

L = logging.getLogger('hazelbean')

L.setLevel(LOGGING_LEVEL)
L.addHandler(logging.NullHandler())  # silence logging by default

L = CustomLogger(L, {'msg': 'Custom message: '})

logging_levels = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'critical': logging.CRITICAL,
}

##Deactvated logging to file.
# handler = logging.StreamHandler()
# handler.setLevel(logging.DEBUG)#
# formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# handler.setFormatter(formatter)
# L.addHandler(handler)
# logging.Logger.debug_deeper_1 = debug_deeper_1

def get_logger(logger_name=None, logging_level='info', format='full'):
    """ STATUS: Decided that I need to write a custom ground-up logger for HB and ProjectFlow, perhaps including cython
    Used to get a custom logger specific to a file other than just susing the config defined one."""
    if not logger_name:
        try:
            # Get the basename from the name of the current file
            logger_name = os.path.basename(inspect.getfile(inspect.currentframe().f_back))
            # logger_name = os.path.basename(main.__file__)
        except:
            logger_name = 'unnamed_logger'
    L = logging.getLogger(logger_name)
    L.setLevel(logging_levels[logging_level])
    # CL = CustomLogger(L, {'msg': 'Custom message: '})
    # FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    FORMAT = "%(message)s"
    formatter = logging.Formatter(FORMAT)
    # formatter = logging.Formatter("%(message)s")
    
    for handler in L.handlers:
        L.removeHandler(handler)

    # handler = logging.StreamHandler()
    # handler.setFormatter(formatter)
    # L.addHandler(handler)
    return L

def critical(self, msg, *args, **kwargs):
    """
    Delegate a debug call to the underlying logger, after adding
    contextual information from this adapter instance.
    """
    msg, kwargs = self.process_critical_logger(msg, kwargs)
    L.critical(msg, *args, **kwargs)

if not os.path.exists(TEMPORARY_DIR):
    try:
        os.makedirs(TEMPORARY_DIR)
    except:
        raise Exception('Could not create temp file at ' + TEMPORARY_DIR + '. Perhaps you do not have permission? Try setting hazelbean/config.TEMPORARY_DIR to something in your user folder.')

uris_to_delete_at_exit = []
plots_to_display_at_exit = []


def general_callback(df_complete, psz_message, p_progress_arg):
    """The argument names come from the GDAL API for callbacks."""
    try:
        current_time = time.time()
        if ((current_time - general_callback.last_time) > 5.0 or
                (df_complete == 1.0 and general_callback.total_time >= 5.0)):
            print (
                "ReprojectImage %.1f%% complete %s, psz_message %s",
                df_complete * 100, p_progress_arg[0], psz_message)
            general_callback.last_time = current_time
            general_callback.total_time += current_time
    except AttributeError:
        general_callback.last_time = time.time()
        general_callback.total_time = 0.0

def delete_path_at_exit(path):
    if not os.path.exists(path):
        raise NameError('Cannot delete path ' + path + ' that does not exist.')
    if path in uris_to_delete_at_exit:
        L.warning('Attempted to add ' + path + ' to uris_to_delete_at_exit but it was already in there.')
        return
    else:
        uris_to_delete_at_exit.append(path)





def get_global_geotransform_from_resolution(input_resolution):
    return (-180.0, input_resolution, 0.0, 90.0, 0.0, -input_resolution)

common_bounding_boxes_in_degrees = {
    'global': [-180., -90., 180., 90.]
}

common_projection_wkts = {
    'wgs84': "GEOGCS[\"WGS 84\", DATUM[\"WGS_1984\", SPHEROID[\"WGS 84\", 6378137, 298.257223563, AUTHORITY[\"EPSG\", \"7030\"]], AUTHORITY[\"EPSG\", \"6326\"]],PRIMEM[\"Greenwich\", 0], UNIT[\"degree\", 0.0174532925199433], AUTHORITY[\"EPSG\", \"4326\"]]"
}


# TODOO Put this in base_data repo instead
luh_data_dir = os.path.join(BASE_DATA_DIR, 'luh2', 'raw_data')
# Corresponds to a directory containing the latest LUH data download of states.nc and management.nc from maryland website
luh_scenario_names = [
    "rcp26_ssp1",
    "rcp34_ssp4",
    "rcp45_ssp2",
    "rcp60_ssp4",
    "rcp70_ssp3",
    "rcp85_ssp5",
    # "historical",
]

luh_scenario_states_paths = OrderedDict()
luh_scenario_states_paths['rcp26_ssp1'] = os.path.join(luh_data_dir, 'rcp26_ssp1', r"multiple-states_input4MIPs_landState_ScenarioMIP_UofMD-IMAGE-ssp126-2-1-f_gn_2015-2100.nc")
luh_scenario_states_paths['rcp34_ssp4'] = os.path.join(luh_data_dir, 'rcp34_ssp4', r"multiple-states_input4MIPs_landState_ScenarioMIP_UofMD-GCAM-ssp434-2-1-f_gn_2015-2100.nc")
luh_scenario_states_paths['rcp45_ssp2'] = os.path.join(luh_data_dir, 'rcp45_ssp2', r"multiple-states_input4MIPs_landState_ScenarioMIP_UofMD-MESSAGE-ssp245-2-1-f_gn_2015-2100.nc")
luh_scenario_states_paths['rcp60_ssp4'] = os.path.join(luh_data_dir, 'rcp60_ssp4', r"multiple-states_input4MIPs_landState_ScenarioMIP_UofMD-GCAM-ssp460-2-1-f_gn_2015-2100.nc")
luh_scenario_states_paths['rcp70_ssp3'] = os.path.join(luh_data_dir, 'rcp70_ssp3', r"multiple-states_input4MIPs_landState_ScenarioMIP_UofMD-AIM-ssp370-2-1-f_gn_2015-2100.nc")
luh_scenario_states_paths['rcp85_ssp5'] = os.path.join(luh_data_dir, 'rcp85_ssp5', r"multiple-states_input4MIPs_landState_ScenarioMIP_UofMD-MAGPIE-ssp585-2-1-f_gn_2015-2100.nc")
luh_scenario_states_paths['historical'] = os.path.join(luh_data_dir, 'historical', r"states.nc")

luh_scenario_management_paths = OrderedDict()
luh_scenario_management_paths['rcp26_ssp1'] = os.path.join(luh_data_dir, 'rcp26_ssp1', r"multiple-management_input4MIPs_landState_ScenarioMIP_UofMD-IMAGE-ssp126-2-1-f_gn_2015-2100.nc")
luh_scenario_management_paths['rcp34_ssp4'] = os.path.join(luh_data_dir, 'rcp34_ssp4', r"multiple-management_input4MIPs_landState_ScenarioMIP_UofMD-GCAM-ssp434-2-1-f_gn_2015-2100.nc")
luh_scenario_management_paths['rcp45_ssp2'] = os.path.join(luh_data_dir, 'rcp45_ssp2', r"multiple-management_input4MIPs_landState_ScenarioMIP_UofMD-MESSAGE-ssp245-2-1-f_gn_2015-2100.nc")
luh_scenario_management_paths['rcp60_ssp4'] = os.path.join(luh_data_dir, 'rcp60_ssp4', r"multiple-management_input4MIPs_landState_ScenarioMIP_UofMD-GCAM-ssp460-2-1-f_gn_2015-2100.nc")
luh_scenario_management_paths['rcp70_ssp3'] = os.path.join(luh_data_dir, 'rcp70_ssp3', r"multiple-management_input4MIPs_landState_ScenarioMIP_UofMD-AIM-ssp370-2-1-f_gn_2015-2100.nc")
luh_scenario_management_paths['rcp85_ssp5'] = os.path.join(luh_data_dir, 'rcp85_ssp5', r"multiple-management_input4MIPs_landState_ScenarioMIP_UofMD-MAGPIE-ssp585-2-1-f_gn_2015-2100.nc")
luh_scenario_management_paths['historical'] = os.path.join(luh_data_dir, 'historical', r"management.nc")

luh_state_names = [
    'primf',
    'primn',
    'secdf',
    'secdn',
    'urban',
    'c3ann',
    'c4ann',
    'c3per',
    'c4per',
    'c3nfx',
    'pastr',
    'range',
    'secmb',
    'secma',
]

luh_management_names = [
    'fertl_c3ann',
    'irrig_c3ann',
    'crpbf_c3ann',
    'fertl_c4ann',
    'irrig_c4ann',
    'crpbf_c4ann',
    'fertl_c3per',
    'irrig_c3per',
    'crpbf_c3per',
    'fertl_c4per',
    'irrig_c4per',
    'crpbf_c4per',
    'fertl_c3nfx',
    'irrig_c3nfx',
    'crpbf_c3nfx',
    'fharv_c3per',
    'fharv_c4per',
    'flood',
    'rndwd',
    'fulwd',
    'combf',
    'crpbf_total',
]



worldclim_bioclimatic_variable_names = OrderedDict()
worldclim_bioclimatic_variable_names[1] = 'Annual Mean Temperature'
worldclim_bioclimatic_variable_names[2] = 'Mean Diurnal Range (Mean of monthly (max temp - min temp))'
worldclim_bioclimatic_variable_names[3] = 'Isothermality (BIO2/BIO7) (* 100)'
worldclim_bioclimatic_variable_names[4] = 'Temperature Seasonality (standard deviation *100)'
worldclim_bioclimatic_variable_names[5] = 'Max Temperature of Warmest Month'
worldclim_bioclimatic_variable_names[6] = 'Min Temperature of Coldest Month'
worldclim_bioclimatic_variable_names[7] = 'Temperature Annual Range (BIO5-BIO6)'
worldclim_bioclimatic_variable_names[8] = 'Mean Temperature of Wettest Quarter'
worldclim_bioclimatic_variable_names[9] = 'Mean Temperature of Driest Quarter'
worldclim_bioclimatic_variable_names[10] = 'Mean Temperature of Warmest Quarter'
worldclim_bioclimatic_variable_names[11] = 'Mean Temperature of Coldest Quarter'
worldclim_bioclimatic_variable_names[12] = 'Annual Precipitation'
worldclim_bioclimatic_variable_names[13] = 'Precipitation of Wettest Month'
worldclim_bioclimatic_variable_names[14] = 'Precipitation of Driest Month'
worldclim_bioclimatic_variable_names[15] = 'Precipitation Seasonality (Coefficient of Variation)'
worldclim_bioclimatic_variable_names[16] = 'Precipitation of Wettest Quarter'
worldclim_bioclimatic_variable_names[17] = 'Precipitation of Driest Quarter'
worldclim_bioclimatic_variable_names[18] = 'Precipitation of Warmest Quarter'
worldclim_bioclimatic_variable_names[19] = 'Precipitation of Coldest Quarter'

countries_full_column_names = ['id', 'iso3', 'nev_name', 'fao_name', 'fao_id_c', 'gtap140', 'continent', 'region_un', 'region_wb', 'geom_index', 'abbrev', 'adm0_a3', 'adm0_a3_is', 'adm0_a3_un', 'adm0_a3_us', 'adm0_a3_wb', 'admin', 'brk_a3', 'brk_group', 'brk_name', 'country', 'disp_name', 'economy', 'fao_id', 'fao_reg', 'fips_10_', 'formal_en', 'formal_fr', 'gau', 'gdp_md_est', 'gdp_year', 'geounit', 'gu_a3', 'income_grp', 'iso', 'iso2_cull', 'iso3_cull', 'iso_3digit', 'iso_a2', 'iso_a3', 'iso_a3_eh', 'iso_n3', 'lastcensus', 'name', 'name_alt', 'name_ar', 'name_bn', 'name_cap', 'name_ciawf', 'name_de', 'name_el', 'name_en', 'name_es', 'name_fr', 'name_hi', 'name_hu', 'name_id', 'name_it', 'name_ja', 'name_ko', 'name_long', 'name_nl', 'name_pl', 'name_pt', 'name_ru', 'name_sort', 'name_sv', 'name_tr', 'name_vi', 'name_zh', 'ne_id', 'nev_lname', 'nev_sname', 'note_adm0', 'note_brk', 'official', 'olympic', 'pop_est', 'pop_rank', 'pop_year', 'postal', 'sov_a3', 'sovereignt', 'su_a3',
                               'subregion', 'subunit', 'type', 'un_a3', 'un_iso_n', 'un_vehicle', 'undp', 'uni', 'wb_a2', 'wb_a3', 'wiki1', 'wikidataid', 'wikipedia', 'woe_id', 'woe_id_eh', 'woe_note']

possible_shapefile_extensions = ['.shp', '.shx', '.dbf', '.prj', '.sbn', '.sbx', '.fbn', '.fbx', '.ain', '.aih', '.ixs', '.mxs', '.atx', '.shp.xml', '.cpg', '.qix']
common_gdal_readable_file_extensions = ['.tif', '.bil', '.adf', '.asc', '.hdf', '.nc',]
# gdal_readable_formats = ['AAIGrid', 'ACE2', 'ADRG', 'AIG', 'ARG', 'BLX', 'BAG', 'BMP', 'BSB', 'BT', 'CPG', 'CTG', 'DIMAP', 'DIPEx', 'DODS', 'DOQ1', 'DOQ2', 'DTED', 'E00GRID', 'ECRGTOC', 'ECW', 'EHdr', 'EIR', 'ELAS', 'ENVI', 'ERS', 'FAST', 'GPKG', 'GEORASTER', 'GRIB', 'GMT', 'GRASS', 'GRASSASCIIGrid', 'GSAG', 'GSBG', 'GS7BG', 'GTA', 'GTiff', 'GTX', 'GXF', 'HDF4', 'HDF5', 'HF2', 'HFA', 'IDA', 'ILWIS', 'INGR', 'IRIS', 'ISIS2', 'ISIS3', 'JDEM', 'JPEG', 'JPEG2000', 'JP2ECW', 'JP2KAK', 'JP2MrSID', 'JP2OpenJPEG', 'JPIPKAK', 'KEA', 'KMLSUPEROVERLAY', 'L1B', 'LAN', 'LCP', 'Leveller', 'LOSLAS', 'MBTiles', 'MAP', 'MEM', 'MFF', 'MFF2 (HKV)', 'MG4Lidar', 'MrSID', 'MSG', 'MSGN', 'NDF', 'NGSGEOID', 'NITF', 'netCDF', 'NTv2', 'NWT_GRC', 'NWT_GRD', 'OGDI', 'OZI', 'PCIDSK', 'PCRaster', 'PDF', 'PDS', 'PLMosaic', 'PostGISRaster', 'Rasterlite', 'RIK', 'RMF', 'ROI_PAC', 'RPFTOC', 'RS2', 'RST', 'SAGA', 'SAR_CEOS', 'SDE', 'SDTS', 'SGI', 'SNODAS', 'SRP', 'SRTMHGT', 'USGSDEM', 'VICAR', 'VRT', 'WCS', 'WMS', 'XYZ', 'ZMap',]