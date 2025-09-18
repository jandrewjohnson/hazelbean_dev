# Integration Test Functions

> **Clean view of test functions only** | **Generated from 5 test files**

This page shows only the test functions without class setup/teardown methods.

## Data Processing

- **Resample To Match** - Test basic raster resampling to match reference raster
- **Misc Operations** - Test miscellaneous array and data structure operations
- **Describe** - Test describe functionality for arrays
- **Google Cloud Bucket Integration** - Test Google Cloud bucket integration (without actual cloud calls)
- **Bucket Name Assignment** - Test bucket name assignment
- **Cloud Path Fallback** - Test cloud path fallback when local file not found
- **Existing Cartographic Data Access** - Test access to existing cartographic data
- **Existing Pyramid Data Access** - Test access to existing pyramid data
- **Existing Crops Data Access** - Test access to existing crops data
- **Existing Data Access** - Test access to existing test data
- **Load Geotiff Chunk By Cr** - Test loading GeoTIFF chunks by column-row coordinates
- **Load Geotiff Chunk By Bb** - Test loading GeoTIFF chunks by bounding box
- **Add Rows Or Cols To Geotiff** - Test adding rows or columns to GeoTIFF
- **Fill To Match Extent** - Test filling raster to match extent
- **Fill To Match Extent Manual** - Test manual fill to match extent
- **Convert Ndv To Alpha Band** - Test converting no-data values to alpha band
- **Raster To Area Raster** - Check if TIFF files are valid Cloud-Optimized GeoTIFFs (COGs).
- **Raster Calculator Hb** - Test hazelbean raster calculator
- **Assert Gdal Paths In Same Projection** - Test assertion of GDAL paths in same projection
- **Zonal Statistics Faster** - Test fast zonal statistics implementation
- **Zonal Statistics Enumeration** - Test zonal statistics enumeration
- **Super Simplify** - Test vector super simplification
- **Resample To Cell Size** - Test resampling to specific cell size
- **Resample To Match** - Test resampling to match reference raster
- **Get Wkt From Epsg Code** - Test WKT generation from EPSG codes
- **Rank Array** - Test array ranking functionality
- **Create Vector From Raster Extents** - Test creating vector from raster extents
- **Read 1D Npy Chunk** - Test reading 1D numpy array chunks
- **Get Attribute Table Columns From Shapefile** - Test extracting attribute table columns from shapefiles
- **Extract Features In Shapefile By Attribute** - Test feature extraction by attribute
- **Get Bounding Box** - Test bounding box extraction from various data types
- **Reading Csvs** - Test auto downloading of files via get_path
- **Get Reclassification Dict From Df** - Test reclassification dictionary generation from DataFrame
- **Clipping Simple** - Test simple raster clipping operations
- **Reclassify Raster Hb** - Test raster reclassification with hazelbean
- **Reclassify Raster With Negatives Hb** - Test raster reclassification with negative values
- **Reclassify Raster Arrayframe** - Test raster reclassification with arrayframe

**Source:** `test_data_processing.py`

## End To End Workflow

- **Create Dummy Raster Basic** - Test basic dummy raster creation with known values
- **Create Dummy Raster With Pattern** - Test dummy raster creation with mathematical pattern
- **Create Dummy Raster With Known Sum** - Test dummy raster creation with predetermined sum for validation
- **Tile Dummy Raster Sum Conservation** - Test that tiling preserves total sum of values
- **Dummy Raster Reproducibility** - Test that dummy raster generation is reproducible with same parameters
- **Complete Integration Workflow** - Test complete workflow: create dummy raster -> tile -> verify -> aggregate results
- **Single File Complete Pipeline** - Test complete pipeline processing for a single file.
- **Multiple Files Batch Processing** - Test batch processing of multiple test files.
- **Template System Integration** - Test integration with template system for various file types.
- **Error Handling Across Pipeline** - Test error handling across complete workflow pipeline.
- **Configuration System Integration** - Test integration with configuration system.
- **Performance Requirements Validation** - Test that end-to-end pipeline meets performance requirements.
- **Stress Testing Multiple Files** - Test system behavior under stress with many files.

