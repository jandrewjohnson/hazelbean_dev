# Getting Started with Hazelbean

> **Complete setup guide for the Hazelbean geospatial processing library**

Welcome to Hazelbean! This guide will get you from zero to running geospatial analyses in about 15 minutes.

## 🎯 What You'll Accomplish

By the end of this guide, you'll have: - ✅ **Working Hazelbean environment** with all dependencies - ✅ **Running examples** demonstrating core workflows\
- ✅ **Access to comprehensive documentation** for continued learning - ✅ **Understanding of project structure** for your own work

## 📋 Prerequisites

-   **Python experience:** Basic familiarity with Python programming
-   **System requirements:** macOS, Windows, or Linux with conda/mamba
-   **Time needed:** \~15 minutes for complete setup

## 🚀 Step 1: Environment Setup (5 minutes)

### Option A: Complete Development Setup (Recommended)

**Best for:** Learning Hazelbean, contributing to the project, or accessing all features

``` bash
# 1. Clone the complete repository
git clone https://github.com/jandrewjohnson/hazelbean_dev.git
cd hazelbean_dev

# 2. Create environment from configuration file
mamba env create -f environment.yml

# 3. Activate the environment
mamba activate hazelbean_env

# 4. Install hazelbean package (compiles Cython extensions)
pip install -e . --no-deps

# 5. Verify installation (comprehensive check)
python scripts/verify_installation.py
```

**What happens in Step 4:**
- Compiles platform-specific Cython extensions (required for performance-critical operations)
- Installs hazelbean in editable mode for development
- The `--no-deps` flag prevents pip from reinstalling conda packages

