# Clean Test Function Documentation

> **Test functions only** - No setup methods, no class infrastructure

This section provides a clean view of test functions extracted from the hazelbean test suite. Each page shows only the test function names and their descriptions, without the class setup/teardown code or infrastructure.

## Available Categories

- **[Unit Test Functions](clean-unit.md)** - Individual component tests
- **[Integration Test Functions](clean-integration.md)** - Workflow and interaction tests  
- **[Performance Test Functions](clean-performance.md)** - Benchmarks and performance validation
- **[System Test Functions](clean-system.md)** - End-to-end system validation

## Why This Documentation?

The regular [test documentation](index.md) shows complete class structures with setup methods, inheritance, and infrastructure code. This clean documentation focuses purely on what each test does, making it easier to understand test coverage and functionality.

## Usage

1. **Browse test functions** - See what functionality is tested
2. **Understand test purpose** - Read concise descriptions  
3. **Find relevant tests** - Locate tests for specific features
4. **Run specific tests** - Copy test commands from each page

---

*This documentation is automatically generated. To regenerate, run:*

```bash
python tools/generate_clean_test_docs.py
```
