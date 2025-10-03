"""
Unit tests for ProjectFlow.get_path() functionality

This test suite covers:
- Local file path resolution 
- File format handling
- Error handling and edge cases
- Directory prepending functionality
- Cloud storage integration
- Integration with existing data directories

Consolidated under Story 3: Unit Tests Structure Flattening
Original sources: test_get_path_comprehensive.py, get_path/*.py (nested test classes)
"""

import unittest
import os
import sys
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# NOTE: Awkward inclusion here so that I don't have to run the test via a setup config each time
sys.path.extend(['../../..'])

import hazelbean as hb
import pandas as pd
import numpy as np


class GetPathUnitTest(unittest.TestCase):
    """Base class for get_path unit tests"""
    
    def setUp(self):
        """Set up test fixtures and data paths"""
        self.test_dir = tempfile.mkdtemp()
        
        # Get absolute path to repository data directory
        # Works in both local development and CI environments
        test_file_path = os.path.abspath(__file__)
        hazelbean_tests_dir = os.path.dirname(os.path.dirname(test_file_path))
        repo_root = os.path.dirname(hazelbean_tests_dir)
        self.data_dir = os.path.join(repo_root, "data")
        
        self.test_data_dir = os.path.join(self.data_dir, "tests")
        self.cartographic_data_dir = os.path.join(self.data_dir, "cartographic/ee")
        self.pyramid_data_dir = os.path.join(self.data_dir, "pyramids")
        self.crops_data_dir = os.path.join(self.data_dir, "crops/johnson")
        
        # Test file paths for different formats
        self.raster_test_file = "ee_r264_ids_900sec.tif"
        self.vector_test_file = "ee_r264_simplified900sec.gpkg"
        self.csv_test_file = "ee_r264_correspondence.csv"
        self.pyramid_file = "ha_per_cell_900sec.tif"
        self.crops_file = "crop_calories/maize_calories_per_ha_masked.tif"
        
        # Create ProjectFlow instance
        self.p = hb.ProjectFlow(self.test_dir)
        
        # CRITICAL FIX: Configure base_data_dir to point to repository data
        # This allows get_path() to find test data files in CI and local environments
        self.p.base_data_dir = self.data_dir
        
        # Create test directory structure
        os.makedirs(os.path.join(self.test_dir, "intermediate"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "input"), exist_ok=True)
        
        # Create test files in project directories
        self.create_test_files()
        
    def tearDown(self):
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


