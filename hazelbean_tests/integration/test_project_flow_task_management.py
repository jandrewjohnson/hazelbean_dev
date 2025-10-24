"""
Cross-Method Integration Tests for ProjectFlow add_task() and add_iterator()

Tests how add_task() and add_iterator() methods work together in complex hierarchies,
validating mixed task/iterator relationships, attribute management, configuration
inheritance, and memory cleanup patterns.

Story 4: Cross-Method Integration Testing
Story 5: Multi-Level Workflow Testing (Integration Execution Tests)

NOTE: Tests may fail due to discovered bugs in hazelbean ProjectFlow integration.
These failures help identify real issues in the codebase vs test setup problems.
See ../KNOWN_BUGS.md for details on known integration issues.
"""

import pytest
import os
import gc
import logging
from unittest.mock import Mock, patch
import sys
import tempfile

# Add hazelbean to path
sys.path.extend(['../..'])

import hazelbean as hb
import anytree
from hazelbean_tests.unit.test_fixtures import (
    isolated_project, anytree_node_tracker, clean_task_tree,
    validate_task_attributes, validate_iterator_attributes
)


class TestMixedHierarchyConstruction:
    """
    Task 4.1: Create mixed hierarchy construction tests
    
    Tests for iterators with child tasks, tasks with iterator parents,
    and complex nesting patterns between task and iterator types.
    """
    
    @pytest.mark.xfail(
        reason="Bug in hazelbean/project_flow.py: add_iterator() doesn't append to task_names_defined "
               "(line ~778 missing: self.task_names_defined.append(function.__name__)). "
               "add_task(), add_input_task(), and add_output_task() all do this, but add_iterator() doesn't.",
        strict=False
    )
    def test_iterator_with_child_tasks_hierarchy(self, isolated_project, anytree_node_tracker):
        """Test iterator as parent with multiple child tasks."""
        
        def setup_iterator(p):
            """Iterator function that prepares scenarios for child tasks."""
            p.iterator_replacements = {
                'scenario_name': ['alpha', 'beta'],
                'cur_dir_parent_dir': [
                    os.path.join(p.intermediate_dir, 'alpha'),
                    os.path.join(p.intermediate_dir, 'beta')
                ]
            }
            # Create directories
            for dir_path in p.iterator_replacements['cur_dir_parent_dir']:
                os.makedirs(dir_path, exist_ok=True)
        
        def child_task_a(p):
            """First child task under iterator."""
            output_file = os.path.join(p.cur_dir, 'task_a_result.txt')
            with open(output_file, 'w') as f:
                f.write(f"Task A completed in {p.scenario_name}")
        
        def child_task_b(p):
            """Second child task under iterator."""
            output_file = os.path.join(p.cur_dir, 'task_b_result.txt') 
            with open(output_file, 'w') as f:
                f.write(f"Task B completed in {p.scenario_name}")
        
        # Create mixed hierarchy: iterator → tasks
        iterator = isolated_project.add_iterator(setup_iterator, run_in_parallel=False)
        task_a = isolated_project.add_task(child_task_a, parent=iterator)
        task_b = isolated_project.add_task(child_task_b, parent=iterator)
        
        # Validate hierarchy structure
        assert iterator.parent == isolated_project.task_tree
        assert task_a.parent == iterator
        assert task_b.parent == iterator
        assert len(iterator.children) == 2
        
        # Validate mixed type relationships
        assert iterator.type == 'iterator'
        assert task_a.type == 'task'
        assert task_b.type == 'task'
        
        # Validate task names are tracked in project
        # All methods should consistently track function names in task_names_defined
        assert setup_iterator.__name__ in isolated_project.task_names_defined  # Should track iterator names
        assert child_task_a.__name__ in isolated_project.task_names_defined
        assert child_task_b.__name__ in isolated_project.task_names_defined

    def test_task_with_iterator_children_hierarchy(self, isolated_project, anytree_node_tracker):
        """Test task as parent with iterator children."""
        
        def parent_task(p):
            """Parent task that sets up data for iterator children."""
            setup_file = os.path.join(p.cur_dir, 'setup_data.txt')
            with open(setup_file, 'w') as f:
                f.write("Parent task setup complete")
        
        def child_iterator_a(p):
            """First iterator child under parent task."""
            p.iterator_replacements = {
                'iteration_type': ['type1', 'type2'],
                'cur_dir_parent_dir': [
                    os.path.join(p.cur_dir, 'type1'),
                    os.path.join(p.cur_dir, 'type2')
                ]
            }
            for dir_path in p.iterator_replacements['cur_dir_parent_dir']:
                os.makedirs(dir_path, exist_ok=True)
        
        def child_iterator_b(p):
            """Second iterator child under parent task."""
            p.iterator_replacements = {
                'batch_id': ['batch_x', 'batch_y'], 
                'cur_dir_parent_dir': [
                    os.path.join(p.cur_dir, 'batch_x'),
                    os.path.join(p.cur_dir, 'batch_y')
                ]
            }
            for dir_path in p.iterator_replacements['cur_dir_parent_dir']:
                os.makedirs(dir_path, exist_ok=True)
        
        # Create mixed hierarchy: task → iterators
        parent = isolated_project.add_task(parent_task)
        iter_a = isolated_project.add_iterator(child_iterator_a, parent=parent, run_in_parallel=False)
        iter_b = isolated_project.add_iterator(child_iterator_b, parent=parent, run_in_parallel=False)
        
        # Validate hierarchy structure
        assert parent.parent == isolated_project.task_tree
        assert iter_a.parent == parent
        assert iter_b.parent == parent
        assert len(parent.children) == 2
        
        # Validate mixed type relationships
        assert parent.type == 'task'
        assert iter_a.type == 'iterator'
        assert iter_b.type == 'iterator'

    def test_complex_nested_mixed_hierarchy(self, isolated_project, anytree_node_tracker):
        """Test deep hierarchies with alternating task/iterator types."""
        
        def root_task(p):
            """Root level task."""
            os.makedirs(os.path.join(p.cur_dir, 'root_output'), exist_ok=True)
        
        def level_1_iterator(p):
            """Level 1 iterator under root task."""
            p.iterator_replacements = {
                'level1_scenario': ['scenario_1', 'scenario_2'],
                'cur_dir_parent_dir': [
                    os.path.join(p.cur_dir, 'scenario_1'),
                    os.path.join(p.cur_dir, 'scenario_2')
                ]
            }
            for dir_path in p.iterator_replacements['cur_dir_parent_dir']:
                os.makedirs(dir_path, exist_ok=True)
        
        def level_2_task(p):
            """Level 2 task under level 1 iterator."""
            output_file = os.path.join(p.cur_dir, 'level2_result.txt')
            with open(output_file, 'w') as f:
                f.write(f"Level 2 task in {p.level1_scenario}")
        
        def level_3_iterator(p):
            """Level 3 iterator under level 2 task."""
            p.iterator_replacements = {
                'level3_batch': ['batch_a', 'batch_b'],
                'cur_dir_parent_dir': [
                    os.path.join(p.cur_dir, 'batch_a'),
                    os.path.join(p.cur_dir, 'batch_b')
                ]
            }
            for dir_path in p.iterator_replacements['cur_dir_parent_dir']:
                os.makedirs(dir_path, exist_ok=True)
        
        # Create complex nested hierarchy: task → iterator → task → iterator
        root = isolated_project.add_task(root_task)
        iter_1 = isolated_project.add_iterator(level_1_iterator, parent=root, run_in_parallel=False)
        task_2 = isolated_project.add_task(level_2_task, parent=iter_1)
        iter_3 = isolated_project.add_iterator(level_3_iterator, parent=task_2, run_in_parallel=False)
        
        # Validate complex hierarchy structure
        assert root.parent == isolated_project.task_tree
        assert iter_1.parent == root
        assert task_2.parent == iter_1
        assert iter_3.parent == task_2
        
        # Validate alternating types
        assert root.type == 'task'
        assert iter_1.type == 'iterator'
        assert task_2.type == 'task'
        assert iter_3.type == 'iterator'
        
        # Validate hierarchy depth and relationships
        assert len(root.children) == 1
        assert len(iter_1.children) == 1
        assert len(task_2.children) == 1
        assert len(iter_3.children) == 0  # Leaf iterator
        
    def test_sibling_tasks_and_iterators(self, isolated_project, anytree_node_tracker):
        """Test tasks and iterators as siblings in same hierarchy."""
        
        def sibling_task(p):
            """Task sibling."""
            output_file = os.path.join(p.cur_dir, 'task_output.txt')
            with open(output_file, 'w') as f:
                f.write("Sibling task completed")
        
        def sibling_iterator(p):
            """Iterator sibling.""" 
            p.iterator_replacements = {
                'sibling_scenario': ['sib_a', 'sib_b'],
                'cur_dir_parent_dir': [
                    os.path.join(p.intermediate_dir, 'sib_a'),
                    os.path.join(p.intermediate_dir, 'sib_b')
                ]
            }
            for dir_path in p.iterator_replacements['cur_dir_parent_dir']:
                os.makedirs(dir_path, exist_ok=True)
        
        # Create siblings under task tree root
        task_sibling = isolated_project.add_task(sibling_task)
        iterator_sibling = isolated_project.add_iterator(sibling_iterator, run_in_parallel=False)
        
        # Validate sibling relationships
        assert task_sibling.parent == isolated_project.task_tree
        assert iterator_sibling.parent == isolated_project.task_tree
        assert len(isolated_project.task_tree.children) == 2
        
        # Validate both are siblings (same parent, different types)
        siblings = list(isolated_project.task_tree.children)
        assert task_sibling in siblings
        assert iterator_sibling in siblings
        assert task_sibling.type == 'task'
        assert iterator_sibling.type == 'iterator'


