import os
import netCDF4
import netCDF4 as nc
import hazelbean as hb
import time
import numpy as np
import pandas as pd
from hazelbean import config as hb_config

L = hb_config.get_logger('netcdf')


def describe_netcdf(input_nc_path, just_metadata=False, return_as_string=False, max_to_describe=6):
    # Describe the contents of the netcdf file at input_nc_path. Optyionally return
    # as a string.

    if return_as_string:
        return_string = '\ndescribe_netcdf: ' + input_nc_path + '\n'
    else:
        print('\ndescribe_netcdf: ' + input_nc_path)

    try:
        ds = netCDF4.Dataset(input_nc_path, 'r')
    except:
        raise NameError('Unable to load netcdf at ' + input_nc_path)

    metadata_dict = ds.__dict__
    if just_metadata:
        if return_as_string:
            return_string += str(hb.print_dict(metadata_dict, return_as_string=return_as_string))
            return return_string
        else:
            hb.print_dict(metadata_dict)
            return
        
    else:
        full_dict = get_netcdf_description_dict(input_nc_path, max_to_describe)
        if return_as_string:
            return_string += str(hb.print_dict(full_dict, return_as_string=return_as_string))
            return return_string
        else:
            hb.print_dict(full_dict)
            return
            

def get_netcdf_description_dict(input_nc_path, max_dimension_load_size=2000):
    # Get a nested dictionary of the contents of the netcdf file at input_nc_path.
    # Useful for iterating through the content. Different than just
    # describing it because it gives you a lookup list of the dim values
    # and dim keys.

    try:
        ds = netCDF4.Dataset(input_nc_path, 'r')
    except:
        raise NameError('Unable to load netcdf at ' + input_nc_path)

    contents_dict = {}
    contents_dict['metadata'] = ds.__dict__
    attributes_to_skip = []
    
    dimensions_dict = dict(zip(ds.dimensions.keys(), ds.dimensions.values()))
    contents_dict['dims'] = {}
    for k, v in dimensions_dict.items():
        contents_dict['dims'][k] = {}
        for attr in hb.get_attributes_of_object_as_list_of_strings(v):
            if not attr.startswith('_') and attr not in attributes_to_skip:
                contents_dict['dims'][k][attr] = getattr(v, attr)

        if k in ds.variables.keys():
            dim_as_variable = ds.variables[k]            
            for attr in hb.get_attributes_of_object_as_list_of_strings(dim_as_variable):
                if not attr.startswith('_') and attr not in attributes_to_skip:
                    contents_dict['dims'][k][attr] = getattr(dim_as_variable, attr)

            if v.size < max_dimension_load_size:
                contents_dict['dims'][k]['values'] = dim_as_variable[:]
                contents_dict['dims'][k]['index_value_lookup'] = dict(zip(range(len(v)), contents_dict['dims'][k]['values']))
            else:
                contents_dict['dims'][k]['values'] = dim_as_variable[:max_dimension_load_size]
                # contents_dict['dims'][k]['index_value_lookup'] = 'Not loaded due to size'

    vars_dict = dict(zip(ds.variables.keys(), ds.variables.values()))
    
    contents_dict['vars'] = {}
    for k, v in vars_dict.items():
        if k not in contents_dict['dims']:
            contents_dict['vars'][k] = {}
            for attr in hb.get_attributes_of_object_as_list_of_strings(v):
                if not attr.startswith('_') and attr not in attributes_to_skip:
                    contents_dict['vars'][k][attr] = getattr(v, attr)

    return contents_dict



def get_netcdf_writable_vars_from_description_dict(description_dict):
    # Get a list of the variables that can be written from a netcdf based
    # on a description dict that has been generated.

    possible_extract_dims = {}
    possible_vars = {}
    canonical_dims = ['lat', 'lon', 'x', 'y', 'z']

    suffix_vars = {}
    
    for dim_name, dim_dict in description_dict['dims'].items():
        if dim_name not in canonical_dims:
            if 'values' in dim_dict:
                possible_extract_dims[dim_name] = dim_dict['values']
        
    for var_name, var_dict in description_dict['vars'].items():
        if var_name not in canonical_dims and var_name not in description_dict['dims']:
            possible_vars[var_name] = var_dict['dimensions']

    
    return possible_extract_dims, possible_vars
