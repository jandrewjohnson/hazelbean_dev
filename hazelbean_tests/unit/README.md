# Unit Tests

Component-based unit tests organized by hazelbean modules with flexible hierarchical structure support.

## 🏗️ Organization Patterns

**Mixed Structure Support:**
- **Flat organization**: Direct test files in component directories (e.g., `test_arrayframe.py`)
- **Nested organization**: Test files organized in subdirectories (e.g., `get_path/test_*.py`)
- **Documentation generation**: Both patterns supported with automatic collision prevention
- **Path resolution**: Automatic standardization of data paths and sys.path cleanup for QMD generation

**Examples:**
```
unit/
├── test_get_path.py              # Flat: generates get_path.qmd
├── get_path/                     # Nested: generates unique names
│   ├── test_error_handling.py    #   → get_path_error_handling.qmd
│   ├── test_file_formats.py      #   → get_path_file_formats.qmd
│   └── test_local_files.py       #   → get_path_local_files.qmd
├── test_arrayframe.py            # Flat: generates arrayframe.qmd
└── tile_iterator/                # Nested organization
    ├── test_basic_iteration.py   #   → tile_iterator_basic_iteration.qmd
    ├── test_parallel_processing.py #   → tile_iterator_parallel_processing.qmd
    └── test_spatial_logic.py     #   → tile_iterator_spatial_logic.qmd
```

## Directory Structure

Each subdirectory contains unit tests for a specific hazelbean component:

- `arrayframe/` - Array and DataFrame operations
- `calculation_core/` - Core calculation functions (Cython)
- `cat_ears/` - Cat ears functionality
- `cloud_utils/` - Cloud storage utilities
- `cog/` - Cloud Optimized GeoTIFF operations
- `config/` - Configuration management
- `core/` - Core utilities and functions
- `file_io/` - File input/output operations
- `geoprocessing/` - Geoprocessing functions
- `globals/` - Global variables and settings
- `os_utils/` - Operating system utilities
- `parallel/` - Parallel processing
- `pog/` - POG operations
- `project_flow/` - ProjectFlow and Task classes
- `pyramids/` - Pyramid/tiling operations
- `raster_vector_interface/` - Raster-vector operations
- `spatial_projection/` - Projection and coordinate systems
- `spatial_utils/` - Spatial utility functions
- `stats/` - Statistical functions
- `ui/` - User interface components
- `utils/` - General utilities
- `vector/` - Vector operations
- `visualization/` - Visualization tools

## Running Tests

```bash
# Run all unit tests
pytest hazelbean_tests/unit/

# Run tests for a specific component
pytest hazelbean_tests/unit/arrayframe/

# Run nested test suites
pytest hazelbean_tests/unit/get_path/          # All get_path nested tests
pytest hazelbean_tests/unit/tile_iterator/     # All tile_iterator nested tests

# Run with specific markers
pytest hazelbean_tests/unit/ -m unit
```

## 📚 Documentation Generation

The hierarchical structure is fully supported by the QMD automation system:

```bash
# Generate documentation for unit tests only
python tools/qmd_automation/cli.py generate --category unit

# Generate for specific nested modules
python tools/qmd_automation/cli.py generate --files unit/get_path/test_*.py

# Watch for changes during development
python tools/qmd_automation/cli.py generate --category unit --watch
```

**Documentation Output:**
- Flat files: `unit/test_get_path.py` → `get_path.qmd`
- Nested files: `unit/get_path/test_error_handling.py` → `get_path_error_handling.qmd`
- Enhanced breadcrumbs: `Unit Tests > Get Path > Error Handling`
- No naming conflicts: System automatically generates unique names

**Best Practices:**
- Use nested organization for related test groups (e.g., all get_path variations)
- Use flat organization for standalone component tests
- Both patterns can coexist in the same project
- Documentation generation handles mixed patterns seamlessly
