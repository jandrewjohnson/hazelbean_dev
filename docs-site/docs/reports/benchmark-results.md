# Benchmark Results Summary

**Latest Run:** 2025-09-04 10:32  
**Status:** ✅ Pass (5 of 5 benchmarks)  
**Performance:** ➡️ Stable (±4.8%)

## Current Status

**Total Benchmarks:** 5  
**Performance Summary:** Avg: 2.29ms  
**Commit:** `20a2ada7` on `main`

## Performance Analysis

### Performance Range
- **Fastest Test:** `test_path_resolution_benchmark` - 0.013ms (±0.002ms)
- **Slowest Test:** `test_array_operations_benchmark` - 10.5ms (±0.646ms)

### Detailed Results

| Benchmark | Mean Time | Std Dev | Rounds | Performance |
|-----------|-----------|---------|---------|-------------|
| `test_path_resolution_benchmark` | 0.013ms | 0.002ms | 17279 | ⚡ Fast |
| `test_hazelbean_get_path_benchmark` | 0.132ms | 0.011ms | 6625 | ⚡ Fast |
| `test_file_io_benchmark` | 0.201ms | 0.255ms | 4424 | ⚡ Fast |
| `test_array_processing_benchmark` | 0.656ms | 0.065ms | 423 | ⚡ Fast |
| `test_array_operations_benchmark` | 10.5ms | 0.646ms | 91 | ⚠️ Moderate |

## Recent Benchmark History (Last 3 runs)

| Date | Status | Benchmarks | Performance | Notes |
|------|--------|------------|-------------|-------|
| 2025-09-04 10:32 | ✅ Pass | 5 tests | Avg: 2.29ms | Current run |
| 2025-09-04 10:22 | ✅ Pass | 5 tests | Avg: 2.45ms | Stable (±2.6%) |
| 2025-09-04 10:09 | ✅ Pass | 5 tests | Avg: 2.39ms | No comparison data |

## System Information

- **System:** Darwin 24.5.0
- **Processor:** Apple M1 Pro (arm architecture)
- **CPU Cores:** 10
- **Python:** 3.13.2

## Data Sources

View detailed benchmark data:
- **Latest Results:** `/metrics/benchmarks/benchmark_20250904_103226.json`
- **All Benchmarks:** `/metrics/benchmarks/` directory

---

*This report is automatically generated from `/metrics/benchmarks/` data. To update, run `./tools/generate_reports.sh`*
