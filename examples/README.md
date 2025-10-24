# Hazelbean Educational Examples

> **Progressive tutorials for learning Hazelbean geospatial workflows**

This directory contains 5 focused tutorial examples that teach core Hazelbean workflows through practical, copy-pasteable code. Each example builds on the previous one and can be run independently.

## 📚 Tutorial Sequence

### Step 1: Project Setup (`step_1_project_setup.py`)
**Learning Time:** 5 minutes  
**Prerequisites:** Basic Python knowledge

Learn how to initialize a Hazelbean ProjectFlow for organized geospatial workflows. Understand automatic directory creation and data discovery hierarchy.

**Key concepts:**
- ProjectFlow initialization
- Directory management (`inputs/`, `intermediate/`, `outputs/`)
- Data discovery paths

### Step 2: Data Loading (`step_2_data_loading.py`)
**Learning Time:** 10 minutes  
**Prerequisites:** Completed step 1

Learn Hazelbean's intelligent file discovery system and basic raster loading operations.

**Key concepts:**
- `get_path()` for smart file location
- Raster information extraction
- Loading geospatial arrays
- Error handling for missing data

### Step 3: Basic Processing (`step_3_basic_processing.py`)
**Learning Time:** 15 minutes  
**Prerequisites:** Completed steps 1-2

Learn fundamental raster operations including transformations, resampling, and mathematical operations.

**Key concepts:**
- Raster resampling and warping
- Array-based mathematical operations
- Statistical calculations
- Synthetic data creation

### Step 4: Spatial Analysis (`step_4_analysis.py`)
**Learning Time:** 20 minutes  
**Prerequisites:** Completed steps 1-3

Learn advanced spatial analysis including multi-raster operations, spatial calculations, and pattern analysis.

**Key concepts:**
- Multi-raster combinations
- Zone-based statistics
- Neighborhood analysis
- Hot spot identification
- Spatial pattern detection

### Step 5: Export Results (`step_5_export_results.py`)
**Learning Time:** 15 minutes  
**Prerequisites:** Completed steps 1-4

Learn proper result organization, output formatting, and project documentation.

**Key concepts:**
- Organized output directory structure
- Metadata creation
- Analysis reporting
- Professional project organization

## 🚀 Quick Start

### Prerequisites
- Hazelbean installed in conda environment
- Basic Python programming knowledge

### Running the Examples

1. **Activate your conda environment:**
   ```bash
   conda activate hazelbean_env
   ```

2. **Navigate to examples directory:**
   ```bash
   cd examples
   ```

3. **Run each example in sequence:**
   ```bash
   python step_1_project_setup.py
   python step_2_data_loading.py
   python step_3_basic_processing.py
   python step_4_analysis.py
   python step_5_export_results.py
   ```

### Expected Output
Each example provides clear console output showing:
- ✓ Successful operations
- ✗ Missing data with graceful fallbacks
- 🎉 Completion messages with next steps

## 📁 Generated Files

After running all examples, you'll have:
```
hazelbean_tutorial/
├── inputs/           # Input data directory
├── intermediate/     # Processing files
│   └── analysis_summary.txt
└── outputs/          # Final results
    └── tutorial_analysis_[timestamp]/
        ├── rasters/  # Analysis outputs
        └── reports/  # Documentation
```

## 🎯 Learning Objectives

By completing these tutorials, you will understand:

- **Project Organization**: How to structure geospatial analysis projects
- **Data Management**: Intelligent file discovery and loading
- **Raster Processing**: Basic transformations and mathematical operations  
- **Spatial Analysis**: Multi-raster operations and pattern detection
- **Professional Workflow**: Result organization and documentation

## 🔧 Customization

These examples are designed to be modified for your own projects:

1. **Replace sample data** with your own geospatial files
2. **Modify processing steps** for your specific analysis needs
3. **Extend analysis functions** using additional Hazelbean capabilities
4. **Adapt output formats** for your reporting requirements

## 📖 Further Learning

- **Hazelbean Documentation**: `/docs/` directory
- **Test Examples**: `/hazelbean_tests/` for advanced usage patterns
- **Performance Demos**: `/examples/baseline_management_demos/` for benchmarking

## ❓ Troubleshooting

**Common issues:**
- **Import errors**: Ensure hazelbean conda environment is activated
- **Missing data**: Examples gracefully handle missing sample files with synthetic data
- **Path issues**: Examples use `get_path()` for cross-platform compatibility

**Need help?** These examples are self-contained and include error handling for common issues. Each step provides clear guidance for the next tutorial.

---

**Happy learning with Hazelbean! 🌿**

## 🔄 Generating Educational Tutorials

These example files are the source for auto-generated QMD tutorials that create a learning website.

### To Generate Web Tutorials:

```bash
# From project root:
python tools/education/generate.py

# Then render to HTML:
conda activate hazelbean_env
cd docs/educational
quarto render *.qmd
```

### To Generate Specific Steps Only:

```bash
# Generate only steps 1 and 3:
python tools/education/generate.py --steps step_1,step_3

# Preview what would be generated:
python tools/education/generate.py --dry-run
```

### Generated Output Location:
- **QMD files:** `docs/educational/*.qmd`
- **HTML files:** `docs/educational/*.html` (after rendering)
- **Index page:** `docs/educational/index.html` - Learning path overview

### Generator Tool Details:
- **Main script:** `tools/education/generate.py`
- **Configuration:** `tools/education/config.yaml`  
- **Templates:** `tools/education/templates/`
- **Documentation:** `tools/education/README.md`

**To modify tutorial content:** Edit the Python files in this directory, then regenerate.

---

*The Educational Content Generator (5 files, ~300 lines) replaces the complex 58-file QMD automation system with a simple tool focused specifically on educational content.*