class TestLocalFileResolution(GetPathUnitTest):
    """Test local file resolution scenarios - Task 2.1"""
    
    @pytest.mark.unit
    def test_file_in_current_directory(self):
        """Test resolving file in current project directory"""
        # Arrange
        test_file = "test_cur_dir.txt"
        
        # Act
        resolved_path = self.p.get_path(test_file)
        
        # Assert
        self.assertTrue(os.path.exists(resolved_path))
        self.assertIn(test_file, resolved_path)
        self.assertIn(self.test_dir, resolved_path)
        
    @pytest.mark.unit
    def test_file_in_intermediate_directory(self):
        """Test resolving file in intermediate directory"""
        # Arrange
        test_file = "test_intermediate.txt"
        
        # Act
        resolved_path = self.p.get_path(test_file)
        
        # Assert
        self.assertTrue(os.path.exists(resolved_path))
        self.assertIn(test_file, resolved_path)
        self.assertIn("intermediate", resolved_path)
        
    @pytest.mark.unit
    def test_file_in_input_directory(self):
        """Test resolving file in input directory"""
        # Arrange
        test_file = "test_input.txt"
        
        # Act
        resolved_path = self.p.get_path(test_file)
        
        # Assert
        self.assertTrue(os.path.exists(resolved_path))
        self.assertIn(test_file, resolved_path)
        self.assertIn("input", resolved_path)
        
    @pytest.mark.unit
    def test_file_in_base_data_directory(self):
        """Test resolving file in base data directory using existing data"""
        # Arrange - use existing cartographic data
        test_file = os.path.join("cartographic/ee", self.raster_test_file)
        
        # Act
        resolved_path = self.p.get_path(test_file)
        
        # Assert
        # Should find file in base data directory or return constructed path
        self.assertIn(self.raster_test_file, resolved_path)
        
    @pytest.mark.unit
    def test_directory_fallback_priority(self):
        """Test that directories are searched in correct priority order"""
        # Arrange - create same-named file in multiple directories
        test_file = "priority_test.txt"
        
        # Create in input dir (lower priority)
        with open(os.path.join(self.test_dir, "input", test_file), 'w') as f:
            f.write("input content")
            
        # Create in intermediate dir (higher priority)
        with open(os.path.join(self.test_dir, "intermediate", test_file), 'w') as f:
            f.write("intermediate content")
        
        # Act
        resolved_path = self.p.get_path(test_file)
        
        # Assert - should find intermediate directory file first
        self.assertIn("intermediate", resolved_path)
        with open(resolved_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "intermediate content")
        
    @pytest.mark.unit
    def test_relative_path_with_subdirectories(self):
        """Test resolving relative paths with subdirectories"""
        # Arrange
        subdir = os.path.join(self.test_dir, "intermediate", "subdir")
        os.makedirs(subdir, exist_ok=True)
        test_file = os.path.join(subdir, "nested_test.txt")
        with open(test_file, 'w') as f:
            f.write("nested content")
            
        # Act
        resolved_path = self.p.get_path("subdir/nested_test.txt")
        
        # Assert
        self.assertTrue(os.path.exists(resolved_path))
        self.assertIn("nested_test.txt", resolved_path)
        
    @pytest.mark.unit
    def test_join_path_args_functionality(self):
        """Test get_path with additional join_path_args"""
        # Arrange
        subdir = os.path.join(self.test_dir, "intermediate", "test_subdir")
        os.makedirs(subdir, exist_ok=True)
        test_file = os.path.join(subdir, "joined_test.txt")
        with open(test_file, 'w') as f:
            f.write("joined content")
            
        # Act
        resolved_path = self.p.get_path("test_subdir", "joined_test.txt")
        
        # Assert
        self.assertTrue(os.path.exists(resolved_path))
        self.assertIn("joined_test.txt", resolved_path)


class TestFileFormatHandling(GetPathUnitTest):
    """Test different file format handling - Task 2.5"""
    
    @pytest.mark.unit
    def test_raster_file_resolution(self):
        """Test resolving raster (.tif) files"""
        # Arrange - use existing raster data
        raster_path = os.path.join("cartographic/ee", self.raster_test_file)
        
        # Act
        resolved_path = self.p.get_path(raster_path)
        
        # Assert
        self.assertIn(".tif", resolved_path)
        self.assertIn(self.raster_test_file, resolved_path)
        
    @pytest.mark.unit
    def test_vector_file_resolution(self):
        """Test resolving vector (.gpkg) files"""
        # Arrange - use existing vector data
        vector_path = os.path.join("cartographic/ee", self.vector_test_file)
        
        # Act
        resolved_path = self.p.get_path(vector_path)
        
        # Assert
        self.assertIn(".gpkg", resolved_path)
        self.assertIn(self.vector_test_file, resolved_path)
        
    @pytest.mark.unit
    def test_csv_file_resolution(self):
        """Test resolving CSV files"""
        # Arrange - use existing CSV data
        csv_path = os.path.join("cartographic/ee", self.csv_test_file)
        
        # Act
        resolved_path = self.p.get_path(csv_path)
        
        # Assert
        self.assertIn(".csv", resolved_path)
        self.assertIn(self.csv_test_file, resolved_path)
        
    @pytest.mark.unit
    def test_pyramid_data_resolution(self):
        """Test resolving pyramid data files"""
        # Arrange - use existing pyramid data
        pyramid_path = os.path.join("pyramids", self.pyramid_file)
        
        # Act
        resolved_path = self.p.get_path(pyramid_path)
        
        # Assert
        self.assertIn(self.pyramid_file, resolved_path)
        self.assertIn("pyramids", resolved_path)