**Source:** `test_end_to_end_workflow.py`

## Parallel Processing

- **Basic Parallel Setup** - Test basic parallel processing setup
- **Pygeoprocessing Integration** - Test integration with pygeoprocessing library
- **Multiprocess Workflow** - Test multiprocess workflow execution
- **Resource Management** - Test resource management in parallel environments
- **Error Handling Parallel** - Test error handling in parallel processing contexts

**Source:** `test_parallel_processing.py`

## Project Flow

- **Projectflow** - Test basic ProjectFlow creation and task execution
- **Full Generation Still Works** - Test that full generation continues to work alongside incremental.
- **No Corruption Of Existing Docs** - Test that incremental updates don't corrupt existing documentation.
- **Fallback To Full Generation** - Test graceful fallback to full generation when incremental fails.

**Source:** `test_project_flow.py`

## Project Flow Task Management

- **Iterator With Child Tasks Hierarchy** - Test iterator as parent with multiple child tasks.
- **Task With Iterator Children Hierarchy** - Test task as parent with iterator children.
- **Complex Nested Mixed Hierarchy** - Test deep hierarchies with alternating task/iterator types.
- **Sibling Tasks And Iterators** - Test tasks and iterators as siblings in same hierarchy.
- **Task Names Defined Tracking Across Methods** - Test consistent task_names_defined tracking across both methods.
- **Project Flow Setattr Behavior With Mixed Methods** - Test ProjectFlow attribute assignment with mixed method usage.
- **Name Collision Handling Between Methods** - Test behavior when duplicate task names created across methods.
- **Attribute Cleanup Consistency** - Test that ProjectFlow attributes clean up properly across methods.
- **Logging Level Inheritance Consistency** - Test logging level inheritance works consistently between add_task and add_iterator.
- **Parameter Default Behavior Consistency** - Test that parameter defaults behave consistently across methods.
- **Override Patterns Across Methods** - Test parameter override behavior works similarly.
- **Project Level Settings Respect** - Test that both methods respect project-level configuration.
- **Anytree Hierarchy Navigation With Mixed Types** - Test anytree navigation works correctly with mixed task/iterator hierarchies.
- **Complex Object Graph Integrity** - Test that complex mixed hierarchies maintain object graph integrity.
- **Hierarchy Search And Filtering** - Test searching and filtering mixed hierarchies by type and other criteria.
- **Complex Hierarchy Memory Cleanup** - Test memory cleanup for complex mixed hierarchies.
- **Project Flow Isolation With Complex Hierarchies** - Test that complex hierarchies don't leak between ProjectFlow instances.
- **Error Condition Cleanup In Complex Hierarchies** - Test cleanup works even when hierarchy construction fails.
- **Reference Counting In Complex Object Graphs** - Test that complex object graphs clean up properly without circular references.
- **Task Execution Integration Workflow** - Test add_task() -> execute() workflow with real task execution.
- **Iterator Execution Integration Workflow** - Test add_iterator() -> execute() workflow with iterator scenarios.
- **Mixed Hierarchy Execution Workflow** - Test complex mixed task/iterator hierarchy execution.
- **Skip Existing Behavior In Execution Workflow** - Test skip_existing behavior with real file system operations.
- **Directory Creation And Management Workflow** - Test task directory creation and path resolution during execution.
- **Path Resolution During Execution Workflow** - Test get_path() integration with task execution.
- **Task** - No description available
- **Iterator** - No description available

**Source:** `test_project_flow_task_management.py`


---

## Running Integration Tests

```bash
# Activate environment
conda activate hazelbean_env

# Run all integration tests
pytest hazelbean_tests/integration/ -v

# Run specific test file  
pytest hazelbean_tests/integration/test_example.py -v
```

## Complete Documentation

For full test context including class structure and setup methods, see the [complete integration test documentation](../tests/integration.md).

---

*Generated automatically from 5 test files (86 test functions)*
