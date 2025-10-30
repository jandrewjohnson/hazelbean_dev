# NOTE Test is manual because uses CWD directly and inspeciton

import os, sys, time

import numpy as np
import hazelbean as hb
from hazelbean import netcdf
from hazelbean.netcdf import *

paths = [
    # luh2/raw_data/historical/states.nc
    'luh2/raw_data/RCP26_SSP1/multiple-states_input4MIPs_landState_ScenarioMIP_UofMD-IMAGE-ssp126-2-1-f_gn_2015-2100.nc',
    # luh2/raw_data/RCP34_SSP4/multiple-states_input4MIPs_landState_ScenarioMIP_UofMD-GCAM-ssp434-2-1-f_gn_2015-2100.nc
    # btc/AIM/BendingTheCurveFT-LCproj-AIM-RCPref_SSP1p_BIOD-R2_wabn_15Nov2019_FinalMask.nc
    # btc/GLOBIOM/BendingTheCurveFT-LCproj-GLOBIOM-RCPref_SSP1p_BIOD-R2_wabn_15Nov2019_FinalMask.nc
    # btc/AIM/BendingTheCurveFT-LCproj-AIM-RCPref_SSP1p_BIOD-R2_wabn_15Nov2019_FinalMask.nc
    # btc/AIM/BendingTheCurveFT-LCproj-AIM-RCPref_SSP1p_BIOD-R2_wabn_15Nov2019_FinalMask.nc
    'btc/GLOBIOM/BendingTheCurveFT-LCproj-GLOBIOM-RCPref_SSP1p_BIOD-R2_wabn_15Nov2019_FinalMask.nc',
    # btc/GLOBIOM/BendingTheCurveFT-LCproj-GLOBIOM-RCPref_SSP2_NOBIOD-R2_wabn_15Nov2019_FinalMask.nc
    'magpie/SSP2_NPI_base_LPJmL5/cell.land_0.5_share_to_seals_SSP2_NPI_base_LPJmL5.nc',
    # magpie/SSP2_NPI_base_LPJmL5/cell.land_0.5_share_to_seals_SSP2_NPI_base_LPJmL5.nc
    # magpie/SSP2_BiodivPol+ClimPol+NCPpol_LPJmL5/cell.land_0.5_share_to_seals_SSP2_BiodivPol+ClimPol+NCPpol_LPJmL5.nc
]

base_data_dir = 'G:/My Drive/Files/base_data'


do_test = 1
if do_test:
    path = paths[0]
    input_nc_path = os.path.join(base_data_dir, path)
    describe_netcdf(input_nc_path)

do_test = 1
if do_test:
    description_dict = get_netcdf_description_dict(input_nc_path)
    print('Generated the following description dict:')
    hb.print_dict(description_dict)

    possible_extract_dims, possible_vars = get_netcdf_writable_vars_from_description_dict(description_dict)
   
    print('Possible extract dims:')
    print(possible_extract_dims)

    print('Possible vars:')
    print(possible_vars)

do_test = 1
if do_test:
    output_dir = 'c:/tempcomp/extract'
    hb.create_directories(output_dir)


do_test = 1
if do_test:   
    
    output_dir = 'c:/tempcomp/btc'
    hb.create_directories(output_dir)

    adjustment_dict = {
        'time': '+2015',  # or *5+14 eg
    }


    filter_dict = {
        'time': [2015, 2050],
        'variables': ['range', 'pastr']

    }

    extract_global_netcdf(
            input_nc_path, 
            output_dir, 
            adjustment_dict=adjustment_dict,
            filter_dict=filter_dict,
            only_report_names=False,
            skip_if_exists=False,
            verbose=False
        )


do_test = 1
if do_test:
    base_data_dir = 'G:/My Drive/Files/base_data'
    path = paths[1]
    input_nc_path = os.path.join(base_data_dir, path)    


    output_dir = 'c:/tempcomp/luh2'

    hb.create_directories(output_dir)
    
    adjustment_dict = {
        # 'time': '+10',  # or *5+14 eg
    }

    filter_dict = {
        'lc_class': [1, 2],
        'time': [2030, 2040],
    }

    extract_global_netcdf(
            input_nc_path, 
            output_dir, 
            adjustment_dict=adjustment_dict,
            filter_dict=filter_dict,
            only_report_names=False,
            skip_if_exists=False,
            verbose=False
        )

do_test = 1
if do_test:

    base_data_dir = 'G:/My Drive/Files/base_data'
    path = paths[2]
    input_nc_path = os.path.join(base_data_dir, path)
    output_dir = 'c:/tempcomp/magpie'

    hb.create_directories(output_dir)

    adjustment_dict = {
        # 'time': '+2015',  # or *5+14 eg
    }

    filter_dict = {
        'time': [2050],
        'variables': ['forest', 'pastr']

    }

    extract_global_netcdf(
            input_nc_path, 
            output_dir, 
            adjustment_dict=adjustment_dict,
            filter_dict=filter_dict,
            only_report_names=False,
            skip_if_exists=False,
            verbose=False
        )