def extract_global_netcdf_to_geotiffs(input_nc_path,
                                     output_dir,
                                     vars_to_extract=None,
                                     time_indices_to_extract=None,
                                     ndv=None,
                                     output_files_prefix=None,
                                     flip_array_vertically=False,
                                     verbose=False):
    
    # Old version kept for reference. Use others.

    if output_files_prefix is None:
        output_files_prefix = hb.file_root(input_nc_path)

    if not hb.path_exists(input_nc_path):
        raise FileNotFoundError(input_nc_path)

    ds = netCDF4.Dataset(input_nc_path, 'r')
    L.debug('Loaded nc file ', input_nc_path)

    ds_dict = ds.__dict__

    if verbose:
        L.info('  NC metadata dict:', ds_dict)

    dim_names = ds.dimensions.keys()
    dims_dict = {}

    for dim_name in dim_names:
        dims_dict[ds.dimensions[dim_name].name] = ds.dimensions[dim_name].size

    if verbose:
        L.info('  NC dimensions', dims_dict)

    var_names = ds.variables.keys()
    vars_dict = {}

    time_labels = np.asarray(ds.variables['time'])
    if verbose:
        L.info('time dimension had labels', time_labels)

    if time_indices_to_extract is not None:
        if type(time_indices_to_extract) is not list:
            time_indices_to_extract = [time_indices_to_extract]
    elif time_indices_to_extract == 'all':
        time_indices_to_extract = range(len(ds.variables['time']))
    else:
        # If no time indices are given, extract just the first one'
        time_indices_to_extract = [0]


    # Dim names are typically [lat, lon, time]
    dim_names = ds.dimensions.keys()

    # # Get the dims data to assess the potentially asymetric sizes of different dimensions
    # dims_data = {}
    # for dim_name in dim_names:
    #     # The dims data is treated like any other variable (though it would be different size than the actual data)
    #     dims_data[dim_name] = ds.variables[dim_name][:]

    # Derive geotransform based on calculated resolution from size of longitude index.
    res = (360.0) / len(ds.variables['lon'])
    geotransform = [-180.0, res, 0.0, 90.0, 0.0, -1 * res]
    # projection = 'wgs84'
    projection = 4326
    # srs = osr.SpatialReference()
    # srs.ImportFromEPSG(4326)
    # projection = srs.ExportToWkt()

    for var_name, var in ds.variables.items():

        if vars_to_extract is not None:
            if var_name not in vars_to_extract:
                break

        for time_index in time_indices_to_extract:

            # Skip data that is just the data of the dims
            if var_name not in dim_names:
                if verbose:
                    L.info('Processing ' + var_name + ' with metadata ' + str([str(k) + ': ' +str(v) for k, v in var.__dict__.items()]))

                # Following stackoverflow, I originally used the below notation, but this was 1000x slower than the following one which uses only numpy indices.
                # array = var[:][dim_selection_indices[0]]
                array = np.array(var[time_index])

                if flip_array_vertically:
                    array = np.flipud(array)

                if '_FillValue' in var.__dict__:
                    fill_value = var.__dict__['_FillValue']
                if 'missing_value' in var.__dict__:
                    fill_value = var.__dict__['missing_value']

                if ndv is None:
                    ndv = -9999

                array = np.where(array == fill_value, ndv, array)

                # if output_geotiff_paths is None:
                #     output_geotiff_path = os.path.join(output_dir, output_files_prefix + '_' + var_name + '_' + str(int(time_labels[time_index])) + '.tif')
                # else:
                #     output_geotiff_path [i]
                #
                output_geotiff_path = os.path.join(output_dir, output_files_prefix + '_' + var_name + '_' + str(int(time_labels[time_index])) + '.tif')

                if verbose:
                    L.info('Saving array to ', output_geotiff_path)
                hb.save_array_as_geotiff(array, output_geotiff_path, ndv=ndv, data_type=7, compress=True, n_cols=array.shape[1], n_rows=array.shape[0],
                                         geotransform_override=geotransform, projection_override=projection)


