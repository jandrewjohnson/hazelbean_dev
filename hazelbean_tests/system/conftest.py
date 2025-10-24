"""
Shared fixtures and configuration for system tests.

This file provides common fixtures for system-level testing including
smoke tests, CLI tests, installation validation, and environment checks.
"""

import pytest
import subprocess
import sys
import os
from pathlib import Path

@pytest.fixture
def system_environment():
    """Provides system environment information for testing."""
    return {
        "python_version": sys.version_info,
        "platform": sys.platform,
        "executable": sys.executable,
        "path": os.environ.get("PATH", ""),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", None)
    }

@pytest.fixture
def cli_runner():
    """Provides a CLI runner for testing command-line interfaces."""
    def run_command(cmd, cwd=None, check=False):
        """Run a command and return result."""
        try:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                cwd=cwd,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            return e
    
    return run_command

@pytest.fixture
def hazelbean_installation_path():
    """Returns the hazelbean installation path."""
    import hazelbean
    return Path(hazelbean.__file__).parent

@pytest.fixture
def environment_check():
    """Provides environment validation utilities."""
    def check_package_installed(package_name):
        """Check if a package is installed."""
        try:
            __import__(package_name)
            return True
        except ImportError:
            return False
    
    def check_command_available(command):
        """Check if a command is available in PATH."""
        try:
            subprocess.run([command, "--version"], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    return {
        "package_installed": check_package_installed,
        "command_available": check_command_available
    }