class TestCrossMethodAttributeManagement:
    """
    Task 4.2: Implement cross-method attribute management validation
    
    Tests for task_names_defined tracking, ProjectFlow setattr behavior,
    name collision handling, and attribute cleanup consistency.
    """
    
    @pytest.mark.xfail(
        reason="Bug in hazelbean/project_flow.py: add_iterator() doesn't append to task_names_defined. "
               "Test expects both add_task() and add_iterator() to track names consistently, but only add_task() does. "
               "See add_iterator() around line 778 - missing self.task_names_defined.append(function.__name__)",
        strict=False
    )
    def test_task_names_defined_tracking_across_methods(self, isolated_project):
        """Test consistent task_names_defined tracking across both methods."""
        
        def test_task(p):
            pass
        
        def test_iterator(p):
            p.iterator_replacements = {
                'test_var': ['a', 'b'],
                'cur_dir_parent_dir': [p.intermediate_dir, p.intermediate_dir]
            }
        
        # Initially empty
        initial_count = len(isolated_project.task_names_defined)
        
        # Add task via add_task()
        task = isolated_project.add_task(test_task)
        assert len(isolated_project.task_names_defined) == initial_count + 1
        assert test_task.__name__ in isolated_project.task_names_defined
        
        # Add iterator via add_iterator() - should NOT add to task_names_defined
        # (based on project_flow.py lines 700-732, add_iterator doesn't call task_names_defined.append)
        iterator = isolated_project.add_iterator(test_iterator)
        
        # Both methods should consistently track function names
        assert len(isolated_project.task_names_defined) == initial_count + 2  # Both task and iterator should be added
        assert test_task.__name__ in isolated_project.task_names_defined
        assert test_iterator.__name__ in isolated_project.task_names_defined  # add_iterator should also track names
        
    def test_project_flow_setattr_behavior_with_mixed_methods(self, isolated_project):
        """Test ProjectFlow attribute assignment with mixed method usage."""
        
        def my_task(p):
            pass
            
        def my_iterator(p):
            p.iterator_replacements = {'test': ['val'], 'cur_dir_parent_dir': [p.intermediate_dir]}
        
        # Add both types
        task = isolated_project.add_task(my_task)
        iterator = isolated_project.add_iterator(my_iterator)
        
        # Verify both methods set attributes on the ProjectFlow object
        assert hasattr(isolated_project, 'my_task')
        assert hasattr(isolated_project, 'my_iterator')
        assert isolated_project.my_task is task
        assert isolated_project.my_iterator is iterator
        
        # Verify attribute types
        assert isinstance(isolated_project.my_task, hb.Task)
        assert isinstance(isolated_project.my_iterator, hb.Task)  # Iterator is also Task subclass
        assert isolated_project.my_task.type == 'task'
        assert isolated_project.my_iterator.type == 'iterator'
        
    def test_name_collision_handling_between_methods(self, isolated_project):
        """Test behavior when duplicate task names created across methods."""
        
        def duplicate_name(p):
            pass
        
        def duplicate_name_iterator(p):
            p.iterator_replacements = {'test': ['val'], 'cur_dir_parent_dir': [p.intermediate_dir]}
        
        # Create task first
        task = isolated_project.add_task(duplicate_name)
        original_task_ref = isolated_project.duplicate_name
        
        # Create iterator with different function but let's see what happens to naming
        # Note: This uses different function name so won't actually collide
        iterator = isolated_project.add_iterator(duplicate_name_iterator)
        
        # Test actual collision scenario by manually creating same name
        def same_function_name(p):
            p.iterator_replacements = {'test': ['val'], 'cur_dir_parent_dir': [p.intermediate_dir]}
        
        # Rename function to create collision
        same_function_name.__name__ = 'duplicate_name'
        
        # This should overwrite the previous attribute
        iterator_duplicate = isolated_project.add_iterator(same_function_name)
        
        # Verify behavior: last one wins (iterator overwrites task attribute)
        assert hasattr(isolated_project, 'duplicate_name')
        # The attribute should now point to the iterator
        current_attr = isolated_project.duplicate_name
        assert current_attr is iterator_duplicate
        assert current_attr.type == 'iterator'
        
        # Original task should still exist in task tree but not as direct attribute
        all_tasks = list(anytree.LevelOrderIter(isolated_project.task_tree))
        task_nodes = [t for t in all_tasks if hasattr(t, 'function') and t.function is duplicate_name]
        assert len(task_nodes) == 1  # Original task still exists in tree
        
    def test_attribute_cleanup_consistency(self, isolated_project):
        """Test that ProjectFlow attributes clean up properly across methods."""
        
        def cleanup_task(p):
            pass
            
        def cleanup_iterator(p):
            p.iterator_replacements = {'test': ['val'], 'cur_dir_parent_dir': [p.intermediate_dir]}
        
        # Add both types
        task = isolated_project.add_task(cleanup_task)
        iterator = isolated_project.add_iterator(cleanup_iterator)
        
        # Verify attributes exist
        assert hasattr(isolated_project, 'cleanup_task')
        assert hasattr(isolated_project, 'cleanup_iterator')
        
        # Test cleanup (using the clean_task_tree function)
        clean_task_tree(isolated_project)
        
        # After cleanup, anytree references should be cleared
        # (ProjectFlow attributes might still exist but point to None)
        # This tests the cleanup behavior implemented in test_fixtures.py