def extract_global_netcdf(
    input_nc_path, 
    output_dir, 
    adjustment_dict={},
    filter_dict={},
    ndv=None,
    only_report_names=False,
    skip_if_exists=False,
    verbose=False,    
    ):
    # Full-featured extraction of a global netcdf file. By default extracts everything.
    # Adjustment_dict can adjust a numeric variable by a constant or a multiplier. 
    # This is useful for when time was put in in a strange way.
    # Filter dict can filter defines which variables to extract. Keys are
    # the dimension names except for the reserved word 'variables',
    # which refers to which variables to extract.
    # Examplers:
    # adjustment_dict = {
    #     'time': '+10',  # or *5+14 eg
    # }

    # filter_dict = {
    #     'lc_class': [1, 2],
    #     'time': [2030, 2040],
    # }


    try:
        ds = netCDF4.Dataset(input_nc_path, 'r')
    except:
        raise NameError('Unable to load netcdf at ' + input_nc_path)
    L.debug('Loaded nc file ', input_nc_path)


    # Derive geotransform based on calculated resolution from size of longitude index.
    res = (360.0) / len(ds.variables['lon'])
    geotransform = [-180.0, res, 0.0, 90.0, 0.0, -1 * res]
    projection = 'wgs84'

    nc_dict = get_netcdf_description_dict(input_nc_path, 2000)

    extraction_dims, vars = get_netcdf_writable_vars_from_description_dict(nc_dict)

    if verbose:        
        L.info('Loaded nc file ', input_nc_path)

        describe_netcdf(input_nc_path)
        hb.print_dict(extraction_dims)
        hb.print_dict(vars)
    
    def walk_var_dims(var_name, filter_dict, preceding_dirs=[], dim_name_counter=0, packed_dims=[], output_dir=None, ndv=None, skip_if_exists=None):
        if verbose:
            L.info('Walking var dims for var ', var_name, ' dim_name_counter ', dim_name_counter, ' packed_dims ', packed_dims)
        current_dim_name = dim_names_for_this_var[dim_name_counter]
        
        updated_dim_names_for_this_var = nc_dict['vars'][var_name]['dimensions']
        if dim_name_counter <  len(dim_names_for_this_var) - 3:
            
            dim_values_for_this_var = nc_dict['dims'][current_dim_name]['values']
            for dim_value_counter, dim_value in enumerate(dim_values_for_this_var):
                preceding_dirs[dim_name_counter] = current_dim_name + '_' +str(int(dim_value))
                adjusted_dim_value = dim_value
                # preceding_dirs.append(str(int(dim_value)))
                packed_dims[dim_name_counter] = dim_value_counter
                
                dim_name_counter += 1
                
                current_filter_list = [current_dim_name + '_' + str(i) for i in filter_dict[current_dim_name]]

                if current_dim_name in adjustment_dict:
                    if not pd.isna(adjustment_dict[current_dim_name]):
                        operations = adjustment_dict[current_dim_name].split(' ')

                        # Iterate through the operations to apply to the dim values
                        for op in operations:
                            if op.startswith('+'):
                                adjusted_dim_value += int(op[1:])
                            elif op.startswith('-'):
                                adjusted_dim_value -= int(op[1:])
                            elif op.startswith('*'):
                                adjusted_dim_value *= int(op[1:])
                            elif op.startswith('/'):
                                adjusted_dim_value /= int(op[1:])                  

                        # Make a copy of the dim values to modify
                        dim_as_var = ds.variables[current_dim_name]
                        dim_values_present = list(np.array(dim_as_var[:]))
                        current_adjusted_dim_values_to_extract = dim_values_present.copy()

                        # adjusted_dim_value = dim_value
                        # Iterate through the alues present to get ready to apply the adjustment op
                        for dim_value_present_counter, dim_values in enumerate(dim_values_present):

                            # Iterate through the operations to apply to the dim values
                            for op in operations:
                                if op.startswith('+'):
                                    current_adjusted_dim_values_to_extract[dim_value_present_counter] += int(op[1:])
                                elif op.startswith('-'):
                                    current_adjusted_dim_values_to_extract[dim_value_present_counter] -= int(op[1:])
                                elif op.startswith('*'):
                                    current_adjusted_dim_values_to_extract[dim_value_present_counter] *= int(op[1:])
                                elif op.startswith('/'):
                                    current_adjusted_dim_values_to_extract[dim_value_present_counter] /= int(op[1:])
                                else:
                                    pass 

                if current_dim_name + '_' + str(int(adjusted_dim_value)) in current_filter_list:

                    walk_var_dims(var_name, filter_dict, preceding_dirs, dim_name_counter, packed_dims, output_dir=output_dir, ndv=ndv, skip_if_exists=skip_if_exists)
                else:
                    L.debug('Skipping ', current_dim_name + '_' + str(int(adjusted_dim_value)), ' because it is not in the filter list ', current_filter_list)
                    pass
                dim_name_counter -= 1


        elif dim_name_counter <  len(dim_names_for_this_var) - 2:
            dim_values_for_this_var = nc_dict['dims'][current_dim_name]['values']
            # packed_dims.append('')
            for dim_value_counter, dim_value in enumerate(dim_values_for_this_var):
                packed_dims[-1] = int(dim_value_counter)

                adjusted_dim_value = dim_value


                if current_dim_name in adjustment_dict:
                    if not pd.isna(adjustment_dict[current_dim_name]):
                        operations = adjustment_dict[current_dim_name].split(' ')

                        # Iterate through the operations to apply to the dim values
                        for op in operations:
                            if op.startswith('add'):
                                adjusted_dim_value += int(op[3:])
                            elif op.startswith('subtract'):
                                adjusted_dim_value -= int(op[8:])
                            elif op.startswith('multiply'):
                                adjusted_dim_value *= int(op[8:])
                            elif op.startswith('divide'):
                                adjusted_dim_value /= int(op[6:])              

                        # Make a copy of the dim values to modify
                        dim_as_var = ds.variables[current_dim_name]
                        dim_values_present = list(np.array(dim_as_var[:]))
                        current_adjusted_dim_values_to_extract = dim_values_present.copy()

                        # adjusted_dim_value = dim_value
                        # Iterate through the alues present to get ready to apply the adjustment op
                        for dim_value_present_counter, dim_values in enumerate(dim_values_present):

                            # Iterate through the operations to apply to the dim values
                            for op in operations:
                                if op.startswith('add'):
                                    current_adjusted_dim_values_to_extract[dim_value_present_counter] += int(op[3:])
                                elif op.startswith('subtract'):
                                    current_adjusted_dim_values_to_extract[dim_value_present_counter] -= int(op[8:])
                                elif op.startswith('multiply'):
                                    current_adjusted_dim_values_to_extract[dim_value_present_counter] *= int(op[8:])
                                elif op.startswith('divide'):
                                    current_adjusted_dim_values_to_extract[dim_value_present_counter] /= int(op[6:])
                                else:
                                    pass 

                if current_dim_name in filter_dict:

                    current_filter_list = [current_dim_name + '_' + str(i) for i in filter_dict[current_dim_name]]
                else:
                    current_filter_list = []

                final_output_dir = os.path.join(output_dir, *preceding_dirs, current_dim_name + '_' + str(int(adjusted_dim_value)) ) # LEARNING POINT, the star unpacks the list into individual arguments
                

                do_this_one = False
                output_geotiff_path = os.path.join(final_output_dir, var_name + '.tif')
                
                if len(current_filter_list) > 0:
                    if current_dim_name + '_' + str(int(adjusted_dim_value)) in current_filter_list:
                        do_this_one = True
                else:
                    do_this_one = True

                if do_this_one:

                    if only_report_names:
                        L.info('Found tif from nc to write: ', output_geotiff_path)
                    
                    if (not hb.path_exists(output_geotiff_path) or not skip_if_exists) and not only_report_names:
                        hb.create_directories(final_output_dir)
                        # # Lol so close to being good code... then I did this... oh well. I probably should have subclassed the numpy slice object but i'm lazy af today.
                        if 'variables' in filter_dict:
                            if var_name in filter_dict['variables']:
                                do_it = True
                            else:
                                do_it = False
                        else:
                            do_it = True

                        if do_it:
                            var = ds.variables[var_name]             

                            # Important optimization note: 
                            # array = np.array(var[packed_dims[0], :]) is about 100x as fast as array = np.array(var)[packed_dims[0], :]     
                            # because it more efficiently slices and odesn't have to convert the whole masked array in the nc to
                            # a numpy array.
                            if len(packed_dims) == 1:   
                                array = np.array(var[packed_dims[0], :])
                            elif len(packed_dims) == 2:
                                array = np.array(var[packed_dims[0], packed_dims[1], :]  ) 
                            elif len(packed_dims) == 3:
                                array = np.array(var[packed_dims[0], packed_dims[1], packed_dims[2] :]  ) 
                            elif len(packed_dims) == 4:
                                array = np.array(var[packed_dims[0], packed_dims[1], packed_dims[2], packed_dims[3], :])   
                            elif len(packed_dims) == 5:
                                array = np.array(var[packed_dims[0], packed_dims[1], packed_dims[2], packed_dims[3], packed_dims[4], :]   )
                            elif len(packed_dims) == 6:
                                array = np.array(var[packed_dims[0], packed_dims[1], packed_dims[2], packed_dims[3], packed_dims[4], packed_dims[5], :]  ) 
                            elif len(packed_dims) == 7:
                                array = np.array(var[packed_dims[0], packed_dims[1], packed_dims[2], packed_dims[3], packed_dims[4], packed_dims[5], packed_dims[6], :]  ) 


                            fill_value = None
                            if '_FillValue' in var.__dict__:
                                fill_value = var.__dict__['_FillValue']
                            if 'missing_value' in var.__dict__:
                                fill_value = var.__dict__['missing_value']

                            if ndv is None:
                                ndv = -9999
                            if fill_value is not None:
                                array = np.where(array == fill_value, ndv, array)


                            if verbose:
                                L.info('Writing to ', output_geotiff_path)
                            hb.save_array_as_geotiff(array, output_geotiff_path, ndv=ndv, data_type=7, compress=True, n_cols=array.shape[1], n_rows=array.shape[0],
                                                    geotransform_override=geotransform, projection_override=projection)
        else:
            L.debug('Current var is less than 3 dimensions. Skipping. Current dim name: ' + str(current_dim_name))            


    for var_name in vars:
        dim_names_for_this_var = nc_dict['vars'][var_name]['dimensions']
        preceding_dirs = [''] * (len(dim_names_for_this_var) - 2)
        
        # TODOOO: Note that i should not have put a year on the luh2 version ones (primf_2014)
        var_name
        packed_dims = [''] * (len(dim_names_for_this_var) - 2)
        walk_var_dims(var_name, filter_dict, preceding_dirs=preceding_dirs, packed_dims=packed_dims, output_dir=output_dir, ndv=ndv, skip_if_exists=skip_if_exists)


