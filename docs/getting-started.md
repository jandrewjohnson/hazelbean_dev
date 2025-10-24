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

# 4. Verify installation
python -c "import hazelbean as hb; print('✅ Hazelbean ready!')"
```

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

**🌐 [Visit Full Documentation](https://jandrewjohnson.github.io/hazelbean_dev/)**

Your one-stop resource for: - **📖 [Educational Tutorials](https://jandrewjohnson.github.io/hazelbean_dev/educational/)** - Step-by-step learning path - **🧪 [Test Examples](https://jandrewjohnson.github.io/hazelbean_dev/tests/)** - 50+ real-world usage patterns\
- **📊 [Live Reports](https://jandrewjohnson.github.io/hazelbean_dev/reports/)** - Current system metrics - **🔍 [Search Functionality](https://jandrewjohnson.github.io/hazelbean_dev/)** - Find anything instantly

### Local Documentation (Development Setup)

``` bash
# Serve documentation locally
cd docs-site
mkdocs serve

# Visit: http://127.0.0.1:8000
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
├── docs-site/              # Complete documentation system
├── hazelbean_tests/        # Comprehensive test suite
└── environment.yml         # Environment configuration
```

## 🎓 Learning Path

### For New Users (Start Here)

1.  **Complete setup** using Option A above
2.  **Run all 5 tutorial examples** in `examples/` directory\
3.  **Explore [Educational Journey](https://jandrewjohnson.github.io/hazelbean_dev/educational/)** online
4.  **Try modifying examples** with your own data

### For Contributors

1.  **Complete development setup** (Option A)
2.  **Review [Test Documentation](https://jandrewjohnson.github.io/hazelbean_dev/tests/)** to understand patterns
3.  **Check [Live Reports](https://jandrewjohnson.github.io/hazelbean_dev/reports/)** for current system status
4.  **Read contribution guidelines** in the repository

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
# ├── inputs/      # Source data
# ├── intermediate/ # Processing files  
# └── outputs/     # Final results
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

**MkDocs Command Not Found**

``` bash
# Ensure you're in the hazelbean_env environment
conda activate hazelbean_env
cd docs-site
mkdocs serve
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

### Getting Help

1.  **Check [Documentation Site](https://jandrewjohnson.github.io/hazelbean_dev/)** for comprehensive guides
2.  **Review [Test Examples](https://jandrewjohnson.github.io/hazelbean_dev/tests/)** for usage patterns
3.  **Search documentation** using the site search functionality
4.  **Check [GitHub Issues](https://github.com/jandrewjohnson/hazelbean_dev/issues)** for known problems

## 🎉 Next Steps

**You're ready to start using Hazelbean!** Here are recommended next steps:

### Immediate Next Steps

-   **Complete all 5 tutorial examples** in sequence
-   **Explore the [Educational Journey](https://jandrewjohnson.github.io/hazelbean_dev/educational/)** online
-   **Try modifying examples** with your own data files

### Continued Learning

-   **Study [Test Documentation](https://jandrewjohnson.github.io/hazelbean_dev/tests/)** for advanced patterns
-   **Review ProjectFlow architecture** to understand task management
-   **Experiment with performance benchmarking** tools

### Contributing Back

-   **Report issues** or improvements on GitHub
-   **Share examples** of your own Hazelbean workflows\
-   **Contribute test cases** for functionality you use

------------------------------------------------------------------------

**Welcome to the Hazelbean community!** 🌿

*This getting-started guide reflects the current project structure as of the latest version. For the most up-to-date information, always refer to the [comprehensive documentation site](https://jandrewjohnson.github.io/hazelbean_dev/).*