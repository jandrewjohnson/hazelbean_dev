"""
Consolidated Integration Tests for Data Processing Workflows

This file consolidates tests from:
- data_processing_workflows/test_align.py
- data_processing_workflows/test_describe.py  
- data_processing_workflows/test_get_path_integration.py
- data_processing_workflows/test_pyramids_original.py
- data_processing_workflows/test_pyramids.py
- data_processing_workflows/test_raster_vector_interface.py
- data_processing_workflows/test_spatial_projection.py
- data_processing_workflows/test_spatial_utils.py

Covers comprehensive data processing integration testing including:
- Raster resampling and alignment operations
- Array and data structure operations
- Path resolution and cloud storage integration
- Pyramid processing and COG validation
- Raster-vector interface operations
- Spatial projection and transformation
- Spatial utilities and analysis functions
"""

from unittest import TestCase
import unittest
import os, sys, time
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# NOTE Awkward inclusion here so that I don't have to run the test via a setup config each time
sys.path.extend(['../..'])

import hazelbean as hb
import pandas as pd
import numpy as np
import hazelbean.raster_vector_interface as raster_vector_interface
from hazelbean.pyramids import *

delete_on_finish = 1
L = hb.get_logger('raster_vector_interface')


class BaseDataProcessingTest(TestCase):
    """Base class for data processing integration tests with shared setup"""
    
    def setUp(self):        
        self.data_dir = os.path.join(os.path.dirname(__file__), "../../data")
        self.test_data_dir = os.path.join(self.data_dir, "tests")
        self.cartographic_data_dir = os.path.join(self.data_dir, "cartographic/ee")        
        self.pyramid_data_dir = os.path.join(self.data_dir, "pyramids")
        self.crops_data_dir = os.path.join(self.data_dir, "crops/johnson")
        
        # Common test paths
        self.ee_r264_ids_900sec_path = os.path.join(self.cartographic_data_dir, "ee_r264_ids_900sec.tif")
        self.global_1deg_raster_path = os.path.join(self.pyramid_data_dir, "ha_per_cell_3600sec.tif")        
        self.ee_r264_correspondence_vector_path = os.path.join(self.cartographic_data_dir, "ee_r264_simplified900sec.gpkg")
        self.ee_r264_correspondence_csv_path = os.path.join(self.cartographic_data_dir, "ee_r264_correspondence.csv")        
        self.maize_calories_path = os.path.join(self.data_dir, "crops/johnson/crop_calories/maize_calories_per_ha_masked.tif")
        
        # Try to get pyramid paths - skip test if not available (CI doesn't have large data files)
        try:
            self.ha_per_cell_column_900sec_path = hb.get_path(hb.ha_per_cell_column_ref_paths[900])
            self.ha_per_cell_900sec_path = hb.get_path(hb.ha_per_cell_ref_paths[900])
            self.pyramid_match_900sec_path = hb.get_path(hb.pyramid_match_ref_paths[900])
        except (NameError, KeyError, FileNotFoundError):
            # Data files not available - skip tests that need them
            pytest.skip("Large pyramid data files not available in CI environment")
        
        # Pyramid-specific paths
        self.ha_per_cell_path = os.path.join(self.pyramid_data_dir, "ha_per_cell_300sec.tif")
        self.valid_cog_path = os.path.join(self.test_data_dir, "valid_cog_example.tif")
        self.invalid_cog_path = os.path.join(self.test_data_dir, "invalid_cog_example.tif")        
        self.valid_pog_path = os.path.join(self.cartographic_data_dir, "ee_r264_ids_900sec.tif")
        
        # Spatial utils specific setup
        user_dir = os.path.expanduser("~")
        self.output_dir = os.path.join(user_dir, "temp")
        
    def tearDown(self):
        pass