def extract_netcdf_to_geotiffs(input_nc_path, output_dir, vars_to_extract=None, var_rename_dict=None, time_indices_to_extract=None, time_rename_op=None, ndv=None, data_type=None, return_only_proposed_filenames=False, verbose=True):
    # NYI, need to incorporate changes in extract_global_netcdf_to_geotiff
    
    # Like original funciton but intended to fail gracefully and informatively so can work through the complex index structure.
    ds = netCDF4.Dataset(input_nc_path, 'r')
    L.debug('Loaded nc file ', input_nc_path)
    if verbose:
        L.info(hb.describe_netcdf(input_nc_path, return_as_string=True))

    ds_dict = ds.__dict__

    dim_names = ds.dimensions.keys()
    dims_dict = {}

    for dim_name in dim_names:
        dims_dict[ds.dimensions[dim_name].name] = ds.dimensions[dim_name].size

    vars_dict = dict(zip(ds.variables.keys(), ds.variables.values()))


    var_names = ds.variables.keys()
    vars_dict = {}

    if time_indices_to_extract is not None:
        if type(time_indices_to_extract) is not list:
            time_indices_to_extract = [time_indices_to_extract]
    elif time_indices_to_extract == 'all':
        time_indices_to_extract = range(len(ds.variables['time']))
    elif time_indices_to_extract == 'first':

        time_indices_to_extract = [0]
    else:
        # If no time indices are given, extract just the first one'

        time_indices_to_extract = list(ds.variables['time'])
        # time_indices_to_extract = range(len(ds.variables['time']))

    # Dim names are typically [lat, lon, time]
    dim_names = ds.dimensions.keys()

    # # Get the dims data to assess the potentially asymetric sizes of different dimensions
    # dims_data = {}
    # for dim_name in dim_names:
    #     # The dims data is treated like any other variable (though it would be different size than the actual data)
    #     dims_data[dim_name] = ds.variables[dim_name][:]

    # Derive geotransform based on calculated resolution from size of longitude index.
    res = (360.0) / len(ds.variables['lon'])
    geotransform = [-180.0, res, 0.0, 90.0, 0.0, -1 * res]
    projection = 'wgs84'
    proposed_filenames = []

    for var_name, var in ds.variables.items():
        if vars_to_extract is not None:
            if var_name not in vars_to_extract:
                break

        for time_index, time_value in enumerate(time_indices_to_extract):
            # Skip data that is just the data of the dims
            if var_name not in dim_names:
                L.info('Processing ' + var_name + ' with metadata ' + str([str(k) + ': ' +str(v) for k, v in var.__dict__.items()]))

                if time_rename_op is not None:
                    if isinstance(time_rename_op, str):
                        if time_rename_op[0:11] == 'days_since_':
                            days_since_year_value = int(time_rename_op.split('_')[2])
                            renamed_time_value = int(round(float(time_value) / 365.2425)) + days_since_year_value
                    else:
                        renamed_time_value = time_rename_op(time_value)

                if var_rename_dict is not None:
                    if var_name in var_rename_dict.keys():
                        renamed_var_name = var_rename_dict[var_name]
                    else:
                        renamed_var_name = var_name
                else:
                    renamed_var_name = var_name

                output_geotiff_path = os.path.join(output_dir, renamed_var_name + '_' + str(renamed_time_value) + '.tif')

                proposed_filenames.append(output_geotiff_path)

                # LEARNING POINT ollowing stackoverflow, I originally used the below notation, but this was 1000x slower than the following one which uses only numpy indices.
                # array = var[:][dim_selection_indices[0]]

                if not return_only_proposed_filenames:

                    if hb.path_exists(output_geotiff_path):
                        L.info(output_geotiff_path + ' already exists so netcdf_to_geotiffs() skipped it.')
                    else:
                        array = np.array(var[time_index])
                        fill_value = None
                        if '_FillValue' in var.__dict__:
                            fill_value = var.__dict__['_FillValue']
                        if 'missing_value' in var.__dict__:
                            fill_value = var.__dict__['missing_value']

                        if ndv is None:
                            ndv = -9999
                        if fill_value is not None:
                            array = np.where(array == fill_value, ndv, array)

                        hb.save_array_as_geotiff(array, output_geotiff_path, ndv=ndv, data_type=data_type, compress=True, n_cols=array.shape[1], n_rows=array.shape[0],
                                                 geotransform_override=geotransform, projection_override=projection)

    return proposed_filenames


