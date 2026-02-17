#!/usr/bin/env python3
"""
Automation script to extract test functions from Python test files
and generate Quarto QMD documentation with collapsible source code blocks.

This script:
1. Parses Python test files using the AST module
2. Extracts test functions with their docstrings and source code
3. Generates QMD files with collapsible callout blocks
4. Maintains the structure for different test categories (unit, integration, etc.)
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional
import re


class TestFunctionExtractor:
    """Extract test functions from Python test files."""
    
    def __init__(self, test_file_path: str):
        self.test_file_path = test_file_path
        self.file_content = None
        self.source_lines = []
        
    def read_file(self):
        """Read the test file content."""
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            self.file_content = f.read()
            f.seek(0)
            self.source_lines = f.readlines()
    
    def extract_functions(self) -> List[Dict]:
        """Extract all test functions from the file."""
        if not self.file_content:
            self.read_file()
        
        try:
            tree = ast.parse(self.file_content, filename=self.test_file_path)
        except SyntaxError as e:
            print(f"Warning: Could not parse {self.test_file_path}: {e}")
            return []
        
        functions = []
        
        # Find all test functions (both standalone and in classes)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if it's a test function or fixture
                if (node.name.startswith('test_') or 
                    self._has_pytest_mark(node) or
                    self._is_fixture(node)):
                    
                    func_info = self._extract_function_info(node)
                    if func_info:
                        functions.append(func_info)
        
        return functions
    
    def _has_pytest_mark(self, node: ast.FunctionDef) -> bool:
        """Check if function has pytest markers."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if isinstance(decorator.value, ast.Name):
                    if decorator.value.id == 'pytest':
                        return True
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if isinstance(decorator.func.value, ast.Name):
                        if decorator.func.value.id == 'pytest':
                            return True
        return False
    
    def _is_fixture(self, node: ast.FunctionDef) -> bool:
        """Check if function is a pytest fixture."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if decorator.attr == 'fixture':
                    return True
            elif isinstance(decorator, ast.Name):
                if decorator.id == 'fixture':
                    return True
        return False
    
    def _extract_function_info(self, node: ast.FunctionDef) -> Optional[Dict]:
        """Extract information about a single function."""
        try:
            # Get function source code
            start_line = node.lineno - 1
            end_line = node.end_lineno
            
            # Include decorators if present
            if node.decorator_list:
                first_decorator = node.decorator_list[0]
                start_line = first_decorator.lineno - 1
            
            func_source = ''.join(self.source_lines[start_line:end_line])
            
            # Get docstring
            docstring = ast.get_docstring(node) or ""
            
            # Extract short description from docstring (first line)
            short_desc = ""
            if docstring:
                short_desc = docstring.strip().split('\n')[0]
            
            # Get pytest markers
            markers = self._get_pytest_markers(node)
            
            return {
                'name': node.name,
                'docstring': docstring,
                'short_desc': short_desc,
                'source': func_source,
                'file': self.test_file_path,
                'markers': markers,
                'is_fixture': self._is_fixture(node),
                'line_start': start_line + 1,
                'line_end': end_line
            }
        except Exception as e:
            print(f"Warning: Could not extract {node.name}: {e}")
            return None
    
    def _get_pytest_markers(self, node: ast.FunctionDef) -> List[str]:
        """Extract pytest marker names."""
        markers = []
        for decorator in node.decorator_list:
            try:
                if isinstance(decorator, ast.Attribute):
                    if isinstance(decorator.value, ast.Name):
                        if decorator.value.id == 'pytest':
                            markers.append(decorator.attr)
                elif isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        if isinstance(decorator.func.value, ast.Name):
                            if decorator.func.value.id == 'pytest':
                                markers.append(decorator.func.attr)
            except:
                pass
        return markers


class QuartoQMDGenerator:
    """Generate Quarto QMD documentation from test functions."""
    
    def __init__(self, category: str, category_title: str):
        self.category = category
        self.category_title = category_title
        self.functions_by_file = {}
    
    def add_functions(self, test_file_path: str, functions: List[Dict]):
        """Add functions from a test file."""
        if functions:
            self.functions_by_file[test_file_path] = functions
    
    def generate_qmd(self) -> str:
        """Generate complete QMD content."""
        qmd_content = self._generate_header()
        
        # Group functions by test file
        for test_file, functions in sorted(self.functions_by_file.items()):
            file_section = self._generate_file_section(test_file, functions)
            qmd_content += file_section
        
        qmd_content += self._generate_footer()
        
        return qmd_content
    
    def _generate_header(self) -> str:
        """Generate QMD header with frontmatter."""
        return f"""---
