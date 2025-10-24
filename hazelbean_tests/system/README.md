# System Tests

System-level testing for hazelbean installation and environment validation.

## Directory Structure

- `smoke/` - Smoke tests for basic functionality
- `cli/` - CLI interface testing
- `installation/` - Installation validation
- `environment/` - Environment validation

## Running Tests

```bash
# Run all system tests
pytest hazelbean_tests/system/

# Run smoke tests only
pytest hazelbean_tests/system/smoke/

# Run with system markers
pytest hazelbean_tests/ -m smoke
```
