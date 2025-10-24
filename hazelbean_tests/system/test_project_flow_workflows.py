"""
System-Level Workflow Tests for ProjectFlow add_task() and add_iterator()

Tests complete project lifecycles with real file system operations, full 
execution workflows, and end-to-end validation of task management methods
in realistic project scenarios.

Story 5: Multi-Level Workflow Testing (System Workflow Tests)

NOTE: Tests may fail due to discovered bugs in hazelbean ProjectFlow workflows.
These failures help identify real issues in the codebase vs test setup problems.
See ../KNOWN_BUGS.md for details on known workflow issues.
"""

import pytest
import os
import tempfile
import shutil
import gc
import logging
from unittest.mock import Mock, patch
import sys
import time

# Add hazelbean to path
sys.path.extend(['../..'])

import hazelbean as hb
import anytree
from hazelbean_tests.unit.test_fixtures import (
    isolated_project, anytree_node_tracker, clean_task_tree
)


class TestEndToEndProjectLifecycles:
    """
    Story 5: System workflow tests for complete project lifecycles
    
    Tests full project creation → task definition → execution → cleanup
    workflows to validate that add_task() and add_iterator() work correctly
    in complete ProjectFlow execution cycles.
    """
    
    def test_complete_project_creation_to_cleanup_lifecycle(self, temp_dir):
        """Test full project lifecycle from creation to cleanup."""
        lifecycle_log = []
        
        # Phase 1: Project Creation
        project_dir = os.path.join(temp_dir, 'test_project')
        p = hb.ProjectFlow(project_dir)
        
        lifecycle_log.append("project_created")
        
        # Validate project directories were created
        assert os.path.exists(p.project_dir)
        # Note: intermediate_dir is created during execution, not at project creation
        
        # Phase 2: Task Definition
        def data_preparation_task(p):
            """Prepare initial data files."""
            lifecycle_log.append("data_preparation_executed")
            
            # Create input data
            input_file = os.path.join(p.cur_dir, 'input_data.txt')
            with open(input_file, 'w') as f:
                f.write("Initial data for processing")
        
        def processing_iterator(p):
            """Process data in multiple scenarios."""
            lifecycle_log.append("processing_iterator_executed")
            
            # Set up processing scenarios
            p.iterator_replacements = {
                'process_type': ['clean', 'validate', 'transform'],
                'cur_dir_parent_dir': [
                    os.path.join(p.intermediate_dir, 'clean'),
                    os.path.join(p.intermediate_dir, 'validate'),
                    os.path.join(p.intermediate_dir, 'transform')
                ]
            }
            
            for dir_path in p.iterator_replacements['cur_dir_parent_dir']:
                os.makedirs(dir_path, exist_ok=True)
        
        def scenario_processing_task(p):
            """Process each scenario."""
            lifecycle_log.append(f"scenario_processing_executed_{p.process_type}")
            
            # Read input data
            input_file = os.path.join(p.data_preparation_task_dir, 'input_data.txt')
            if os.path.exists(input_file):
                with open(input_file, 'r') as f:
                    input_data = f.read()
                
                # Create scenario output
                output_file = os.path.join(p.cur_dir, f'{p.process_type}_result.txt')
                with open(output_file, 'w') as f:
                    f.write(f"{p.process_type.title()} processing: {input_data}")
            else:
                pytest.fail(f"Input data not found for {p.process_type} processing")
        
        def results_compilation_task(p):
            """Compile all processing results."""
            lifecycle_log.append("results_compilation_executed")
            
            # Collect results from all scenarios - files are in task subdirectories
            scenario_results = []
            for process_type in ['clean', 'validate', 'transform']:
                result_file = os.path.join(
                    p.intermediate_dir, process_type, 'scenario_processing_task', f'{process_type}_result.txt'
                )
                if os.path.exists(result_file):
                    with open(result_file, 'r') as f:
                        scenario_results.append(f.read())
            
            # Create final compilation
            final_output = os.path.join(p.cur_dir, 'final_results.txt')
            with open(final_output, 'w') as f:
                f.write("Compiled Results:\n")
                f.write("\n".join(scenario_results))
        
        # Build project workflow
        data_prep = p.add_task(data_preparation_task)
        processing = p.add_iterator(processing_iterator, run_in_parallel=False)
        scenario_task = p.add_task(scenario_processing_task, parent=processing)
        results = p.add_task(results_compilation_task)
        
        lifecycle_log.append("tasks_defined")
        
        # Phase 3: Execution
        p.execute()
        lifecycle_log.append("execution_completed")
        
        # Phase 4: Validation
        assert len(lifecycle_log) == 9  # 1 created + 1 defined + 1 data_prep + 1 iterator + 3 scenarios + 1 compilation + 1 execution_completed
        
        # Validate execution order
        expected_order = [
            "project_created",
            "tasks_defined", 
            "data_preparation_executed",
            "processing_iterator_executed",
            "scenario_processing_executed_clean",
            "scenario_processing_executed_validate", 
            "scenario_processing_executed_transform",
            "results_compilation_executed",
            "execution_completed"
        ]
        
        for i, expected in enumerate(expected_order):
            assert lifecycle_log[i].startswith(expected) or lifecycle_log[i] == expected
        
        # Validate file outputs
        input_file = os.path.join(p.data_preparation_task_dir, 'input_data.txt')
        final_results = os.path.join(p.results_compilation_task_dir, 'final_results.txt')
        
        assert os.path.exists(input_file)
        assert os.path.exists(final_results)
        
        # Validate final results content
        with open(final_results, 'r') as f:
            content = f.read()
            assert "Clean processing: Initial data" in content
            assert "Validate processing: Initial data" in content
            assert "Transform processing: Initial data" in content
        
        # Phase 5: Cleanup (handled by temp_dir fixture)
        lifecycle_log.append("cleanup_ready")

    def test_multi_stage_project_workflow_with_dependencies(self, temp_dir):
        """Test complex multi-stage project with task dependencies."""
        stage_tracking = {'current_stage': 0, 'completed_stages': []}
        
        project_dir = os.path.join(temp_dir, 'multi_stage_project')
        p = hb.ProjectFlow(project_dir)
        
        def stage_1_setup(p):
            """Stage 1: Initial setup and configuration."""
            stage_tracking['current_stage'] = 1
            stage_tracking['completed_stages'].append(1)
            
            config_file = os.path.join(p.cur_dir, 'project_config.txt')
            with open(config_file, 'w') as f:
                f.write("project_version=1.0\nprocessing_mode=batch\noutput_format=csv")
        
        def stage_2_data_collection_iterator(p):
            """Stage 2: Collect data from multiple sources."""
            stage_tracking['current_stage'] = 2
            stage_tracking['completed_stages'].append(2)
            
            # Verify stage 1 completed
            config_file = os.path.join(p.stage_1_setup_dir, 'project_config.txt')
            assert os.path.exists(config_file), "Stage 1 dependency not met"
            
            # Set up data collection scenarios
            p.iterator_replacements = {
                'data_source': ['database', 'api', 'files'],
                'cur_dir_parent_dir': [
                    os.path.join(p.cur_dir, 'database_collection'),
                    os.path.join(p.cur_dir, 'api_collection'),
                    os.path.join(p.cur_dir, 'files_collection')
                ]
            }
            
            for dir_path in p.iterator_replacements['cur_dir_parent_dir']:
                os.makedirs(dir_path, exist_ok=True)
        
        def data_collection_task(p):
            """Collect data from specific source."""
            collected_file = os.path.join(p.cur_dir, f'{p.data_source}_data.txt')
            with open(collected_file, 'w') as f:
                f.write(f"Data collected from {p.data_source} source")
        
        def stage_3_processing(p):
            """Stage 3: Process all collected data."""
            stage_tracking['current_stage'] = 3
            stage_tracking['completed_stages'].append(3)
            
            # Verify stage 2 dependencies - files are in task subdirectories
            required_files = [
                'database_collection/data_collection_task/database_data.txt',
                'api_collection/data_collection_task/api_data.txt', 
                'files_collection/data_collection_task/files_data.txt'
            ]
            
            stage_2_dir = p.stage_2_data_collection_iterator_dir
            for req_file in required_files:
                full_path = os.path.join(stage_2_dir, req_file)
                assert os.path.exists(full_path), f"Stage 2 dependency missing: {req_file}"
            
            # Process all data
            processed_data = []
            for req_file in required_files:
                full_path = os.path.join(stage_2_dir, req_file)
                with open(full_path, 'r') as f:
                    processed_data.append(f.read())
            
            # Create processed output
            output_file = os.path.join(p.cur_dir, 'processed_data.txt')
            with open(output_file, 'w') as f:
                f.write("Processed Data:\n")
                f.write("\n".join(processed_data))
        
        def stage_4_final_output(p):
            """Stage 4: Generate final project outputs."""
            stage_tracking['current_stage'] = 4
            stage_tracking['completed_stages'].append(4)
            
            # Verify all previous stage dependencies
            dependencies = [
                (p.stage_1_setup_dir, 'project_config.txt'),
                (p.stage_3_processing_dir, 'processed_data.txt')
            ]
            
            for dep_dir, dep_file in dependencies:
                dep_path = os.path.join(dep_dir, dep_file)
                assert os.path.exists(dep_path), f"Dependency missing: {dep_path}"
            
            # Generate final output
            final_output = os.path.join(p.cur_dir, 'project_final_output.txt')
            with open(final_output, 'w') as f:
                f.write("Project completed successfully\n")
                f.write(f"Completed stages: {stage_tracking['completed_stages']}\n")
                f.write(f"Final stage: {stage_tracking['current_stage']}")
        
        # Build multi-stage workflow
        stage_1 = p.add_task(stage_1_setup)
        stage_2_iterator = p.add_iterator(stage_2_data_collection_iterator, run_in_parallel=False)
        collection_task = p.add_task(data_collection_task, parent=stage_2_iterator)
        stage_3 = p.add_task(stage_3_processing)
        stage_4 = p.add_task(stage_4_final_output)
        
        # Execute complete workflow
        p.execute()
        
        # Validate workflow completion
        assert stage_tracking['current_stage'] == 4
        assert stage_tracking['completed_stages'] == [1, 2, 3, 4]
        
        # Validate final output exists and is correct
        final_output_path = os.path.join(p.stage_4_final_output_dir, 'project_final_output.txt')
        assert os.path.exists(final_output_path)
        
        with open(final_output_path, 'r') as f:
            content = f.read()
            assert "Project completed successfully" in content
            assert "[1, 2, 3, 4]" in content
            assert "Final stage: 4" in content

    def test_error_handling_in_complete_project_workflow(self, temp_dir):
        """Test error handling and recovery in complete project workflows."""
        error_tracking = {'errors_encountered': [], 'recovery_successful': False}
        
        project_dir = os.path.join(temp_dir, 'error_handling_project')
        p = hb.ProjectFlow(project_dir)
        
        def reliable_setup_task(p):
            """Task that always succeeds."""
            setup_file = os.path.join(p.cur_dir, 'setup_success.txt')
            with open(setup_file, 'w') as f:
                f.write("Setup completed successfully")
        
        def error_prone_iterator(p):
            """Iterator that may encounter issues but handles them gracefully."""
            try:
                p.iterator_replacements = {
                    'scenario': ['success', 'warning', 'recoverable'],
                    'cur_dir_parent_dir': [
                        os.path.join(p.cur_dir, 'success_scenario'),
                        os.path.join(p.cur_dir, 'warning_scenario'),
                        os.path.join(p.cur_dir, 'recoverable_scenario')
                    ]
                }
                
                for dir_path in p.iterator_replacements['cur_dir_parent_dir']:
                    os.makedirs(dir_path, exist_ok=True)
                    
            except Exception as e:
                error_tracking['errors_encountered'].append(f"Iterator setup error: {e}")
                # Recovery: set minimal scenarios
                p.iterator_replacements = {
                    'scenario': ['recovery'],
                    'cur_dir_parent_dir': [os.path.join(p.cur_dir, 'recovery_scenario')]
                }
                os.makedirs(p.iterator_replacements['cur_dir_parent_dir'][0], exist_ok=True)
        
        def scenario_handling_task(p):
            """Task that handles different scenario types."""
            scenario_type = p.scenario
            
            if scenario_type == 'success':
                # Normal processing
                output_file = os.path.join(p.cur_dir, 'success_result.txt')
                with open(output_file, 'w') as f:
                    f.write("Successfully processed")
                    
            elif scenario_type == 'warning':
                # Processing with warnings
                error_tracking['errors_encountered'].append(f"Warning in {scenario_type}")
                output_file = os.path.join(p.cur_dir, 'warning_result.txt')
                with open(output_file, 'w') as f:
                    f.write("Processed with warnings")
                    
            elif scenario_type == 'recoverable':
                # Recoverable error handling
                try:
                    # Simulate recoverable error
                    if not os.path.exists('/nonexistent/path'):
                        raise FileNotFoundError("Simulated recoverable error")
                except FileNotFoundError as e:
                    error_tracking['errors_encountered'].append(f"Recoverable error: {e}")
                    # Recovery action
                    output_file = os.path.join(p.cur_dir, 'recovered_result.txt')
                    with open(output_file, 'w') as f:
                        f.write("Recovered from error")
                        
            elif scenario_type == 'recovery':
                # Recovery scenario
                error_tracking['recovery_successful'] = True
                output_file = os.path.join(p.cur_dir, 'recovery_result.txt')
                with open(output_file, 'w') as f:
                    f.write("Recovery scenario executed")
        
        def cleanup_and_summary_task(p):
            """Final task that summarizes error handling."""
            summary_file = os.path.join(p.cur_dir, 'error_summary.txt')
            with open(summary_file, 'w') as f:
                f.write(f"Errors encountered: {len(error_tracking['errors_encountered'])}\n")
                f.write(f"Recovery successful: {error_tracking['recovery_successful']}\n")
                f.write("Error details:\n")
                for error in error_tracking['errors_encountered']:
                    f.write(f"- {error}\n")
        
        # Build error-handling workflow
        setup = p.add_task(reliable_setup_task)
        error_iterator = p.add_iterator(error_prone_iterator, run_in_parallel=False)
        scenario_task = p.add_task(scenario_handling_task, parent=error_iterator)
        cleanup = p.add_task(cleanup_and_summary_task)
        
        # Execute workflow (should complete despite errors)
        p.execute()
        
        # Validate error handling
        assert len(error_tracking['errors_encountered']) > 0  # Should have encountered some issues
        
        # Validate workflow completed
        summary_file = os.path.join(p.cleanup_and_summary_task_dir, 'error_summary.txt')
        assert os.path.exists(summary_file)
        
        # Validate error summary
        with open(summary_file, 'r') as f:
            content = f.read()
            assert "Errors encountered:" in content
            assert "Recovery successful:" in content