def extract_luh_netcdf_to_geotiffs(input_nc_uri, output_dir, dim_selection_indices):
    """
    DEPRECATED IN FAVOR OF def extract_global_netcdf

    WARNING: currently only works given the nc structure of LUH2. Use extract_global_netcdf_to_geotiff

    dim_selection_indices allows you to select all the data specific to an asigned set of indices.
    For example, with a standard time, lat, lon dimension structure of the .nc, assigning
    dim_selection_indices = [7, None, None] would grab time=7, all lats, all lons. If dim_selection_indices
    is a single value, it assumes that will be the selection for the first dimension..
    """

    if type(dim_selection_indices) in [float, int]:
        dim_selection_indices = [dim_selection_indices, None, None]

    L.info('Called extract_luh_netcdf_to_geotiffs on ' + str(input_nc_uri))
    ncfile = netCDF4.Dataset(input_nc_uri, 'r')
    dim_names = ncfile.dimensions.keys()
    dims_data = {}
    dim_lengths = []
    for dim_name in dim_names:
        if dim_name != 'bounds':
            dims_data[dim_name] = ncfile.variables[dim_name][:]
            dim_lengths.append(len(dims_data[dim_name]))
    # ASSUME THIS IS GLOBAL to derive the geotransform
    res = (360.0) / len(dims_data['lon'])
    geotransform = [-180.0, res, 0.0, 90.0, 0.0, -1 * res]
    projection = 'wgs84'

    for var_name, var in ncfile.variables.items():
        if 'standard_name' in var.__dict__:
            var_string = str(var_name)
            # var_string = str(var_name) + ' ^ ' + var.__dict__['standard_name'] + ' ^ ' + var.__dict__['long_name']

            L.info('Processing ' + var_string)

            if var_name not in dim_names:
                # BROKEN, this wouldn't work with other dim_selection_indices schemes.
                array = var[:][dim_selection_indices[0]]

                no_data_value = -9999
                array = np.where(array > 1E19, no_data_value, array)

                output_geotiff_path = os.path.join(output_dir, var_string + '.tif')
                hb.save_array_as_geotiff(array, output_geotiff_path, ndv=no_data_value, data_type=7, compress=True, n_cols=array.shape[1], n_rows=array.shape[0],
                                         geotransform_override=geotransform, projection_override=projection)

                # output_geotiff_rp_uri = hb.suri(output_geotiff_path, 'eck')
                # wkt = hb.get_wkt_from_epsg_code(54012)
                # hb.reproject_dataset_uri(output_geotiff_path, 0.25, wkt, 'bilinear', output_geotiff_rp_uri)




