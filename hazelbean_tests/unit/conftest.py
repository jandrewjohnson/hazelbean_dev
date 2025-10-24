"""
Shared fixtures and configuration for unit tests.

This file provides common fixtures and pytest configuration 
for all component-based unit tests.
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path

@pytest.fixture
def temp_dir():
    """Provides a temporary directory that's cleaned up after tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def temp_file():
    """Provides a temporary file that's cleaned up after tests."""
    temp_fd, temp_path = tempfile.mkstemp()
    os.close(temp_fd)
    yield temp_path
    if os.path.exists(temp_path):
        os.remove(temp_path)

@pytest.fixture
def hazelbean_test_data_dir():
    """Returns the path to test data directory."""
    return Path(__file__).parent.parent.parent / "data" / "tests"

@pytest.fixture
def mock_env_vars():
    """Provides isolated environment variables for testing."""
    original_env = os.environ.copy()
    yield os.environ
    os.environ.clear()
    os.environ.update(original_env)
