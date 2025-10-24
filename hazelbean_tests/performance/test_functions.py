"""
Consolidated Performance Function Tests

This file consolidates tests from:
- functions/test_get_path_benchmarks.py
- functions/test_path_resolution_benchmarks.py
- functions/test_tiling_benchmarks.py

Covers function-level performance testing including:
- Individual function performance benchmarks
- Path resolution algorithm performance
- Tiling operation performance benchmarks
- Function-specific regression testing
- Memory usage and efficiency testing
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
import numpy as np


class BaseFunctionPerformanceTest(unittest.TestCase):
    """Base class for function-level performance tests with shared setup"""
    
    def setUp(self):
        """Set up test fixtures and data paths"""
        self.test_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(os.path.dirname(__file__), "../../data")
        
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


class TestGetPathFunctionBenchmarks(BaseFunctionPerformanceTest):
    """Test get_path function-specific benchmarks (from test_get_path_benchmarks.py)"""
    
    @pytest.mark.benchmark
    def test_get_path_function_overhead(self):
        """Benchmark just the get_path function call overhead"""
        test_file = "test_cur_dir.txt"
        
        # Warm up
        for _ in range(5):
            self.p.get_path(test_file)
        
        # Benchmark pure function call
        iterations = 1000
        start_time = time.time()
        
        for _ in range(iterations):
            result = self.p.get_path(test_file)
        
        end_time = time.time()
        
        total_duration = end_time - start_time
        avg_duration = total_duration / iterations
        
        # Performance assertions
        assert total_duration < 5.0, f"1000 function calls took {total_duration:.4f}s, should be <5s"
        assert avg_duration < 0.005, f"Average function call took {avg_duration:.6f}s, should be <0.005s"
    
    @pytest.mark.benchmark
    def test_get_path_cache_performance(self):
        """Benchmark get_path caching efficiency"""
        test_file = "test_cur_dir.txt"
        
        # First call (no cache)
        start_time = time.time()
        result1 = self.p.get_path(test_file)
        first_call_time = time.time() - start_time
        
        # Subsequent calls (should use cache if implemented)
        cached_times = []
        for _ in range(100):
            start_time = time.time()
            result2 = self.p.get_path(test_file)
            cached_times.append(time.time() - start_time)
        
        avg_cached_time = sum(cached_times) / len(cached_times)
        
        # Verify results are consistent
        assert result1 == result2, "Cached results should be identical"
        
        # Performance assertion (cached calls should be faster, if caching is implemented)
        # If no caching, this test documents current performance
        assert avg_cached_time < 0.01, f"Average cached call took {avg_cached_time:.6f}s, should be <0.01s"
    
    @pytest.mark.benchmark
    def test_get_path_different_patterns(self):
        """Benchmark get_path with different file name patterns"""
        patterns = [
            "simple.txt",                    # Simple filename
            "intermediate/nested.txt",       # Nested path
            "deep/nested/path/file.txt",     # Deep nesting
            "file_with_long_name_and_numbers_12345.extension",  # Long filename
            "file-with-dashes.txt",          # Special characters
            "file_with_spaces.txt",          # Spaces (if supported)
            "UPPERCASE.TXT",                 # Uppercase
            "mixed_Case_File.TxT",          # Mixed case
        ]
        
        # Create test files for existing patterns
        for pattern in patterns:
            if "/" in pattern:
                dir_path = os.path.dirname(os.path.join(self.test_dir, pattern))
                os.makedirs(dir_path, exist_ok=True)
            
            full_path = os.path.join(self.test_dir, pattern)
            if not os.path.exists(full_path):
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write("test content")
        
        # Benchmark each pattern
        pattern_times = {}
        for pattern in patterns:
            start_time = time.time()
            for _ in range(100):  # Multiple calls per pattern
                result = self.p.get_path(pattern)
            end_time = time.time()
            
            avg_time = (end_time - start_time) / 100
            pattern_times[pattern] = avg_time
            
            # Individual performance assertion
            assert avg_time < 0.05, f"Pattern '{pattern}' took {avg_time:.6f}s avg, should be <0.05s"
        
        # Verify performance consistency across patterns
        max_time = max(pattern_times.values())
        min_time = min(pattern_times.values())
        time_variance = max_time - min_time
        
        # Performance shouldn't vary dramatically by pattern
        assert time_variance < 0.1, f"Performance variance {time_variance:.6f}s too high across patterns"


class TestPathResolutionBenchmarks(BaseFunctionPerformanceTest):
    """Test path resolution algorithm benchmarks (from test_path_resolution_benchmarks.py)"""
    
    @pytest.mark.benchmark
    def test_absolute_path_resolution(self):
        """Benchmark absolute path resolution performance"""
        # Create absolute path
        abs_path = os.path.abspath(os.path.join(self.test_dir, "test_cur_dir.txt"))
        
        # Benchmark absolute path resolution
        start_time = time.time()
        for _ in range(100):
            result = self.p.get_path(abs_path)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100
        
        # Performance assertion
        assert avg_time < 0.01, f"Absolute path resolution took {avg_time:.6f}s avg, should be <0.01s"
        
        # Verify result
        assert result == abs_path or abs_path in result
    
    @pytest.mark.benchmark
    def test_relative_path_resolution(self):
        """Benchmark relative path resolution performance"""
        rel_paths = [
            "test_cur_dir.txt",
            "intermediate/test_intermediate.txt",
            "../hazelbean_tests/performance/test_functions.py",  # Up and back down
            "./test_cur_dir.txt",  # Explicit current dir
        ]
        
        for rel_path in rel_paths:
            start_time = time.time()
            for _ in range(50):
                try:
                    result = self.p.get_path(rel_path)
                except:
                    # Some paths may not exist, that's OK for performance testing
                    pass
            end_time = time.time()
            
            avg_time = (end_time - start_time) / 50
            
            # Performance assertion
            assert avg_time < 0.02, f"Relative path '{rel_path}' took {avg_time:.6f}s avg, should be <0.02s"
    
    @pytest.mark.benchmark
    def test_nonexistent_path_resolution(self):
        """Benchmark performance when resolving non-existent paths"""
        nonexistent_paths = [
            "does_not_exist.txt",
            "missing/directory/file.txt",
            "very/deep/nested/missing/path/file.extension",
        ]
        
        for path in nonexistent_paths:
            start_time = time.time()
            for _ in range(50):
                result = self.p.get_path(path, raise_error_if_fail=False)  # Return constructed path
            end_time = time.time()
            
            avg_time = (end_time - start_time) / 50
            
            # Nonexistent paths may take longer, but should still be reasonable
            assert avg_time < 0.1, f"Nonexistent path '{path}' took {avg_time:.6f}s avg, should be <0.1s"
    
    @pytest.mark.benchmark
    def test_path_normalization_performance(self):
        """Benchmark path normalization and cleanup performance"""
        messy_paths = [
            "test_cur_dir.txt",
            "./test_cur_dir.txt",
            "intermediate/../test_cur_dir.txt",
            "intermediate/./test_intermediate.txt",
            "intermediate//test_intermediate.txt",  # Double slash
            "intermediate/subdir/../test_intermediate.txt",
        ]
        
        # Create the actual files where possible
        os.makedirs(os.path.join(self.test_dir, "intermediate", "subdir"), exist_ok=True)
        
        for messy_path in messy_paths:
            start_time = time.time()
            for _ in range(100):
                result = self.p.get_path(messy_path)
            end_time = time.time()
            
            avg_time = (end_time - start_time) / 100
            
            # Path normalization should be fast
            assert avg_time < 0.01, f"Path normalization '{messy_path}' took {avg_time:.6f}s avg, should be <0.01s"


class TestTilingBenchmarks(BaseFunctionPerformanceTest):
    """Test tiling operation benchmarks (from test_tiling_benchmarks.py)"""
    
    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_array_tiling_performance(self):
        """Benchmark array tiling operations"""
        # Create test array
        test_array = np.random.rand(1000, 1000)
        temp_path = hb.temp('.npy', 'tiling_test', True)
        hb.save_array_as_npy(test_array, temp_path)
        
        # Benchmark array tiling (if implemented)
        start_time = time.time()
        
        # Simulate tiling operation - breaking array into chunks
        tile_size = 100
        tiles = []
        for i in range(0, test_array.shape[0], tile_size):
            for j in range(0, test_array.shape[1], tile_size):
                tile = test_array[i:i+tile_size, j:j+tile_size]
                tiles.append(tile)
        
        end_time = time.time()
        
        duration = end_time - start_time
        tiles_per_second = len(tiles) / duration
        
        # Performance assertions
        assert duration < 5.0, f"Array tiling took {duration:.4f}s, should be <5s"
        assert tiles_per_second > 10, f"Tiling rate {tiles_per_second:.2f} tiles/s, should be >10/s"
        assert len(tiles) == 100  # 10x10 grid of tiles
    
    @pytest.mark.benchmark
    def test_small_array_tiling_performance(self):
        """Benchmark tiling performance for small arrays"""
        # Test with smaller arrays to measure overhead
        small_arrays = [
            (100, 100),
            (50, 50),
            (25, 25),
            (10, 10)
        ]
        
        for width, height in small_arrays:
            test_array = np.random.rand(width, height)
            
            start_time = time.time()
            
            # Tile into 5x5 chunks
            tile_size = max(5, min(width, height) // 2)
            tiles = []
            for i in range(0, width, tile_size):
                for j in range(0, height, tile_size):
                    tile = test_array[i:i+tile_size, j:j+tile_size]
                    tiles.append(tile)
            
            end_time = time.time()
            
            duration = end_time - start_time
            
            # Small arrays should tile very quickly
            assert duration < 0.1, f"Small array ({width}x{height}) tiling took {duration:.6f}s, should be <0.1s"
            assert len(tiles) > 0, "Should generate at least one tile"
    
    @pytest.mark.benchmark
    def test_tile_reassembly_performance(self):
        """Benchmark tile reassembly performance"""
        # Create original array
        original_array = np.random.rand(200, 200)
        
        # Break into tiles
        tile_size = 50
        tiles = []
        positions = []
        
        for i in range(0, original_array.shape[0], tile_size):
            for j in range(0, original_array.shape[1], tile_size):
                tile = original_array[i:i+tile_size, j:j+tile_size]
                tiles.append(tile)
                positions.append((i, j))
        
        # Benchmark reassembly
        start_time = time.time()
        
        # Reassemble tiles
        reassembled = np.zeros_like(original_array)
        for tile, (i, j) in zip(tiles, positions):
            end_i = min(i + tile_size, original_array.shape[0])
            end_j = min(j + tile_size, original_array.shape[1])
            reassembled[i:end_i, j:end_j] = tile
        
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Performance assertion
        assert duration < 1.0, f"Tile reassembly took {duration:.4f}s, should be <1s"
        
        # Verify correctness
        assert np.array_equal(original_array, reassembled), "Reassembled array should match original"
    
    @pytest.mark.benchmark
    def test_memory_efficient_tiling(self):
        """Benchmark memory-efficient tiling operations"""
        # Test tiling without loading entire array into memory at once
        
        # Create a larger "virtual" array through file operations
        temp_dir = tempfile.mkdtemp()
        try:
            # Create multiple small array files to simulate large dataset
            file_count = 20
            array_files = []
            
            for i in range(file_count):
                small_array = np.random.rand(50, 50)
                file_path = os.path.join(temp_dir, f"array_{i:02d}.npy")
                np.save(file_path, small_array)
                array_files.append(file_path)
            
            # Benchmark processing files individually (memory efficient)
            start_time = time.time()
            
            processed_count = 0
            for file_path in array_files:
                # Load, process, and immediately release
                array = np.load(file_path)
                # Simulate processing (tiling)
                tiles = [array[i:i+10, j:j+10] for i in range(0, 50, 10) for j in range(0, 50, 10)]
                processed_count += len(tiles)
                del array, tiles  # Explicit cleanup
            
            end_time = time.time()
            
            duration = end_time - start_time
            files_per_second = file_count / duration
            
            # Performance assertions
            assert duration < 10.0, f"Memory-efficient processing took {duration:.4f}s, should be <10s"
            assert files_per_second > 1, f"Processing rate {files_per_second:.2f} files/s, should be >1/s"
            assert processed_count > 0, "Should have processed some tiles"
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

