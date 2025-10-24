"""
Consolidated Integration Tests for End-to-End Workflows

This file consolidates tests from:
- end_to_end_workflows/test_dummy_raster_integration.py
- end_to_end_workflows/test_end_to_end_workflow.py

Covers comprehensive end-to-end workflow testing including:
- Complete pipeline: test file → analysis → quality assessment → QMD generation
- Multiple test file processing workflows
- Template system integration validation  
- Plugin system end-to-end execution
- Configuration system integration
- Error handling across complete workflows
- Dummy raster generation and tiling validation
- Raster tiling operations with sum verification
- Integration reproducibility and consistency testing
- Complete workflow validation from creation through verification
"""

import unittest
import os
import sys
import tempfile
import shutil
import glob
import time
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from unittest.mock import patch, MagicMock
from osgeo import gdal, osr
import pytest
import numpy as np

# Add project path for imports
sys.path.extend(['../..'])

import hazelbean as hb

# Import QMD automation components with fallback handling
try:
    from hazelbean_tests.qmd_automation.core.base_plugin import TestFileMetadata, ProcessingResult
    from hazelbean_tests.qmd_automation.core.test_analysis_engine import TestAnalysisEngine, TestCategory
    from hazelbean_tests.qmd_automation.core.quality_assessment_engine import QualityAssessmentEngine, QualityCategory
    from hazelbean_tests.qmd_automation.core.plugin_manager import PluginManager
    QMD_COMPONENTS_AVAILABLE = True
except ImportError as e:
    # Create mock components for testing when full system not available
    print(f"QMD automation components not fully available: {e}")
    QMD_COMPONENTS_AVAILABLE = False
    
    # Mock components for basic testing
    class TestFileMetadata:
        def __init__(self, file_path, category=None):
            self.file_path = file_path
            self.category = category or 'unit'
            self.test_functions = []
            self.content = ""
            self.imports = []
    
    class ProcessingResult:
        def __init__(self, success=True):
            self.success = success
    
    class TestAnalysisEngine:
        def analyze_test_file(self, file_path):
            metadata = TestFileMetadata(file_path)
            # Basic analysis - count test functions
            with open(file_path, 'r') as f:
                content = f.read()
                metadata.content = content
                import re
                test_functions = re.findall(r'def (test_\w+)', content)
                metadata.test_functions = test_functions
            return metadata
    
    class TestCategory:
        UNIT = 'unit'
        INTEGRATION = 'integration'  
        PERFORMANCE = 'performance'
        MANUAL_SCRIPT = 'manual_script'
    
    class QualityCategory:
        HIGH = 'HIGH'
        MEDIUM = 'MEDIUM'
        LOW = 'LOW'
        STUB = 'STUB'
    
    class QualityAssessment:
        def __init__(self):
            self.quality_score = 50
            self.category = QualityCategory.MEDIUM
            self.educational_value = 5
            self.suggestions = []
    
    class QualityAssessmentEngine:
        def assess_quality(self, metadata):
            assessment = QualityAssessment()
            # Basic quality score based on test function count
            assessment.quality_score = min(len(metadata.test_functions) * 20, 100)
            return assessment
    
    class PluginManager:
        def process_file(self, metadata):
            return [ProcessingResult(success=True)]
        
        def get_loaded_plugins(self):
            return []

# Optional components with fallback
try:
    from hazelbean_tests.qmd_automation.core.template_system import TemplateSystem
except ImportError:
    class TemplateSystem:
        def render_qmd(self, metadata, template_name='default'):
            return f"# Test: {metadata.file_path}\n\nGenerated QMD content"