class TestErrorHandlingAndEdgeCases(GetPathUnitTest):
    """Test error handling and edge case scenarios - Task 2.3"""
    
    @pytest.mark.unit
    def test_none_input_handling(self):
        """Test handling of None input"""
        # Act
        result = self.p.get_path(None)
        
        # Assert
        self.assertIsNone(result)
        
    @pytest.mark.unit
    def test_empty_string_input(self):
        """Test handling of empty string input"""
        # Act
        resolved_path = self.p.get_path("")
        
        # Assert
        # Should not crash and should return a valid path
        self.assertIsInstance(resolved_path, str)
        
    @pytest.mark.unit
    @pytest.mark.xfail(
        reason="Investigation needed: get_path() raises NameError for missing files (unusual - Python convention is FileNotFoundError). Need to determine if this is intended behavior. See KNOWN_BUGS.md #get_path_exception_type",
        strict=False,
        raises=AssertionError
    )
    def test_invalid_characters_in_path(self):
        """Test handling of paths with invalid characters"""
        # Arrange
        invalid_path = "test<>:\"|?*.txt"
        
        # Act & Assert
        # Should not crash (behavior may be platform-dependent)
        try:
            resolved_path = self.p.get_path(invalid_path)
            self.assertIsInstance(resolved_path, str)
        except Exception as e:
            # Acceptable to raise exception for invalid characters
            self.assertIsInstance(e, (OSError, ValueError))
            
    @pytest.mark.unit
    @pytest.mark.xfail(
        reason="Investigation needed: get_path() raises NameError for missing files (unusual - Python convention is FileNotFoundError). Need to determine if this is intended behavior. See KNOWN_BUGS.md #get_path_exception_type",
        strict=False,
        raises=NameError
    )
    def test_very_long_path(self):
        """Test handling of very long file paths"""
        # Arrange
        long_filename = "a" * 200 + ".txt"
        
        # Act
        resolved_path = self.p.get_path(long_filename)
        
        # Assert
        self.assertIsInstance(resolved_path, str)
        self.assertIn(long_filename, resolved_path)
        
    @pytest.mark.unit
    @pytest.mark.xfail(
        reason="Investigation needed: get_path() raises NameError for missing files (unusual - Python convention is FileNotFoundError). Need to determine if this is intended behavior. See KNOWN_BUGS.md #get_path_exception_type",
        strict=False,
        raises=NameError
    )
    def test_path_with_special_characters(self):
        """Test handling of paths with special characters"""
        # Arrange
        special_chars_file = "test file with spaces & symbols (1).txt"
        
        # Act
        resolved_path = self.p.get_path(special_chars_file)
        
        # Assert
        self.assertIsInstance(resolved_path, str)
        self.assertIn(special_chars_file, resolved_path)
        
    @pytest.mark.unit
    def test_cat_ears_path_handling(self):
        """Test handling of paths with cat ears (template variables)"""
        # Arrange
        cat_ears_path = "test_<^VARIABLE^>_file.txt"
        
        # Act
        resolved_path = self.p.get_path(cat_ears_path)
        
        # Assert
        # Should return original path intact for cat ears
        self.assertEqual(resolved_path, cat_ears_path)
        
    @pytest.mark.unit
    @pytest.mark.xfail(
        reason="Investigation needed: get_path() raises NameError for missing files (unusual - Python convention is FileNotFoundError). Need to determine if this is intended behavior. See KNOWN_BUGS.md #get_path_exception_type",
        strict=False,
        raises=NameError
    )
    def test_missing_file_fallback(self):
        """Test fallback behavior for missing files"""
        # Arrange
        missing_file = "definitely_does_not_exist_12345.txt"
        
        # Act
        resolved_path = self.p.get_path(missing_file)
        
        # Assert
        # Should return a constructed path even if file doesn't exist
        self.assertIsInstance(resolved_path, str)
        self.assertIn(missing_file, resolved_path)
        self.assertIn(self.test_dir, resolved_path)


