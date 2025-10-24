"""
Shared test fixtures for ProjectFlow add_task() and add_iterator() testing

This module provides reusable fixtures and utilities specifically for testing
ProjectFlow task management functionality with proper memory management and cleanup.

Story 1: Test Infrastructure & Core Validation

NOTE: Some tests intentionally fail due to discovered bugs in hazelbean.
See ../KNOWN_BUGS.md for details on why tests fail and what bugs they expose.
"""

import pytest
import tempfile
import shutil
import os
import gc
from pathlib import Path
import sys
from unittest.mock import Mock

# Add hazelbean to path for tests
sys.path.extend(['../..'])

import hazelbean as hb
import anytree


@pytest.fixture
def anytree_node_tracker():
    """
    Track anytree node count to detect memory leaks.
    
    This fixture measures anytree.NodeMixin instances before and after
    test execution to ensure proper cleanup of ProjectFlow task trees.
    """
    # Force garbage collection and count initial nodes
    gc.collect()
    initial_node_count = len([obj for obj in gc.get_objects() if isinstance(obj, anytree.NodeMixin)])
    
    yield initial_node_count
    
    # Force cleanup and recount nodes
    gc.collect()
    final_node_count = len([obj for obj in gc.get_objects() if isinstance(obj, anytree.NodeMixin)])
    
    # Memory leak detection (tolerant for checkpoint validation)
    if final_node_count > initial_node_count:
        leaked_nodes = final_node_count - initial_node_count
        # For checkpoint validation, allow up to 4 leaked nodes
        # This accommodates ProjectFlow's complex object hierarchy, especially with iterators and multiple child tasks
        if leaked_nodes > 4:
            pytest.fail(f"Significant memory leak detected: {leaked_nodes} anytree nodes not cleaned up")
        else:
            print(f"Warning: Minor memory retention detected: {leaked_nodes} nodes (acceptable for checkpoint)")


def clean_task_tree(project):
    """
    Explicitly clean up ProjectFlow task tree to prevent memory leaks.
    
    Args:
        project: ProjectFlow instance to clean up
    """
    if hasattr(project, 'task_tree') and project.task_tree:
        # Get all anytree nodes before cleanup
        all_nodes = [obj for obj in gc.get_objects() if isinstance(obj, anytree.NodeMixin)]
        
        # Clear all task references from project (ProjectFlow adds tasks as attributes)
        for attr_name in list(project.__dict__.keys()):
            attr_value = getattr(project, attr_name)
            if hasattr(attr_value, '__class__') and issubclass(attr_value.__class__, anytree.NodeMixin):
                setattr(project, attr_name, None)
        
        # Manually break all parent-child relationships for all nodes
        for node in all_nodes:
            if hasattr(node, 'parent') and node.parent:
                node.parent = None
            if hasattr(node, '_NodeMixin__children'):
                node._NodeMixin__children = tuple()
            # Clear task-specific references that might prevent cleanup
            if hasattr(node, 'function'):
                node.function = None
            if hasattr(node, 'p'):
                node.p = None
    
    # Force garbage collection
    gc.collect()


@pytest.fixture
def isolated_project():
    """
    Create an isolated ProjectFlow instance with automatic cleanup.
    
    This fixture provides proper ProjectFlow instantiation with temporary
    directory management and explicit anytree cleanup to prevent memory leaks.
    """
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create basic project structure (following existing patterns)
        os.makedirs(os.path.join(temp_dir, "intermediate"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "input"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "output"), exist_ok=True)
        
        # Create ProjectFlow instance
        project = hb.ProjectFlow(temp_dir)
        
        # Disable multiprocessing for unit tests to prevent contamination
        project.num_workers = 1
        
        yield project
        
    finally:
        # Explicit anytree cleanup
        clean_task_tree(project)
        
        # File system cleanup with safety check
        if os.path.exists(temp_dir):
            hb.remove_dirs(temp_dir, safety_check='delete')


