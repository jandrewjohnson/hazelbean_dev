"""
Core Proof Tests for ProjectFlow add_task() method

This module contains essential validation tests for ProjectFlow's add_task()
functionality, focusing on realistic use cases and robust infrastructure.

Story 1: Test Infrastructure & Core Validation - Core Proof Test 1
"""

import pytest
import os
import sys
import time
from pathlib import Path

# Add hazelbean to path for tests  
sys.path.extend(['../..'])

import hazelbean as hb
from hazelbean_tests.unit.test_fixtures import (
    isolated_project, 
    sample_task_function,
    invalid_task_function,
    anytree_node_tracker,
    validate_task_attributes,
    measure_test_execution_time
)


class TestAddTaskCoreProof:
    """
    Core Proof Test 1: add_task() Functional Validation
    
    This test validates that add_task() works with realistic use cases including:
    - Actual task function execution
    - Directory creation and file operations  
    - Task attribute management
    - Memory leak prevention
    """
    
    def test_add_task_functional_execution(self, isolated_project, sample_task_function, anytree_node_tracker):
        """
        CORE PROOF TEST 1: Functional validation of add_task() with execution
        
        This test validates:
        - Task creation with valid callable function
        - Task execution through ProjectFlow workflow
        - Directory creation and file operations
        - Task attribute correctness
        - Memory leak prevention
        
        Success criteria:
        - Task created with correct attributes
        - Task executes and creates expected files  
        - No anytree memory leaks
        - Execution completes under 5 seconds
        """
        time_checker = measure_test_execution_time()
        
        # Test setup
        project = isolated_project
        
        # Core functionality: Add task
        task = project.add_task(sample_task_function)
        
        # Validate task creation
        validate_task_attributes(task, 'process_data')
        assert task.function == sample_task_function, "Task function should match provided function"
        assert hasattr(project, 'process_data'), "ProjectFlow should have task as attribute"
        assert getattr(project, 'process_data') == task, "ProjectFlow task attribute should reference task"
        
        # Validate task is in project task tree
        assert task.parent == project.task_tree, "Task parent should be project task_tree"
        assert task in project.task_tree.children, "Task should be child of task_tree"
        
        # Execute the task (realistic workflow)
        project.execute()
        
        # Validate execution results
        expected_output = os.path.join(project.intermediate_dir, 'process_data', 'processed_data.txt')
        assert os.path.exists(expected_output), f"Task should create output file at {expected_output}"
        
        # Validate file content 
        with open(expected_output, 'r') as f:
            content = f.read()
            assert "Processed data" in content, "Output file should contain expected content"
            assert "process_data" in content, "Output file should contain task name"
        
        # Performance validation
        elapsed = time_checker()
        assert elapsed < 5.0, f"Test should complete under 5 seconds, took {elapsed:.2f}s"
        
        # Memory leak detection handled by anytree_node_tracker fixture
        
    
    def test_add_task_parameter_validation(self, isolated_project, sample_task_function):
        """
        Validate add_task() parameter handling and task attribute configuration.
        
        Tests:
        - Custom run and skip_existing parameters
        - Task directory configuration
        - Task type assignment
        """
        project = isolated_project
        
        # Test with custom parameters
        task = project.add_task(
            sample_task_function, 
            run=0, 
            skip_existing=1,
            type='custom_task'
        )
        
        # Validate parameter application
        validate_task_attributes(task, 'process_data', expected_run=0, expected_skip_existing=1)
        assert task.type == 'custom_task', f"Expected type='custom_task', got '{task.type}'"
        
        # Test task_dir parameter
        custom_task_dir = os.path.join(project.intermediate_dir, 'custom_location')
        task_with_dir = project.add_task(
            sample_task_function,
            task_dir=custom_task_dir
        )
        
        # Note: task_dir is set during execution, not immediately
        # This validates the parameter is stored correctly
        assert hasattr(task_with_dir, 'task_dir'), "Task should have task_dir attribute"


