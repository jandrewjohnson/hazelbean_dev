# Performance Tests

Performance tests measure execution time, memory usage, and computational efficiency to ensure hazelbean maintains acceptable performance characteristics.

## Overview

The performance test suite includes:

- **Benchmarking** - Standardized performance measurements
- **Function Performance** - Testing individual function execution times
- **Workflow Performance** - End-to-end processing performance
- **Baseline Management** - Tracking performance changes over time

---

## Performance Benchmarking

Comprehensive benchmarks that measure and track performance metrics across different operations.

### Core Performance Tests
::: hazelbean_tests.performance.test_benchmarks

---

## Function Performance Testing

Tests focused on measuring the performance of individual functions and methods.

### Individual Function Benchmarks
::: hazelbean_tests.performance.test_functions

---

## Workflow Performance Testing

Performance tests for complete workflows and processing pipelines.

### End-to-End Performance Tests
::: hazelbean_tests.performance.test_workflows

---

## Baseline Management Testing

Tests for the baseline management system that tracks performance changes over time.

### Baseline Management Tests
::: hazelbean_tests.performance.unit.test_baseline_manager

---

## Performance Baseline Manager

The baseline management system helps track and validate performance changes.

::: hazelbean_tests.performance.baseline_manager

---

## Running Performance Tests

To run the complete performance test suite:

```bash
# Activate the hazelbean environment
conda activate hazelbean_env

# Run all performance tests
pytest hazelbean_tests/performance/ -v

# Run performance tests with benchmarking
pytest hazelbean_tests/performance/ -v --benchmark-only

# Run with performance profiling
pytest hazelbean_tests/performance/ --profile

# Generate performance report
python scripts/run_performance_benchmarks.py
```

## Performance Metrics

Performance tests measure:

- **Execution Time** - How long operations take to complete
- **Memory Usage** - RAM consumption during processing
- **CPU Utilization** - Processor usage patterns
- **I/O Performance** - File read/write speeds
- **Scalability** - Performance with different data sizes

## Baseline Management

The performance testing system includes baseline management to:

- **Track Changes** - Monitor performance trends over time  
- **Detect Regressions** - Alert when performance degrades
- **Validate Optimizations** - Confirm performance improvements
- **Generate Reports** - Create performance analysis documents

## Performance Artifacts

Performance tests generate artifacts in:

- `hazelbean_tests/performance/artifacts/` - Benchmark results and reports
- `baselines/` - Performance baseline snapshots
- `metrics/` - Historical performance data

## Interpreting Results

When analyzing performance test results:

- **Compare to Baselines** - Look for significant deviations
- **Consider Data Size** - Performance scales with input data
- **Account for System Variation** - Results may vary between runs
- **Focus on Trends** - Long-term patterns are more meaningful than individual measurements

## Optimization Guidelines

Based on performance test results:

- **Identify Bottlenecks** - Find the slowest operations
- **Optimize Critical Paths** - Focus on frequently used functions
- **Consider Memory vs Speed** - Balance memory usage and execution time
- **Test with Real Data** - Use realistic datasets for accurate measurements

## Related Test Categories

- **Unit Tests** → Understand component performance in [Unit Tests](unit.md)
- **Integration Tests** → See workflow performance in [Integration Tests](integration.md)
- **System Tests** → Validate system-wide performance in [System Tests](system.md)

## Performance Test Matrix

| Test Focus | Test File | Metrics Tracked | Related Components |
|------------|-----------|-----------------|-------------------|
| Function Benchmarks | [test_functions.py](performance.md#function-performance-testing) | Execution time, memory usage | Unit-tested functions |
| Workflow Performance | [test_workflows.py](performance.md#workflow-performance-testing) | End-to-end timing | Integration workflows |
| Baseline Tracking | [test_benchmarks.py](performance.md#performance-benchmarking) | Historical trends | All components |
| Baseline Management | [test_baseline_manager.py](performance.md#baseline-management-testing) | System reliability | Performance infrastructure |

## Performance Baselines

Current performance targets:

- **Small datasets** (<100MB): <30 seconds processing time
- **Medium datasets** (100MB-1GB): <5 minutes processing time  
- **Large datasets** (>1GB): Tracked for optimization opportunities
- **Memory usage**: <2GB RAM for typical workflows