def get_cell_size_from_nc_path(input_path):
    hb.assert_path_is_gdal_readable(input_path)

    if input_path.endswith('.nc'):
        ds = netCDF4.Dataset(input_path, 'r')
        dims_dict = {}
        dim_names = ds.dimensions.keys()
        for dim_name in dim_names:
            dims_dict[ds.dimensions[dim_name].name] = ds.dimensions[dim_name].size

        if 'lat' in dims_dict:
            return 180. / float(dims_dict['lat'])
        else:
            raise NameError('get_cell_size_from_path on ' + str(input_path) + ' did not have lat in its dimensions, thus could not determine cellsize.')

    else:
        raise NameError('Didnt read the path correctly, it should end in .nc')

def write_geotiff_as_netcdf(input_path, output_path):

    return 1

def load_netcdf_as_array(input_path):
    nc_fid = netCDF4.Dataset(input_path, 'r')  # Dataset is the class behavior to open the file
    """w (write mode) to create a new file, use clobber=True to over-write and existing one
    r (read mode) to open an existing file read-only
    r+ (append mode) to open an existing file and change its contents"""
    # and create an instance of the ncCDF4 class
    nc_fid.close()

def create_netcdf_at_path(output_path):
    f = netCDF4.Dataset(output_path, 'w')

    """The first dimension is called time with unlimited size (i.e. variable values may be 
    appended along the this dimension). Unlimited size dimensions must be declared before (“to the left of”) other dimensions. 
    We usually use only a single unlimited size dimension that is used for time."""
    f.createDimension('time', None)
    f.createDimension('z', 3)
    f.createDimension('y', 4)
    f.createDimension('x', 5)

    lats = f.createVariable('lat', float, ('y',), zlib=True)
    lons = f.createVariable('lon', float, ('x',), zlib=True)
    orography = f.createVariable('orog', float, ('y', 'x'), zlib=True, least_significant_digit=1, fill_value=0)

    # create latitude and longitude 1D arrays
    lat_out = [60, 65, 70, 75]
    lon_out = [30, 60, 90, 120, 150]
    # Create field values for orography
    data_out = np.arange(4 * 5)  # 1d array but with dimension x*y
    data_out.shape = (4, 5)  # reshape to 2d array
    orography[:] = data_out

    """lats is a netCDF variable; a lot more than a simple numpy array while lats[:] allows you to access 
    the latitudes values stored in the lats netCDF variable. lats[:] is a numpy array."""

    lats[:] = lat_out
    lons[:] = lon_out
    # close file to write on disk
    f.close()