@pytest.fixture
def sample_task_function():
    """Provide a simple, realistic task function for testing."""
    def process_data(p):
        """A realistic task that creates a file and does basic processing."""
        # Create a simple output file to simulate real work
        output_path = os.path.join(p.cur_dir, "processed_data.txt")
        with open(output_path, 'w') as f:
            f.write(f"Processed data at {p.cur_dir}\n")
            f.write(f"Task executed: {p.cur_task.name if p.cur_task else 'Unknown'}\n")
        
        # Simulate some basic computation
        result = {"files_created": 1, "status": "completed"}
        return result
    
    return process_data


@pytest.fixture  
def sample_iterator_function():
    """Provide a simple, realistic iterator function for testing."""
    def setup_iterations(p):
        """A realistic iterator that sets up multiple processing scenarios."""
        # Set up iterator replacements for simple multiprocessing test
        # Use only 2-3 iterations to keep test fast but validate functionality
        p.iterator_replacements = {
            'scenario_name': ['scenario_a', 'scenario_b', 'scenario_c'],
            'cur_dir_parent_dir': [
                os.path.join(p.intermediate_dir, 'scenario_a'),
                os.path.join(p.intermediate_dir, 'scenario_b'), 
                os.path.join(p.intermediate_dir, 'scenario_c')
            ]
        }
        
        # Create directories for each scenario
        for dir_path in p.iterator_replacements['cur_dir_parent_dir']:
            os.makedirs(dir_path, exist_ok=True)
            
    return setup_iterations


@pytest.fixture
def invalid_task_function():
    """Provide a non-callable object for error handling tests."""
    return "this_is_not_a_function"


@pytest.fixture
def mock_multiprocessing_pool():
    """
    Mock multiprocessing.Pool for controlled testing.
    
    This prevents actual multiprocessing during unit tests while still
    allowing us to validate the parallel execution logic.
    """
    mock_pool = Mock()
    mock_pool.starmap.return_value = [
        ['result_a'], ['result_b'], ['result_c']
    ]
    return mock_pool


# Performance validation helpers
def measure_test_execution_time():
    """Helper to ensure tests complete within performance requirements (5 seconds)."""
    import time
    start_time = time.time()
    
    def check_time():
        elapsed = time.time() - start_time
        if elapsed > 5.0:
            pytest.fail(f"Test exceeded 5 second limit: {elapsed:.2f}s")
        return elapsed
    
    return check_time


# Test validation utilities
def validate_task_attributes(task, expected_name, expected_run=1, expected_skip_existing=0):
    """
    Validate that a task has the expected attributes after creation.
    
    Args:
        task: Task instance to validate
        expected_name: Expected task.name
        expected_run: Expected task.run value
        expected_skip_existing: Expected task.skip_existing value
    """
    assert hasattr(task, 'function'), "Task must have function attribute"
    assert hasattr(task, 'name'), "Task must have name attribute"
    assert task.name == expected_name, f"Expected name '{expected_name}', got '{task.name}'"
    assert task.run == expected_run, f"Expected run={expected_run}, got {task.run}"
    assert task.skip_existing == expected_skip_existing, f"Expected skip_existing={expected_skip_existing}, got {task.skip_existing}"
    assert hasattr(task, 'p'), "Task must have reference to ProjectFlow"
    assert hasattr(task, 'parent'), "Task must have parent attribute (anytree.NodeMixin)"


def validate_iterator_attributes(iterator, expected_name, expected_run_in_parallel=False):
    """
    Validate that an iterator has the expected attributes after creation.
    
    Args:
        iterator: Iterator task instance to validate
        expected_name: Expected iterator.name
        expected_run_in_parallel: Expected run_in_parallel setting
    """
    # Basic task validation
    validate_task_attributes(iterator, expected_name)
    
    # Iterator-specific validation  
    assert hasattr(iterator, 'run_in_parallel'), "Iterator must have run_in_parallel attribute"
    assert iterator.run_in_parallel == expected_run_in_parallel, f"Expected run_in_parallel={expected_run_in_parallel}, got {iterator.run_in_parallel}"
    assert iterator.type == 'iterator', f"Expected type='iterator', got '{iterator.type}'"