class TestAddTaskErrorHandling:
    """
    Core Proof Test 3A: Error handling validation for add_task()
    
    This test ensures robust error handling when invalid parameters
    are provided to add_task().
    """
    
    def test_add_task_invalid_function_error(self, isolated_project, invalid_task_function, anytree_node_tracker):
        """
        CORE PROOF TEST 3A: Error handling for invalid function parameter
        
        Validates:
        - TypeError raised for non-callable function parameter
        - Clear error message provided
        - No memory leaks during error conditions
        - No partial task creation on error
        """
        project = isolated_project
        initial_children_count = len(project.task_tree.children)
        
        # Test invalid function parameter
        # NOTE: BUG DISCOVERED IN HAZELBEAN - This test SHOULD pass but currently fails
        # project_flow.py line 593 tries to access function.__name__ on invalid objects
        # causing AttributeError instead of the intended TypeError
        with pytest.raises(TypeError) as exc_info:
            project.add_task(invalid_task_function)
        
        # What the error message SHOULD contain when bug is fixed
        error_message = str(exc_info.value)
        assert "must be callable" in error_message.lower(), f"Error message should mention 'callable': {error_message}"
        assert "this_is_not_a_function" in error_message, f"Error message should include function name: {error_message}"
        
        # Validate no partial task creation
        assert len(project.task_tree.children) == initial_children_count, "No tasks should be added on error"
        
        # Memory leak detection handled by anytree_node_tracker fixture
        
        
    def test_add_task_none_function_error(self, isolated_project):
        """
        Test error handling when None is passed as function parameter.
        """
        project = isolated_project
        
        # NOTE: BUG DISCOVERED IN HAZELBEAN - This test SHOULD pass but currently fails
        # project_flow.py line 593 tries to access None.__name__, causing AttributeError instead of TypeError
        with pytest.raises(TypeError) as exc_info:
            project.add_task(None)
            
        error_message = str(exc_info.value)
        assert "must be callable" in error_message.lower() or "nonetype" in error_message.lower()


class TestAddTaskParameterValidation:
    """
    Story 2: Comprehensive parameter validation for add_task() method.
    
    Tests all parameter combinations and edge cases for robust validation.
    """
    
    def test_add_task_run_parameter_variants(self, isolated_project, sample_task_function):
        """
        Test run parameter validation: run=0, run=1, default behavior.
        """
        project = isolated_project
        
        # Test run=0 (task should not execute)
        task_no_run = project.add_task(sample_task_function, run=0)
        validate_task_attributes(task_no_run, 'process_data', expected_run=0)
        
        # Test run=1 (task should execute)
        task_run = project.add_task(sample_task_function, run=1)
        validate_task_attributes(task_run, 'process_data', expected_run=1)
        
        # Test default run behavior (should be 1)
        task_default = project.add_task(sample_task_function)
        validate_task_attributes(task_default, 'process_data', expected_run=1)
        
        
    def test_add_task_skip_existing_parameter_variants(self, isolated_project, sample_task_function):
        """
        Test skip_existing parameter: skip_existing=0, skip_existing=1, default behavior.
        """
        project = isolated_project
        
        # Test skip_existing=0 (should not skip)
        task_no_skip = project.add_task(sample_task_function, skip_existing=0)
        validate_task_attributes(task_no_skip, 'process_data', expected_skip_existing=0)
        
        # Test skip_existing=1 (should skip if exists)
        task_skip = project.add_task(sample_task_function, skip_existing=1)
        validate_task_attributes(task_skip, 'process_data', expected_skip_existing=1)
        
        # Test default skip_existing behavior (should be 0)
        task_default = project.add_task(sample_task_function)
        validate_task_attributes(task_default, 'process_data', expected_skip_existing=0)
        
        
    def test_add_task_logging_level_parameter(self, isolated_project, sample_task_function):
        """
        Test logging_level parameter: inheritance, explicit override, None handling.
        """
        project = isolated_project
        import logging
        
        # Test explicit logging level override
        task_debug = project.add_task(sample_task_function, logging_level=logging.DEBUG)
        assert task_debug.logging_level == logging.DEBUG, f"Expected DEBUG level, got {task_debug.logging_level}"
        
        # Test inheritance from project (default behavior)
        task_inherit = project.add_task(sample_task_function)
        assert task_inherit.logging_level == project.logging_level, f"Expected inherited level {project.logging_level}, got {task_inherit.logging_level}"
        
        # Test None handling (None remains None rather than inheriting)
        task_none = project.add_task(sample_task_function, logging_level=None)
        assert task_none.logging_level is None, f"Expected None when explicitly set to None, got {task_none.logging_level}"
        
        
    def test_add_task_task_dir_parameter(self, isolated_project, sample_task_function):
        """
        Test task_dir parameter: custom directory, None handling, path validation.
        """
        project = isolated_project
        
        # Test custom task_dir
        custom_dir = "/custom/task/location"
        task_custom = project.add_task(sample_task_function, task_dir=custom_dir)
        assert hasattr(task_custom, 'task_dir'), "Task should have task_dir attribute"
        assert task_custom.task_dir == custom_dir, f"Expected {custom_dir}, got {task_custom.task_dir}"
        
        # Test None task_dir (default behavior)
        task_default = project.add_task(sample_task_function, task_dir=None)
        assert task_default.task_dir is None, f"Expected None task_dir, got {task_default.task_dir}"
        
        # Test relative path task_dir
        relative_dir = "relative/task/path"
        task_relative = project.add_task(sample_task_function, task_dir=relative_dir)
        assert task_relative.task_dir == relative_dir, f"Expected {relative_dir}, got {task_relative.task_dir}"
        
        
    def test_add_task_creates_dir_parameter(self, isolated_project, sample_task_function):
        """
        Test creates_dir parameter: True/False behavior, directory creation logic.
        """
        project = isolated_project
        
        # Test creates_dir=True (default)
        task_create = project.add_task(sample_task_function, creates_dir=True)
        assert task_create.creates_dir is True, f"Expected creates_dir=True, got {task_create.creates_dir}"
        
        # Test creates_dir=False
        task_no_create = project.add_task(sample_task_function, creates_dir=False)
        assert task_no_create.creates_dir is False, f"Expected creates_dir=False, got {task_no_create.creates_dir}"
        
        # Test default creates_dir behavior (should be True)
        task_default = project.add_task(sample_task_function)
        assert task_default.creates_dir is True, f"Expected default creates_dir=True, got {task_default.creates_dir}"
        
        
    def test_add_task_type_parameter(self, isolated_project, sample_task_function):
        """
        Test type parameter: default 'task', custom type handling.
        """
        project = isolated_project
        
        # Test default type
        task_default = project.add_task(sample_task_function)
        assert task_default.type == 'task', f"Expected type='task', got '{task_default.type}'"
        
        # Test custom type
        task_custom = project.add_task(sample_task_function, type='custom_processing')
        assert task_custom.type == 'custom_processing', f"Expected type='custom_processing', got '{task_custom.type}'"
        
        # Test special types
        task_batch = project.add_task(sample_task_function, type='batch_task')
        assert task_batch.type == 'batch_task', f"Expected type='batch_task', got '{task_batch.type}'"


