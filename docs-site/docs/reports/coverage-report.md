# Code Coverage Report

**Overall Coverage:** 23.4% (4,771 of 20,422 lines)  
**Last Updated:** 2025-09-18 17:05:21

## Summary

**Coverage Trend:** ➡️ Stable  
**Quality Gate:** ❌ Below 60% threshold  
**Missing Lines:** 15,651

## Module Breakdown

| Module | Coverage | Lines Covered | Total Lines | Missing | Status |
|--------|----------|---------------|-------------|---------|---------|
| hazelbean/globals.py | 100.0% | 466 | 466 | 0 | ✅ Excellent |
| hazelbean/__init__.py | 66.7% | 18 | 27 | 9 | ⚠️ Fair |
| hazelbean/cog.py | 66.5% | 218 | 328 | 110 | ⚠️ Fair |
| hazelbean/__init__.py | 63.6% | 138 | 217 | 79 | ⚠️ Fair |
| hazelbean/integration_testing_utils.py | 62.8% | 115 | 183 | 68 | ⚠️ Fair |
| hazelbean/pog.py | 62.0% | 199 | 321 | 122 | ⚠️ Fair |
| hazelbean/json_helper.py | 58.3% | 28 | 48 | 20 | ❌ Poor Line Coverage |
| hazelbean/config.py | 56.1% | 128 | 228 | 100 | ❌ Poor Line Coverage |
| hazelbean/project_flow.py | 53.6% | 384 | 717 | 333 | ❌ Poor Line Coverage |
| hazelbean/geoprocessing_extension.py | 52.8% | 330 | 625 | 295 | ❌ Poor Line Coverage |
| hazelbean/arrayframe_functions.py | 50.0% | 59 | 118 | 59 | ❌ Poor Line Coverage |
| hazelbean/arrayframe.py | 43.7% | 121 | 277 | 156 | ❌ Poor Line Coverage |
| hazelbean/cat_ears.py | 40.9% | 38 | 93 | 55 | ❌ Poor Line Coverage |
| hazelbean/core.py | 35.1% | 79 | 225 | 146 | ❌ Poor Line Coverage |
| hazelbean/pyramids.py | 35.0% | 552 | 1579 | 1027 | ❌ Poor Line Coverage |
| hazelbean/utils.py | 26.9% | 279 | 1037 | 758 | ❌ Poor Line Coverage |
| hazelbean/spatial_utils.py | 23.8% | 744 | 3125 | 2381 | ❌ Poor Line Coverage |
| hazelbean/spatial_projection.py | 22.8% | 98 | 430 | 332 | ❌ Poor Line Coverage |
| hazelbean/cloud_utils.py | 19.6% | 38 | 194 | 156 | ❌ Poor Line Coverage |
| hazelbean/os_utils.py | 18.3% | 267 | 1462 | 1195 | ❌ Poor Line Coverage |
| hazelbean/vector.py | 15.7% | 8 | 51 | 43 | ❌ Poor Line Coverage |
| hazelbean/stats.py | 13.5% | 138 | 1021 | 883 | ❌ Poor Line Coverage |
| hazelbean/visualization.py | 12.1% | 106 | 874 | 768 | ❌ Poor Line Coverage |
| hazelbean/raster_vector_interface.py | 11.0% | 56 | 511 | 455 | ❌ Poor Line Coverage |
| hazelbean/file_io.py | 9.0% | 65 | 726 | 661 | ❌ Poor Line Coverage |
| hazelbean/geoprocessing.py | 7.7% | 72 | 937 | 865 | ❌ Poor Line Coverage |
| hazelbean/netcdf.py | 4.7% | 27 | 569 | 542 | ❌ Poor Line Coverage |
| hazelbean/parallel.py | 0.0% | 0 | 475 | 475 | ❌ Poor Line Coverage |
| hazelbean/slow_config.py | 0.0% | 0 | 6 | 6 | ❌ Poor Line Coverage |
| hazelbean/inputs.py | 0.0% | 0 | 886 | 886 | ❌ Poor Line Coverage |
| hazelbean/launcher.py | 0.0% | 0 | 59 | 59 | ❌ Poor Line Coverage |
| hazelbean/data_structures.py | 0.0% | 0 | 338 | 338 | ❌ Poor Line Coverage |
| hazelbean/validation.py | 0.0% | 0 | 54 | 54 | ❌ Poor Line Coverage |
| hazelbean/usage_logger.py | 0.0% | 0 | 36 | 36 | ❌ Poor Line Coverage |
| hazelbean/utils.py | 0.0% | 0 | 160 | 160 | ❌ Poor Line Coverage |
| hazelbean/usage.py | 0.0% | 0 | 115 | 115 | ❌ Poor Line Coverage |
| hazelbean/watershed_processing.py | 0.0% | 0 | 119 | 119 | ❌ Poor Line Coverage |
| hazelbean/arrayframe_numpy_functions.py | 0.0% | 0 | 63 | 63 | ❌ Poor Line Coverage |
| hazelbean/execution.py | 0.0% | 0 | 31 | 31 | ❌ Poor Line Coverage |
| hazelbean/model.py | 0.0% | 0 | 986 | 986 | ❌ Poor Line Coverage |
| hazelbean/cli.py | 0.0% | 0 | 157 | 157 | ❌ Poor Line Coverage |
| hazelbean/conventions.py | 0.0% | 0 | 125 | 125 | ❌ Poor Line Coverage |
| hazelbean/auto_ui.py | 0.0% | 0 | 67 | 67 | ❌ Poor Line Coverage |
| hazelbean/auto_ui_tg.py | 0.0% | 0 | 90 | 90 | ❌ Poor Line Coverage |
| hazelbean/__init__.py | 0.0% | 0 | 0 | 0 | ❌ Poor Line Coverage |
| hazelbean/datastack.py | 0.0% | 0 | 259 | 259 | ❌ Poor Line Coverage |
| hazelbean/compile_cython_functions.py | 0.0% | 0 | 7 | 7 | ❌ Poor Line Coverage |