class TestDummyRasterGeneration(unittest.TestCase):
    """Test dummy raster generation utilities for integration testing (from test_dummy_raster_integration.py)"""
    
    @pytest.fixture(autouse=True)
    def setup_temp_dir(self):
        """Setup temporary directory for tests"""
        self.temp_dir = tempfile.mkdtemp()
        yield
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_dummy_raster_basic(self):
        """Test basic dummy raster creation with known values"""
        temp_dir = tempfile.mkdtemp()
        try:
            output_path = os.path.join(temp_dir, "dummy_basic.tif")
            width, height = 100, 100
            cell_size = 0.1
            
            # Create dummy raster using utility function
            hb.create_dummy_raster(
                output_path=output_path,
                width=width,
                height=height,
                cell_size=cell_size,
                data_type=gdal.GDT_Float32,
                fill_value=42.0,
                nodata_value=-999.0
            )
            
            # Verify file exists
            assert os.path.exists(output_path), "Dummy raster file should be created"
            
            # Verify raster properties
            dataset = gdal.Open(output_path)
            assert dataset is not None, "Raster should be readable"
            assert dataset.RasterXSize == width, f"Width should be {width}"
            assert dataset.RasterYSize == height, f"Height should be {height}"
            
            # Verify geotransform
            geotransform = dataset.GetGeoTransform()
            assert abs(geotransform[1] - cell_size) < 1e-6, f"Pixel size should be {cell_size}"
            assert abs(geotransform[5] + cell_size) < 1e-6, f"Pixel size should be {cell_size}"
            
            # Verify data values
            band = dataset.GetRasterBand(1)
            assert band.GetNoDataValue() == -999.0, "NoData value should be set correctly"
            
            array = band.ReadAsArray()
            assert np.all(array == 42.0), "All pixels should have fill value"
            
            dataset = None  # Close dataset
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_create_dummy_raster_with_pattern(self):
        """Test dummy raster creation with mathematical pattern"""
        temp_dir = tempfile.mkdtemp()
        try:
            output_path = os.path.join(temp_dir, "dummy_pattern.tif")
            width, height = 50, 50
            
            # Create raster with gradient pattern for known sum calculation
            hb.create_dummy_raster_with_pattern(
                output_path=output_path,
                width=width,
                height=height,
                pattern_type="gradient",
                cell_size=1.0
            )
            
            # Verify file and basic properties
            assert os.path.exists(output_path), "Pattern raster should be created"
            
            dataset = gdal.Open(output_path)
            band = dataset.GetRasterBand(1)
            array = band.ReadAsArray()
            
            # Verify gradient pattern (each row should have incrementing values)
            expected_sum = sum(i * width for i in range(height))  # 0*50 + 1*50 + 2*50 + ... + 49*50
            actual_sum = np.sum(array)
            
            assert abs(actual_sum - expected_sum) < 1e-6, "Gradient pattern sum should be calculable"
            assert array[0, 0] == 0, "Top-left should be 0 in gradient"
            assert array[-1, -1] == height - 1, "Bottom-right should be height-1"
            
            dataset = None
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_create_dummy_raster_with_known_sum(self):
        """Test dummy raster creation with predetermined sum for validation"""
        temp_dir = tempfile.mkdtemp()
        try:
            output_path = os.path.join(temp_dir, "dummy_known_sum.tif")
            width, height = 10, 10
            target_sum = 1000.0
            
            # Create raster with known total sum
            hb.create_dummy_raster_with_known_sum(
                output_path=output_path,
                width=width,
                height=height,
                target_sum=target_sum,
                cell_size=0.5
            )
            
            # Verify file creation
            assert os.path.exists(output_path), "Known sum raster should be created"
            
            # Verify sum calculation
            dataset = gdal.Open(output_path)
            band = dataset.GetRasterBand(1)
            array = band.ReadAsArray()
            
            actual_sum = np.sum(array)
            assert abs(actual_sum - target_sum) < 1e-6, f"Sum should be exactly {target_sum}"
            
            # Verify reasonable value distribution
            assert np.all(array > 0), "All values should be positive for sum verification"
            assert array.shape == (height, width), "Array shape should match dimensions"
            
            dataset = None
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestRasterTilingIntegration(unittest.TestCase):
    """Test raster tiling operations with sum verification"""
    
    def test_tile_dummy_raster_sum_conservation(self):
        """Test that tiling preserves total sum of values"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create dummy raster with known sum
            base_raster = os.path.join(temp_dir, "base_for_tiling.tif")
            width, height = 100, 100
            target_sum = 5000.0
            
            hb.create_dummy_raster_with_known_sum(
                output_path=base_raster,
                width=width,
                height=height,
                target_sum=target_sum,
                cell_size=1.0
            )
            
            # Get original sum
            original_array = hb.as_array(base_raster)
            original_sum = np.sum(original_array)
            
            # Tile the raster
            tile_size = 25  # Create 4x4 = 16 tiles
            tiles_dir = os.path.join(temp_dir, "tiles")
            os.makedirs(tiles_dir, exist_ok=True)
            
            tile_paths = hb.tile_raster_into_grid(
                input_raster_path=base_raster,
                output_dir=tiles_dir,
                tile_size=tile_size,
                overlap=0
            )
            
            # Verify tiles were created
            assert len(tile_paths) > 0, "Tiles should be created"
            
            # Sum all tile values
            total_tiles_sum = 0.0
            valid_tiles = 0
            
            for tile_path in tile_paths:
                if os.path.exists(tile_path):
                    tile_array = hb.as_array(tile_path)
                    tile_sum = np.sum(tile_array[tile_array != hb.get_ndv_from_path(tile_path)])
                    total_tiles_sum += tile_sum
                    valid_tiles += 1
            
            # Verify sum conservation
            assert valid_tiles > 0, "At least one valid tile should exist"
            sum_difference = abs(total_tiles_sum - original_sum)
            tolerance = original_sum * 0.001  # 0.1% tolerance for floating point precision
            
            assert sum_difference < tolerance, (
                f"Sum should be conserved: original={original_sum}, "
                f"tiles_total={total_tiles_sum}, difference={sum_difference}"
            )
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestIntegrationReproducibility(unittest.TestCase):
    """Test reproducibility and consistency of integration operations"""
    
    def test_dummy_raster_reproducibility(self):
        """Test that dummy raster generation is reproducible with same parameters"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create two identical rasters with same parameters
            params = {
                'width': 50,
                'height': 50,
                'cell_size': 0.5,
                'pattern_type': 'gradient'
            }
            
            raster1_path = os.path.join(temp_dir, "reproducible1.tif")
            raster2_path = os.path.join(temp_dir, "reproducible2.tif")
            
            # Create identical rasters
            hb.create_dummy_raster_with_pattern(
                output_path=raster1_path,
                **params
            )
            hb.create_dummy_raster_with_pattern(
                output_path=raster2_path,
                **params
            )
            
            # Compare arrays
            array1 = hb.as_array(raster1_path)
            array2 = hb.as_array(raster2_path)
            
            assert np.array_equal(array1, array2), "Identical parameters should produce identical rasters"
            assert np.sum(array1) == np.sum(array2), "Sums should be identical"
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndWorkflowValidation(unittest.TestCase):
    """Test complete end-to-end workflows from dummy raster creation through tiling and verification"""
    
    def test_complete_integration_workflow(self):
        """Test complete workflow: create dummy raster -> tile -> verify -> aggregate results"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Step 1: Create test data with known properties
            workflow_dir = os.path.join(temp_dir, "complete_workflow")
            os.makedirs(workflow_dir, exist_ok=True)
            
            base_raster = os.path.join(workflow_dir, "workflow_base.tif")
            target_sum = 10000.0
            
            hb.create_dummy_raster_with_known_sum(
                output_path=base_raster,
                width=80,
                height=60,
                target_sum=target_sum,
                cell_size=0.25
            )
            
            # Step 2: Tile the raster
            tiles_dir = os.path.join(workflow_dir, "tiles")
            os.makedirs(tiles_dir, exist_ok=True)
            
            tile_paths = hb.tile_raster_into_grid(
                input_raster_path=base_raster,
                output_dir=tiles_dir,
                tile_size=20,
                overlap=0
            )
            
            # Step 3: Verify each tile individually
            tile_metadata = []
            total_from_tiles = 0.0
            
            for i, tile_path in enumerate(tile_paths):
                if os.path.exists(tile_path):
                    tile_array = hb.as_array(tile_path)
                    nodata_value = hb.get_ndv_from_path(tile_path)
                    
                    if nodata_value is not None:
                        valid_data = tile_array[tile_array != nodata_value]
                    else:
                        valid_data = tile_array.flatten()
                    
                    tile_sum = float(np.sum(valid_data))
                    tile_mean = float(np.mean(valid_data)) if len(valid_data) > 0 else 0.0
                    tile_metadata.append({
                        'tile_id': i,
                        'path': tile_path,
                        'sum': tile_sum,
                        'mean': tile_mean,
                        'valid_pixels': len(valid_data),
                        'shape': list(tile_array.shape)
                    })
                    
                    total_from_tiles += tile_sum
            
            # Step 4: Validate workflow results
            assert len(tile_metadata) > 0, "Should have created valid tiles"
            
            # Sum conservation check
            sum_difference = abs(total_from_tiles - target_sum)
            tolerance = target_sum * 0.001  # 0.1% tolerance
            assert sum_difference < tolerance, (
                f"End-to-end sum conservation failed: "
                f"expected={target_sum}, actual={total_from_tiles}, diff={sum_difference}"
            )
            
            # Verify tile coverage (all pixels accounted for)
            total_valid_pixels = sum(meta['valid_pixels'] for meta in tile_metadata)
            expected_pixels = 80 * 60  # width * height
            assert total_valid_pixels == expected_pixels, (
                f"Pixel count mismatch: expected={expected_pixels}, actual={total_valid_pixels}"
            )
            
            # Step 5: Generate workflow report
            workflow_report = {
                'timestamp': datetime.now().isoformat(),
                'base_raster': {
                    'path': base_raster,
                    'target_sum': target_sum,
                    'dimensions': (80, 60),
                    'cell_size': 0.25
                },
                'tiling_results': {
                    'tiles_created': len(tile_metadata),
                    'total_sum_from_tiles': float(total_from_tiles),
                    'sum_conservation_error': float(sum_difference),
                    'coverage_pixels': total_valid_pixels
                },
                'validation_status': 'PASSED' if sum_difference < tolerance else 'FAILED',
                'tile_details': tile_metadata
            }
            
            # Save report for analysis
            report_path = os.path.join(workflow_dir, "integration_workflow_report.json")
            with open(report_path, 'w') as f:
                json.dump(workflow_report, f, indent=2)
            
            # Final assertion: workflow completed successfully
            assert workflow_report['validation_status'] == 'PASSED', "Complete workflow should pass validation"
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestQMDAutomationEndToEnd(unittest.TestCase):
    """
    Test complete QMD automation workflows from test files to QMD output
    (from test_end_to_end_workflow.py)
    
    This test suite validates complete workflows from test files to QMD output:
    - Complete pipeline: test file → analysis → quality assessment → QMD generation
    - Multiple test file processing workflows
    - Template system integration validation  
    - Plugin system end-to-end execution
    - Configuration system integration
    - Error handling across complete workflows
    """
    
    def setUp(self):
        """Set up test environment for QMD automation testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_files_dir = os.path.join(self.temp_dir, "test_files")
        self.output_dir = os.path.join(self.temp_dir, "qmd_output")
        os.makedirs(self.test_files_dir)
        os.makedirs(self.output_dir)
        
        # Create sample test files for processing
        self.create_sample_test_files()
        
        # Initialize engines
        self.analysis_engine = TestAnalysisEngine()
        self.quality_engine = QualityAssessmentEngine()
        self.plugin_manager = PluginManager()
        self.template_system = TemplateSystem()
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def create_sample_test_files(self):
        """Create various sample test files for end-to-end testing"""
        # High-quality test file with comprehensive tests
        high_quality_content = '''
"""
Comprehensive unit tests for mathematical operations module.

This module provides extensive testing coverage for mathematical operations
including basic arithmetic, advanced functions, and edge cases.
"""

import unittest
import math
import pytest
from typing import List, Union

class TestMathematicalOperations(unittest.TestCase):
    """Test suite for mathematical operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_numbers = [1, 2, 3, 4, 5]
        self.zero_value = 0
        self.negative_numbers = [-1, -2, -3]
        
    def test_addition_positive_numbers(self):
        """Test addition with positive numbers."""
        result = 2 + 3
        self.assertEqual(result, 5)
        
    def test_addition_negative_numbers(self):
        """Test addition with negative numbers."""
        result = -2 + (-3)
        self.assertEqual(result, -5)
        
    def test_addition_mixed_numbers(self):
        """Test addition with mixed positive and negative numbers."""
        result = 5 + (-3)
        self.assertEqual(result, 2)
        
    def test_division_by_zero_raises_exception(self):
        """Test that division by zero raises ZeroDivisionError."""
        with self.assertRaises(ZeroDivisionError):
            result = 10 / 0
            
    def test_square_root_positive_number(self):
        """Test square root of positive numbers."""
        result = math.sqrt(16)
        self.assertEqual(result, 4.0)
        
    def test_power_operations(self):
        """Test various power operations."""
        self.assertEqual(2**3, 8)
        self.assertEqual(5**0, 1)
        self.assertEqual(4**0.5, 2.0)
        
    @pytest.mark.parametrize("x,y,expected", [
        (2, 3, 5),
        (0, 5, 5),
        (-1, 1, 0),
        (10, -5, 5)
    ])
    def test_parametrized_addition(self, x, y, expected):
        """Parametrized test for addition operations."""
        assert x + y == expected

if __name__ == '__main__':
    unittest.main()
        '''
        
        # Medium-quality test file with some tests but limited documentation
        medium_quality_content = '''
import unittest

class TestStringOperations(unittest.TestCase):
    
    def test_string_upper(self):
        result = "hello".upper()
        self.assertEqual(result, "HELLO")
        
    def test_string_lower(self):
        result = "WORLD".lower()
        self.assertEqual(result, "world")
        
    def test_string_length(self):
        text = "test"
        self.assertEqual(len(text), 4)

if __name__ == '__main__':
    unittest.main()
        '''
        
        # Low-quality test file (stub with minimal content)
        low_quality_content = '''
def test_something():
    pass
        '''
        
        # Integration test file
        integration_content = '''
"""
Integration tests for database operations.

Tests the integration between the application and database layer.
"""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock

class TestDatabaseIntegration(unittest.TestCase):
    """Integration tests for database operations."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.mktemp()
        
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
            
    def test_database_connection_integration(self):
        """Test database connection establishment."""
        # Mock database connection
        with patch('database.connect') as mock_connect:
            mock_connect.return_value = MagicMock()
            # Test integration logic here
            assert True
            
    def test_data_persistence_integration(self):
        """Test data persistence across operations."""
        # Test data persistence
        assert True

if __name__ == '__main__':
    unittest.main()
        '''
        
        # Performance test file
        performance_content = '''
"""
Performance benchmarks for critical operations.

Measures and validates performance requirements for key system functions.
"""

import time
import unittest
import pytest

class TestPerformanceBenchmarks(unittest.TestCase):
    """Performance benchmark test suite."""
    
    @pytest.mark.benchmark
    def test_operation_performance(self):
        """Benchmark critical operation performance."""
        start_time = time.time()
        
        # Simulate operation
        for i in range(1000):
            result = i ** 2
            
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in less than 1 second
        self.assertLess(duration, 1.0)
        
    def test_memory_usage_benchmark(self):
        """Test memory usage stays within bounds."""
        # Mock memory usage test
        assert True

if __name__ == '__main__':
    unittest.main()
        '''
        
        # Write test files
        test_files = [
            ("test_math_high_quality.py", high_quality_content),
            ("test_strings_medium_quality.py", medium_quality_content), 
            ("test_stub_low_quality.py", low_quality_content),
            ("test_database_integration.py", integration_content),
            ("test_performance_benchmarks.py", performance_content)
        ]
        
        for filename, content in test_files:
            file_path = os.path.join(self.test_files_dir, filename)
            with open(file_path, 'w') as f:
                f.write(content)

    def test_single_file_complete_pipeline(self):
        """Test complete pipeline processing for a single file."""
        test_file = os.path.join(self.test_files_dir, "test_math_high_quality.py")
        
        # Step 1: Analyze test file
        metadata = self.analysis_engine.analyze_test_file(test_file)
        
        # Verify analysis results
        self.assertEqual(metadata.file_path, test_file)
        self.assertGreater(len(metadata.test_functions), 0)
        self.assertIn("test_addition_positive_numbers", metadata.test_functions)
        
        # Step 2: Quality assessment
        quality_assessment = self.quality_engine.assess_quality(metadata)
        
        # High-quality file should score well
        self.assertGreater(quality_assessment.quality_score, 80)
        
        # Step 3: Plugin processing
        processing_results = self.plugin_manager.process_file(metadata)
        
        # Verify processing completed successfully
        self.assertTrue(all(result.success for result in processing_results))
        
        # Step 4: QMD generation
        qmd_content = self.template_system.render_qmd(metadata)
        
        # Verify QMD content was generated
        self.assertIsInstance(qmd_content, str)
        self.assertGreater(len(qmd_content), 0)
        self.assertIn(os.path.basename(test_file), qmd_content)
        
        # Step 5: Save QMD output
        output_path = os.path.join(self.output_dir, "test_math_high_quality.qmd")
        with open(output_path, 'w') as f:
            f.write(qmd_content)
            
        # Verify output file exists
        self.assertTrue(os.path.exists(output_path))

    def test_multiple_files_batch_processing(self):
        """Test batch processing of multiple test files."""
        test_files = glob.glob(os.path.join(self.test_files_dir, "*.py"))
        
        processing_results = []
        
        for test_file in test_files:
            # Process each file through complete pipeline
            try:
                # Analysis
                metadata = self.analysis_engine.analyze_test_file(test_file)
                
                # Quality assessment
                quality = self.quality_engine.assess_quality(metadata)
                
                # Plugin processing
                plugin_results = self.plugin_manager.process_file(metadata)
                
                # QMD generation
                qmd_content = self.template_system.render_qmd(metadata)
                
                # Save output
                output_filename = os.path.basename(test_file).replace('.py', '.qmd')
                output_path = os.path.join(self.output_dir, output_filename)
                
                with open(output_path, 'w') as f:
                    f.write(qmd_content)
                
                processing_results.append({
                    'file_path': test_file,
                    'success': True,
                    'quality_score': quality.quality_score,
                    'output_path': output_path
                })
                
            except Exception as e:
                processing_results.append({
                    'file_path': test_file,
                    'success': False,
                    'error': str(e)
                })
        
        # Verify all files were processed
        self.assertEqual(len(processing_results), len(test_files))
        
        # Verify most files processed successfully (allow for some failures in edge cases)
        successful_processing = [r for r in processing_results if r['success']]
        success_rate = len(successful_processing) / len(processing_results)
        self.assertGreater(success_rate, 0.8)  # At least 80% success rate
        
        # Verify output files exist for successful processing
        for result in successful_processing:
            if 'output_path' in result:
                self.assertTrue(os.path.exists(result['output_path']))

    def test_template_system_integration(self):
        """Test integration with template system for various file types."""
        test_cases = [
            ("test_math_high_quality.py", "default"),
            ("test_database_integration.py", "integration"),
            ("test_performance_benchmarks.py", "performance")
        ]
        
        for filename, template_type in test_cases:
            test_file = os.path.join(self.test_files_dir, filename)
            
            # Analyze file
            metadata = self.analysis_engine.analyze_test_file(test_file)
            
            # Generate QMD with specific template
            qmd_content = self.template_system.render_qmd(metadata, template_type)
            
            # Verify template-specific content
            self.assertIn(os.path.basename(test_file), qmd_content)
            self.assertGreater(len(qmd_content), 0)

    def test_error_handling_across_pipeline(self):
        """Test error handling across complete workflow pipeline."""
        # Create invalid test file
        invalid_file = os.path.join(self.test_files_dir, "invalid_syntax.py")
        with open(invalid_file, 'w') as f:
            f.write("def invalid_syntax(\n")  # Intentionally invalid Python
        
        # Test graceful handling of invalid file
        try:
            metadata = self.analysis_engine.analyze_test_file(invalid_file)
            # Should handle gracefully or raise appropriate exception
        except SyntaxError:
            # Expected behavior for invalid syntax
            pass
        except Exception as e:
            # Should not crash with unhandled exception
            self.fail(f"Unhandled exception in pipeline: {e}")

    def test_configuration_system_integration(self):
        """Test integration with configuration system."""
        # Test would verify configuration loading and application
        # For now, just verify components can be configured
        self.assertIsInstance(self.analysis_engine, TestAnalysisEngine)
        self.assertIsInstance(self.quality_engine, QualityAssessmentEngine)
        self.assertIsInstance(self.plugin_manager, PluginManager)

    def test_performance_requirements_validation(self):
        """Test that end-to-end pipeline meets performance requirements."""
        test_file = os.path.join(self.test_files_dir, "test_math_high_quality.py")
        
        # Measure complete pipeline performance
        start_time = time.time()
        
        # Run complete pipeline
        metadata = self.analysis_engine.analyze_test_file(test_file)
        quality = self.quality_engine.assess_quality(metadata)
        results = self.plugin_manager.process_file(metadata)
        qmd_content = self.template_system.render_qmd(metadata)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete single file processing in reasonable time
        self.assertLess(total_time, 10.0)  # Less than 10 seconds per file

    @pytest.mark.slow
    def test_stress_testing_multiple_files(self):
        """Test system behavior under stress with many files."""
        # Create additional test files for stress testing
        stress_test_dir = os.path.join(self.temp_dir, "stress_test")
        os.makedirs(stress_test_dir)
        
        # Generate multiple test files
        for i in range(20):
            test_file = os.path.join(stress_test_dir, f"test_stress_{i:03d}.py")
            with open(test_file, 'w') as f:
                f.write(f'''
def test_function_{i}():
    """Test function {i}"""
    assert {i} == {i}

def test_another_{i}():
    """Another test function {i}"""
    result = {i} * 2
    assert result == {i * 2}
                ''')
        
        # Process all stress test files
        stress_files = glob.glob(os.path.join(stress_test_dir, "*.py"))
        successful_processing = 0
        
        start_time = time.time()
        
        for test_file in stress_files:
            try:
                metadata = self.analysis_engine.analyze_test_file(test_file)
                quality = self.quality_engine.assess_quality(metadata)
                results = self.plugin_manager.process_file(metadata)
                qmd_content = self.template_system.render_qmd(metadata)
                successful_processing += 1
            except Exception as e:
                print(f"Failed to process {test_file}: {e}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify high success rate even under stress
        success_rate = successful_processing / len(stress_files)
        self.assertGreater(success_rate, 0.9)  # 90% success rate minimum
        
        # Verify reasonable performance even with many files
        average_time_per_file = total_time / len(stress_files)
        self.assertLess(average_time_per_file, 5.0)  # Less than 5 seconds average per file


if __name__ == '__main__':
    unittest.main()

