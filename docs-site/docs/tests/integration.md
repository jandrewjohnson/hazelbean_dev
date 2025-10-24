# Integration Tests

Integration tests validate that different components work together correctly, focusing on end-to-end workflows and component interactions.

## Overview

The integration test suite covers:

- **End-to-End Workflows** - Complete processing pipelines from data input to final output
- **Data Processing Pipelines** - Multi-step geospatial data processing workflows
- **Parallel Processing** - Testing concurrent operations and thread safety
- **Project Flow Integration** - Testing the ProjectFlow framework with real workflows

---

## End-to-End Workflow Testing

Comprehensive tests that validate complete processing workflows from start to finish.

**Key End-to-End Test Cases:**
- ✅ Complete geospatial processing workflows
- ✅ Data input through final output validation
- ✅ Multi-component integration testing

::: hazelbean_tests.integration.test_end_to_end_workflow

---

## Data Processing Pipeline Testing

Tests for multi-step data processing workflows that integrate multiple hazelbean components.

**Key Integration Test Cases Covered:**
- ✅ `test_reclassify_raster_hb()` - Raster value reclassification workflows
- ✅ `test_reclassify_raster_with_negatives_hb()` - Handle negative values in reclassification
- ✅ `test_reclassify_raster_arrayframe()` - ArrayFrame-based reclassification
- ✅ Raster resampling and alignment operations
- ✅ Multi-step geospatial processing pipelines
- ✅ Data format conversion and validation

::: hazelbean_tests.integration.test_data_processing

---

## ProjectFlow Integration Testing

Tests for the ProjectFlow framework, ensuring that project management and task execution work correctly together.

**Key ProjectFlow Integration Tests:**
- ✅ Project initialization and setup workflows
- ✅ Task dependency management and execution
- ✅ Multi-step project processing pipelines

<!-- TODO: Re-enable when upgrading to modern handler (see docs/plans/mkdocs-griffe-import-resolution-fix.md)
::: hazelbean_tests.integration.test_project_flow
-->

---

## Parallel Processing Integration Testing

Tests for concurrent operations, thread safety, and parallel processing workflows.

**Key Parallel Processing Tests:**
- ✅ Concurrent raster processing operations
- ✅ Thread safety validation for shared resources
- ✅ Parallel workflow performance testing

<!-- TODO: Re-enable when upgrading to modern handler (see docs/plans/mkdocs-griffe-import-resolution-fix.md)
::: hazelbean_tests.integration.test_parallel_processing
-->

---

## Running Integration Tests

To run the complete integration test suite:

```bash
# Activate the hazelbean environment
conda activate hazelbean_env

# Run all integration tests
pytest hazelbean_tests/integration/ -v

# Run specific integration test
pytest hazelbean_tests/integration/test_project_flow.py -v

# Run with detailed output
pytest hazelbean_tests/integration/ -v -s

# Run with timeout for long-running tests
pytest hazelbean_tests/integration/ --timeout=300
```

## Test Characteristics

Integration tests typically:

- **Take longer to run** - Process real data and complete workflows
- **Use realistic data** - Work with actual geospatial datasets
- **Test component interactions** - Verify that modules work together correctly
- **Validate workflows** - Ensure end-to-end processing produces expected results
- **Check resource usage** - Monitor memory and computational requirements

## Test Data

Integration tests use test data located in:

- `hazelbean_tests/data/` - Sample datasets for testing
- `hazelbean_tests/temp_test_data/` - Temporary files created during testing
- External data sources when testing real-world scenarios

## Troubleshooting

Common integration test issues:

- **Data availability** - Ensure test datasets are present
- **Environment setup** - Verify all dependencies are installed
- **Resource limits** - Some tests may require significant memory or processing time
- **Network access** - Some tests may download test data

## Related Test Categories

- **Unit Tests** → Understand individual components in [Unit Tests](unit.md)
- **Performance Tests** → Measure workflow efficiency in [Performance Tests](performance.md)
- **System Tests** → Validate complete system in [System Tests](system.md)

## Test Dependencies

Integration tests build upon unit tests:

| Integration Test | Related Unit Tests | Purpose |
|------------------|-------------------|---------|
| [test_project_flow.py](integration.md#projectflow-integration-testing) | test_utils.py, test_os_funcs.py | End-to-end project workflows |
| [test_data_processing.py](integration.md#data-processing-pipeline-testing) | test_arrayframe.py, test_cog.py | Multi-step data processing |
| [test_parallel_processing.py](integration.md#parallel-processing-integration-testing) | test_utils.py | Concurrent operations |
| [test_end_to_end_workflow.py](integration.md#end-to-end-workflow-testing) | Multiple unit modules | Complete workflows |
