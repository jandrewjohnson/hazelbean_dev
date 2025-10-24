# Performance Tests

Performance testing organized by functions and workflows.

## Directory Structure

- `functions/` - Function-level benchmarks
- `workflows/` - Workflow-level benchmarks  
- `regression/` - Performance regression detection
- `baseline/` - Baseline management and storage
- `unit/` - Performance unit tests
- `benchmarks/` - General benchmark tests

## Running Tests

```bash
# Run all performance tests
pytest hazelbean_tests/performance/

# Run benchmark tests specifically
pytest hazelbean_tests/performance/ -m benchmark

# Run with performance markers
pytest hazelbean_tests/performance/ -m performance
```