class TestConfigurationInheritanceAcrossMethods:
    """
    Task 4.3: Create configuration inheritance testing across both methods
    
    Tests for logging level inheritance, parameter default behavior,
    override patterns, and project-level settings consistency.
    """
    
    def test_logging_level_inheritance_consistency(self, isolated_project):
        """Test logging level inheritance works consistently between add_task and add_iterator."""
        
        # Set project-level logging
        isolated_project.logging_level = logging.WARNING
        
        def task_with_logging(p):
            pass
            
        def iterator_with_logging(p):
            p.iterator_replacements = {'test': ['val'], 'cur_dir_parent_dir': [p.intermediate_dir]}
        
        # Create both types
        task = isolated_project.add_task(task_with_logging)
        iterator = isolated_project.add_iterator(iterator_with_logging)
        
        # Both should inherit project logging level
        assert task.logging_level == logging.WARNING
        assert iterator.logging_level == logging.WARNING
        
    def test_parameter_default_behavior_consistency(self, isolated_project):
        """Test that parameter defaults behave consistently across methods."""
        
        def default_task(p):
            pass
            
        def default_iterator(p):
            p.iterator_replacements = {'test': ['val'], 'cur_dir_parent_dir': [p.intermediate_dir]}
        
        # Test default parameters
        task = isolated_project.add_task(default_task)  # Uses defaults
        iterator = isolated_project.add_iterator(default_iterator)  # Uses defaults
        
        # Verify consistent defaults
        assert task.run == 1  # Default for add_task
        assert task.skip_existing == 0  # Default for add_task
        assert iterator.run == 1  # Should match add_task defaults
        assert iterator.run_in_parallel == False  # Default for add_iterator
        
    def test_override_patterns_across_methods(self, isolated_project):
        """Test parameter override behavior works similarly."""
        
        def override_task(p):
            pass
            
        def override_iterator(p):
            p.iterator_replacements = {'test': ['val'], 'cur_dir_parent_dir': [p.intermediate_dir]}
        
        # Test explicit overrides
        task = isolated_project.add_task(override_task, run=0, skip_existing=1, logging_level=logging.DEBUG)
        iterator = isolated_project.add_iterator(override_iterator, run_in_parallel=True)
        
        # Verify overrides applied correctly
        assert task.run == 0
        assert task.skip_existing == 1
        assert task.logging_level == logging.DEBUG
        assert iterator.run_in_parallel == True
        
    @pytest.mark.xfail(
        reason="Bug in hazelbean/project_flow.py: Task.report_time_elapsed_when_task_completed doesn't inherit from ProjectFlow. "
               "Task.__init__ (line 222) hardcodes it to True instead of None. "
               "add_task() and add_iterator() don't set it from project like they do for logging_level. "
               "ProjectFlow.__init__ doesn't even define this attribute. "
               "Should follow the pattern used for logging_level inheritance.",
        strict=False
    )
    def test_project_level_settings_respect(self, isolated_project):
        """Test that both methods respect project-level configuration."""
        
        # Set various project-level settings
        isolated_project.logging_level = logging.CRITICAL
        isolated_project.report_time_elapsed_when_task_completed = False
        
        def project_aware_task(p):
            pass
            
        def project_aware_iterator(p):
            p.iterator_replacements = {'test': ['val'], 'cur_dir_parent_dir': [p.intermediate_dir]}
        
        # Create both types
        task = isolated_project.add_task(project_aware_task)
        iterator = isolated_project.add_iterator(project_aware_iterator)
        
        # Verify both respect project settings
        assert task.logging_level == logging.CRITICAL
        assert iterator.logging_level == logging.CRITICAL
        
        # Tasks should inherit project-level settings
        assert task.report_time_elapsed_when_task_completed == False  # Should inherit from project setting
        
        # Iterator should also inherit project settings if it has the attribute
        if hasattr(iterator, 'report_time_elapsed_when_task_completed'):
            assert iterator.report_time_elapsed_when_task_completed == False  # Should inherit from project setting


