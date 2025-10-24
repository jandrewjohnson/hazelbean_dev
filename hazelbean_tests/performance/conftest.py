"""
Shared fixtures and configuration for performance tests.

This file provides common fixtures for benchmark and performance testing.
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path

@pytest.fixture
def performance_temp_dir():
    """Provides a temporary directory for performance tests."""
    temp_dir = tempfile.mkdtemp(prefix="hazelbean_perf_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def benchmark_config():
    """Configuration for benchmark tests."""
    return {
        "min_rounds": 5,
        "max_time": 0.1,
        "min_time": 0.005,
        "warmup_iterations": 2
    }

@pytest.fixture
def performance_baseline_dir():
    """Returns the performance baseline directory."""
    return Path(__file__).parent.parent.parent / "metrics"

@pytest.fixture
def timer():
    """Simple timer utility for performance measurements."""
    class Timer:
        def __init__(self):
            self.start_time = None
            
        def start(self):
            self.start_time = time.perf_counter()
            
        def stop(self):
            if self.start_time is None:
                raise RuntimeError("Timer not started")
            return time.perf_counter() - self.start_time
            
        def __enter__(self):
            self.start()
            return self
            
        def __exit__(self, *args):
            self.elapsed = self.stop()
    
    return Timer()
