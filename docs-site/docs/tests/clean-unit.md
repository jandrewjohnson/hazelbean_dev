# Unit Test Functions

> **Clean view of test functions only** | **Generated from 12 test files**

This page shows only the test functions without class setup/teardown methods.

## Add Iterator

- **Add Iterator Simple Multiprocessing** - CORE PROOF TEST 2: Simple multiprocessing validation with add_iterator()
- **Add Iterator Parallel Configuration** - Test add_iterator() with run_in_parallel=True configuration.
- **Add Iterator Replacement Setup** - Test iterator replacements setup with realistic scenario data.
- **Add Iterator Invalid Function Error** - CORE PROOF TEST 3B: Error handling for invalid function parameter
- **Add Iterator None Function Error** - Test error handling when None is passed as function parameter.
- **Add Iterator With Multiple Child Tasks** - Test iterator with multiple child tasks (realistic workflow).
- **Add Iterator Task Isolation** - Test that iterator task execution maintains proper isolation between scenarios.
- **Iterator Object Creation With Type Validation** - B1.1: Test iterator object creation with correct type='iterator'
- **Iterator Task Object Inheritance** - B1.2: Test Task object inheritance for iterator objects
- **Iterator Naming And Attributes** - B1.3: Test iterator naming and attribute assignment
- **Projectflow Setattr Behavior** - B1.4: Test ProjectFlow object attribute setting (setattr behavior)
- **Run In Parallel False Configuration** - B2.1: Test run_in_parallel=False configuration and persistence
- **Run In Parallel True Configuration** - B2.2: Test run_in_parallel=True configuration and persistence
- **Run In Parallel Default Behavior** - B2.3: Test default run_in_parallel parameter behavior
- **Iterator As Parent For Child Tasks** - B3.1: Test iterator serving as parent for child tasks (anytree structure)
- **Task Tree Integration And Navigation** - B3.2: Test iterator integration into overall task_tree and navigation
- **Parent Child Relationship Validation** - B3.3: Test parent-child relationship validation with anytree
- **Logging Level Inheritance** - B4.1: Test logging level inheritance from ProjectFlow
- **Documentation Extraction From Task Note** - B4.2: Test documentation extraction from task_note variables
- **Documentation Extraction From Task Documentation** - B4.3: Test documentation extraction from task_documentation variables
- **Iterator Specific Attribute Management** - B4.4: Test iterator-specific attribute management
- **Non Callable Function Parameter** - B5.1: Test non-callable function parameter validation
- **None Function Parameter** - B5.2: Test None function parameter handling
- **Invalid Parent Parameter Scenarios** - B5.3: Test invalid parent parameter scenarios
- **Unit Multiprocessing Disabled** - B6.1: Test unit test execution with parallel processing disabled
- **Run In Parallel Attribute Persistence Without Execution** - B6.2: Test run_in_parallel attribute persistence without actual multiprocessing
- **Memory Isolation With Iterator Hierarchies** - B6.3: Test memory isolation validation with iterator hierarchies

**Source:** `test_add_iterator.py`

## Add Task

- **Add Task Functional Execution** - CORE PROOF TEST 1: Functional validation of add_task() with execution
- **Add Task Parameter Validation** - Validate add_task() parameter handling and task attribute configuration.
- **Add Task Invalid Function Error** - CORE PROOF TEST 3A: Error handling for invalid function parameter
- **Add Task None Function Error** - Test error handling when None is passed as function parameter.
- **Add Task Run Parameter Variants** - Test run parameter validation: run=0, run=1, default behavior.
- **Add Task Skip Existing Parameter Variants** - Test skip_existing parameter: skip_existing=0, skip_existing=1, default behavior.
- **Add Task Logging Level Parameter** - Test logging_level parameter: inheritance, explicit override, None handling.
- **Add Task Task Dir Parameter** - Test task_dir parameter: custom directory, None handling, path validation.
- **Add Task Creates Dir Parameter** - Test creates_dir parameter: True/False behavior, directory creation logic.
- **Add Task Type Parameter** - Test type parameter: default 'task', custom type handling.
- **Add Task Basic Object Creation** - Test basic task object creation with proper attributes.
- **Add Task Function Reference Validation** - Test that task correctly stores function reference.
- **Add Task Name Attribute Derivation** - Test that task.name is correctly derived from function.__name__.
- **Add Task Project Reference Validation** - Test that task correctly stores project reference.
- **Add Task Default Parent Assignment** - Test default parent assignment to project.task_tree.
- **Add Task Custom Parent Assignment** - Test custom parent assignment and hierarchy validation.
- **Add Task Anytree Hierarchy Validation** - Test anytree hierarchy construction and validation.
- **Add Task Documentation Extraction Success** - Test successful extraction of task_documentation from function code.
- **Add Task Note Extraction Success** - Test successful extraction of task_note from function code.
- **Add Task No Documentation Handling** - Test handling when function has no task_documentation or task_note.
- **Add Task Invalid Function Error** - Test error handling for non-callable function parameter.
- **Add Task None Function Error** - Test error handling when None is passed as function parameter.
- **Add Task Invalid Parent Parameter** - Test error handling for invalid parent parameter.
- **Add Task Extreme Parameter Values** - Test error handling for extreme or edge case parameter values.
- **Add Task Names Defined Tracking** - Test that task_names_defined list is updated correctly.
- **Add Task Project Attribute Assignment** - Test that tasks are assigned as attributes on the ProjectFlow object.
- **Add Task Tree Structure Integration** - Test integration with ProjectFlow task_tree structure.
- **Add Task Directory Integration** - Test add_task() integration with ProjectFlow directory management.
- **Add Task Multiple Tasks** - Test adding multiple tasks to validate task tree management.