title: "{self.category_title}"
execute:
  enabled: false
format:
  html:
    code-fold: false
    code-line-numbers: true
    code-copy: true
    highlight-style: github
    toc: true
---

{self._get_category_description()}

---

"""
    
    def _get_category_description(self) -> str:
        """Get description for test category."""
        descriptions = {
            'unit': """Unit tests focus on testing individual functions and classes in isolation, ensuring that each component behaves correctly under various conditions.

## Overview

The unit test suite covers core hazelbean functionality including:

- **Path Resolution** - Testing file path handling and resolution logic
- **Array Framework** - Testing the ArrayFrame data structure and operations
- **Core Utilities** - Testing utility functions and helper methods
- **Data Structures** - Testing custom data types and containers
- **Geospatial Operations** - Testing fundamental geospatial processing functions""",
            
            'integration': """Integration tests verify that different components of hazelbean work together correctly, testing the interactions between modules and subsystems.

## Overview

The integration test suite covers:

- **Data Processing Pipelines** - Testing end-to-end data workflows
- **Project Flow Integration** - Testing ProjectFlow task management
- **Parallel Processing** - Testing multi-threaded operations
- **Component Interactions** - Testing how modules work together""",
            
            'performance': """Performance tests measure and benchmark the speed, memory usage, and scalability of hazelbean operations.

## Overview

The performance test suite covers:

- **Benchmarking** - Measuring execution time of key operations
- **Scalability Tests** - Testing performance with large datasets
- **Memory Profiling** - Monitoring memory usage patterns
- **Baseline Management** - Tracking performance over time""",
            
            'system': """System tests validate the complete hazelbean system, including smoke tests to verify basic functionality and end-to-end workflows.

## Overview

The system test suite covers:

- **Smoke Tests** - Quick validation that core features work
- **Workflow Tests** - Complete ProjectFlow workflows
- **Environment Tests** - Testing in different environments
- **Installation Tests** - Verifying correct installation"""
        }
        
        return descriptions.get(self.category, "Test suite documentation.")
    
    def _generate_file_section(self, test_file: str, functions: List[Dict]) -> str:
        """Generate section for a test file."""
        # Get relative path for display
        file_name = Path(test_file).name
        relative_path = self._get_relative_path(test_file)
        
        # Create section header
        section_title = self._format_file_title(file_name)
        
        content = f"""## {section_title}

**Source File:** `{relative_path}`

"""
        
        # Add each function
        for func in functions:
            if func['name'].startswith('test_'):  # Only include actual tests
                content += self._generate_function_block(func)
        
        return content
    
    def _get_relative_path(self, test_file: str) -> str:
        """Get relative path from repository root."""
        # Convert to relative path from hazelbean_tests
        path = Path(test_file)
        try:
            # Find 'hazelbean_tests' in the path
            parts = path.parts
            if 'hazelbean_tests' in parts:
                idx = parts.index('hazelbean_tests')
                return str(Path(*parts[idx:]))
        except:
            pass
        return str(path.name)
    
    def _format_file_title(self, file_name: str) -> str:
        """Format test file name into readable title."""
        # Remove test_ prefix and .py suffix
        title = file_name.replace('test_', '').replace('.py', '')
        # Convert underscores to spaces and title case
        title = title.replace('_', ' ').title()
        return f"{title} Tests"
    
    def _generate_function_block(self, func: Dict) -> str:
        """Generate collapsible block for a test function."""
        # Format function name
        func_name = func['name']
        
        # Get short description (first line of docstring or default)
        description = func['short_desc'] if func['short_desc'] else "Test function"
        
        # Get pytest markers
        markers_str = ""
        if func['markers']:
            markers_str = f" `@pytest.mark.{', @pytest.mark.'.join(func['markers'])}`"
        
        return f"""### {func_name}()