class TestAlignmentOperations(BaseDataProcessingTest):
    """Tests for raster alignment and resampling operations (from test_align.py)"""
    
    def test_resample_to_match(self): 
        """Test basic raster resampling to match reference raster"""
        output_dir = 'data'
        output_path = hb.temp('.tif', 'resampled', delete_on_finish, output_dir)

        hb.resample_to_match(self.ee_r264_ids_900sec_path, 
                     self.global_1deg_raster_path, 
                     output_path, 
                     resample_method='near',
                     output_data_type=6, 
                     src_ndv=None, 
                     ndv=None, 
                     compress=True,
                     calc_raster_stats=False,
                     add_overviews=False,
                     pixel_size_override=None)

        output2_path = hb.temp('.tif', 'mask', delete_on_finish, output_dir)
        hb.create_valid_mask_from_vector_path(self.ee_r264_correspondence_vector_path, self.global_1deg_raster_path, output2_path,
                                        all_touched=True)

    def test_misc_operations(self):
        """Test miscellaneous array and data structure operations"""
        output_dir = 'data'
        
        # Test comma linebreak string to array conversion
        input_string = '''0,1,1
        3,2,2
        1,4,1'''
        a = hb.comma_linebreak_string_to_2d_array(input_string)
        a = hb.comma_linebreak_string_to_2d_array(input_string, dtype=np.int8)

        # Test numpy array save/load operations
        a = np.random.rand(5, 5)
        temp_path = hb.temp('.npy', 'npytest', delete_on_finish, output_dir)
        hb.save_array_as_npy(a, temp_path)
        r = hb.describe(temp_path, surpress_print=True, surpress_logger=True)

        # Test directory operations
        folder_list = ['asdf', 'asdf/qwer']
        hb.create_directories(folder_list)
        hb.remove_dirs(folder_list, safety_check='delete')

        # Test dict/dataframe conversion
        input_dict = {
            'row_1': {'col_1': 1, 'col_2': 2},
            'row_2': {'col_1': 3, 'col_2': 4}
        }
        df = hb.dict_to_df(input_dict)
        generated_dict = hb.df_to_dict(df)
        assert(input_dict == generated_dict)


class TestDescribeOperations(BaseDataProcessingTest):
    """Tests for array description and analysis (from test_describe.py)"""
    
    def test_describe(self):
        """Test describe functionality for arrays"""
        a = np.random.rand(5, 5)
        tmp_path = hb.temp('.npy', remove_at_exit=True)
        hb.save_array_as_npy(a, tmp_path)
        hb.describe(tmp_path, surpress_print=True, surpress_logger=True)


