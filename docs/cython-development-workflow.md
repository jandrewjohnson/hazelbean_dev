# Cython Development Workflow

## Overview

Hazelbean includes Cython extensions in `hazelbean/calculation_core/` for high-performance geospatial computations. This document explains when and how to recompile Cython code during development.

## Important: Runtime Recompilation is Disabled

The `recompile_cython` flag in `hazelbean/calculation_core/__init__.py` **must remain `False`** for:

- ✅ Production deployments
- ✅ CI/CD builds
- ✅ Wheel/sdist packaging
- ✅ Regular development (non-Cython changes)

**Why?** Runtime recompilation causes build failures because:
1. Wheel distributions don't include `.pyx` source files
2. Compilation at import time requires build dependencies not present in installed packages
3. It significantly slows down import times
4. It can cause file permission issues in some environments

## When to Recompile Cython

You only need to recompile Cython code when:

1. **Modifying `.pyx` files** - Changing Cython source code
2. **Adding new Cython extensions** - Creating new `.pyx` modules
3. **Updating Cython version** - After upgrading Cython compiler
4. **Debugging Cython code** - Testing changes to compiled extensions

## How to Recompile Cython

### Method 1: Using the Compilation Script (Recommended)

```bash
# From project root
conda activate hazelbean_env
python scripts/compile_cython_files.py
```

This script:
- Compiles all Cython extensions in `hazelbean/calculation_core/`
- Uses the correct Python executable from your conda environment
- Handles platform-specific compilation settings
- Provides verbose output for debugging

### Method 2: Using setup.py

```bash
# From project root
conda activate hazelbean_env
python setup.py build_ext --inplace
```

This method:
- Compiles extensions defined in `setup.py`
- Places compiled `.so` (Linux/Mac) or `.pyd` (Windows) files next to source
- Useful for testing before building wheels

### Method 3: Full Package Build

```bash
# From project root
conda activate hazelbean_env
python -m build --wheel
```

This method:
- Creates a complete wheel distribution
- Compiles all Cython extensions as part of build
- Recommended before releases or for testing installation

## Development Workflow

### Typical Development Cycle

1. **Make changes to `.pyx` file**
   ```bash
   # Edit hazelbean/calculation_core/cython_functions.pyx
   ```

2. **Recompile the extension**
   ```bash
   python scripts/compile_cython_files.py
   ```

3. **Test your changes**
   ```bash
   conda activate hazelbean_env
   python -c "import hazelbean as hb; # test your function"
   pytest hazelbean_tests/unit/test_cython_functions.py
   ```

4. **Commit both source and compiled files** (for local development)
   ```bash
   git add hazelbean/calculation_core/cython_functions.pyx
   git add hazelbean/calculation_core/cython_functions.c
   # Note: .so/.pyd files are in .gitignore
   ```

### Emergency: I Accidentally Set recompile_cython = True

If you accidentally committed `recompile_cython = True`:

1. **Immediately revert**:
   ```bash
   # Edit hazelbean/calculation_core/__init__.py
   # Set: recompile_cython = False
   git add hazelbean/calculation_core/__init__.py
   git commit -m "Fix: Disable runtime Cython recompilation"
   ```

2. **Why this matters**: CI builds will fail across all platforms if this flag is True

## Cython Files in the Project

Current Cython extensions:

- `hazelbean/calculation_core/cython_functions.pyx` - Core computational functions
- `hazelbean/calculation_core/aspect_ratio_array_functions.pyx` - Array aspect ratio calculations

Each `.pyx` file generates:
- `.c` file - Intermediate C code (committed to git)
- `.so` (Linux/Mac) or `.pyd` (Windows) - Compiled binary (not committed, in .gitignore)

## Platform-Specific Notes

### macOS
- Requires Xcode Command Line Tools: `xcode-select --install`
- Uses `clang` compiler
- Extensions have `.cpython-3XX-darwin.so` naming

### Linux
- Requires `gcc` and Python development headers
- Usually available in conda environment
- Extensions have `.cpython-3XX-x86_64-linux-gnu.so` naming

### Windows
- Requires Visual Studio Build Tools (see `calculation_core/__init__.py` comments)
- Extensions have `.pyd` naming
- May require specific VS version for Python compatibility

## Troubleshooting

### "ImportError: cannot import name 'cython_functions'"

**Cause**: Cython extension not compiled  
**Solution**: Run `python scripts/compile_cython_files.py`

### "error: Microsoft Visual C++ 14.0 is required" (Windows)

**Cause**: Missing C++ compiler  
**Solution**: Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2019)

### "Permission denied" during compilation

**Cause**: Trying to write to protected directory  
**Solution**: Ensure you have write permissions in the project directory

### CI builds failing with Cython errors

**Cause**: Likely `recompile_cython = True` in `__init__.py`  
**Solution**: Verify it's set to `False` and commit

## Best Practices

1. ✅ **Always test locally** after Cython changes before pushing
2. ✅ **Commit `.c` files** - Allows building without Cython installed
3. ✅ **Use conda/mamba** - Ensures consistent build environment
4. ✅ **Document Cython functions** - Helps others understand compiled code
5. ❌ **Never set `recompile_cython = True`** - Keep runtime compilation disabled

## References

- [Cython Documentation](https://cython.readthedocs.io/)
- [Python Packaging Guide - Binary Extensions](https://packaging.python.org/guides/packaging-binary-extensions/)
- [setuptools build_ext](https://setuptools.pypa.io/en/latest/userguide/ext_modules.html)