def show_netcdf(input_path):
    import netCDF4
    import numpy as np
    import scipy
    import scipy.cluster.vq
    # from scipy.cluster.vq import *
    from matplotlib import colors as c
    import matplotlib.pyplot as plt

    np.random.seed((1000, 2000))

    f = netCDF4.Dataset(input_path, 'r')
    lats = f.variables['latitude'][:]
    lons = f.variables['longitude'][:]
    pw = f.variables['precipitable_water'][0, :, :]

    f.close()
    # Flatten image to get line of values
    flatraster = pw.flatten()
    flatraster.mask = False
    flatraster = flatraster.data

    # In first subplot add original image
    fig, (ax1, ax2, ax3) = plt.subplots(3, sharex=True)

    # Create figure to receive results
    fig.set_figheight(20)
    fig.set_figwidth(15)

    fig.suptitle('K-Means Clustering')
    ax1.axis('off')
    ax1.set_title('Original Image\nMonthly Average Precipitable Water\n over Ice-Free Oceans (kg m-2)')
    original = ax1.imshow(pw, cmap='rainbow', interpolation='nearest', aspect='auto', origin='lower')
    plt.colorbar(original, cmap='rainbow', ax=ax1, orientation='vertical')
    # In remaining subplots add k-means clustered images
    # Define colormap
    list_colors = ['blue', 'orange', 'green', 'magenta', 'cyan', 'gray', 'red', 'yellow']

    print ("Calculate k-means with 6 clusters.")

    # This scipy code classifies k-mean, code has same length as flattened
    # raster and defines which cluster the value corresponds to
    centroids, variance = scipy.cluster.vq.kmeans(flatraster.astype(float), 6)
    code, distance = scipy.cluster.vq.vq(flatraster, centroids)

    # Since code contains the clustered values, reshape into SAR dimensions
    codeim = code.reshape(pw.shape[0], pw.shape[1])

    # Plot the subplot with 4th k-means
    ax2.axis('off')
    xlabel = '6 clusters'
    ax2.set_title(xlabel)
    bounds = range(0, 6)
    cmap = c.ListedColormap(list_colors[0:6])
    kmp = ax2.imshow(codeim, interpolation='nearest', aspect='auto', cmap=cmap, origin='lower')
    plt.colorbar(kmp, cmap=cmap, ticks=bounds, ax=ax2, orientation='vertical')

    #####################################

    thresholded = np.zeros(codeim.shape)
    thresholded[codeim == 3] = 1
    thresholded[codeim == 5] = 2

    # Plot only values == 5
    ax3.axis('off')
    xlabel = 'Keep the fifth cluster only'
    ax3.set_title(xlabel)
    bounds = range(0, 2)
    cmap = c.ListedColormap(['white', 'green', 'cyan'])
    kmp = ax3.imshow(thresholded, interpolation='nearest', aspect='auto', cmap=cmap, origin='lower')
    plt.colorbar(kmp, cmap=cmap, ticks=bounds, ax=ax3, orientation='vertical')

    plt.show()


def compress_netcdf(input_path, output_path):


    src = nc.Dataset(input_path)
    trg = nc.Dataset(output_path, mode='w')

    # Create the dimensions of the file
    for name, dim in src.dimensions.items():
        trg.createDimension(name, len(dim) if not dim.isunlimited() else None)

    # Copy the global attributes
    trg.setncatts({a: src.getncattr(a) for a in src.ncattrs()})

    # Create the variables in the file
    for name, var in src.variables.items():
        trg.createVariable(name, var.dtype, var.dimensions, zlib=True)

        # Copy the variable attributes
        trg.variables[name].setncatts({a: var.getncattr(a) for a in var.ncattrs()})

        # Copy the variables values (as 'f4' eventually)
        trg.variables[name][:] = src.variables[name][:]

    # Save the file
    trg.close()
    src.close()

def combine_earthstat_tifs_to_nc(tif_paths, nc_path):
    # get Dims
    z = len(tif_paths)
    size_check = list(set([hb.get_shape_from_dataset_path(path) for path in tif_paths]))

    if len(size_check) < 1:
        raise NameError('Shapes given as a list to combine_tifs_to_nc led to no shape.')
    elif len(size_check) > 1:
        raise NameError('Shapes given as a list to combine_tifs_to_nc didnt all have the same shape.')
    else:
        pass

    y = size_check[0][0]
    x = size_check[0][1]

    match = nc.Dataset(r"C:\OneDrive\Projects\base_data\luh2\raw_data\RCP26_SSP1\multiple-states_input4MIPs_landState_ScenarioMIP_UofMD-IMAGE-ssp126-2-1-f_gn_2015-2100.nc")


    # y = match.variables['primf'].current_shape


    target_nc = nc.Dataset(nc_path, mode='w', format='NETCDF4')
    target_nc.description = 'Description is here.'

    # copy Global attributes from original file
    for att in match.ncattrs():
        setattr(target_nc, att, getattr(match, att))

    # Get metadata from known source

    hb.pp(match)
    hb.pp(match['primf'])

    target_nc.createDimension('y', y)
    target_nc.createDimension('x', x)

    lon_var = target_nc.createVariable('lon', 'f4', ('x'))
    lat_var = target_nc.createVariable('lat', 'f4', ('y'))
    # x_var = target_nc.createVariable('x', 'f4', ('x'))
    # y_var = target_nc.createVariable('y', 'f4', ('y'))
    primf_var = target_nc.createVariable('primf', 'f4', ('y', 'x'))

    # for var in match.variables:
    # for var in ['bounds']:
    for var in ['lat', 'lon', 'primf']:
        hb.pp(match.variables[var].ncattrs())
        for att in match.variables[var].ncattrs():
            setattr(target_nc.variables[var], att, getattr(match.variables[var], att))
    lon_var[:] = match.variables['lon'][:]
    lat_var[:] = match.variables['lat'][:]
    primf_var[:] = match.variables['primf'][:]
    # x_var[:] = match.variables['x'][:]
    # y_var[:] = match.variables['y'][:]

    target_nc.Conventions = 'CF-1.6'



    target_nc.extent = hb.global_bounding_box
    target_nc.close()


