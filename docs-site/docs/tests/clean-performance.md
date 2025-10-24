# Performance Test Functions

> **Clean view of test functions only** | **Generated from 4 test files**

This page shows only the test functions without class setup/teardown methods.

## Benchmarks

- **Single Call Performance Local File** - Benchmark single get_path call for local file - Target: <0.1 seconds
- **Single Call Performance Nested File** - Benchmark single get_path call for nested file - Target: <0.1 seconds
- **Multiple Calls Performance** - Benchmark multiple sequential get_path calls - Target: <1.0 seconds for 100 calls
- **Missing File Resolution Performance** - Benchmark get_path performance for missing files - Target: <0.2 seconds
- **Setup** - Set up test fixtures
- **Array Operations Benchmark** - Simple array operations benchmark
- **File Io Benchmark** - Simple file I/O operations benchmark
- **Project Flow Creation Benchmark** - Benchmark ProjectFlow creation performance
- **Hazelbean Temp Benchmark** - Benchmark hazelbean temp file operations
- **Numpy Save Load Benchmark** - Benchmark numpy array save/load operations with hazelbean
- **Data Processing Workflow Benchmark** - Benchmark complete data processing workflow
- **Multi File Processing Benchmark** - Benchmark processing multiple files
- **Path Resolution Stress Test** - Stress test path resolution performance with many files

**Source:** `test_benchmarks.py`

## Functions

- **Get Path Function Overhead** - Benchmark just the get_path function call overhead
- **Get Path Cache Performance** - Benchmark get_path caching efficiency
- **Get Path Different Patterns** - Benchmark get_path with different file name patterns
- **Absolute Path Resolution** - Benchmark absolute path resolution performance
- **Relative Path Resolution** - Benchmark relative path resolution performance
- **Nonexistent Path Resolution** - Benchmark performance when resolving non-existent paths
- **Path Normalization Performance** - Benchmark path normalization and cleanup performance
- **Array Tiling Performance** - Benchmark array tiling operations
- **Small Array Tiling Performance** - Benchmark tiling performance for small arrays
- **Tile Reassembly Performance** - Benchmark tile reassembly performance
- **Memory Efficient Tiling** - Benchmark memory-efficient tiling operations

**Source:** `test_functions.py`

## Project Flow Scalability

- **Add Task Single Performance Baseline** - Establish baseline performance for single add_task() call
- **Add Task Moderate Load 100 Tasks** - Test add_task() performance with 100 tasks
- **Add Task High Load 500 Tasks** - Test add_task() performance with 500 tasks - may expose scalability limits
- **Add Task Extreme Load 1000 Tasks** - Test add_task() performance with 1000 tasks - extreme load may expose significant issues
- **Add Iterator Single Performance Baseline** - Establish baseline performance for single add_iterator() call
- **Add Iterator Moderate Load 50 Iterators** - Test add_iterator() performance with 50 iterators
- **Add Iterator High Load 200 Iterators** - Test add_iterator() performance with 200 iterators - may expose scalability limits
- **Iterator Parallel Flag Performance Comparison** - Compare performance characteristics of parallel vs serial iterator creation
- **Task Tree Memory Growth Pattern** - Analyze memory growth pattern during large task tree creation
- **Task Tree Cleanup Memory Recovery** - Test memory recovery after task tree cleanup
- **Mixed Task Iterator Memory Pattern** - Test memory usage with mixed task and iterator creation
- **Anytree Hierarchy Navigation Performance** - Test performance of anytree hierarchy navigation operations
- **Anytree Deep Hierarchy Performance** - Test anytree performance with deep nested hierarchies
- **Anytree Wide Hierarchy Performance** - Test anytree performance with wide hierarchies (many children)
- **Performance Baseline Establishment** - Establish performance baselines for regression detection
- **Regression Detection Simulation** - Simulate regression detection by comparing current performance to mock baseline
- **Complex Mixed Hierarchy Stress** - Stress test with complex mixed task and iterator hierarchies
- **Edge Case Massive Flat Hierarchy Stress** - Stress test edge case: massive flat hierarchy (many siblings)
- **Edge Case Rapid Creation Destruction Stress** - Stress test edge case: rapid creation and destruction cycles

**Source:** `test_project_flow_scalability.py`

## Workflows

- **Json Artifact Storage Performance** - Test JSON artifact storage and version control integration performance
- **Performance Baseline Validation Workflow** - Test performance baseline establishment and validation workflow
- **Ci Cd Performance Integration** - Test integration with CI/CD pipeline performance validation
- **Performance Metrics Aggregation** - Test aggregation of performance metrics from multiple sources
- **Performance Trend Analysis** - Test performance trend analysis workflow
- **Performance Report Generation** - Test performance report generation workflow
- **Cross Platform Performance Consistency** - Test performance consistency across different environments

**Source:** `test_workflows.py`


---

## Running Performance Tests

```bash
# Activate environment
conda activate hazelbean_env

# Run all performance tests
pytest hazelbean_tests/performance/ -v

# Run specific test file  
pytest hazelbean_tests/performance/test_example.py -v
```

## Complete Documentation

For full test context including class structure and setup methods, see the [complete performance test documentation](../tests/performance.md).

---

*Generated automatically from 4 test files (50 test functions)*