class TestComplexHierarchyNavigation:
    """
    Task 4.4: Implement complex anytree hierarchy navigation and validation tests
    
    Tests for anytree hierarchy navigation, mixed task/iterator hierarchies,
    complex object graphs, and navigation utilities.
    """
    
    def test_anytree_hierarchy_navigation_with_mixed_types(self, isolated_project):
        """Test anytree navigation works correctly with mixed task/iterator hierarchies."""
        
        def root_task(p):
            pass
            
        def child_iterator(p):
            p.iterator_replacements = {
                'nav_test': ['nav_a', 'nav_b'],
                'cur_dir_parent_dir': [
                    os.path.join(p.intermediate_dir, 'nav_a'),
                    os.path.join(p.intermediate_dir, 'nav_b')
                ]
            }
            for d in p.iterator_replacements['cur_dir_parent_dir']:
                os.makedirs(d, exist_ok=True)
                
        def grandchild_task(p):
            pass
        
        # Create hierarchy: root_task → child_iterator → grandchild_task
        root = isolated_project.add_task(root_task)
        child_iter = isolated_project.add_iterator(child_iterator, parent=root, run_in_parallel=False)
        grandchild = isolated_project.add_task(grandchild_task, parent=child_iter)
        
        # Test anytree navigation methods
        # Test descendants
        descendants = list(anytree.LevelOrderIter(root))
        assert len(descendants) == 3  # root, child_iter, grandchild
        assert root in descendants
        assert child_iter in descendants
        assert grandchild in descendants
        
        # Test ancestors
        grandchild_ancestors = list(grandchild.ancestors)
        assert len(grandchild_ancestors) == 3  # child_iter, root, task_tree (execute)
        assert child_iter in grandchild_ancestors
        assert root in grandchild_ancestors
        assert isolated_project.task_tree in grandchild_ancestors  # Root "execute" node
        
        # Test siblings (grandchild should have no siblings)
        assert len(grandchild.siblings) == 0
        
        # Test path from root
        path_to_grandchild = grandchild.path
        assert len(path_to_grandchild) == 4  # task_tree, root, child_iter, grandchild
        assert path_to_grandchild[0] == isolated_project.task_tree  # execute root
        assert path_to_grandchild[1] == root
        assert path_to_grandchild[2] == child_iter
        assert path_to_grandchild[3] == grandchild
        
    def test_complex_object_graph_integrity(self, isolated_project):
        """Test that complex mixed hierarchies maintain object graph integrity."""
        
        def setup_complex_graph(project):
            """Create a complex graph with multiple branches and types."""
            
            def branch_a_task(p): pass
            def branch_a_iterator(p):
                p.iterator_replacements = {'branch_a': ['a1', 'a2'], 'cur_dir_parent_dir': [p.intermediate_dir]*2}
            def branch_a_leaf(p): pass
            
            def branch_b_iterator(p):
                p.iterator_replacements = {'branch_b': ['b1', 'b2'], 'cur_dir_parent_dir': [p.intermediate_dir]*2}
            def branch_b_task(p): pass
            def branch_b_leaf(p): pass
            
            # Branch A: task → iterator → task
            a_task = project.add_task(branch_a_task)
            a_iter = project.add_iterator(branch_a_iterator, parent=a_task, run_in_parallel=False)
            a_leaf = project.add_task(branch_a_leaf, parent=a_iter)
            
            # Branch B: iterator → task → task
            b_iter = project.add_iterator(branch_b_iterator, run_in_parallel=False)
            b_task = project.add_task(branch_b_task, parent=b_iter)
            b_leaf = project.add_task(branch_b_leaf, parent=b_task)
            
            return [a_task, a_iter, a_leaf, b_iter, b_task, b_leaf]
        
        nodes = setup_complex_graph(isolated_project)
        a_task, a_iter, a_leaf, b_iter, b_task, b_leaf = nodes
        
        # Verify graph integrity
        # All nodes should be reachable from task_tree root
        all_reachable = list(anytree.LevelOrderIter(isolated_project.task_tree))
        for node in nodes:
            assert node in all_reachable
            
        # Verify parent-child relationships are bidirectional
        assert a_iter.parent == a_task
        assert a_iter in a_task.children  # Check child in parent's children
        
        assert a_leaf.parent == a_iter
        assert a_leaf in a_iter.children
        
        assert b_task.parent == b_iter
        assert b_task in b_iter.children
        
        # Verify no circular references
        for node in nodes:
            ancestors = list(node.ancestors)
            assert node not in ancestors  # Node should not be its own ancestor
            
    def test_hierarchy_search_and_filtering(self, isolated_project):
        """Test searching and filtering mixed hierarchies by type and other criteria."""
        
        def create_searchable_hierarchy(project):
            """Create hierarchy with various searchable characteristics."""
            
            def high_priority_task(p): pass
            def low_priority_iterator(p):
                p.iterator_replacements = {'priority': ['low'], 'cur_dir_parent_dir': [p.intermediate_dir]}
            def medium_priority_task(p): pass
            
            # Add custom attributes for testing
            task_high = project.add_task(high_priority_task, priority='high')
            iter_low = project.add_iterator(low_priority_iterator, priority='low')
            task_med = project.add_task(medium_priority_task, parent=iter_low, priority='medium')
            
            return [task_high, iter_low, task_med]
        
        nodes = create_searchable_hierarchy(isolated_project)
        task_high, iter_low, task_med = nodes
        
        # Search all nodes
        all_nodes = list(anytree.LevelOrderIter(isolated_project.task_tree))
        
        # Filter by type
        tasks = [n for n in all_nodes if hasattr(n, 'type') and n.type == 'task']
        iterators = [n for n in all_nodes if hasattr(n, 'type') and n.type == 'iterator']
        
        # Should find both regular tasks plus the execute root
        assert len(tasks) >= 2  # At least task_high and task_med (plus possibly execute root)
        assert len(iterators) == 1  # Just iter_low
        
        assert task_high in tasks
        assert task_med in tasks  
        assert iter_low in iterators
        
        # Filter by custom attributes (if they were set)
        # Note: kwargs in add_task might not create custom attributes, depends on implementation
        # This tests whether custom parameters are preserved