def combine_earthstat_tifs_to_nc_new(tif_paths, nc_path):

    aborted = 1    
    if aborted:
        return

    # get Dims
    z = len(tif_paths)
    size_check = list(set([hb.get_shape_from_dataset_path(path) for path in tif_paths]))

    if len(size_check) < 1:
        raise NameError('Shapes given as a list to combine_tifs_to_nc led to no shape.')
    elif len(size_check) > 1:
        raise NameError('Shapes given as a list to combine_tifs_to_nc didnt all have the same shape.')
    else:
        pass
    y = size_check[0][0]
    x = size_check[0][1]

    target_nc = nc.Dataset(nc_path, mode='w')
    # target_nc.createDimension('time', z)
    # target_nc.createDimension('esa_lulc_class', z)
    target_nc.createDimension('lon', y)
    target_nc.createDimension('lat', x)

    # time = target_nc.createVariable('time', float, ('time',), zlib=True, fill_value=-9999)
    lats = target_nc.createVariable('lat', float, ('lat',), zlib=False, fill_value=-9999.)
    lons = target_nc.createVariable('lon', float, ('lon',), zlib=False, fill_value=-9999.)

    y_res = 180.0 / y
    x_res = 360.0 / x

    lats[:] = np.arange(-180., 180., x_res)
    lons[:] = np.arange(-90., 90., y_res)

    lats[:] = np.arange(-180. + x_res / 2., 180. + x_res / 2., x_res)
    lons[:] = np.arange(-90. + y_res / 2., 90. + y_res / 2., y_res)

    for c, path in enumerate(tif_paths):
        crop_name = os.path.split(path)[1].split('_')[0]
        var = target_nc.createVariable(crop_name, float, ('lon', 'lat'), zlib=True, fill_value=-9999.0, chunksizes=(43, 21))
        # ds = gdal.OpenEx(path)
        # current_array = ds.ReadAsArray()
        # var[:] = np.flipud(current_array)
        # var[c, :] = current_array
    #
    # close file to write on disk
    target_nc.close()

def read_earthstat_nc_slice(input_nc_path, crop_name):
    # TODOOO, conclusion is that ::4 slicing is 10x faster in gdal but chunk slicing in a square is 2x faster in nc.
    start = time.time()

    aborted = 1    
    if aborted:
        return

    ds = nc.Dataset(input_nc_path)

    start = time.time()
    # ds = gdal.OpenEx(r"C:\OneDrive\Projects\base_data\crops\earthstat\crop_production\barley_HarvAreaYield_Geotiff\barley_HarvestedAreaFraction.tif")

def prune_nc_by_vars_list(input_path, output_path, vars_to_include):

    # HACKish, but basically all the spatial reference stuff comes from input file, with the axes named canonically as follows
    vars_to_include += ['time', 'lat', 'lon']

    with netCDF4.Dataset(input_path) as src, netCDF4.Dataset(output_path, "w") as dst:
        # copy global attributes all at once via dictionary
        L.info('Setting global nc attributes: ' +str(src.__dict__))
        dst.setncatts(src.__dict__)
        # copy dimensions
        for name, dimension in src.dimensions.items():
            L.info('Creating dimensions ' + str(name))
            dst.createDimension(
                name, (len(dimension) if not dimension.isunlimited() else None))
        # copy all file data except for the excluded
        for name, variable in src.variables.items():
            if name in vars_to_include:
                x = dst.createVariable(name, variable.datatype, variable.dimensions, zlib=True)
                # copy variable attributes all at once via dictionary

                L.info('Setting variable nc attributes for ' + str(name) + ': ' + str(src[name].__dict__))
                dst[name].setncatts(src[name].__dict__)


                dst[name][:] = src[name][:]

def generate_nc_from_attributes(output_path):

    dsout = nc.Dataset(output_path, 'w', clobber=True)

    rows = 2180
    cols = 4320
    lats = np.linspace(-90.0, 90.0, cols)
    lons = np.linspace(-180.0, 180.0, rows)

    time = dsout.createDimension('time', 0)

    lat = dsout.createDimension('lat', cols)
    lat = dsout.createVariable('lat', 'f4', ('lat',), zlib=True)
    lat.standard_name = 'latitude'
    lat.units = 'degrees_north'
    lat.axis = "Y"
    lat[:] = lats

    lon = dsout.createDimension('lon', rows)
    lon = dsout.createVariable('lon', 'f4', ('lon',), zlib=True)
    lon.standard_name = 'longitude'
    lon.units = 'degrees_east'
    lon.axis = "X"
    lon[:] = lons

    times = dsout.createVariable('time', 'f4', ('time',), zlib=True)
    times.standard_name = 'time'
    times.long_name = 'time'
    times.units = 'hours since 1970-01-01 00:00:00'
    times.calendar = 'gregorian'

    actual_variable = dsout.createVariable(
        'actual_variable_name',
        'f4',
        ('time', 'lat', 'lon'),
        zlib=True,
        complevel=4,
        # least_significant_digit=1,
        fill_value=-9999., chunksizes=(1, 432, 216)
    )


    actual_variable[:] = np.ones((1, rows, cols))
    actual_variable.standard_name = 'acc_precipitation_amount'
    actual_variable.units = 'mm'
    actual_variable.setncattr('grid_mapping', 'spatial_ref')

    crs = dsout.createVariable('spatial_ref', 'i4')
    crs.spatial_ref = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]'
