# Unit Tests

Unit tests focus on testing individual functions and classes in isolation, ensuring that each component behaves correctly under various conditions.

## Overview

The unit test suite covers core hazelbean functionality including:

- **Path Resolution** - Testing file path handling and resolution logic
- **Array Framework** - Testing the ArrayFrame data structure and operations
- **Core Utilities** - Testing utility functions and helper methods
- **Data Structures** - Testing custom data types and containers
- **Geospatial Operations** - Testing fundamental geospatial processing functions

---

## Path Resolution Testing

Tests for file path handling, validation, and resolution across different operating systems.

**Key Test Cases Covered:**

- ✅ `test_file_in_current_directory()` - Resolves files in project root
- ✅ `test_file_in_intermediate_directory()` - Finds files in intermediate folders  
- ✅ `test_file_in_input_directory()` - Locates input data files
- ✅ `test_raster_file_resolution()` - Handles .tif/.tiff raster formats
- ✅ `test_vector_file_resolution()` - Processes .gpkg/.shp vector files
- ✅ `test_csv_file_resolution()` - Manages .csv data files
- ✅ `test_pyramid_data_resolution()` - Accesses pyramid datasets
- ✅ `test_none_input_handling()` - Gracefully handles None inputs
- ✅ `test_empty_string_input()` - Validates empty string behavior
- ✅ `test_invalid_characters_in_path()` - Rejects invalid path characters
- ✅ `test_google_cloud_bucket_integration()` - Cloud storage integration
- ✅ `test_bucket_name_assignment()` - Cloud bucket configuration

::: hazelbean_tests.unit.test_get_path

---

## Array Framework Testing  

Comprehensive tests for the ArrayFrame class, which provides enhanced array operations for geospatial data.

**Key Test Cases Covered:**

- ✅ `test_arrayframe_load_and_save()` - Load, process, and save geospatial arrays

??? note "🔧 Helper Methods (Click to expand)"
    
    These are setup and utility methods used by the test class:
    
    - `setUp()` - Hook method for setting up the test fixture before exercising it
    - `tearDown()` - Hook method for deconstructing the test fixture after testing it  
    - `delete_on_finish()` - Custom cleanup method for test data

::: hazelbean_tests.unit.test_arrayframe

---

## Core Utilities Testing

Tests for general utility functions used throughout the hazelbean library.

**Key Test Cases Covered:**

- ✅ `test_fn()` - Core utility function validation
- ✅ `test_parse_flex_to_python_object()` - Flexible object parsing

::: hazelbean_tests.unit.test_utils

---

## Operating System Functions Testing

Tests for OS-specific functionality and cross-platform compatibility.

::: hazelbean_tests.unit.test_os_funcs

---

## Data Structures Testing

Tests for custom data structures and containers used in hazelbean.

**Key Test Cases Covered:**

- ✅ `test_cls()` - Core data structure class functionality

::: hazelbean_tests.unit.test_data_structures

---

## Cloud Optimized GeoTIFF Testing

Tests for COG (Cloud Optimized GeoTIFF) functionality and optimization.

**Key Test Cases Covered:**

- ✅ `test_is_cog()` - Validate Cloud Optimized GeoTIFF format
- ✅ `test_make_path_cog()` - Convert raster to COG format  
- ✅ `test_write_random_cog()` - Generate test COG files
- ✅ `test_cog_validation_performance()` - COG validation speed benchmarks

::: hazelbean_tests.unit.test_cog

---

## Performance-Optimized Geotiff Testing

Tests for POG (Performance-Optimized Geotiff) processing and optimization.

::: hazelbean_tests.unit.test_pog

---

## Categorical Data Testing

Tests for handling categorical/classified raster data operations.

::: hazelbean_tests.unit.test_cat_ears

---

## Tile Iterator Testing

Tests for efficient iteration over large raster datasets using tiling strategies.

::: hazelbean_tests.unit.test_tile_iterator

---

## Running Unit Tests

To run the complete unit test suite:

```bash
# Activate the hazelbean environment
conda activate hazelbean_env

# Run all unit tests
pytest hazelbean_tests/unit/ -v

# Run specific test file
pytest hazelbean_tests/unit/test_get_path.py -v

# Run with coverage
pytest hazelbean_tests/unit/ --cov=hazelbean --cov-report=html
```

## Test Coverage

Unit tests aim for comprehensive coverage of:

- **Happy path scenarios** - Normal usage patterns
- **Edge cases** - Boundary conditions and unusual inputs  
- **Error conditions** - Invalid inputs and exception handling
- **Cross-platform compatibility** - Different operating systems
- **Performance characteristics** - Memory usage and execution time

## Related Test Categories

- **Integration Tests** → See how unit-tested components work together in [Integration Tests](integration.md)
- **Performance Tests** → Review performance implications in [Performance Tests](performance.md)
- **System Tests** → Validate complete system behavior in [System Tests](system.md)

## Quick Navigation

| Component | Test File | Primary Focus |
|-----------|-----------|---------------|
| Path Resolution | [test_get_path.py](unit.md#path-resolution-testing) | Cross-platform path handling |
| Array Operations | [test_arrayframe.py](unit.md#array-framework-testing) | Geospatial array processing |
| Core Utilities | [test_utils.py](unit.md#core-utilities-testing) | General helper functions |
| File I/O | [test_os_funcs.py](unit.md#operating-system-functions-testing) | OS-specific operations |
| Data Types | [test_data_structures.py](unit.md#data-structures-testing) | Custom containers |
| Raster Optimization | [test_cog.py](unit.md#cloud-optimized-geotiff-testing) | COG processing |
| Performance Optimization | [test_pog.py](unit.md#performance-optimized-geotiff-testing) | POG processing |
| Classification | [test_cat_ears.py](unit.md#categorical-data-testing) | Categorical operations |
| Tiling | [test_tile_iterator.py](unit.md#tile-iterator-testing) | Large dataset processing |