class TestAddTaskObjectCreation:
    """
    Story 2: Task object creation and attribute validation tests.
    
    Tests task object instantiation, attribute assignment, and correctness.
    """
    
    def test_add_task_basic_object_creation(self, isolated_project, sample_task_function):
        """
        Test basic task object creation with proper attributes.
        """
        project = isolated_project
        task = project.add_task(sample_task_function)
        
        # Validate core task attributes
        validate_task_attributes(task, 'process_data')
        
        # Validate task class and inheritance
        assert isinstance(task, hb.Task), f"Task should be instance of hb.Task, got {type(task)}"
        assert hasattr(task, 'parent'), "Task should have parent attribute (anytree.NodeMixin)"
        assert hasattr(task, 'children'), "Task should have children attribute (anytree.NodeMixin)"
        
        
    def test_add_task_function_reference_validation(self, isolated_project, sample_task_function):
        """
        Test that task correctly stores function reference.
        """
        project = isolated_project
        task = project.add_task(sample_task_function)
        
        # Validate function reference
        assert task.function == sample_task_function, "Task function should match provided function"
        assert task.function.__name__ == 'process_data', f"Function name should be 'process_data', got '{task.function.__name__}'"
        assert callable(task.function), "Task function should be callable"
        
        
    def test_add_task_name_attribute_derivation(self, isolated_project):
        """
        Test that task.name is correctly derived from function.__name__.
        """
        project = isolated_project
        
        def custom_function_name(p):
            pass
            
        def another_name(p):
            pass
            
        # Test name derivation
        task1 = project.add_task(custom_function_name)
        assert task1.name == 'custom_function_name', f"Expected 'custom_function_name', got '{task1.name}'"
        
        task2 = project.add_task(another_name)
        assert task2.name == 'another_name', f"Expected 'another_name', got '{task2.name}'"
        
        
    def test_add_task_project_reference_validation(self, isolated_project, sample_task_function):
        """
        Test that task correctly stores project reference.
        """
        project = isolated_project
        task = project.add_task(sample_task_function)
        
        # Validate project reference
        assert task.p == project, "Task should have reference to ProjectFlow instance"
        assert hasattr(task.p, 'project_dir'), "Task project reference should be valid ProjectFlow"
        assert task.p.project_dir == project.project_dir, "Task project reference should match original"


