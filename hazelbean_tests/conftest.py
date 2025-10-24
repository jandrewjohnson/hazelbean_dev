"""
Shared test configuration and fixtures for Hazelbean tests

This file provides common test fixtures and utilities used across
the organized test suite structure.

Story 11: Test Suite Organization & Structure
"""

# Set GDAL environment variables before any imports that might use GDAL
import os
os.environ['GDAL_DISABLE_READDIR_ON_OPEN'] = 'EMPTY_DIR'

import pytest
import tempfile
import shutil
import sys
import types
from pathlib import Path

# Add hazelbean to path for tests
sys.path.extend(['../..'])

# --- Google Cloud stubs for test environment (before hazelbean import) ---
for name in [
    "google", "google.cloud", "google.cloud.storage",
    "googleapiclient", "googleapiclient.discovery",
    "google_auth_oauthlib", "google_auth_oauthlib.flow",
    "google.auth", "google.auth.transport", "google.auth.transport.requests",
]:
    mod = types.ModuleType(name); mod.__path__ = []
    sys.modules[name] = mod

sys.modules["google.cloud.storage"].Client = object
sys.modules["googleapiclient.discovery"].build = lambda *a, **k: None
class _Flow:                                  # Minimal InstalledAppFlow stub
    def __init__(self, *a, **k): pass
    def run_local_server(self, *a, **k): return None
sys.modules["google_auth_oauthlib.flow"].InstalledAppFlow = _Flow
sys.modules["google.auth.transport.requests"].Request = object
# -----------------------------------------------------------------------

import hazelbean as hb

# pytest-benchmark configured in pytest.ini

# GDAL/pyogrio initialization fixture
@pytest.fixture(scope="session", autouse=True)
def initialize_gdal():
    """Initialize GDAL and pyogrio properly for test environment"""
    import os
    from osgeo import gdal
    
    # Force GDAL configuration for test environment
    os.environ['GDAL_DISABLE_READDIR_ON_OPEN'] = 'EMPTY_DIR'
    os.environ['GDAL_NUM_THREADS'] = '1'
    os.environ['GDAL_HTTP_TIMEOUT'] = '30'
    
    # Set PROJ_LIB if not already set (missing on macOS)
    if 'PROJ_LIB' not in os.environ or not os.environ['PROJ_LIB']:
        conda_env_path = os.path.dirname(os.path.dirname(sys.executable))
        proj_path = os.path.join(conda_env_path, 'share', 'proj')
        if os.path.exists(proj_path):
            os.environ['PROJ_LIB'] = proj_path
    
    # Initialize GDAL with error handling
    gdal.UseExceptions()
    gdal.SetConfigOption('GDAL_DATA', os.environ.get('GDAL_DATA'))
    
    # Try to import pyogrio early to catch initialization issues
    try:
        import pyogrio
        # Force initialization by doing a minimal operation
        _ = pyogrio.__version__
    except Exception as e:
        print(f"Warning: pyogrio initialization issue: {e}")
    
    yield
    
    # Cleanup
    gdal.DontUseExceptions()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test isolation"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture  
def sample_project(temp_dir):
    """Create a sample ProjectFlow with basic directory structure"""
    # Create basic project structure
    os.makedirs(os.path.join(temp_dir, "intermediate"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "input"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "output"), exist_ok=True)
    
    # Create sample files
    with open(os.path.join(temp_dir, "test_file.txt"), 'w') as f:
        f.write("test content")
    with open(os.path.join(temp_dir, "intermediate", "intermediate_file.txt"), 'w') as f:
        f.write("intermediate content")
    with open(os.path.join(temp_dir, "input", "input_file.txt"), 'w') as f:
        f.write("input content")
        
    # Create and return ProjectFlow instance
    project = hb.ProjectFlow(temp_dir)
    return project


@pytest.fixture
def data_paths():
    """Provide paths to test data directories"""
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "../data")
    
    return {
        'data_dir': data_dir,
        'test_data_dir': os.path.join(data_dir, "tests"),
        'cartographic_data_dir': os.path.join(data_dir, "cartographic/ee"),
        'pyramid_data_dir': os.path.join(data_dir, "pyramids"),
        'crops_data_dir': os.path.join(data_dir, "crops/johnson")
    }


@pytest.fixture
def sample_files(data_paths):
    """Provide commonly used test file names"""
    return {
        'raster_file': "ee_r264_ids_900sec.tif",
        'vector_file': "ee_r264_simplified900sec.gpkg", 
        'csv_file': "ee_r264_correspondence.csv",
        'pyramid_file': "ha_per_cell_900sec.tif",
        'crops_file': "crop_calories/maize_calories_per_ha_masked.tif"
    }


# Test collection customization
def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on their location and content"""
    for item in items:
        # Add markers based on test file location
        if "unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "performance/" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            
        # Add slow marker for certain patterns
        if "benchmark" in item.name.lower() or "performance" in item.name.lower():
            item.add_marker(pytest.mark.slow)


# Custom markers for better test organization
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests that test individual functions in isolation"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests that test component interactions"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and benchmark tests"
    )
    config.addinivalue_line(
        "markers", "gdal_env: Tests that require GDAL environment (may fail on some systems)"
    )
    config.addinivalue_line(
        "markers", "smoke: Smoke tests for basic functionality validation"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer to run"
    )
    config.addinivalue_line(
        "markers", "benchmark: Benchmark tests (requires pytest-benchmark)"
    )