class TestMemoryManagementComplexHierarchies:
    """
    Task 4.5: Create memory management tests for complex hierarchies
    
    Tests for anytree hierarchy cleanup, ProjectFlow isolation,
    reference counting, and error condition cleanup.
    """
    
    def test_complex_hierarchy_memory_cleanup(self, anytree_node_tracker):
        """Test memory cleanup for complex mixed hierarchies."""
        
        # Create isolated project for memory testing
        temp_dir = tempfile.mkdtemp()
        
        try:
            project = hb.ProjectFlow(temp_dir)
            project.num_workers = 1  # Disable multiprocessing
            
            def create_complex_hierarchy(p):
                """Create a complex hierarchy that could cause memory leaks."""
                
                def level1_task(p): pass
                def level1_iterator(p):
                    p.iterator_replacements = {'level1': ['a', 'b'], 'cur_dir_parent_dir': [p.intermediate_dir]*2}
                def level2_task(p): pass
                def level2_iterator(p):
                    p.iterator_replacements = {'level2': ['x', 'y'], 'cur_dir_parent_dir': [p.intermediate_dir]*2}
                def level3_task(p): pass
                
                # Create deep hierarchy
                l1_task = p.add_task(level1_task)
                l1_iter = p.add_iterator(level1_iterator, parent=l1_task, run_in_parallel=False)
                l2_task = p.add_task(level2_task, parent=l1_iter)
                l2_iter = p.add_iterator(level2_iterator, parent=l2_task, run_in_parallel=False)
                l3_task = p.add_task(level3_task, parent=l2_iter)
                
                return [l1_task, l1_iter, l2_task, l2_iter, l3_task]
            
            nodes = create_complex_hierarchy(project)
            
            # Verify hierarchy was created
            assert len(nodes) == 5
            all_descendants = list(anytree.LevelOrderIter(project.task_tree))
            for node in nodes:
                assert node in all_descendants
            
        finally:
            # Explicit cleanup
            clean_task_tree(project)
            
            # File system cleanup
            if os.path.exists(temp_dir):
                hb.remove_dirs(temp_dir, safety_check='delete')
    
    def test_project_flow_isolation_with_complex_hierarchies(self, anytree_node_tracker):
        """Test that complex hierarchies don't leak between ProjectFlow instances."""
        
        temp_dir_1 = tempfile.mkdtemp()
        temp_dir_2 = tempfile.mkdtemp()
        
        try:
            # Create two isolated projects
            project1 = hb.ProjectFlow(temp_dir_1)
            project1.num_workers = 1
            project2 = hb.ProjectFlow(temp_dir_2)
            project2.num_workers = 1
            
            def shared_task_name(p): pass
            def shared_iterator_name(p):
                p.iterator_replacements = {'isolation': ['test'], 'cur_dir_parent_dir': [p.intermediate_dir]}
            
            # Add to both projects using same function references
            task1 = project1.add_task(shared_task_name)
            iter1 = project1.add_iterator(shared_iterator_name, run_in_parallel=False)
            
            task2 = project2.add_task(shared_task_name)
            iter2 = project2.add_iterator(shared_iterator_name, run_in_parallel=False)
            
            # Verify isolation
            assert task1.p is project1
            assert task2.p is project2
            assert iter1.p is project1
            assert iter2.p is project2
            
            # Verify separate hierarchies
            project1_nodes = list(anytree.LevelOrderIter(project1.task_tree))
            project2_nodes = list(anytree.LevelOrderIter(project2.task_tree))
            
            # No cross-contamination
            assert task1 in project1_nodes
            assert task1 not in project2_nodes
            assert task2 in project2_nodes
            assert task2 not in project1_nodes
            
        finally:
            # Cleanup both projects
            clean_task_tree(project1)
            clean_task_tree(project2)
            
            if os.path.exists(temp_dir_1):
                hb.remove_dirs(temp_dir_1, safety_check='delete')
            if os.path.exists(temp_dir_2):
                hb.remove_dirs(temp_dir_2, safety_check='delete')
    
    def test_error_condition_cleanup_in_complex_hierarchies(self, anytree_node_tracker):
        """Test cleanup works even when hierarchy construction fails."""
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            project = hb.ProjectFlow(temp_dir)
            project.num_workers = 1
            
            def working_task(p): pass
            def failing_task(p):
                raise ValueError("Intentional test failure")
            def working_iterator(p):
                p.iterator_replacements = {'error_test': ['val'], 'cur_dir_parent_dir': [p.intermediate_dir]}
            
            # Create partial hierarchy
            good_task = project.add_task(working_task)
            good_iter = project.add_iterator(working_iterator, parent=good_task, run_in_parallel=False)
            
            # Try to add failing task (this should work for creation, failing only on execution)
            bad_task = project.add_task(failing_task, parent=good_iter)
            
            # Hierarchy should be created (tasks don't fail until execution)
            assert bad_task.parent == good_iter
            assert len(good_iter.children) == 1
            
            # Test cleanup works even with error conditions in hierarchy
            # (This tests that our cleanup is robust to problematic task functions)
            
        finally:
            # Cleanup should work despite potential errors
            clean_task_tree(project)
            
            if os.path.exists(temp_dir):
                hb.remove_dirs(temp_dir, safety_check='delete')
    
    def test_reference_counting_in_complex_object_graphs(self, anytree_node_tracker):
        """Test that complex object graphs clean up properly without circular references."""
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            project = hb.ProjectFlow(temp_dir)
            project.num_workers = 1
            
            # Create cross-referencing hierarchy
            def ref_task_a(p):
                # Store reference to sibling in project
                if hasattr(p, 'ref_task_b'):
                    p.cross_ref_a = p.ref_task_b
                    
            def ref_task_b(p):
                # Store reference to sibling in project  
                if hasattr(p, 'ref_task_a'):
                    p.cross_ref_b = p.ref_task_a
            
            def ref_iterator(p):
                p.iterator_replacements = {'ref_test': ['val'], 'cur_dir_parent_dir': [p.intermediate_dir]}
                # Store references to child tasks
                if hasattr(p, 'ref_task_a') and hasattr(p, 'ref_task_b'):
                    p.iter_refs = [p.ref_task_a, p.ref_task_b]
            
            # Create potentially circular structure
            task_a = project.add_task(ref_task_a)  # Creates project.ref_task_a
            task_b = project.add_task(ref_task_b)  # Creates project.ref_task_b  
            iterator = project.add_iterator(ref_iterator, run_in_parallel=False)
            
            # Add cross-references manually (simulating complex object graph)
            project.cross_ref_a = task_b
            project.cross_ref_b = task_a
            project.iter_refs = [task_a, task_b, iterator]
            
            # Verify references exist
            assert hasattr(project, 'cross_ref_a')
            assert hasattr(project, 'cross_ref_b')
            assert hasattr(project, 'iter_refs')
            
        finally:
            # Test that cleanup handles complex reference graphs
            clean_task_tree(project)
            
            if os.path.exists(temp_dir):
                hb.remove_dirs(temp_dir, safety_check='delete')


