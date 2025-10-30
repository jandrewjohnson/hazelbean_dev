#!/usr/bin/env python3
"""
Simple Test Function Documentation Generator

Extracts only test functions from class-based unittest files and generates
clean markdown documentation without setup/teardown methods or class infrastructure.

Usage:
    python tools/generate_clean_test_docs.py

Generates:
    docs-site/docs/tests/clean-unit.md
    docs-site/docs/tests/clean-integration.md  
    docs-site/docs/tests/clean-performance.md
    docs-site/docs/tests/clean-system.md
"""

import ast
import os
from pathlib import Path

def extract_test_functions(file_path):
    """Extract test functions and docstrings from a Python file.
    
    Args:
        file_path: Path to Python test file
        
    Returns:
        List of (function_name, docstring) tuples
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        test_functions = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef) and 
                node.name.startswith('test_')):
                docstring = ast.get_docstring(node) or "No description available"
                # Just take the first line of docstring for clean display
                first_line = docstring.split('\n')[0].strip()
                test_functions.append((node.name, first_line))
                
        return test_functions
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []

def generate_category_page(category_name, category_dir, output_file):
    """Generate clean markdown for a test category.
    
    Args:
        category_name: Name of test category (unit, integration, etc.)
        category_dir: Path to category directory  
        output_file: Path where markdown should be written
    """
    test_files = list(Path(category_dir).glob('test_*.py'))
    if not test_files:
        return
    
    # Build markdown content
    content = f"""# {category_name.title()} Test Functions

> **Clean view of test functions only** | **Generated from {len(test_files)} test files**

This page shows only the test functions without class setup/teardown methods.

"""

    total_tests = 0
    
    for test_file in sorted(test_files):
        test_functions = extract_test_functions(test_file)
        if test_functions:
            # Clean up file name for display
            file_display_name = test_file.stem.replace('test_', '').replace('_', ' ').title()
            content += f"## {file_display_name}\n\n"
            
            for func_name, docstring in test_functions:
                # Clean up function name for display
                clean_name = func_name.replace('test_', '').replace('_', ' ').title()
                content += f"- **{clean_name}** - {docstring}\n"
                total_tests += 1
                
            content += f"\n**Source:** `{test_file.name}`\n\n"
    
    # Add running instructions
    content += f"""
---

## Running {category_name.title()} Tests

```bash
# Activate environment
conda activate hazelbean_env

# Run all {category_name} tests
pytest hazelbean_tests/{category_name}/ -v

# Run specific test file  
pytest hazelbean_tests/{category_name}/test_example.py -v
```

## Complete Documentation

For full test context including class structure and setup methods, see the [complete {category_name} test documentation](../tests/{category_name}.md).

---

*Generated automatically from {len(test_files)} test files ({total_tests} test functions)*
"""
    
    # Write the file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Generated {output_file} ({total_tests} test functions)")

def main():
    """Generate clean test documentation for all categories."""
    
    # Define test categories and their paths  
    categories = {
        'unit': 'hazelbean_tests/unit',
        'integration': 'hazelbean_tests/integration', 
        'performance': 'hazelbean_tests/performance',
        'system': 'hazelbean_tests/system'
    }
    
    print("Generating clean test function documentation...")
    
    for category_name, category_path in categories.items():
        if os.path.exists(category_path):
            output_file = f'docs-site/docs/tests/clean-{category_name}.md'
            generate_category_page(category_name, category_path, output_file)
        else:
            print(f"Skipping {category_name} - directory not found: {category_path}")
    
    # Generate index page for clean docs
    generate_clean_index()
    
    print("✅ Clean test documentation generation complete!")

def generate_clean_index():
    """Generate index page for clean test documentation."""
    
    content = """# Clean Test Function Documentation

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
"""

    output_file = 'docs-site/docs/tests/clean-index.md'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Generated {output_file}")

if __name__ == '__main__':
    main()