**Source:** `test_add_task.py`

## Arrayframe

- **Arrayframe Load And Save** - No description available

**Source:** `test_arrayframe.py`

## Cat Ears

- **Basics** - No description available
- **Make And Remove Folders** - No description available
- **List Dirs In Dir Recursively** - No description available

**Source:** `test_cat_ears.py`

## Cog

- **Is Cog** - Check if TIFF files are valid Cloud-Optimized GeoTIFFs (COGs).
- **Make Path Cog** - Test make_path_cog() Need to find a non-translate way. maybe rio?
- **Write Random Cog** - Test make_path_cog() Need to find a non-translate way. maybe rio?
- **Cog Validation Performance** - Benchmark COG validation performance.

**Source:** `test_cog.py`

## Data Structures

- **Cls** - No description available

**Source:** `test_data_structures.py`

## Get Path

- **File In Current Directory** - Test resolving file in current project directory
- **File In Intermediate Directory** - Test resolving file in intermediate directory
- **File In Input Directory** - Test resolving file in input directory
- **File In Base Data Directory** - Test resolving file in base data directory using existing data
- **Directory Fallback Priority** - Test that directories are searched in correct priority order
- **Relative Path With Subdirectories** - Test resolving relative paths with subdirectories
- **Join Path Args Functionality** - Test get_path with additional join_path_args
- **Raster File Resolution** - Test resolving raster (.tif) files
- **Vector File Resolution** - Test resolving vector (.gpkg) files
- **Csv File Resolution** - Test resolving CSV files
- **Pyramid Data Resolution** - Test resolving pyramid data files
- **None Input Handling** - Test handling of None input
- **Empty String Input** - Test handling of empty string input
- **Invalid Characters In Path** - Test handling of paths with invalid characters
- **Very Long Path** - Test handling of very long file paths
- **Path With Special Characters** - Test handling of paths with special characters
- **Cat Ears Path Handling** - Test handling of paths with cat ears (template variables)
- **Missing File Fallback** - Test fallback behavior for missing files
- **Prepend Single Directory** - Test prepending a single directory to search path
- **Prepend Multiple Directories** - Test prepending multiple directories to search path
- **Google Cloud Bucket Integration** - Test Google Cloud bucket integration (without actual cloud calls)
- **Bucket Name Assignment** - Test bucket name assignment
- **Cloud Path Fallback** - Test cloud path fallback when local file not found
- **Existing Cartographic Data Access** - Test access to existing cartographic data
- **Existing Pyramid Data Access** - Test access to existing pyramid data
- **Existing Crops Data Access** - Test access to existing crops data
- **Existing Data Access** - Test access to existing test data

**Source:** `test_get_path.py`

## Os Funcs

- **Misc** - No description available

**Source:** `test_os_funcs.py`

## Pog

- **Is Path Pog** - Test make_path_cog()
- **Make Path Pog From Non Global Cog** - Test make_path_pog
- **Write Pog Of Value From Match** - Test write_pog_of_value_from_match function.
- **Write Pog Of Value From Scratch** - Test write_pog_of_value_from_scratch function.

**Source:** `test_pog.py`

## Tile Iterator

- **Project Flow Iterator Creation** - Test that ProjectFlow can create iterator tasks
- **Tiling Iterator Configuration** - Test that tiling iterator properly configures tile boundaries
- **Iterator Directory Structure** - Test that iterator creates proper directory structure
- **Integration With Existing Unitstructure** - Test integration with existing unittest structure
- **Iterator Parallel Flag Configuration** - Test that iterator can be configured for parallel execution
- **Parallel Flag Configuration Only** - Test parallel flag configuration without actual execution
- **Minimal Tiling Workflow Execution** - Test minimal tiling workflow executes without errors
- **Spatial Tiling Bounds Calculation** - Test that spatial tiling calculations produce correct bounds
- **Iterator** - Test iterator for parallel configuration testing

**Source:** `test_tile_iterator.py`

## Utils

- **Fn** - No description available
- **Parse Flex To Python Object** - Test parsing a flex item (int, float, string, None, string that represents a python object) element to a Python object.

**Source:** `test_utils.py`


---

## Running Unit Tests

```bash
# Activate environment
conda activate hazelbean_env

# Run all unit tests
pytest hazelbean_tests/unit/ -v

# Run specific test file  
pytest hazelbean_tests/unit/test_example.py -v
```

## Complete Documentation

For full test context including class structure and setup methods, see the [complete unit test documentation](../tests/unit.md).

---

*Generated automatically from 12 test files (108 test functions)*