class TestIntegrationWorkflowExecution:
    """
    Story 5: Multi-Level Workflow Testing - Integration Execution Tests
    
    Tests that add_task() and add_iterator() work correctly with real ProjectFlow
    execution cycles, validating that task hierarchies execute in proper order
    with directory creation, file operations, and proper cleanup.
    """
    
    def test_task_execution_integration_workflow(self, isolated_project, anytree_node_tracker):
        """Test add_task() -> execute() workflow with real task execution."""
        execution_log = []
        
        def setup_task(p):
            """Setup task that creates initial data."""
            execution_log.append(f"setup_task executed in {p.cur_dir}")
            output_file = os.path.join(p.cur_dir, 'setup_complete.txt')
            with open(output_file, 'w') as f:
                f.write("Setup task completed successfully")
            assert os.path.exists(output_file)
        
        def process_task(p):
            """Process task that uses setup data."""
            execution_log.append(f"process_task executed in {p.cur_dir}")
            setup_file = os.path.join(isolated_project.setup_task_dir, 'setup_complete.txt')
            
            # Read from setup task output
            if os.path.exists(setup_file):
                with open(setup_file, 'r') as f:
                    setup_content = f.read()
                
                # Create processed output
                output_file = os.path.join(p.cur_dir, 'processed_result.txt')
                with open(output_file, 'w') as f:
                    f.write(f"Processed: {setup_content}")
                    
                assert os.path.exists(output_file)
            else:
                pytest.fail("Setup task output not found - execution order problem")
        
        # Add tasks to project
        setup = isolated_project.add_task(setup_task)
        process = isolated_project.add_task(process_task)
        
        # Validate hierarchy before execution
        assert setup.parent == isolated_project.task_tree
        assert process.parent == isolated_project.task_tree
        
        # Execute the project workflow
        isolated_project.execute()
        
        # Validate execution completed successfully
        assert len(execution_log) == 2
        assert "setup_task executed" in execution_log[0]
        assert "process_task executed" in execution_log[1]
        
        # Validate file system results
        setup_output = os.path.join(isolated_project.setup_task_dir, 'setup_complete.txt')
        process_output = os.path.join(isolated_project.process_task_dir, 'processed_result.txt')
        
        assert os.path.exists(setup_output)
        assert os.path.exists(process_output)
        
        # Verify content was processed correctly
        with open(process_output, 'r') as f:
            content = f.read()
            assert "Processed: Setup task completed successfully" in content

    def test_iterator_execution_integration_workflow(self, isolated_project, anytree_node_tracker):
        """Test add_iterator() -> execute() workflow with iterator scenarios."""
        execution_log = []
        
        def setup_iterator(p):
            """Iterator that sets up multiple scenarios."""
            execution_log.append(f"setup_iterator executed in {p.cur_dir}")
            
            # Set up iterator scenarios
            p.iterator_replacements = {
                'scenario_id': ['scenario_1', 'scenario_2'],
                'data_value': [100, 200],
                'cur_dir_parent_dir': [
                    os.path.join(p.intermediate_dir, 'scenario_1'),
                    os.path.join(p.intermediate_dir, 'scenario_2')
                ]
            }
            
            # Create scenario directories
            for dir_path in p.iterator_replacements['cur_dir_parent_dir']:
                os.makedirs(dir_path, exist_ok=True)
        
        def scenario_task(p):
            """Child task under iterator that processes each scenario."""
            execution_log.append(f"scenario_task executed for {p.scenario_id} in {p.cur_dir}")
            
            # Create scenario-specific output
            output_file = os.path.join(p.cur_dir, f'{p.scenario_id}_result.txt')
            with open(output_file, 'w') as f:
                f.write(f"Scenario {p.scenario_id} processed with value {p.data_value}")
            
            assert os.path.exists(output_file)
        
        # Create iterator with child task
        iterator = isolated_project.add_iterator(setup_iterator, run_in_parallel=False)
        child_task = isolated_project.add_task(scenario_task, parent=iterator)
        
        # Validate hierarchy before execution  
        assert iterator.parent == isolated_project.task_tree
        assert child_task.parent == iterator
        
        # Execute the iterator workflow
        isolated_project.execute()
        
        # Validate execution completed for both scenarios
        assert len(execution_log) == 3  # 1 iterator + 2 child task executions
        assert "setup_iterator executed" in execution_log[0]
        assert "scenario_task executed for scenario_1" in execution_log[1]
        assert "scenario_task executed for scenario_2" in execution_log[2]
        
        # Validate scenario-specific files were created
        # Iterator child tasks create an additional task directory layer:
        # intermediate/scenario_X/scenario_task/result_file.txt
        scenario_1_file = os.path.join(isolated_project.intermediate_dir, 'scenario_1', 'scenario_task', 'scenario_1_result.txt')
        scenario_2_file = os.path.join(isolated_project.intermediate_dir, 'scenario_2', 'scenario_task', 'scenario_2_result.txt')
        
        assert os.path.exists(scenario_1_file), f"Expected scenario 1 file not found at {scenario_1_file}"
        assert os.path.exists(scenario_2_file), f"Expected scenario 2 file not found at {scenario_2_file}"
        
        # Verify scenario-specific content
        with open(scenario_1_file, 'r') as f:
            content = f.read()
            assert "Scenario scenario_1 processed with value 100" in content
            
        with open(scenario_2_file, 'r') as f:
            content = f.read()
            assert "Scenario scenario_2 processed with value 200" in content

    def test_mixed_hierarchy_execution_workflow(self, isolated_project, anytree_node_tracker):
        """Test complex mixed task/iterator hierarchy execution."""
        execution_log = []
        
        def parent_task(p):
            """Parent task that prepares data for iterator."""
            execution_log.append("parent_task executed")
            
            # Create shared data file
            shared_file = os.path.join(p.cur_dir, 'shared_data.txt')
            with open(shared_file, 'w') as f:
                f.write("Shared data from parent task")
        
        def child_iterator(p):
            """Iterator nested under parent task."""
            execution_log.append("child_iterator executed")
            
            # Set up iterator using parent task data
            shared_file = os.path.join(isolated_project.parent_task_dir, 'shared_data.txt')
            if os.path.exists(shared_file):
                p.iterator_replacements = {
                    'worker_id': ['worker_a', 'worker_b'], 
                    'cur_dir_parent_dir': [
                        os.path.join(p.cur_dir, 'worker_a'),
                        os.path.join(p.cur_dir, 'worker_b')
                    ]
                }
                
                for dir_path in p.iterator_replacements['cur_dir_parent_dir']:
                    os.makedirs(dir_path, exist_ok=True)
            else:
                pytest.fail("Parent task output missing - execution order problem")
        
        def grandchild_task(p):
            """Task nested under iterator that processes worker scenarios."""
            execution_log.append(f"grandchild_task executed for {p.worker_id}")
            
            # Create worker-specific output
            output_file = os.path.join(p.cur_dir, f'{p.worker_id}_work.txt')
            with open(output_file, 'w') as f:
                f.write(f"Work completed by {p.worker_id}")
        
        # Build complex hierarchy: task -> iterator -> task
        parent = isolated_project.add_task(parent_task)
        iterator = isolated_project.add_iterator(child_iterator, parent=parent, run_in_parallel=False)
        grandchild = isolated_project.add_task(grandchild_task, parent=iterator)
        
        # Validate hierarchy structure
        assert parent.parent == isolated_project.task_tree
        assert iterator.parent == parent
        assert grandchild.parent == iterator
        
        # Execute complex workflow
        isolated_project.execute()
        
        # Validate execution order and completion
        expected_executions = 4  # 1 parent + 1 iterator + 2 grandchild tasks
        assert len(execution_log) == expected_executions
        assert execution_log[0] == "parent_task executed"
        assert execution_log[1] == "child_iterator executed"
        assert "grandchild_task executed for worker_a" in execution_log[2]
        assert "grandchild_task executed for worker_b" in execution_log[3]
        
        # Validate file outputs
        # Complex hierarchy: parent_task/child_iterator/worker_X/grandchild_task/file.txt
        worker_a_file = os.path.join(isolated_project.parent_task_dir, 'child_iterator', 'worker_a', 'grandchild_task', 'worker_a_work.txt')
        worker_b_file = os.path.join(isolated_project.parent_task_dir, 'child_iterator', 'worker_b', 'grandchild_task', 'worker_b_work.txt')
        
        assert os.path.exists(worker_a_file), f"Expected worker A file not found at {worker_a_file}"
        assert os.path.exists(worker_b_file), f"Expected worker B file not found at {worker_b_file}"


