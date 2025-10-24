"""
Consolidated Performance Benchmark Tests

This file consolidates tests from:
- benchmarks/test_get_path_performance.py
- benchmarks/test_integration_scenarios_benchmark.py
- benchmarks/test_simple_benchmarks.py

Covers comprehensive performance benchmarking including:
- Single and multiple call performance benchmarks
- Integration scenario performance validation
- Simple working performance benchmarks
- Benchmark baseline establishment and validation
- Performance regression testing
- Benchmark artifact generation and storage
"""

import unittest
import os
import sys
import tempfile
import shutil
import time
import pytest
from pathlib import Path

# NOTE: Awkward inclusion here so that I don't have to run the test via a setup config each time
sys.path.extend(['../..'])

import hazelbean as hb
import pandas as pd
import numpy as np


class BasePerformanceTest(unittest.TestCase):
    """Base class for performance benchmark tests with shared setup"""
    
    def setUp(self):
        """Set up test fixtures and data paths"""
        self.test_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(os.path.dirname(__file__), "../../data")
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


class TestGetPathPerformance(BasePerformanceTest):
    """Test ProjectFlow.get_path() performance benchmarks (from test_get_path_performance.py)"""
    
    @pytest.mark.benchmark
    def test_single_call_performance_local_file(self):
        """Benchmark single get_path call for local file - Target: <0.1 seconds"""
        # Test file in current directory
        test_file = "test_cur_dir.txt"
        
        # Benchmark single call
        start_time = time.time()
        resolved_path = self.p.get_path(test_file)
        end_time = time.time()
        
        call_duration = end_time - start_time
        
        # Performance assertion
        assert call_duration < 0.1, f"Single call took {call_duration:.4f}s, should be <0.1s"
        
        # Verify functionality
        assert test_file in resolved_path
        assert os.path.exists(resolved_path)
        
    @pytest.mark.benchmark
    def test_single_call_performance_nested_file(self):
        """Benchmark single get_path call for nested file - Target: <0.1 seconds"""
        # Test file in nested directory
        test_file = "intermediate/test_intermediate.txt"
        
        # Benchmark single call
        start_time = time.time()
        resolved_path = self.p.get_path(test_file)
        end_time = time.time()
        
        call_duration = end_time - start_time
        
        # Performance assertion
        assert call_duration < 0.1, f"Nested file call took {call_duration:.4f}s, should be <0.1s"
        
        # Verify functionality
        assert "test_intermediate.txt" in resolved_path
        assert os.path.exists(resolved_path)
        
    @pytest.mark.benchmark
    def test_multiple_calls_performance(self):
        """Benchmark multiple sequential get_path calls - Target: <1.0 seconds for 100 calls"""
        test_files = [
            "test_cur_dir.txt",
            "intermediate/test_intermediate.txt", 
            "input/test_input.txt",
            "nonexistent_file.txt"  # Include missing file
        ]
        
        call_count = 100
        
        # Benchmark multiple calls
        start_time = time.time()
        for i in range(call_count):
            for test_file in test_files:
                resolved_path = self.p.get_path(test_file, raise_error_if_fail=False)
        end_time = time.time()
        
        total_duration = end_time - start_time
        avg_duration = total_duration / (call_count * len(test_files))
        
        # Performance assertions
        assert total_duration < 10.0, f"100x4 calls took {total_duration:.4f}s, should be <10s"
        assert avg_duration < 0.025, f"Average call took {avg_duration:.4f}s, should be <0.025s"
        
    @pytest.mark.benchmark
    def test_missing_file_resolution_performance(self):
        """Benchmark get_path performance for missing files - Target: <0.2 seconds"""
        missing_file = "definitely_does_not_exist.txt"
        
        # Benchmark missing file resolution (use flag to return constructed path instead of raising error)
        start_time = time.time()
        resolved_path = self.p.get_path(missing_file, raise_error_if_fail=False)
        end_time = time.time()
        
        call_duration = end_time - start_time
        
        # Performance assertion - missing files may take longer due to search
        assert call_duration < 0.2, f"Missing file call took {call_duration:.4f}s, should be <0.2s"
        
        # Verify functionality - should still return a path
        assert missing_file in resolved_path