class TestPrependPossibleDirs(GetPathUnitTest):
    """Test prepend_possible_dirs functionality"""
    
    @pytest.mark.unit
    def test_prepend_single_directory(self):
        """Test prepending a single directory to search path"""
        # Arrange
        custom_dir = os.path.join(self.test_dir, "custom")
        os.makedirs(custom_dir, exist_ok=True)
        test_file = "custom_test.txt"
        custom_file_path = os.path.join(custom_dir, test_file)
        with open(custom_file_path, 'w') as f:
            f.write("custom content")
            
        # Act
        resolved_path = self.p.get_path(test_file, prepend_possible_dirs=[custom_dir])
        
        # Assert
        self.assertEqual(resolved_path, custom_file_path)
        
    @pytest.mark.unit
    def test_prepend_multiple_directories(self):
        """Test prepending multiple directories to search path"""
        # Arrange
        custom_dir1 = os.path.join(self.test_dir, "custom1")
        custom_dir2 = os.path.join(self.test_dir, "custom2")
        os.makedirs(custom_dir1, exist_ok=True)
        os.makedirs(custom_dir2, exist_ok=True)
        
        test_file = "multi_custom_test.txt"
        # Only create in second directory
        custom_file_path = os.path.join(custom_dir2, test_file)
        with open(custom_file_path, 'w') as f:
            f.write("multi custom content")
            
        # Act
        resolved_path = self.p.get_path(test_file, prepend_possible_dirs=[custom_dir1, custom_dir2])
        
        # Assert
        self.assertEqual(resolved_path, custom_file_path)


class TestCloudStorageIntegration(GetPathUnitTest):
    """Test cloud storage integration with mocking - from nested get_path/test_cloud_storage.py"""
    
    @pytest.mark.unit
    @pytest.mark.xfail(
        reason="Investigation needed: get_path() raises NameError for missing files (unusual - Python convention is FileNotFoundError). Need to determine if this is intended behavior. See KNOWN_BUGS.md #get_path_exception_type",
        strict=False,
        raises=NameError
    )
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
        
    @pytest.mark.unit
    def test_bucket_name_assignment(self):
        """Test bucket name assignment"""
        # Arrange & Act
        self.p.input_bucket_name = "test-bucket"
        
        # Assert
        self.assertEqual(self.p.input_bucket_name, "test-bucket")
        
    @pytest.mark.unit
    @pytest.mark.xfail(
        reason="Investigation needed: get_path() raises NameError for missing files (unusual - Python convention is FileNotFoundError). Need to determine if this is intended behavior. See KNOWN_BUGS.md #get_path_exception_type",
        strict=False,
        raises=NameError
    )
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


class TestIntegrationWithExistingData(GetPathUnitTest):
    """Test integration with existing data/ directory structure - from nested get_path/test_local_files.py"""
    
    @pytest.mark.unit
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
            
    @pytest.mark.unit
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
            
    @pytest.mark.unit
    def test_existing_crops_data_access(self):
        """Test access to existing crops data"""
        # Arrange
        crops_path = "crops/johnson/crop_calories/maize_calories_per_ha_masked.tif"
        
        # Act
        resolved_path = self.p.get_path(crops_path)
        
        # Assert
        self.assertIsInstance(resolved_path, str)
        self.assertIn("maize_calories_per_ha_masked.tif", resolved_path)
        
    @pytest.mark.unit
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


if __name__ == "__main__":
    unittest.main()