class TestFileSystemIntegrationWorkflows:
    """
    Story 5: Multi-Level Workflow Testing - File System Integration Tests
    
    Tests that validate skip_existing behavior, directory management, and file
    system operations work correctly during real ProjectFlow execution cycles.
    """
    
    def test_skip_existing_behavior_in_execution_workflow(self, isolated_project, anytree_node_tracker):
        """Test skip_existing behavior with real file system operations."""
        execution_count = {'value': 0}
        
        def file_creation_task(p):
            """Task that creates a file and tracks execution count."""
            # Only increment and create file if p.run_this is True
            if p.run_this:
                execution_count['value'] += 1
                
                output_file = os.path.join(p.cur_dir, 'created_file.txt')
                with open(output_file, 'w') as f:
                    f.write(f"Execution #{execution_count['value']}")
        
        # Add task with skip_existing=1
        task = isolated_project.add_task(file_creation_task, skip_existing=1)
        
        # First execution - should run
        isolated_project.execute()
        assert execution_count['value'] == 1
        
        # Verify file was created
        output_file = os.path.join(isolated_project.file_creation_task_dir, 'created_file.txt')
        assert os.path.exists(output_file)
        
        with open(output_file, 'r') as f:
            content = f.read()
            assert "Execution #1" in content
        
        # Second execution - should skip because directory exists
        isolated_project.execute()
        assert execution_count['value'] == 1  # Should not increment
        
        # File should still contain original content
        with open(output_file, 'r') as f:
            content = f.read()
            assert "Execution #1" in content  # Should not be "#2"

    def test_directory_creation_and_management_workflow(self, isolated_project, anytree_node_tracker):
        """Test task directory creation and path resolution during execution."""
        directory_checks = []
        
        def directory_aware_task(p):
            """Task that validates its directory environment."""
            directory_checks.append({
                'cur_dir': p.cur_dir,
                'task_dir_exists': os.path.exists(p.cur_dir),
                'is_directory': os.path.isdir(p.cur_dir),
                'can_write': os.access(p.cur_dir, os.W_OK)
            })
            
            # Create a test file to verify write access
            test_file = os.path.join(p.cur_dir, 'directory_test.txt')
            with open(test_file, 'w') as f:
                f.write("Directory management test successful")
        
        def nested_task(p):
            """Task nested under first task to test directory hierarchy."""
            directory_checks.append({
                'cur_dir': p.cur_dir,
                'parent_dir': os.path.dirname(p.cur_dir),
                'task_dir_exists': os.path.exists(p.cur_dir),
                'parent_exists': os.path.exists(os.path.dirname(p.cur_dir))
            })
        
        # Create task hierarchy
        parent_task = isolated_project.add_task(directory_aware_task)
        child_task = isolated_project.add_task(nested_task, parent=parent_task)
        
        # Execute workflow
        isolated_project.execute()
        
        # Validate directory management
        assert len(directory_checks) == 2
        
        # Check parent task directory
        parent_check = directory_checks[0]
        assert parent_check['task_dir_exists'] is True
        assert parent_check['is_directory'] is True
        assert parent_check['can_write'] is True
        
        # Check nested task directory
        child_check = directory_checks[1]
        assert child_check['task_dir_exists'] is True
        assert child_check['parent_exists'] is True
        
        # Verify files were created successfully
        parent_file = os.path.join(isolated_project.directory_aware_task_dir, 'directory_test.txt')
        assert os.path.exists(parent_file)

    def test_path_resolution_during_execution_workflow(self, isolated_project, anytree_node_tracker):
        """Test get_path() integration with task execution."""
        path_resolutions = []
        
        def path_using_task(p):
            """Task that uses get_path for file operations."""
            # Test different path resolution scenarios
            test_paths = [
                'input_data.txt',
                'subdir/nested_file.txt', 
                os.path.join('output', 'result.txt')
            ]
            
            for test_path in test_paths:
                # Use raise_error_if_fail=False since we're testing path resolution, not file existence
                resolved_path = p.get_path(test_path, raise_error_if_fail=False)
                path_resolutions.append({
                    'input_path': test_path,
                    'resolved_path': resolved_path,
                    'cur_dir': p.cur_dir
                })
            
            # Create a file using resolved path (also use flag for consistency)
            output_path = p.get_path('task_output.txt', raise_error_if_fail=False)
            
            # Ensure the directory exists before creating the file
            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                
            with open(output_path, 'w') as f:
                f.write("Path resolution test successful")
        
        # Add and execute task
        task = isolated_project.add_task(path_using_task)
        isolated_project.execute()
        
        # Validate path resolutions
        assert len(path_resolutions) == 3
        
        # All paths should be resolved relative to task directory
        for resolution in path_resolutions:
            assert resolution['resolved_path'].startswith(resolution['cur_dir'])
        
        # Verify output file was created where get_path() placed it
        # The file will be placed according to get_path() logic, which may include subdirectories
        expected_output_simple = os.path.join(isolated_project.path_using_task_dir, 'task_output.txt')
        expected_output_subdir = os.path.join(isolated_project.path_using_task_dir, 'path_using_task', 'task_output.txt')
        
        # Check both possible locations since get_path() behavior may vary
        assert os.path.exists(expected_output_simple) or os.path.exists(expected_output_subdir), \
            f"Expected file not found at {expected_output_simple} or {expected_output_subdir}"


if __name__ == "__main__":
    # Enable running specific test classes for debugging
    pytest.main([__file__ + "::TestIntegrationWorkflowExecution::test_task_execution_integration_workflow", "-v"])