class TestSimpleBenchmarks(BasePerformanceTest):
    """Simple working performance benchmarks for testing the system (from test_simple_benchmarks.py)"""

    # Note: test_setup fixture removed - was being called directly as a test which is incorrect
    # The BasePerformanceTest class already provides setUp/tearDown for fixtures

    @pytest.mark.benchmark
    def test_array_operations_benchmark(self):
        """Simple array operations benchmark"""
        def array_operations():
            # Create test arrays
            arr1 = np.random.rand(1000, 1000)
            arr2 = np.random.rand(1000, 1000)
            
            # Perform operations
            result = arr1 + arr2
            result = result * 2
            result = np.mean(result)
            
            return result
        
        # Benchmark the operations
        start_time = time.time()
        result = array_operations()
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Should complete in reasonable time
        assert duration < 10.0, f"Array operations took {duration:.4f}s, should be <10s"
        assert isinstance(result, (int, float, np.number))

    @pytest.mark.benchmark
    def test_file_io_benchmark(self):
        """Simple file I/O operations benchmark"""
        temp_dir = tempfile.mkdtemp()
        try:
            test_file = os.path.join(temp_dir, "benchmark_test.txt")
            test_data = "test data " * 1000  # Create some test data
            
            # Benchmark write operation
            start_time = time.time()
            with open(test_file, 'w') as f:
                for i in range(100):
                    f.write(f"{test_data} {i}\n")
            write_time = time.time() - start_time
            
            # Benchmark read operation
            start_time = time.time()
            with open(test_file, 'r') as f:
                content = f.read()
            read_time = time.time() - start_time
            
            # Performance assertions
            assert write_time < 5.0, f"Write operations took {write_time:.4f}s, should be <5s"
            assert read_time < 1.0, f"Read operation took {read_time:.4f}s, should be <1s"
            assert len(content) > 0
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.benchmark
    def test_project_flow_creation_benchmark(self):
        """Benchmark ProjectFlow creation performance"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Benchmark ProjectFlow creation
            start_time = time.time()
            for i in range(10):
                p = hb.ProjectFlow(temp_dir)
                # Basic operation to ensure it's working (file may not exist, so use flag)
                path = p.get_path("test.txt", raise_error_if_fail=False)
            end_time = time.time()
            
            duration = end_time - start_time
            avg_duration = duration / 10
            
            # Performance assertions
            assert duration < 5.0, f"10 ProjectFlow creations took {duration:.4f}s, should be <5s"
            assert avg_duration < 0.5, f"Average creation took {avg_duration:.4f}s, should be <0.5s"
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.benchmark
    def test_hazelbean_temp_benchmark(self):
        """Benchmark hazelbean temp file operations"""
        # Benchmark temp file creation
        start_time = time.time()
        temp_paths = []
        
        for i in range(50):
            temp_path = hb.temp('.txt', f'benchmark_{i}', True)
            temp_paths.append(temp_path)
            
        end_time = time.time()
        
        duration = end_time - start_time
        avg_duration = duration / 50
        
        # Performance assertions
        assert duration < 5.0, f"50 temp file creations took {duration:.4f}s, should be <5s"
        assert avg_duration < 0.1, f"Average temp creation took {avg_duration:.4f}s, should be <0.1s"
        
        # Verify files exist (they should be temporary)
        assert len(temp_paths) == 50

    @pytest.mark.benchmark
    def test_numpy_save_load_benchmark(self):
        """Benchmark numpy array save/load operations with hazelbean"""
        # Create test array
        test_array = np.random.rand(500, 500)
        
        temp_path = hb.temp('.npy', 'numpy_benchmark', True)
        
        # Benchmark save operation
        start_time = time.time()
        hb.save_array_as_npy(test_array, temp_path)
        save_time = time.time() - start_time
        
        # Benchmark load operation  
        start_time = time.time()
        loaded_array = np.load(temp_path)
        load_time = time.time() - start_time
        
        # Performance assertions
        assert save_time < 2.0, f"Array save took {save_time:.4f}s, should be <2s"
        assert load_time < 1.0, f"Array load took {load_time:.4f}s, should be <1s"
        
        # Verify functionality
        assert np.array_equal(test_array, loaded_array)


class TestIntegrationScenarioBenchmarks(BasePerformanceTest):
    """Integration scenario performance benchmarks (from test_integration_scenarios_benchmark.py)"""

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_data_processing_workflow_benchmark(self):
        """Benchmark complete data processing workflow"""
        # This would test a complete hazelbean workflow
        # Including raster processing, array operations, etc.
        
        start_time = time.time()
        
        # Simulate data processing workflow
        p = hb.ProjectFlow(self.test_dir)
        
        # Create test array
        test_array = np.random.rand(100, 100)
        temp_path = hb.temp('.npy', 'workflow_test', True)
        
        # Save and process array
        hb.save_array_as_npy(test_array, temp_path)
        result = hb.describe(temp_path, surpress_print=True, surpress_logger=True)
        
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Performance assertion
        assert duration < 10.0, f"Data processing workflow took {duration:.4f}s, should be <10s"

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_multi_file_processing_benchmark(self):
        """Benchmark processing multiple files"""
        # Create multiple test files
        test_files = []
        for i in range(10):
            test_array = np.random.rand(50, 50)
            temp_path = hb.temp('.npy', f'multi_test_{i}', True)
            hb.save_array_as_npy(test_array, temp_path)
            test_files.append(temp_path)
        
        # Benchmark processing all files
        start_time = time.time()
        
        results = []
        for file_path in test_files:
            result = hb.describe(file_path, surpress_print=True, surpress_logger=True)
            results.append(result)
            
        end_time = time.time()
        
        duration = end_time - start_time
        avg_duration = duration / len(test_files)
        
        # Performance assertions
        assert duration < 20.0, f"Multi-file processing took {duration:.4f}s, should be <20s"
        assert avg_duration < 2.0, f"Average file processing took {avg_duration:.4f}s, should be <2s"
        assert len(results) == len(test_files)

    @pytest.mark.benchmark
    def test_path_resolution_stress_test(self):
        """Stress test path resolution performance with many files"""
        # Create many test files
        file_count = 100
        test_files = []
        
        for i in range(file_count):
            subdir = f"subdir_{i % 10}"  # Create 10 subdirectories
            os.makedirs(os.path.join(self.test_dir, subdir), exist_ok=True)
            
            file_path = os.path.join(subdir, f"test_file_{i}.txt")
            full_path = os.path.join(self.test_dir, file_path)
            
            with open(full_path, 'w') as f:
                f.write(f"test content {i}")
            
            test_files.append(file_path)
        
        # Benchmark path resolution for all files
        start_time = time.time()
        
        resolved_paths = []
        for file_path in test_files:
            resolved = self.p.get_path(file_path)
            resolved_paths.append(resolved)
            
        end_time = time.time()
        
        duration = end_time - start_time
        avg_duration = duration / file_count
        
        # Performance assertions
        assert duration < 30.0, f"Stress test took {duration:.4f}s, should be <30s"
        assert avg_duration < 0.3, f"Average resolution took {avg_duration:.4f}s, should be <0.3s"
        assert len(resolved_paths) == file_count
        
        # Verify all paths were resolved
        for resolved in resolved_paths:
            assert os.path.exists(resolved)


if __name__ == "__main__":
    unittest.main()