**If Step 4 fails on Windows:** See [Cython Compilation Issues](#cython-compilation-issues-windows) below.

### Option B: Package Installation Only

**Best for:** Using Hazelbean in existing projects

``` bash
# Install core dependencies
mamba install -c conda-forge natcap.invest geopandas pygeoprocessing taskgraph cython

# Install Hazelbean via pip
pip install hazelbean

# Verify installation  
python -c "import hazelbean as hb; print('✅ Hazelbean ready!')"
```

## 🧪 Step 2: Run Your First Example (5 minutes)

Test your installation with hands-on examples:

``` bash
# Navigate to examples (Option A setup)
cd examples

# Run the first tutorial
python step_1_project_setup.py
```

**Expected output:**

```         
🚀 Starting Hazelbean Project Setup Tutorial
✅ ProjectFlow initialized successfully
✅ Directory structure created
🎉 Tutorial complete! Try step_2_data_loading.py next.
```

**If using Option B setup:** You can still run examples by creating the tutorial files manually or downloading them from the repository.

## 📚 Step 3: Explore Documentation (5 minutes)

### Comprehensive Documentation Site

Hazelbean's published documentation lives on the Earth-Economy Devstack site:

**🌐 [Visit Full Documentation](https://justinandrewjohnson.com/earth_economy_devstack/hazelbean.html)**

- **📖 [Learning Path](https://justinandrewjohnson.com/earth_economy_devstack/hazelbean_learning_path.html)** - step-by-step route through the library
- **🧪 [Tutorial Examples](https://justinandrewjohnson.com/earth_economy_devstack/hazelbean_tutorials.html)** - worked usage patterns
- **🔧 [Troubleshooting](https://justinandrewjohnson.com/earth_economy_devstack/hazelbean_troubleshooting.html)** - common setup and runtime problems
- **🔍 Search** - available from the search box on any page of the site

### Local Documentation (Development Setup)

The tutorial sources live in this repo under `docs/educational/`. Render them
with Quarto:

``` bash
quarto preview docs/educational
```

## 🗂️ Understanding Project Structure

After setup, you'll have access to:

```         
hazelbean_dev/
├── hazelbean/              # Core library source
├── examples/               # 5-step tutorial sequence  
│   ├── step_1_project_setup.py
│   ├── step_2_data_loading.py
│   ├── step_3_basic_processing.py
│   ├── step_4_analysis.py
│   └── step_5_export_results.py
├── docs/                   # Documentation sources (incl. educational/)
├── hazelbean_tests/        # Comprehensive test suite
└── environment.yml         # Environment configuration
```

## 🎓 Learning Path

### For New Users (Start Here)

1.  **Complete setup** using Option A above
2.  **Run all 5 tutorial examples** in `examples/` directory\
3.  **Explore the [Learning Path](https://justinandrewjohnson.com/earth_economy_devstack/hazelbean_learning_path.html)** online
4.  **Try modifying examples** with your own data

### For Contributors

1.  **Complete development setup** (Option A)
2.  **Review the test suite** in `hazelbean_tests/` to understand patterns
3.  **Read [How to Contribute](https://justinandrewjohnson.com/earth_economy_devstack/version_control.html)** for the branching and PR workflow

### For Power Users

1.  **Explore test examples** in `hazelbean_tests/` for advanced patterns
2.  **Review performance benchmarks** in `examples/baseline_management_demos/`
3.  **Understand ProjectFlow architecture** through test documentation

## 🛠️ Core Concepts

### ProjectFlow System

Hazelbean organizes work using **ProjectFlow** - an intelligent task management system:

``` python
import hazelbean as hb

# Initialize organized project
p = hb.ProjectFlow('my_analysis')

# Automatic directory structure:
# my_analysis/
# ├── input/      # Source data
# ├── intermediate/ # Processing files  
# └── output/     # Final results
```

### Intelligent Data Discovery

Find data across multiple locations automatically:

``` python
# Smart file location - checks multiple directories
raster_path = p.get_path('land_cover.tif')

# Works with local files, cloud storage, or data repositories
```

### Efficient Processing

Memory-efficient operations with performance tracking:

``` python
# Load and process raster data efficiently  
array = hb.arrayframe_to_array(raster_path)
result = hb.convolve_2d(array, kernel)
```

## ✅ Verification Checklist

Before proceeding, ensure you have:

-   [ ] **Environment activated** (`conda activate hazelbean_env`)
-   [ ] **Import working** (`import hazelbean as hb`)
-   [ ] **Examples running** (at least `step_1_project_setup.py`)
-   [ ] **Documentation accessible** (online or locally)

## 🔧 Troubleshooting

### Common Issues

**Import Error: "No module named 'hazelbean'"**

``` bash
# Ensure environment is activated
conda activate hazelbean_env

# Verify hazelbean is installed
pip list | grep hazelbean
```

**Quarto Command Not Found**

``` bash
# Ensure you're in the hazelbean_env environment
conda activate hazelbean_env
quarto --version
quarto preview docs/educational
```

**Examples Not Running**

``` bash
# Make sure you're in the examples directory
cd examples

# Check that files exist
ls step_*.py

# Verify environment
python -c "import hazelbean; print('OK')"
```

**Missing Sample Data** - Examples are designed to work with or without sample data - Synthetic data will be generated if real data is missing - This is normal and expected for first-time users

### Cython Compilation Issues (Windows)

**Symptoms:**
```
ImportError: cannot import name 'cython_functions' from 'hazelbean.calculation_core'
```
or
```
error: Microsoft Visual C++ 14.0 or greater is required
```

**Diagnosis:**
```bash
python scripts/verify_installation.py
```

This script will identify the exact issue and provide tailored solutions.

**Quick Fix (Recommended):**
```bash
conda activate hazelbean_env
conda install -c conda-forge m2w64-toolchain libpython
pip install -e . --no-deps --force-reinstall
```

**Alternative - Visual Studio Build Tools:**
1. Download from https://visualstudio.microsoft.com/downloads/
2. Select "Build Tools for Visual Studio 2022"
3. Check "Desktop development with C++"
4. After install: `pip install -e . --no-deps --force-reinstall`

**For comprehensive Windows troubleshooting, see:** [Windows Setup Guide](windows-setup.md)

**Mac/Linux Users:** Cython compilation typically works without additional setup since compilers are usually pre-installed.

### Getting Help

1.  **Check the [Documentation Site](https://justinandrewjohnson.com/earth_economy_devstack/hazelbean.html)** for comprehensive guides
2.  **Review the [Troubleshooting Guide](https://justinandrewjohnson.com/earth_economy_devstack/hazelbean_troubleshooting.html)** for common problems
3.  **Search documentation** using the site search functionality
4.  **Check [GitHub Issues](https://github.com/jandrewjohnson/hazelbean_dev/issues)** for known problems

## 🎉 Next Steps

**You're ready to start using Hazelbean!** Here are recommended next steps:

### Immediate Next Steps

-   **Complete all 5 tutorial examples** in sequence
-   **Explore the [Learning Path](https://justinandrewjohnson.com/earth_economy_devstack/hazelbean_learning_path.html)** online
-   **Try modifying examples** with your own data files

### Continued Learning

-   **Study the [Tutorial Examples](https://justinandrewjohnson.com/earth_economy_devstack/hazelbean_tutorials.html)** for advanced patterns
-   **Review ProjectFlow architecture** to understand task management
-   **Experiment with performance benchmarking** tools

### Contributing Back

-   **Report issues** or improvements on GitHub
-   **Share examples** of your own Hazelbean workflows\
-   **Contribute test cases** for functionality you use

------------------------------------------------------------------------

**Welcome to the Hazelbean community!** 🌿

*This getting-started guide reflects the current project structure as of the latest version. For the most up-to-date information, always refer to the [comprehensive documentation site](https://justinandrewjohnson.com/earth_economy_devstack/hazelbean.html).*