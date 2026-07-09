# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Hazelbean is the shared base library for the earth-economy devstack. Shared
devstack guidance (reuse rule + ownership map + EE Spec conventions) is imported
here so it applies whenever you work in this repo:

@../../earth_economy_devstack/devstack_guidance.md

## Project Overview

Hazelbean is a geospatial processing library built on GDAL, NumPy, SciPy, Cython, PyGeoProcessing, and TaskGraph. It provides tools for sustainability science, ecosystem service assessment, and land-use modeling.

## Development Environment

**Required**: Always activate a conda environment with hazelbean's dependencies
before any development work. The environment name is contributor-specific — use
your own (see your user-level Claude config):
```bash
conda activate <your-env>
```

**Installation** (after environment activation):
```bash
pip install -e . --no-deps  # Builds Cython extensions
python scripts/verify_installation.py  # Verify installation
```

## Testing Commands

Always use `python -m pytest` (not direct `pytest`) to avoid taskgraph import issues.

```bash
# Smoke test - basic validation (~30 seconds)
python -m pytest hazelbean_tests/system/smoke/test_smoke.py -v

# Unit tests - core functionality
python -m pytest hazelbean_tests/unit/ -v

# Single test file
python -m pytest hazelbean_tests/unit/test_get_path.py -v

# Integration tests
python -m pytest hazelbean_tests/integration/ -v

# Performance benchmarks
python -m pytest hazelbean_tests/performance/benchmarks/test_simple_benchmarks.py -v --benchmark-only
```

## Architecture

### Core Pattern: ProjectFlow

The central abstraction is `hb.ProjectFlow` - a task-based project management system that:
- Defines a tree of tasks with dependencies
- Manages project directories and data paths
- Supports parallel execution where dependencies allow

Task functions follow this pattern:
```python
def example_task(p):
    """Task functions take ProjectFlow object 'p' and return it."""
    if p.run_this:  # Conditional execution block
        # Computationally intensive work here
        pass
    return p

# Register tasks
def add_all_tasks_to_task_tree(p):
    p.my_task = p.add_task(example_task)
```

### Module Organization

- `hazelbean/core.py` - Core utilities, imported first
- `hazelbean/project_flow.py` - ProjectFlow and Task classes
- `hazelbean/calculation_core/` - Cython-compiled performance functions
- `hazelbean/geoprocessing.py`, `geoprocessing_extension.py` - Raster operations
- `hazelbean/vector.py` - Vector data operations
- `hazelbean/arrayframe.py` - Array operations with spatial metadata
- `hazelbean/pyramids.py` - Multi-resolution raster handling
- `hazelbean/cog.py`, `pog.py` - Cloud-Optimized GeoTIFF support

### Import Convention

The library uses `import hazelbean as hb` convention. Most functions are available at the top level (e.g., `hb.timer()`, `hb.ProjectFlow()`).

### Test Organization

```
hazelbean_tests/
├── unit/          # Component tests (get_path, tile_iterator, etc.)
├── integration/   # Cross-component workflow tests
├── performance/   # Benchmarks with baseline management
├── system/        # Smoke tests, CLI, environment validation
└── tools/         # Test infrastructure and utilities
```

## Documentation

The documentation site uses Quarto and lives in `docs-site/quarto-docs/`.

```bash
# Preview docs (generates reports first, then starts live server)
./tools/preview_docs.sh

# Or manually:
python tools/generate_all_reports.py  # Generate reports first
cd docs-site/quarto-docs
quarto preview  # Live preview
quarto render   # Build static site
```

**Important**: Always run report generation before `quarto preview`. The pre-render hook was removed to prevent an infinite loop (file watcher detecting regenerated .qmd files).

## Known Issues

- Some tests use `@pytest.mark.xfail` for known hazelbean bugs - check `KNOWN_BUGS.md`
- GDAL environment variables are auto-configured based on conda environment path
- Cython extensions may need recompilation on different platforms

## Release Process

Releases are fully automated via GitHub Actions:
1. Create and push a git tag: `git tag -a "v1.7.7" -m "Release version 1.7.7" && git push origin "v1.7.7"`
2. Create a GitHub Release from the tag
3. GitHub Actions builds wheels and uploads to PyPI automatically