{description}{markers_str}

::: {{.callout-note collapse="true"}}
## Source code

```python
{func['source']}
```
:::

---

"""
    
    def _generate_footer(self) -> str:
        """Generate QMD footer with navigation and tips."""
        return f"""
## Running {self.category_title}

To run these tests:

```{{.bash}}
# Activate the hazelbean environment
conda activate hazelbean_env

# Run all {self.category} tests
pytest hazelbean_tests/{self.category}/ -v

# Run specific test file
pytest hazelbean_tests/{self.category}/<test_file>.py -v

# Run with coverage
pytest hazelbean_tests/{self.category}/ --cov=hazelbean --cov-report=html
```

## Test Organization

Tests are organized by:
- **Test Files** - Each file tests a specific module or feature
- **Test Functions** - Individual test cases within files
- **Test Classes** - Grouped related tests (where applicable)
- **Fixtures** - Shared test setup and teardown

## Related Documentation

- [Test Strategy](../README.md) - Overall testing approach
- [CI/CD](../../.github/workflows/) - Automated testing
"""


def generate_test_docs(test_category: str, category_title: str, test_dir: Path, output_file: Path):
    """Generate QMD documentation for a test category."""
    print(f"\n{'='*60}")
    print(f"Generating {category_title} Documentation")
    print(f"{'='*60}\n")
    
    generator = QuartoQMDGenerator(test_category, category_title)
    
    # Find all test files in directory
    test_files = sorted(test_dir.glob("test_*.py"))
    
    for test_file in test_files:
        print(f"Processing: {test_file.name}")
        
        extractor = TestFunctionExtractor(str(test_file))
        functions = extractor.extract_functions()
        
        if functions:
            print(f"  Found {len(functions)} test functions")
            generator.add_functions(str(test_file), functions)
        else:
            print(f"  No test functions found")
    
    # Generate QMD content
    qmd_content = generator.generate_qmd()
    
    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(qmd_content)
    
    print(f"\n✅ Generated: {output_file}")
    print(f"   Output size: {len(qmd_content)} characters\n")


def main():
    """Main entry point."""
    # Define paths
    script_dir = Path(__file__).parent
    hazelbean_tests_dir = script_dir.parent.parent / "hazelbean_tests"
    output_dir = script_dir / "tests"
    
    # Test categories to process
    categories = [
        ('unit', 'Unit Tests', hazelbean_tests_dir / 'unit'),
        ('integration', 'Integration Tests', hazelbean_tests_dir / 'integration'),
        ('performance', 'Performance Tests', hazelbean_tests_dir / 'performance'),
        ('system', 'System Tests', hazelbean_tests_dir / 'system'),
    ]
    
    print("\n" + "="*60)
    print("Test Documentation Generator")
    print("="*60)
    print(f"Source: {hazelbean_tests_dir}")
    print(f"Output: {output_dir}")
    
    # Generate documentation for each category
    for category_key, category_title, test_dir in categories:
        if test_dir.exists():
            output_file = output_dir / f"{category_key}.qmd"
            generate_test_docs(category_key, category_title, test_dir, output_file)
        else:
            print(f"\n⚠️  Warning: {test_dir} not found, skipping...")
    
    print("\n" + "="*60)
    print("✅ All test documentation generated!")
    print("="*60)
    print(f"\nNext steps:")
    print(f"1. Review generated files in: {output_dir}")
    print(f"2. Update _quarto.yml with navigation")
    print(f"3. Run: quarto render")
    print(f"4. Preview: quarto preview")


if __name__ == "__main__":
    main()

