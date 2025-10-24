# System Test Functions

> **Clean view of test functions only** | **Generated from 2 test files**

This page shows only the test functions without class setup/teardown methods.

## Project Flow Workflows

- **Complete Project Creation To Cleanup Lifecycle** - Test full project lifecycle from creation to cleanup.
- **Multi Stage Project Workflow With Dependencies** - Test complex multi-stage project with task dependencies.
- **Error Handling In Complete Project Workflow** - Test error handling and recovery in complete project workflows.
- **File Lifecycle Operations Workflow** - Test complete file lifecycle operations in project workflow.

**Source:** `test_project_flow_workflows.py`

## Smoke

- **Hazelbean Imports Successfully** - Test that hazelbean can be imported without errors
- **Projectflow Imports** - Test that ProjectFlow is available and can be imported
- **Hazelbean Import Performance** - Benchmark the import time of hazelbean module.
- **Projectflow Basic Functionality** - Test basic ProjectFlow functionality works
- **Common Hazelbean Functions Available** - Test that common hazelbean functions are available
- **Numpy Integration** - Test basic numpy integration with hazelbean
- **Basic Error Handling** - Test that basic error conditions are handled gracefully
- **Get Path Generates Doc** - Smoke-test + write example QMD.
- **Error Handling Documentation** - Test documentation generation for error handling scenarios
- **Performance Documentation** - Test documentation generation for performance examples
- **File Formats Documentation** - Test documentation generation for different file formats
- **Temp Directory Creation** - Test that temporary directory creation works
- **Multiple Projectflow Instances** - Test that multiple ProjectFlow instances can coexist
- **Relative Vs Absolute Paths** - Test handling of relative vs absolute paths
- **Special Characters In Paths** - Test handling of special characters in file paths
- **Concurrent Access** - Test basic concurrent access patterns
- **Python Version Compatibility** - Test Python version compatibility
- **Required Dependencies Available** - Test that required dependencies are available
- **File System Permissions** - Test basic file system permissions

**Source:** `test_smoke.py`


---

## Running System Tests

```bash
# Activate environment
conda activate hazelbean_env

# Run all system tests
pytest hazelbean_tests/system/ -v

# Run specific test file  
pytest hazelbean_tests/system/test_example.py -v
```

## Complete Documentation

For full test context including class structure and setup methods, see the [complete system test documentation](../tests/system.md).

---

*Generated automatically from 2 test files (23 test functions)*
