"""
Shared fixtures and configuration for integration tests.

This file provides common fixtures for workflow-based integration testing.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import numpy as np

@pytest.fixture
def integration_temp_dir():
    """Provides a temporary directory for integration test workflows."""
    temp_dir = tempfile.mkdtemp(prefix="hazelbean_integration_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def sample_raster_data():
    """Provides sample raster data for integration testing."""
    # Create a small test raster array
    data = np.random.rand(100, 100).astype(np.float32)
    return data

@pytest.fixture
def workflow_test_data():
    """Provides test data paths for workflow testing."""
    test_data_dir = Path(__file__).parent.parent.parent / "data" / "tests"
    return {
        "valid_cog": test_data_dir / "valid_cog_example.tif",
        "invalid_cog": test_data_dir / "invalid_cog_example.tif"
    }

@pytest.fixture
def integration_test_config():
    """Provides configuration for integration tests."""
    return {
        "timeout": 30,  # seconds
        "memory_limit": "1GB",
        "temp_cleanup": True
    }
