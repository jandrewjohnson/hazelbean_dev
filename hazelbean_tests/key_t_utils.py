import pandas as pd
from hazelbean import cloud_utils

if __name__=='__main__':

    import os
    import hazelbean as hb
    
    global_1deg_raster_path = 'data/global_1deg_floats.tif'
    zones_vector_path = "data/countries_iso3.gpkg"
    zone_ids_raster_path = "data/country_ids_300sec.tif"
    zone_values_path = "data/ha_per_cell_300sec.tif"

    run_all = 0
    remove_temporary_files = 0
    output_dir = 'c:/tempcomp/test_project'

    test_this = 0
    if test_this or run_all:

        # Test getting a Bounding Box of a raster
        bb = hb.get_bounding_box(global_1deg_raster_path)
        print(bb)

        # Test getting a Bounding Box of a vector
        bb = hb.get_bounding_box(zones_vector_path)
        print(bb)

        # Create a new GPKG for just the country of RWA
        rwa_vector_path = hb.temp('.gpkg', 'rwa', remove_temporary_files, output_dir)
        hb.extract_features_in_shapefile_by_attribute(zones_vector_path, rwa_vector_path, "iso3", "RWA")

        # Get the bounding box of that new vector
        bb = hb.get_bounding_box(rwa_vector_path)
        print(bb)

        # Try again with a different one

        # LEARNING POINT: When pasting a windows path, you get BACKSLASHES
        # VS Code has a fast way to replace all backslashes with forward slashes
        # Highlight one of the backslashes and then press CTRL + SHIFT + L
        # This will highlight all instances of that character in the file.
        # Then you can just type a forward slash and it will replace all of them
        

        
    # TEST auto downloading of files via get_path
    test_this = 0
    if test_this or run_all: 
        
        # Test that it does find a path that exists 
        p = hb.ProjectFlow(output_dir)
        p.base_data_dir = '../../../base_data'
        
        # You can put the api credentials anywhere in the folder structure. Preferred is at the root of base data.
         
        p.data_credentials_path = None
        p.input_bucket_name = 'gtap_invest_seals_2023_04_21'
        
        test_path = p.get_path('cartographic/gadm/gadm_410_adm0_labels_test.csv', verbose=True)
        df = pd.read_csv(test_path)
        assert len(df) > 0
        hb.remove_path(test_path)
        
        # Now try it WITH credentials
        p.data_credentials_path = p.get_path('api_key_credentials.json')
        test_path = p.get_path('cartographic/gadm/gadm_410_adm0_labels_test.csv', verbose=True)
        df = pd.read_csv(test_path)
        assert len(df) > 0
        hb.remove_path(test_path)        
        
        

    # TEST get_reclassification_dict_from_df
    test_this = 1
    if test_this or run_all: 
        # Test that it does find a path that exists 
        p = hb.ProjectFlow(output_dir)
        p.base_data_dir = '../../../base_data'
        
        correspondence_path = p.get_path('gtap_invest', 'region_boundaries', 'ee_r50_aez18_correspondence.csv')
        from hazelbean import utils
        
        # TODO This should be extended to cover classifcation dicts from correspondences but also structured and unstructured mappings.
        r = utils.get_reclassification_dict_from_df(correspondence_path, 'gtapv7_r160_id', 'gtapv7_r50_id', 'gtapv7_r160_label', 'gtapv7_r50_label')
        
        hb.print_iterable(r)