class TestGetPathIntegration(BaseDataProcessingTest):
    """Tests for ProjectFlow.get_path() integration functionality (from test_get_path_integration.py)"""
    
    def setUp(self):
        super().setUp()
        # Additional setup for get_path tests
        self.test_dir = tempfile.mkdtemp()
        
        # Create ProjectFlow instance
        self.p = hb.ProjectFlow(self.test_dir)
        
        # Create test directory structure
        os.makedirs(os.path.join(self.test_dir, "intermediate"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "input"), exist_ok=True)
        
        # Create test files in project directories
        self.create_test_files()
        
    def tearDown(self):
        super().tearDown()
        """Clean up test directories"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def create_test_files(self):
        """Create test files in project directories for testing"""
        # Create some test files in intermediate and input directories
        with open(os.path.join(self.test_dir, "intermediate", "test_intermediate.txt"), 'w') as f:
            f.write("test content")
        with open(os.path.join(self.test_dir, "input", "test_input.txt"), 'w') as f:
            f.write("test content")
        with open(os.path.join(self.test_dir, "test_cur_dir.txt"), 'w') as f:
            f.write("test content")

    @pytest.mark.integration
    def test_google_cloud_bucket_integration(self):
        """Test Google Cloud bucket integration (without actual cloud calls)"""
        # Arrange
        self.p.input_bucket_name = "test-hazelbean-bucket"
        test_file = "cloud_test_file.tif"
        
        # Act
        resolved_path = self.p.get_path(test_file)
        
        # Assert
        # Should return a valid path (either local or constructed cloud path)
        self.assertIsInstance(resolved_path, str)
        self.assertIn(test_file, resolved_path)
        
    @pytest.mark.integration
    def test_bucket_name_assignment(self):
        """Test bucket name assignment"""
        # Arrange & Act
        self.p.input_bucket_name = "test-bucket"
        
        # Assert
        self.assertEqual(self.p.input_bucket_name, "test-bucket")
        
    @pytest.mark.integration
    def test_cloud_path_fallback(self):
        """Test cloud path fallback when local file not found"""
        # Arrange
        self.p.input_bucket_name = "test-bucket"
        test_file = "only_in_cloud.tif"
            
        # Act
        resolved_path = self.p.get_path(test_file)
        
        # Assert
        # Should return a constructed path even if file doesn't exist locally
        self.assertIsInstance(resolved_path, str)
        self.assertIn(test_file, resolved_path)

    @pytest.mark.integration
    def test_existing_cartographic_data_access(self):
        """Test access to existing cartographic data"""
        # Arrange
        cartographic_files = [
            "cartographic/ee/ee_r264_ids_900sec.tif",
            "cartographic/ee/ee_r264_simplified900sec.gpkg", 
            "cartographic/ee/ee_r264_correspondence.csv"
        ]
        
        # Act & Assert
        for file_path in cartographic_files:
            resolved_path = self.p.get_path(file_path)
            self.assertIsInstance(resolved_path, str)
            self.assertIn(os.path.basename(file_path), resolved_path)
            
    @pytest.mark.integration
    def test_existing_pyramid_data_access(self):
        """Test access to existing pyramid data"""
        # Arrange
        pyramid_files = [
            "pyramids/ha_per_cell_900sec.tif",
            "pyramids/ha_per_cell_3600sec.tif",
            "pyramids/match_900sec.tif"
        ]
        
        # Act & Assert
        for file_path in pyramid_files:
            resolved_path = self.p.get_path(file_path)
            self.assertIsInstance(resolved_path, str)
            self.assertIn(os.path.basename(file_path), resolved_path)
            
    @pytest.mark.integration
    def test_existing_crops_data_access(self):
        """Test access to existing crops data"""
        # Arrange
        crops_path = "crops/johnson/crop_calories/maize_calories_per_ha_masked.tif"
        
        # Act
        resolved_path = self.p.get_path(crops_path)
        
        # Assert
        self.assertIsInstance(resolved_path, str)
        self.assertIn("maize_calories_per_ha_masked.tif", resolved_path)
        
    @pytest.mark.integration
    def test_existing_test_data_access(self):
        """Test access to existing test data"""
        # Arrange
        test_files = [
            "tests/valid_cog_example.tif",
            "tests/invalid_cog_example.tif"
        ]
        
        # Act & Assert
        for file_path in test_files:
            resolved_path = self.p.get_path(file_path)
            self.assertIsInstance(resolved_path, str)
            self.assertIn(os.path.basename(file_path), resolved_path)


class TestPyramidOperations(BaseDataProcessingTest):
    """Tests for pyramid processing operations (from test_pyramids_original.py and test_pyramids.py)"""

    def test_load_geotiff_chunk_by_cr(self):
        """Test loading GeoTIFF chunks by column-row coordinates"""
        hb.load_geotiff_chunk_by_cr_size(self.global_1deg_raster_path, (1, 2, 5, 5))

    def test_load_geotiff_chunk_by_bb(self):
        """Test loading GeoTIFF chunks by bounding box"""
        input_path = self.maize_calories_path
        left_lat = -40
        bottom_lon = -25
        lat_size = .2
        lon_size = 1
        bb = [left_lat,
              bottom_lon,
              left_lat + lat_size,
              bottom_lon + lon_size]
        hb.load_geotiff_chunk_by_bb(input_path, bb)

    def test_add_rows_or_cols_to_geotiff(self):
        """Test adding rows or columns to GeoTIFF"""
        incomplete_array = hb.load_geotiff_chunk_by_bb(self.global_1deg_raster_path, [-180, -80, 180, 70])
        temp_path = hb.temp('.tif', 'test_add_rows_or_cols_to_geotiff', True)
        geotransform_override = hb.get_raster_info_hb(self.global_1deg_raster_path)['geotransform']
        geotransform_override = [-180, 1, 0, 80, 0, -1]
        n_rows_override = 150

        hb.save_array_as_geotiff(incomplete_array, temp_path, self.global_1deg_raster_path, geotransform_override=geotransform_override, n_rows_override=n_rows_override)
        temp2_path = hb.temp('.tif', 'test_add_rows_or_cols_to_geotiff', True)
        r_above, r_below, c_above, c_below = 10, 20, 0, 0
        hb.add_rows_or_cols_to_geotiff(temp_path, r_above, r_below, c_above, c_below, remove_temporary_files=True)

    def test_fill_to_match_extent(self):
        """Test filling raster to match extent"""
        incomplete_array = hb.load_geotiff_chunk_by_bb(self.global_1deg_raster_path, [-180, -80, 180, 70])
        temp_path = hb.temp('.tif', 'test_add_rows_or_cols_to_geotiff', True)
        geotransform_override = hb.get_raster_info_hb(self.global_1deg_raster_path)['geotransform']
        geotransform_override = [-180, 1, 0, 80, 0, -1]
        n_rows_override = 150

        hb.save_array_as_geotiff(incomplete_array, temp_path, self.global_1deg_raster_path, geotransform_override=geotransform_override, n_rows_override=n_rows_override)
        temp2_path = hb.temp('.tif', 'expand_to_bounding_box', True)
        hb.fill_to_match_extent(temp_path, self.global_1deg_raster_path, temp2_path)

    def test_fill_to_match_extent_manual(self):
        """Test manual fill to match extent"""
        incomplete_array = hb.load_geotiff_chunk_by_bb(self.global_1deg_raster_path, [-180, -80, 180, 70])
        temp_path = hb.temp('.tif', 'test_add_rows_or_cols_to_geotiff', True)
        geotransform_override = hb.get_raster_info_hb(self.global_1deg_raster_path)['geotransform']
        geotransform_override = [-180, 1, 0, 80, 0, -1]
        n_rows_override = 150

        hb.save_array_as_geotiff(incomplete_array, temp_path, self.global_1deg_raster_path, geotransform_override=geotransform_override, n_rows_override=n_rows_override)
        temp2_path = hb.temp('.tif', 'expand_to_bounding_box', True)
        hb.fill_to_match_extent(temp_path, self.global_1deg_raster_path, temp2_path)

    def test_convert_ndv_to_alpha_band(self):
        """Test converting no-data values to alpha band"""
        output_path = hb.temp(folder=os.path.dirname(self.maize_calories_path), remove_at_exit=True)
        hb.convert_ndv_to_alpha_band(self.maize_calories_path, output_path)

    @pytest.mark.integration
    @pytest.mark.slow
    def test_raster_to_area_raster(self):
        """Check if TIFF files are valid Cloud-Optimized GeoTIFFs (COGs)."""
        temp_path = hb.temp('.tif', filename_start='test_raster_to_area_raster', remove_at_exit=True, tag_along_file_extensions=['.aux.xml'])
        with self.subTest(file=self.ha_per_cell_path):
            raster_to_area_raster(self.ha_per_cell_path, temp_path)
            result = hb.path_exists(temp_path)
            self.assertTrue(result)
            
            # Make it a pog
            temp_pog_path = hb.temp('.tif', filename_start='test_area_raster_as_pog', remove_at_exit=True, tag_along_file_extensions=['.aux.xml'])
            hb.make_path_pog(temp_path, temp_pog_path, output_data_type=7, verbose=True)

            result = hb.is_path_pog(temp_pog_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=True)
            self.assertTrue(result)


class TestRasterVectorInterface(BaseDataProcessingTest):
    """Tests for raster-vector interface operations (from test_raster_vector_interface.py)"""

    def test_raster_calculator_hb(self):
        """Test hazelbean raster calculator"""
        t1 = hb.temp(remove_at_exit=True)
        hb.raster_calculator_hb([(self.ee_r264_ids_900sec_path, 1), (self.ee_r264_ids_900sec_path, 1)], lambda x, y: x + y, t1, 7, -9999)

        # LEARNING POINT, I had to be very careful here with type casting to ensure the summation methods yielded the same.
        a = np.sum(hb.as_array(t1))
        b = np.sum(hb.as_array(self.ee_r264_ids_900sec_path).astype(np.float64)) * np.float64(2.0)

        assert  a == b

    def test_assert_gdal_paths_in_same_projection(self):
        """Test assertion of GDAL paths in same projection"""
        self.assertTrue(
            hb.assert_gdal_paths_in_same_projection([
                self.ee_r264_correspondence_vector_path,
                self.ee_r264_ids_900sec_path,
                self.maize_calories_path,
            ], return_result=True)
        )

        self.assertTrue(
            hb.assert_gdal_paths_in_same_projection([
                self.ee_r264_correspondence_vector_path,
                self.ee_r264_ids_900sec_path,
                self.maize_calories_path,
            ], return_result=True)
        )

    def test_zonal_statistics_faster(self):
        """Test fast zonal statistics implementation"""
        test_results = []
        zone_ids_raster_path = hb.temp('.tif', remove_at_exit=True)

        # Test using the pregenereated
        start = time.time()
        results_dict = hb.zonal_statistics_flex(self.maize_calories_path, self.ee_r264_correspondence_vector_path,
                                                zone_ids_raster_path=zone_ids_raster_path, verbose=False)
        print('results_dict', results_dict)

    def test_zonal_statistics_enumeration(self):
        """Test zonal statistics enumeration"""
        test_results = []
        zone_ids_raster_path = hb.temp('.tif', remove_at_exit=True)
        
        # Test using the pregenereated
        start = time.time()
        results_dict = hb.zonal_statistics_flex(self.ee_r264_ids_900sec_path, self.ee_r264_correspondence_vector_path,
                                                zone_ids_raster_path=zone_ids_raster_path, verbose=False)
        print('results_dict', results_dict)

    def test_super_simplify(self):
        """Test vector super simplification"""
        input_vector_path = self.ee_r264_correspondence_vector_path
        id_column_label = 'ee_r264_id'
        blur_size = 300.0 
        output_path = 'simplified_vector.gpkg'
        raster_vector_interface.vector_super_simplify(input_vector_path, id_column_label, blur_size, output_path, remove_temp_files=True)


class TestSpatialProjection(BaseDataProcessingTest):
    """Tests for spatial projection operations (from test_spatial_projection.py)"""

    def test_resample_to_cell_size(self):
        """Test resampling to specific cell size"""
        output_path = hb.temp('.tif', 'test_resample_to_match', True)
        pixel_size_override = 1.0
        hb.resample_to_match(self.maize_calories_path, self.ee_r264_ids_900sec_path, output_path, resample_method='near',
                             output_data_type=6, src_ndv=None, ndv=None, compress=True,
                             calc_raster_stats=False,
                             add_overviews=False,
                             pixel_size_override=pixel_size_override)

    def test_resample_to_match(self):
        """Test resampling to match reference raster"""
        output_path = hb.temp('.tif', 'test_resample_to_match', True)
        hb.resample_to_match(self.maize_calories_path, self.ee_r264_ids_900sec_path, output_path, resample_method='near',
                             output_data_type=6, src_ndv=None, ndv=None, compress=True,
                             calc_raster_stats=False,
                             add_overviews=False,)

        output2_path = hb.temp('.tif', 'mask', True)
        hb.create_valid_mask_from_vector_path(self.ee_r264_correspondence_vector_path, self.ee_r264_ids_900sec_path, output2_path,
                                              all_touched=True)

        output3_path = hb.temp('.tif', 'masked', True)
        hb.set_ndv_by_mask_path(output_path, output2_path, output_path=output3_path, ndv=-9999.)


class TestSpatialUtils(BaseDataProcessingTest):
    """Tests for spatial utilities and analysis functions (from test_spatial_utils.py)"""

    def test_get_wkt_from_epsg_code(self):
        """Test WKT generation from EPSG codes"""
        hb.get_wkt_from_epsg_code(hb.common_epsg_codes_by_name['wgs84'])

    def test_rank_array(self):
        """Test array ranking functionality"""
        array = np.random.rand(6, 6)
        nan_mask = np.zeros((6, 6))
        nan_mask[1:3, 2:5] = 1
        ranked_array, ranked_pared_keys = hb.get_rank_array_and_keys(array, nan_mask=nan_mask)

        assert (ranked_array[1, 2] == -9999)
        assert (len(ranked_pared_keys[0] == 30))

    def test_create_vector_from_raster_extents(self):
        """Test creating vector from raster extents"""
        extent_path = hb.temp('.shp', remove_at_exit=True)
        hb.create_vector_from_raster_extents(self.pyramid_match_900sec_path, extent_path)
        self.assertTrue(os.path.exists(extent_path))

    def test_read_1d_npy_chunk(self):
        """Test reading 1D numpy array chunks"""
        r = np.random.randint(2,9,200)
        temp_path = hb.temp('.npy', remove_at_exit=True)
        hb.save_array_as_npy(r, temp_path)
        output = hb.read_1d_npy_chunk(temp_path, 3, 8)
        self.assertTrue(sum(r[3:3+8])==sum(output))

    def test_get_attribute_table_columns_from_shapefile(self):
        """Test extracting attribute table columns from shapefiles"""
        r = hb.get_attribute_table_columns_from_shapefile(self.ee_r264_correspondence_vector_path, cols='ee_r264_id')
        self.assertIsNotNone(r)

    def test_extract_features_in_shapefile_by_attribute(self):
        """Test feature extraction by attribute"""
        output_gpkg_path = hb.temp('.gpkg', remove_at_exit=True)
        column_name = 'ee_r264_id'
        column_filter = 77
        hb.extract_features_in_shapefile_by_attribute(self.ee_r264_correspondence_vector_path, output_gpkg_path, column_name, column_filter)

    def test_get_bounding_box(self):
        """Test bounding box extraction from various data types"""
        zones_vector_path = self.ee_r264_correspondence_vector_path
        zone_ids_raster_path = self.ee_r264_ids_900sec_path
        zone_values_path = self.ha_per_cell_900sec_path

        run_all = 0
        remove_temporary_files = 1
        output_dir = self.test_data_dir

        # Test getting a Bounding Box of a raster
        bb = hb.get_bounding_box(self.global_1deg_raster_path)
        print(bb)

        # Test getting a Bounding Box of a vector
        bb = hb.get_bounding_box(zones_vector_path)
        print(bb)

        # Create a new GPKG for just the country of RWA
        rwa_vector_path = hb.temp('.gpkg', 'rwa', remove_temporary_files, output_dir)
        hb.extract_features_in_shapefile_by_attribute(zones_vector_path, rwa_vector_path, "ee_r264_id", 70)

        # Get the bounding box of that new vector
        bb = hb.get_bounding_box(rwa_vector_path)
        print(bb)

    def test_reading_csvs(self):
        """Test auto downloading of files via get_path"""
        # Test that it does find a path that exists 
        p = hb.ProjectFlow(self.output_dir)
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

    def test_get_reclassification_dict_from_df(self):
        """Test reclassification dictionary generation from DataFrame"""
        # Test that it does find a path that exists 
        p = hb.ProjectFlow(self.output_dir)
        p.base_data_dir = '../../../base_data'
        
        correspondence_path = p.get_path(os.path.join(self.data_dir, 'cartographic', 'ee', 'ee_r264_correspondence.csv'))
        from hazelbean import utils
        
        # TODO This should be extended to cover classification dicts from correspondences but also structured and unstructured mappings.
        r = utils.get_reclassification_dict_from_df(correspondence_path, 'gtapv7_r160_id', 'gtapv7_r50_id', 'gtapv7_r160_label', 'gtapv7_r50_label')
        
        hb.print_iterable(r)
        
    def test_clipping_simple(self):
        """Test simple raster clipping operations"""
        output_path = hb.temp('.tif', 'clipped', delete_on_finish, self.output_dir)

        hb.clip_raster_by_vector_simple(self.ee_r264_ids_900sec_path, 
                                        output_path, 
                                        self.ee_r264_correspondence_vector_path, 
                                        output_data_type=6, 
                                        gtiff_creation_options=hb.DEFAULT_GTIFF_CREATION_OPTIONS)

        print('Created', output_path)

        output_dir = 'data'
        output_path = hb.temp('.tif', 'clipped_attr', delete_on_finish, output_dir)

        hb.clip_raster_by_vector_simple(self.ee_r264_ids_900sec_path, 
                                        output_path, 
                                        self.ee_r264_correspondence_vector_path, 
                                        output_data_type=6, 
                                        clip_vector_filter='ee_r264_id="120"',
                                        gtiff_creation_options=hb.DEFAULT_GTIFF_CREATION_OPTIONS)

        print('Created', output_path)

    def test_reclassify_raster_hb(self):
        """Test raster reclassification with hazelbean"""
        rules = {235: 34}   
        output_path = hb.temp('.tif', 'reclassify', True, self.output_dir)
        hb.reclassify_raster_hb(self.ee_r264_ids_900sec_path, 
                                rules,
                                output_path)
        
    def test_reclassify_raster_with_negatives_hb(self):
        """Test raster reclassification with negative values"""
        rules = {235: -555}   
        output_path = hb.temp('.tif', 'reclassify', False, self.output_dir)
        hb.reclassify_raster_hb(self.ee_r264_ids_900sec_path, 
                                rules,
                                output_path, 
                                output_data_type=5)
        
        print(hb.enumerate_raster_path(output_path))
                
        output_with_neg_path = hb.temp('.tif', 'reclassify_with_neg', False, self.output_dir)
        
        rules = {
            235: -444,
            241: -9999,
            -555: -888,
            }  # Adding a rule for 241 to be reclassified to -9999
        
        hb.reclassify_raster_hb(output_path, 
                                rules,
                                output_with_neg_path, 
                                output_data_type=5)
        
        print(hb.enumerate_raster_path(output_with_neg_path))

    def test_reclassify_raster_arrayframe(self):
        """Test raster reclassification with arrayframe"""
        rules = {235: 34}   
        output_path = hb.temp('.tif', 'reclassify', True, self.output_dir)
        hb.reclassify_raster_arrayframe(self.ee_r264_ids_900sec_path, 
                                rules,
                                output_path)


if __name__ == "__main__":
    unittest.main()