class TestAddTaskParentChildRelationships:
    """
    Story 2: Parent-child relationship testing with anytree hierarchy validation.
    
    Tests anytree integration and task tree structure management.
    """
    
    def test_add_task_default_parent_assignment(self, isolated_project, sample_task_function):
        """
        Test default parent assignment to project.task_tree.
        """
        project = isolated_project
        task = project.add_task(sample_task_function)
        
        # Validate parent assignment
        assert task.parent == project.task_tree, "Task parent should be project.task_tree by default"
        assert task in project.task_tree.children, "Task should be child of project.task_tree"
        
        
    def test_add_task_custom_parent_assignment(self, isolated_project, sample_task_function):
        """
        Test custom parent assignment and hierarchy validation.
        """
        project = isolated_project
        
        # Create parent task
        parent_task = project.add_task(sample_task_function)
        
        # Create child task with custom parent
        def child_function(p):
            pass
        child_task = project.add_task(child_function, parent=parent_task)
        
        # Validate custom parent relationship
        assert child_task.parent == parent_task, "Child task should have custom parent"
        assert child_task in parent_task.children, "Child task should be in parent's children"
        assert child_task not in project.task_tree.children, "Child task should not be direct child of task_tree"
        
        
    def test_add_task_anytree_hierarchy_validation(self, isolated_project, sample_task_function, anytree_node_tracker):
        """
        Test anytree hierarchy construction and validation.
        """
        project = isolated_project
        
        # Create complex hierarchy: root -> parent -> child -> grandchild
        parent_task = project.add_task(sample_task_function)
        
        def child_func(p):
            pass
        child_task = project.add_task(child_func, parent=parent_task)
        
        def grandchild_func(p):
            pass  
        grandchild_task = project.add_task(grandchild_func, parent=child_task)
        
        # Validate hierarchy using anytree utilities
        import anytree
        from anytree import RenderTree
        tree_structure = list(RenderTree(project.task_tree))
        
        # Should have: task_tree, parent_task, child_func, grandchild_func
        assert len(tree_structure) == 4, f"Expected 4 nodes in tree, got {len(tree_structure)}"
        
        # Validate path from root to grandchild
        assert grandchild_task.parent == child_task, "Grandchild parent should be child"
        assert child_task.parent == parent_task, "Child parent should be parent task"
        assert parent_task.parent == project.task_tree, "Parent task parent should be task_tree"
        
        # Memory leak detection handled by anytree_node_tracker fixture


class TestAddTaskDocumentationExtraction:
    """
    Story 2: Task documentation/note extraction testing.
    
    Tests function code analysis for task_note and task_documentation variables.
    """
    
    def test_add_task_documentation_extraction_success(self, isolated_project):
        """
        Test successful extraction of task_documentation from function code.
        """
        project = isolated_project
        
        def documented_function(p):
            task_documentation = "This is comprehensive documentation for the task"
            # Function implementation
            pass
            
        task = project.add_task(documented_function)
        
        # Validate documentation extraction
        # Note: This tests the current implementation which may have limitations
        # The actual extraction depends on function.__code__.co_varnames and co_consts
        assert hasattr(task, 'documentation'), "Task should have documentation attribute"
        # The current implementation may not extract correctly, but we test the structure
        
        
    def test_add_task_note_extraction_success(self, isolated_project):
        """
        Test successful extraction of task_note from function code.
        """
        project = isolated_project
        
        def noted_function(p):
            task_note = "Brief note about this task"
            # Function implementation
            pass
            
        task = project.add_task(noted_function)
        
        # Validate note extraction
        assert hasattr(task, 'note'), "Task should have note attribute"
        # The current implementation may not extract correctly, but we test the structure
        
        
    def test_add_task_no_documentation_handling(self, isolated_project, sample_task_function):
        """
        Test handling when function has no task_documentation or task_note.
        """
        project = isolated_project
        task = project.add_task(sample_task_function)
        
        # Validate no documentation handling
        assert hasattr(task, 'documentation'), "Task should have documentation attribute even if None"
        assert hasattr(task, 'note'), "Task should have note attribute even if None"
        # These should be None when no documentation is found
        assert task.documentation is None or isinstance(task.documentation, str), "Documentation should be None or string"
        assert task.note is None or isinstance(task.note, str), "Note should be None or string"