## Coverage Analysis

> **Note:** Poor line coverage does not mean that the tests do not test example usage of the component, just that they do not execute every single line from that file. Many hazelbean modules contain extensive functionality where the tests focus on demonstrating proper usage patterns rather than exhaustive line-by-line execution.

### High Coverage Modules (≥90%)
- **hazelbean/globals.py**: 100.0% (466/466 lines)

### Fair Coverage Modules (60-89%)
- **hazelbean/__init__.py**: 66.7% (9 lines missing coverage)
- **hazelbean/cog.py**: 66.5% (110 lines missing coverage)
- **hazelbean/__init__.py**: 63.6% (79 lines missing coverage)
- **hazelbean/integration_testing_utils.py**: 62.8% (68 lines missing coverage)
- **hazelbean/pog.py**: 62.0% (122 lines missing coverage)

### With Low Coverage (<60%)
- **hazelbean/json_helper.py**: 58.3% (20 lines missing coverage)
- **hazelbean/config.py**: 56.1% (100 lines missing coverage)
- **hazelbean/project_flow.py**: 53.6% (333 lines missing coverage)
- **hazelbean/geoprocessing_extension.py**: 52.8% (295 lines missing coverage)
- **hazelbean/arrayframe_functions.py**: 50.0% (59 lines missing coverage)
- **hazelbean/arrayframe.py**: 43.7% (156 lines missing coverage)
- **hazelbean/cat_ears.py**: 40.9% (55 lines missing coverage)
- **hazelbean/core.py**: 35.1% (146 lines missing coverage)
- **hazelbean/pyramids.py**: 35.0% (1027 lines missing coverage)
- **hazelbean/utils.py**: 26.9% (758 lines missing coverage)
- **hazelbean/spatial_utils.py**: 23.8% (2381 lines missing coverage)
- **hazelbean/spatial_projection.py**: 22.8% (332 lines missing coverage)
- **hazelbean/cloud_utils.py**: 19.6% (156 lines missing coverage)
- **hazelbean/os_utils.py**: 18.3% (1195 lines missing coverage)
- **hazelbean/vector.py**: 15.7% (43 lines missing coverage)
- **hazelbean/stats.py**: 13.5% (883 lines missing coverage)
- **hazelbean/visualization.py**: 12.1% (768 lines missing coverage)
- **hazelbean/raster_vector_interface.py**: 11.0% (455 lines missing coverage)
- **hazelbean/file_io.py**: 9.0% (661 lines missing coverage)
- **hazelbean/geoprocessing.py**: 7.7% (865 lines missing coverage)
- **hazelbean/netcdf.py**: 4.7% (542 lines missing coverage)
- **hazelbean/parallel.py**: 0.0% (475 lines missing coverage)
- **hazelbean/slow_config.py**: 0.0% (6 lines missing coverage)
- **hazelbean/inputs.py**: 0.0% (886 lines missing coverage)
- **hazelbean/launcher.py**: 0.0% (59 lines missing coverage)
- **hazelbean/data_structures.py**: 0.0% (338 lines missing coverage)
- **hazelbean/validation.py**: 0.0% (54 lines missing coverage)
- **hazelbean/usage_logger.py**: 0.0% (36 lines missing coverage)
- **hazelbean/utils.py**: 0.0% (160 lines missing coverage)
- **hazelbean/usage.py**: 0.0% (115 lines missing coverage)
- **hazelbean/watershed_processing.py**: 0.0% (119 lines missing coverage)
- **hazelbean/arrayframe_numpy_functions.py**: 0.0% (63 lines missing coverage)
- **hazelbean/execution.py**: 0.0% (31 lines missing coverage)
- **hazelbean/model.py**: 0.0% (986 lines missing coverage)
- **hazelbean/cli.py**: 0.0% (157 lines missing coverage)
- **hazelbean/conventions.py**: 0.0% (125 lines missing coverage)
- **hazelbean/auto_ui.py**: 0.0% (67 lines missing coverage)
- **hazelbean/auto_ui_tg.py**: 0.0% (90 lines missing coverage)
- **hazelbean/__init__.py**: 0.0% (0 lines missing coverage)
- **hazelbean/datastack.py**: 0.0% (259 lines missing coverage)
- **hazelbean/compile_cython_functions.py**: 0.0% (7 lines missing coverage)

---

*This report is automatically generated from coverage.py data. To update, run `./tools/generate_reports.sh`*