class TestRealFileSystemOperations:
    """
    Story 5: System workflow tests with real file system operations
    
    Tests that validate file creation, modification, cleanup, and directory
    management work correctly across complete project execution cycles.
    """
    
    def test_file_lifecycle_operations_workflow(self, temp_dir):
        """Test complete file lifecycle operations in project workflow."""
        file_operations = []
        
        project_dir = os.path.join(temp_dir, 'file_lifecycle_project')
        p = hb.ProjectFlow(project_dir)
        
        def file_creation_task(p):
            """Create various types of files."""
            file_operations.append("file_creation_started")
            
            # Create different file types
            files_to_create = [
                ('data.txt', 'Sample text data'),
                ('config.json', '{"setting": "value", "enabled": true}'),
                ('results.csv', 'name,value,status\ntest,100,pass')
            ]
            
            for filename, content in files_to_create:
                file_path = os.path.join(p.cur_dir, filename)
                with open(file_path, 'w') as f:
                    f.write(content)
                file_operations.append(f"created_{filename}")
                assert os.path.exists(file_path)
        
        def file_modification_iterator(p):
            """Modify files in different ways."""
            file_operations.append("file_modification_started")
            
            p.iterator_replacements = {
                'modification_type': ['append', 'update', 'backup'],
                'cur_dir_parent_dir': [
                    os.path.join(p.cur_dir, 'append_mod'),
                    os.path.join(p.cur_dir, 'update_mod'),
                    os.path.join(p.cur_dir, 'backup_mod')
                ]
            }
            
            for dir_path in p.iterator_replacements['cur_dir_parent_dir']:
                os.makedirs(dir_path, exist_ok=True)
        
        def modification_task(p):
            """Apply specific modification type."""
            file_operations.append(f"modification_{p.modification_type}_started")
            
            source_dir = p.file_creation_task_dir
            
            if p.modification_type == 'append':
                # Append to existing files
                source_file = os.path.join(source_dir, 'data.txt')
                if os.path.exists(source_file):
                    target_file = os.path.join(p.cur_dir, 'appended_data.txt')
                    # Copy original and append
                    shutil.copy2(source_file, target_file)
                    with open(target_file, 'a') as f:
                        f.write("\nAppended content")
                    file_operations.append("append_completed")
                    
            elif p.modification_type == 'update':
                # Update file contents
                source_file = os.path.join(source_dir, 'config.json')
                if os.path.exists(source_file):
                    target_file = os.path.join(p.cur_dir, 'updated_config.json')
                    with open(target_file, 'w') as f:
                        f.write('{"setting": "updated_value", "enabled": false, "version": 2}')
                    file_operations.append("update_completed")
                    
            elif p.modification_type == 'backup':
                # Create backup copies
                source_files = ['data.txt', 'config.json', 'results.csv']
                for filename in source_files:
                    source_path = os.path.join(source_dir, filename)
                    if os.path.exists(source_path):
                        backup_name = f'backup_{filename}'
                        backup_path = os.path.join(p.cur_dir, backup_name)
                        shutil.copy2(source_path, backup_path)
                        file_operations.append(f"backed_up_{filename}")
        
        def file_validation_task(p):
            """Validate all file operations completed correctly."""
            file_operations.append("validation_started")
            
            validation_results = []
            
            # Check original files
            original_files = ['data.txt', 'config.json', 'results.csv']
            for filename in original_files:
                file_path = os.path.join(p.file_creation_task_dir, filename)
                if os.path.exists(file_path):
                    validation_results.append(f"original_{filename}_exists")
            
            # Check modified files
            append_file = os.path.join(p.file_modification_iterator_dir, 'append_mod', 'appended_data.txt')
            update_file = os.path.join(p.file_modification_iterator_dir, 'update_mod', 'updated_config.json')
            
            if os.path.exists(append_file):
                validation_results.append("append_file_exists")
            if os.path.exists(update_file):
                validation_results.append("update_file_exists")
            
            # Check backup files
            backup_dir = os.path.join(p.file_modification_iterator_dir, 'backup_mod')
            backup_files = ['backup_data.txt', 'backup_config.json', 'backup_results.csv']
            for backup_file in backup_files:
                backup_path = os.path.join(backup_dir, backup_file)
                if os.path.exists(backup_path):
                    validation_results.append(f"{backup_file}_exists")
            
            # Write validation report
            report_file = os.path.join(p.cur_dir, 'validation_report.txt')
            with open(report_file, 'w') as f:
                f.write("File Lifecycle Validation Report\n")
                f.write(f"Operations performed: {len(file_operations)}\n")
                f.write(f"Validations passed: {len(validation_results)}\n")
                f.write("\nOperation details:\n")
                for op in file_operations:
                    f.write(f"- {op}\n")
                f.write("\nValidation results:\n")
                for result in validation_results:
                    f.write(f"- {result}\n")
        
        # Build file operations workflow
        creation = p.add_task(file_creation_task)
        modification_iter = p.add_iterator(file_modification_iterator, run_in_parallel=False)
        modification = p.add_task(modification_task, parent=modification_iter)
        validation = p.add_task(file_validation_task)
        
        # Execute file operations workflow
        p.execute()
        
        # Validate workflow completion
        assert len(file_operations) >= 10  # Should have many file operations
        
        # Validate final report exists
        report_file = os.path.join(p.file_validation_task_dir, 'validation_report.txt')
        assert os.path.exists(report_file)
        
        # Validate report content
        with open(report_file, 'r') as f:
            content = f.read()
            assert "File Lifecycle Validation Report" in content
            assert "Operations performed:" in content
            assert "Validations passed:" in content


if __name__ == "__main__":
    # Enable running specific test classes for debugging
    pytest.main([__file__ + "::TestEndToEndProjectLifecycles::test_complete_project_creation_to_cleanup_lifecycle", "-v"])