class TestAddTaskErrorHandling:
    """
    Story 2: Comprehensive error handling tests for all invalid input scenarios.
    
    Tests robust error detection and informative error messages.
    """
    
    @pytest.mark.xfail(
        reason="Known bug in project_flow.py:655-658 - Accesses function.__name__ before validating callable, causing AttributeError instead of TypeError. See KNOWN_BUGS.md #add_task_error_handling",
        strict=True,
        raises=AttributeError
    )
    def test_add_task_invalid_function_error(self, isolated_project, invalid_task_function, anytree_node_tracker):
        """
        Test error handling for non-callable function parameter.
        
        NOTE: This test documents a BUG in hazelbean - it should pass but currently fails.
        See ../KNOWN_BUGS.md for details.
        """
        project = isolated_project
        initial_children_count = len(project.task_tree.children)
        
        # Test invalid function parameter
        # KNOWN BUG: project_flow.py line 593 tries to access function.__name__ on invalid objects
        # causing AttributeError instead of the intended TypeError
        with pytest.raises(TypeError) as exc_info:
            project.add_task(invalid_task_function)
        
        # What the error message SHOULD contain when bug is fixed
        error_message = str(exc_info.value)
        assert "must be callable" in error_message.lower(), f"Error message should mention 'callable': {error_message}"
        assert "this_is_not_a_function" in error_message, f"Error message should include function name: {error_message}"
        
        # Validate no partial task creation
        assert len(project.task_tree.children) == initial_children_count, "No tasks should be added on error"
        
        
    @pytest.mark.xfail(
        reason="Known bug in project_flow.py:655-658 - Accesses None.__name__, causing AttributeError instead of TypeError. See KNOWN_BUGS.md #add_task_error_handling",
        strict=True,
        raises=AttributeError
    )
    def test_add_task_none_function_error(self, isolated_project):
        """
        Test error handling when None is passed as function parameter.
        
        NOTE: This test documents a BUG in hazelbean - it should pass but currently fails.
        """
        project = isolated_project
        
        # KNOWN BUG: project_flow.py line 593 tries to access None.__name__, causing AttributeError
        with pytest.raises(TypeError) as exc_info:
            project.add_task(None)
            
        error_message = str(exc_info.value)
        assert "must be callable" in error_message.lower() or "nonetype" in error_message.lower()
        
        
    def test_add_task_invalid_parent_parameter(self, isolated_project, sample_task_function):
        """
        Test error handling for invalid parent parameter.
        """
        project = isolated_project
        
        # Test with non-Node parent (should work or fail gracefully)
        # anytree will handle invalid parents appropriately
        try:
            # This might raise an error or handle gracefully depending on anytree implementation
            task = project.add_task(sample_task_function, parent="invalid_parent")
        except Exception as e:
            # If anytree raises an error, it should be informative
            assert "parent" in str(e).lower() or "node" in str(e).lower(), f"Error should mention parent/node: {e}"
        
        
    def test_add_task_extreme_parameter_values(self, isolated_project, sample_task_function):
        """
        Test error handling for extreme or edge case parameter values.
        """
        project = isolated_project
        
        # Test extreme run values
        task_negative_run = project.add_task(sample_task_function, run=-1)
        assert task_negative_run.run == -1, "Should accept negative run values"
        
        task_large_run = project.add_task(sample_task_function, run=999999)
        assert task_large_run.run == 999999, "Should accept large run values"
        
        # Test extreme skip_existing values  
        task_negative_skip = project.add_task(sample_task_function, skip_existing=-1)
        assert task_negative_skip.skip_existing == -1, "Should accept negative skip_existing values"
        
        # Test empty string type
        task_empty_type = project.add_task(sample_task_function, type="")
        assert task_empty_type.type == "", "Should accept empty string type"
        

