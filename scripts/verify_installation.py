#!/usr/bin/env python
"""
Verify hazelbean installation including Cython extensions.

This script checks that hazelbean and its Cython extensions are properly
installed and provides clear guidance if issues are detected.

Usage:
    python scripts/verify_installation.py
"""
import sys
import platform

def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")

def print_success(text):
    """Print success message."""
    print(f"✅ {text}")

def print_error(text):
    """Print error message."""
    print(f"❌ {text}")

def print_warning(text):
    """Print warning message."""
    print(f"⚠️  {text}")

def print_info(text):
    """Print info message."""
    print(f"ℹ️  {text}")

def check_python_version():
    """Check Python version compatibility."""
    print_header("Python Version Check")
    version = sys.version_info
    print_info(f"Python {version.major}.{version.minor}.{version.micro}")
    
    if version >= (3, 10):
        print_success("Python version is compatible (3.10+)")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor} is not supported")
        print_info("Hazelbean requires Python 3.10 or later")
        return False

def check_hazelbean_import():
    """Check if hazelbean can be imported."""
    print_header("Hazelbean Import Check")
    
    try:
        import hazelbean as hb
        print_success("Hazelbean imported successfully")
        
        # Get version if available
        if hasattr(hb, '__version__'):
            print_info(f"Version: {hb.__version__}")
        
        return True, hb
    except ImportError as e:
        print_error("Cannot import hazelbean!")
        print_info(f"Error: {e}")
        print("\n📝 To install hazelbean:")
        print("   cd /path/to/hazelbean_dev")
        print("   conda activate hazelbean_env")
        print("   pip install -e . --no-deps")
        return False, None

def check_cython_extensions():
    """Check if Cython extensions are compiled and available."""
    print_header("Cython Extensions Check")
    
    try:
        from hazelbean.calculation_core import cython_functions
        print_success("Cython extensions compiled and loaded")
        
        # Try to access a function to verify it works
        if hasattr(cython_functions, 'add_op'):
            print_info("Core Cython functions available")
        
        return True
    except ImportError as e:
        print_error("Cython extensions not found!")
        print_info(f"Error: {e}")
        print("\n📝 The Cython extensions need to be compiled for your platform.")
        
        os_name = platform.system()
        if os_name == "Windows":
            print("\n🪟 Windows Setup Required:")
            print("   Option 1 (Easiest) - Use conda compiler:")
            print("     conda install -c conda-forge m2w64-toolchain libpython")
            print("     pip install -e . --no-deps --force-reinstall")
            print("\n   Option 2 - Install Visual Studio Build Tools:")
            print("     1. Download from: https://visualstudio.microsoft.com/downloads/")
            print("     2. Select 'Build Tools for Visual Studio 2022'")
            print("     3. Check 'Desktop development with C++'")
            print("     4. Run: pip install -e . --no-deps --force-reinstall")
        else:
            print(f"\n🔧 {os_name} Setup:")
            print("   Run from the hazelbean_dev directory:")
            print("     pip install -e . --no-deps --force-reinstall")
        
        print("\n📚 See docs/windows-setup.md for detailed troubleshooting")
        return False

def check_basic_functionality(hb):
    """Test basic hazelbean functionality."""
    print_header("Basic Functionality Check")
    
    try:
        import tempfile
        import os
        
        # Test ProjectFlow creation
        with tempfile.TemporaryDirectory() as tmp:
            p = hb.ProjectFlow(tmp)
            print_success("ProjectFlow initialization works")
            
            # Test file creation and get_path
            test_file = os.path.join(tmp, "test.txt")
            with open(test_file, 'w') as f:
                f.write("test")
            
            path = p.get_path("test.txt")
            if os.path.exists(path):
                print_success("Basic file operations work")
            else:
                print_warning("File path resolution may have issues")
        
        return True
    except Exception as e:
        print_error(f"Basic functionality test failed: {e}")
        return False

def check_key_dependencies():
    """Check that key dependencies are available."""
    print_header("Key Dependencies Check")
    
    dependencies = [
        ('numpy', 'NumPy', False),
        ('osgeo.gdal', 'GDAL', False),
        ('geopandas', 'GeoPandas', False),
        ('rasterio', 'Rasterio', False),
    ]
    
    all_present = True
    for module, name, optional in dependencies:
        try:
            if '.' in module:
                # Handle nested imports like osgeo.gdal
                parts = module.split('.')
                mod = __import__(module)
                for part in parts[1:]:
                    mod = getattr(mod, part)
            else:
                __import__(module)
            print_success(f"{name} available")
        except (ImportError, AttributeError):
            if optional:
                print_info(f"{name} not found (optional)")
            else:
                print_warning(f"{name} not found (may affect some features)")
            all_present = False
    
    return all_present

def main():
    """Run all verification checks."""
    print("\n" + "="*70)
    print("  🔍 Hazelbean Installation Verification")
    print("="*70)
    print(f"\nPlatform: {platform.system()} {platform.release()}")
    print(f"Architecture: {platform.machine()}")
    
    # Run all checks
    checks_passed = []
    
    # Python version
    checks_passed.append(check_python_version())
    
    # Hazelbean import
    hb_imported, hb = check_hazelbean_import()
    checks_passed.append(hb_imported)
    
    if not hb_imported:
        print_header("Summary")
        print_error("Hazelbean is not installed. Cannot proceed with further checks.")
        print_info("Install hazelbean first, then run this script again.")
        return False
    
    # Cython extensions (critical)
    cython_ok = check_cython_extensions()
    checks_passed.append(cython_ok)
    
    # Dependencies
    checks_passed.append(check_key_dependencies())
    
    # Basic functionality (only if Cython is OK)
    if cython_ok:
        checks_passed.append(check_basic_functionality(hb))
    
    # Summary
    print_header("Verification Summary")
    
    passed = sum(checks_passed)
    total = len(checks_passed)
    
    if all(checks_passed):
        print_success(f"All checks passed ({passed}/{total})")
        print("\n🎉 Hazelbean is properly installed and ready to use!")
        print("\n📚 Next steps:")
        print("   - Explore examples: cd examples && python step_1_project_setup.py")
        print("   - View documentation: cd docs-site && mkdocs serve")
        print("   - Run tests: pytest hazelbean_tests/system/test_smoke.py -v")
        return True
    else:
        print_warning(f"Some checks failed ({passed}/{total} passed)")
        print("\n📝 Please address the issues above and run this script again.")
        print("📚 For detailed help, see:")
        print("   - docs/getting-started.md")
        print("   - docs/windows-setup.md (Windows users)")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

