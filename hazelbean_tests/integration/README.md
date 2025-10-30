# Integration Tests

Workflow-based integration tests for hazelbean functionality.

## Directory Structure

- `cloud_storage_workflows/` - Cloud storage integration workflows
- `data_pipeline_workflows/` - Data processing pipeline workflows
- `end_to_end_workflows/` - Complete end-to-end system workflows
- `parallel_processing_flows/` - Parallel processing integration workflows
- `project_flow_workflows/` - ProjectFlow system workflows

## Running Tests

```bash
# Run all integration tests
pytest hazelbean_tests/integration/

# Run specific workflow tests
pytest hazelbean_tests/integration/end_to_end_workflows/

# Run with integration marker
pytest hazelbean_tests/ -m integration
```
