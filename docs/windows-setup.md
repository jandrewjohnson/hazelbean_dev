# Windows Setup Guide for Hazelbean

This guide provides detailed troubleshooting for Windows users installing hazelbean, with a focus on resolving Cython compilation issues.

## Table of Contents
1. [Quick Diagnosis](#quick-diagnosis)
2. [Common Issues](#common-issues)
3. [Solution 1: Conda Compiler Tools (Recommended)](#solution-1-conda-compiler-tools-recommended)
4. [Solution 2: Visual Studio Build Tools](#solution-2-visual-studio-build-tools)
5. [Verification](#verification)
6. [Troubleshooting Specific Errors](#troubleshooting-specific-errors)

## Quick Diagnosis

If you're seeing errors like:
- `ImportError: cannot import name 'cython_functions' from 'hazelbean.calculation_core'`
- `error: Microsoft Visual C++ 14.0 or greater is required`
- `Unable to find vcvarsall.bat`

**The issue:** Your system lacks the C/C++ compiler tools needed to build Cython extensions.

**Quick test:**
```bash
conda activate hazelbean_env
python scripts/verify_installation.py
```

This will diagnose the exact issue and provide targeted solutions.

## Common Issues

### Issue 1: ImportError - cython_functions not found

**Symptoms:**
```python
ImportError: cannot import name 'cython_functions' from 'hazelbean.calculation_core'
```

**Cause:** Cython extensions weren't compiled during installation.

**Solution:** See [Solution 1](#solution-1-conda-compiler-tools-recommended) or [Solution 2](#solution-2-visual-studio-build-tools) below.

### Issue 2: Microsoft Visual C++ 14.0 is required

**Symptoms:**
```
error: Microsoft Visual C++ 14.0 or greater is required. Get it with "Microsoft C++ Build Tools"
```

**Cause:** Windows doesn't have a C++ compiler installed by default.

**Solution:** Choose either the conda-based compiler (easier) or Visual Studio Build Tools (more robust).

### Issue 3: Compiler runs but Cython extensions still not found

**Symptoms:**
- `pip install -e .` completes without errors
- But `import hazelbean` still fails with ImportError

**Cause:** May be using wrong Python environment or files weren't installed correctly.

**Solution:**
```bash
# Verify you're in the correct environment
conda activate hazelbean_env
which python  # Should show path containing 'hazelbean_env'

# Force reinstall
pip install -e . --no-deps --force-reinstall
```

## Solution 1: Conda Compiler Tools (Recommended)

This is the easiest solution and doesn't require large downloads.

### Step 1: Install Conda Compiler Tools

```bash
# Activate your hazelbean environment
conda activate hazelbean_env

# Install the Windows compiler toolchain via conda
conda install -c conda-forge m2w64-toolchain libpython
```

**What this installs:**
- `m2w64-toolchain`: MinGW-w64 based compiler tools (GCC for Windows)
- `libpython`: Python development headers needed for extension building

### Step 2: Install Hazelbean

```bash
# Now install hazelbean (this will compile Cython extensions)
pip install -e . --no-deps --force-reinstall
```

**Expected output:**
You should see compilation messages like:
```
Building extension for hazelbean.calculation_core.cython_functions
...
Successfully installed hazelbean
```

### Step 3: Verify

```bash
python scripts/verify_installation.py
```

Should show:
```
✅ Hazelbean imported successfully
✅ Cython extensions compiled and loaded
✅ ProjectFlow initialization works
```

### Troubleshooting Solution 1

**If you see "command 'gcc' failed":**
```bash
# Try reinstalling the toolchain
conda remove m2w64-toolchain libpython
conda install -c conda-forge m2w64-toolchain libpython

# Clear any cached builds
pip cache purge
pip install -e . --no-deps --force-reinstall
```

## Solution 2: Visual Studio Build Tools

This is the "official" Microsoft solution and more robust, but requires a larger download (~3-7 GB).

### Step 1: Download Build Tools

1. Go to: https://visualstudio.microsoft.com/downloads/
2. Scroll down to "All Downloads"
3. Expand "Tools for Visual Studio"
4. Download "Build Tools for Visual Studio 2022" (or latest version)

### Step 2: Install Build Tools

1. Run the installer
2. When prompted for workloads, select:
   - ✅ **"Desktop development with C++"**
3. On the right side panel, ensure these are checked:
   - ✅ MSVC v143 - VS 2022 C++ x64/x86 build tools (or latest)
   - ✅ Windows 10 SDK (or Windows 11 SDK)
   - ✅ C++ CMake tools for Windows
4. Click "Install" (will take 15-30 minutes)

### Step 3: Restart Terminal

**Important:** Close and reopen your terminal/command prompt after installation so the build tools are in your PATH.

### Step 4: Install Hazelbean

```bash
# Activate environment
conda activate hazelbean_env

# Install hazelbean (will now use Visual Studio compiler)
pip install -e . --no-deps --force-reinstall
```

### Step 5: Verify

```bash
python scripts/verify_installation.py
```

### Troubleshooting Solution 2

**If Build Tools installed but still getting errors:**

1. **Verify installation:**
   ```bash
   # Check if cl.exe (MSVC compiler) is available
   where cl
   ```
   
   If not found, the build tools PATH may not be set correctly.

2. **Use Developer Command Prompt:**
   - Search for "Developer Command Prompt for VS 2022" in Start Menu
   - Run it
   - Activate conda environment: `conda activate hazelbean_env`
   - Try installation again: `pip install -e . --no-deps --force-reinstall`

## Verification

### Quick Verification

```bash
python -c "import hazelbean as hb; from hazelbean.calculation_core import cython_functions; print('✅ Success!')"
```

### Comprehensive Verification

```bash
python scripts/verify_installation.py
```

This checks:
- Python version compatibility
- Hazelbean import
- Cython extensions
- Key dependencies
- Basic functionality

### Manual Testing

```python
import hazelbean as hb
import tempfile

# Test ProjectFlow
with tempfile.TemporaryDirectory() as tmp:
    p = hb.ProjectFlow(tmp)
    print("✅ ProjectFlow works")
    
# Test Cython functions
from hazelbean.calculation_core import cython_functions
print("✅ Cython extensions loaded")
```

## Troubleshooting Specific Errors

### Error: "vcvarsall.bat not found"

**Full error:**
```
error: Unable to find vcvarsall.bat
```

**Solution:** Install Visual Studio Build Tools (Solution 2) or use conda compiler tools (Solution 1).

### Error: "Python.h: No such file or directory"

**Full error:**
```
fatal error C1083: Cannot open include file: 'Python.h': No such file or directory
```

**Solution:** Install `libpython`:
```bash
conda install -c conda-forge libpython
```

### Error: Compilation succeeds but import still fails

**Symptoms:**
- `pip install -e .` completes without errors
- Import still gives `ImportError`

**Diagnosis:**
```bash
# Check if .pyd files were created
cd hazelbean/calculation_core
dir *.pyd
```

**Solutions:**

1. **If no .pyd files found:**
   ```bash
   # Try python setup.py directly
   python setup.py build_ext --inplace
   ```

2. **If .pyd files exist but import fails:**
   ```bash
   # Check for DLL dependencies
   python -c "from hazelbean.calculation_core import cython_functions"
   ```
   
   If you see "DLL load failed", install Visual C++ Redistributables:
   - Download from: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist

### Error: pytest discovery fails with ImportError

**When running tests:**
```bash
python -m pytest hazelbean_tests/system/test_smoke.py -v
```

**If you see:**
```
ImportError while loading conftest: cannot import name 'cython_functions'
```

**Solution:** The Cython extensions aren't compiled. Follow Solution 1 or 2 above.

## Environment-Specific Notes

### Conda vs System Python

If you're using conda (recommended), always:
1. Activate the conda environment first: `conda activate hazelbean_env`
2. Use `pip install` within the conda environment
3. Never use `pip install --user` in conda environments

### 32-bit vs 64-bit

Hazelbean requires **64-bit Python**. Verify:
```python
import sys
print(f"Python is {sys.maxsize > 2**32 and '64-bit' or '32-bit'}")
```

If 32-bit, reinstall with 64-bit Python.

### Python Version

Hazelbean requires **Python 3.10+**. Check:
```bash
python --version
```

If older, create new environment:
```bash
mamba create -n hazelbean_env python=3.11
conda activate hazelbean_env
mamba env update -f environment.yml
```

## Still Having Issues?

If none of these solutions work:

1. **Collect diagnostic information:**
   ```bash
   python scripts/verify_installation.py > diagnosis.txt
   python --version >> diagnosis.txt
   conda list >> diagnosis.txt
   ```

2. **Check existing issues:** https://github.com/jandrewjohnson/hazelbean_dev/issues

3. **Open a new issue** with:
   - Your `diagnosis.txt` output
   - Error messages (full traceback)
   - Windows version
   - What you've tried

## Additional Resources

- **Cython Compilation on Windows:** https://github.com/cython/cython/wiki/CythonExtensionsOnWindows
- **Visual Studio Build Tools:** https://visualstudio.microsoft.com/downloads/
- **Conda Compiler Tools:** https://anaconda.org/conda-forge/m2w64-toolchain
- **Main Documentation:** [Getting Started Guide](getting-started.md)

