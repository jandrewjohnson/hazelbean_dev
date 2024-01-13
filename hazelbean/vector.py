
import os, sys
import hazelbean as hb
import pandas as pd
import geopandas as gpd
from osgeo import ogr


def get_num_rows(vector_path, layer_id_or_label=0):
    ds = ogr.Open(vector_path)
    layer = ds.GetLayer(layer_id_or_label)
    num_rows = layer.GetFeatureCount()
    return num_rows

def read_vector(vector_path, layer_id_or_label=0, return_slice_list=False, chunk_size=128, logger_level=10):
    # Get the size of the file using os.stat
    file_size = os.stat(vector_path).st_size  
    
    load_as_chunks_threshold = 2**22 
    if file_size > load_as_chunks_threshold:
        load_as_chunks = True
    else:
        load_as_chunks = False
    
    
    if load_as_chunks:
        num_rows = get_num_rows(vector_path, layer_id_or_label)    
        num_chunks = int(num_rows/chunk_size) + 1
        
        slice_list = []
        for i in range(num_chunks):
            
            if logger_level >= 10:
                hb.log('Reading chunk ' + str(i) + ' of ' + str(num_chunks) + ' from ' + vector_path)
                
            if (i + 1) * chunk_size > num_rows:
                cur_slice = slice(i * chunk_size, num_rows)
            else:
                cur_slice = slice(i * chunk_size, (i + 1) * chunk_size)
                
            # slice = slice(i * chunk_size, (i + 1) * chunk_size)
            cur_gdf = gpd.read_file(vector_path, rows=cur_slice)
            slice_list.append(cur_gdf)
        
        if return_slice_list:
            return slice_list
        else:
            return pd.concat(slice_list, ignore_index=True)
    else:
        cur_gdf = gpd.read_file(vector_path)
        if return_slice_list:
            return [cur_gdf]
        else:
            return cur_gdf    
    

def simplify_geometry(vector_input, output_path, tolerance, preserve_topology=True, drop_below_tolerance_multiplier=None, logger_level=10):
    
    if type(vector_input) is str:
        vector_input = hb.read_vector(vector_input)        
    
    hb.log('Running simplify_geometry to ' + output_path, logger_level)

    
    if drop_below_tolerance_multiplier is not None:
        # This is super dangerous cause you might just like, accidentally DELETE whole countries. Lol!        
        gdf_exploded=vector_input.explode()
        
        hb.log('Starting to drop small geometries')
        drop_size = drop_below_tolerance_multiplier * tolerance
        mask = gdf_exploded.area > drop_size  
        gdf_exploded = gdf_exploded.loc[mask]
        
        vector_input = gdf_exploded.dissolve(by='GID_0')
    
    hb.log('Starting to run simplification algorithm with tolerance: ' + str(tolerance))
    
    gdf_simplified_series = vector_input.simplify(tolerance, preserve_topology=preserve_topology)
    
    #  Overwrite the geometry column in the original GeoDataFrame
    vector_input.geometry = gdf_simplified_series.geometry
    
    hb.log('Writing to ' + output_path, logger_level)
    vector_input.to_file(output_path, driver='GPKG')