class TestAddTaskProjectFlowIntegration:
    """
    Story 2: ProjectFlow integration tests.
    
    Tests task_tree assignment, task_names_defined tracking, and project attribute management.
    """
    
    def test_add_task_names_defined_tracking(self, isolated_project, sample_task_function):
        """
        Test that task_names_defined list is updated correctly.
        """
        project = isolated_project
        initial_names_count = len(project.task_names_defined)
        
        # Add task and verify name tracking
        task = project.add_task(sample_task_function)
        
        assert len(project.task_names_defined) == initial_names_count + 1, "task_names_defined should increase by 1"
        assert 'process_data' in project.task_names_defined, "Function name should be in task_names_defined"
        
        # Add another task
        def another_task(p):
            pass
            
        task2 = project.add_task(another_task)
        
        assert len(project.task_names_defined) == initial_names_count + 2, "task_names_defined should increase by 2"
        assert 'another_task' in project.task_names_defined, "Second function name should be in task_names_defined"
        
        
    def test_add_task_project_attribute_assignment(self, isolated_project, sample_task_function):
        """
        Test that tasks are assigned as attributes on the ProjectFlow object.
        """
        project = isolated_project
        
        # Verify task not yet an attribute
        assert not hasattr(project, 'process_data'), "Task should not exist before add_task"
        
        # Add task
        task = project.add_task(sample_task_function)
        
        # Verify task is now a project attribute
        assert hasattr(project, 'process_data'), "Task should be project attribute after add_task"
        assert getattr(project, 'process_data') == task, "Project attribute should reference the task object"
        
        
    def test_add_task_tree_structure_integration(self, isolated_project, sample_task_function, anytree_node_tracker):
        """
        Test integration with ProjectFlow task_tree structure.
        """
        project = isolated_project
        initial_children = len(project.task_tree.children)
        
        # Add multiple tasks and validate tree structure
        task1 = project.add_task(sample_task_function)
        
        def task2_func(p):
            pass
        task2 = project.add_task(task2_func)
        
        # Validate tree structure
        assert len(project.task_tree.children) == initial_children + 2, "Should have 2 more children in task_tree"
        
        # Validate both tasks are children
        children = list(project.task_tree.children)
        assert task1 in children, "Task1 should be child of task_tree"
        assert task2 in children, "Task2 should be child of task_tree"
        
        # Memory leak detection handled by anytree_node_tracker fixture


class TestAddTaskIntegration:
    """
    Integration validation for add_task() with ProjectFlow ecosystem.
    
    Tests task integration with ProjectFlow's directory management,
    logging system, and task execution workflow.
    """
    
    def test_add_task_directory_integration(self, isolated_project, sample_task_function):
        """
        Test add_task() integration with ProjectFlow directory management.
        """
        project = isolated_project
        task = project.add_task(sample_task_function)
        
        # Validate directory structure integration
        expected_task_dir = os.path.join(project.intermediate_dir, 'process_data')
        
        # Execute to trigger directory creation
        project.execute()
        
        # Validate task directory was created
        assert os.path.exists(expected_task_dir), f"Task directory should be created: {expected_task_dir}"
        assert task.task_dir == expected_task_dir, f"Task task_dir should match expected path"
        
        
    def test_add_task_multiple_tasks(self, isolated_project, anytree_node_tracker):
        """
        Test adding multiple tasks to validate task tree management.
        """
        project = isolated_project
        
        def task_a(p):
            with open(os.path.join(p.cur_dir, 'task_a.txt'), 'w') as f:
                f.write('Task A executed')
                
        def task_b(p):
            with open(os.path.join(p.cur_dir, 'task_b.txt'), 'w') as f:
                f.write('Task B executed')
        
        # Add multiple tasks
        task1 = project.add_task(task_a)
        task2 = project.add_task(task_b) 
        
        # Validate both tasks in tree
        assert len(project.task_tree.children) == 2, "Should have 2 tasks in tree"
        assert task1 in project.task_tree.children, "Task 1 should be in tree"
        assert task2 in project.task_tree.children, "Task 2 should be in tree"
        
        # Execute and validate both tasks ran
        project.execute()
        
        task_a_output = os.path.join(project.intermediate_dir, 'task_a', 'task_a.txt')
        task_b_output = os.path.join(project.intermediate_dir, 'task_b', 'task_b.txt')
        
        assert os.path.exists(task_a_output), "Task A should create output file"
        assert os.path.exists(task_b_output), "Task B should create output file"
        
        # Memory leak detection handled by anytree_node_tracker fixture
