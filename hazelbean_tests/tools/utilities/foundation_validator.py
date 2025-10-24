#!/usr/bin/env python
"""
Foundation Architecture Validation Script

This script validates that the test architecture foundation is correctly
implemented according to the specifications from Story 2.

Usage:
    python foundation_validator.py [--verbose] [--fix-issues]
"""

import os
import sys
from pathlib import Path
import argparse
import subprocess
import importlib.util

class FoundationValidator:
    """Validates the test architecture foundation implementation."""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.errors = []
        self.warnings = []
        self.root_dir = Path(__file__).parent.parent.parent.parent
        self.test_dir = self.root_dir / "hazelbean_tests"
        
    def log(self, message, level="INFO"):
        """Log message with level."""
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"[{level}] {message}")
            
    def add_error(self, message):
        """Add an error to the error list."""
        self.errors.append(message)
        self.log(message, "ERROR")
        
    def add_warning(self, message):
        """Add a warning to the warnings list."""
        self.warnings.append(message)
        self.log(message, "WARNING")
        
    def validate_directory_structure(self):
        """Validate the complete component-based directory structure."""
        self.log("Validating directory structure...")
        
        required_dirs = {
            # Unit test component directories
            "unit": [
                "arrayframe", "calculation_core", "cat_ears", "cloud_utils", 
                "cog", "config", "core", "file_io", "geoprocessing", 
                "globals", "get_path", "os_utils", "parallel", "pog", 
                "project_flow", "pyramids", "raster_vector_interface",
                "spatial_projection", "spatial_utils", "stats", 
                "tile_iterator", "ui", "utils", "vector", "visualization"
            ],
            # Integration workflow directories  
            "integration": [
                "cloud_storage_workflows", "data_pipeline_workflows",
                "end_to_end_workflows", "parallel_processing_flows",
                "project_flow_workflows"
            ],
            # Performance test directories
            "performance": [
                "functions", "workflows", "regression", "baseline",
                "unit", "benchmarks"
            ],
            # System test directories
            "system": [
                "smoke", "cli", "installation", "environment"
            ],
            # Testing infrastructure directories
            "tools": [
                "qmd_automation", "fixtures", "data", "utilities"
            ]
        }
        
        for category, subdirs in required_dirs.items():
            category_path = self.test_dir / category
            if not category_path.exists():
                self.add_error(f"Missing category directory: {category_path}")
                continue
                
            for subdir in subdirs:
                subdir_path = category_path / subdir
                if not subdir_path.exists():
                    self.add_error(f"Missing component directory: {subdir_path}")
                else:
                    # Check for __init__.py file
                    init_file = subdir_path / "__init__.py"
                    if not init_file.exists():
                        self.add_warning(f"Missing __init__.py: {init_file}")
                        
    def validate_conftest_files(self):
        """Validate that conftest.py files are properly created."""
        self.log("Validating conftest.py files...")
        
        required_conftest = [
            "hazelbean_tests/conftest.py",  # Root conftest (should exist)
            "hazelbean_tests/unit/conftest.py",
            "hazelbean_tests/integration/conftest.py", 
            "hazelbean_tests/performance/conftest.py",
            "hazelbean_tests/system/conftest.py"
        ]
        
        for conftest_path in required_conftest:
            full_path = self.root_dir / conftest_path
            if not full_path.exists():
                self.add_error(f"Missing conftest.py: {full_path}")
            else:
                # Validate conftest file can be imported
                try:
                    spec = importlib.util.spec_from_file_location("conftest", full_path)
                    if spec is None:
                        self.add_error(f"Invalid conftest.py spec: {full_path}")
                    else:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        self.log(f"Valid conftest.py: {conftest_path}")
                except Exception as e:
                    self.add_error(f"Cannot import conftest.py {full_path}: {e}")
                    
    def validate_pytest_configuration(self):
        """Validate pytest.ini configuration."""
        self.log("Validating pytest configuration...")
        
        pytest_ini = self.root_dir / "pytest.ini"
        if not pytest_ini.exists():
            self.add_error("Missing pytest.ini file")
            return
            
        try:
            with open(pytest_ini, 'r') as f:
                content = f.read()
                
            # Check for required testpaths
            required_paths = [
                "hazelbean_tests",
                "hazelbean_tests/unit", 
                "hazelbean_tests/integration",
                "hazelbean_tests/performance",
                "hazelbean_tests/system",
                "hazelbean_tests/tools"
            ]
            
            for path in required_paths:
                if path not in content:
                    self.add_warning(f"Missing testpath in pytest.ini: {path}")
                    
            # Check for component markers
            component_markers = [
                "arrayframe", "calculation_core", "cat_ears", "cloud_utils",
                "cog", "config", "core", "file_io", "geoprocessing"
            ]
            
            missing_markers = []
            for marker in component_markers:
                if f"{marker}:" not in content:
                    missing_markers.append(marker)
                    
            if missing_markers:
                self.add_warning(f"Missing component markers: {', '.join(missing_markers)}")
                
        except Exception as e:
            self.add_error(f"Cannot read pytest.ini: {e}")
            
    def validate_test_discovery(self):
        """Validate that pytest can discover tests in the new structure."""
        self.log("Validating test discovery...")
        
        try:
            # Run pytest --collect-only to check test discovery
            result = subprocess.run(
                ["python", "-m", "pytest", "--collect-only", "-q"],
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.log("Test discovery successful")
                # Count discovered tests
                lines = result.stdout.strip().split('\n')
                test_count = 0
                for line in lines:
                    if '<Function' in line or '<Method' in line:
                        test_count += 1
                self.log(f"Discovered {test_count} tests")
            else:
                self.add_error(f"Test discovery failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.add_error("Test discovery timed out")
        except Exception as e:
            self.add_error(f"Cannot run test discovery: {e}")
            
    def validate_readme_files(self):
        """Validate that README files are created."""
        self.log("Validating README files...")
        
        required_readmes = [
            "hazelbean_tests/unit/README.md",
            "hazelbean_tests/integration/README.md",
            "hazelbean_tests/performance/README.md", 
            "hazelbean_tests/system/README.md",
            "hazelbean_tests/tools/README.md"
        ]
        
        for readme_path in required_readmes:
            full_path = self.root_dir / readme_path
            if not full_path.exists():
                self.add_warning(f"Missing README: {full_path}")
            else:
                # Check if README has content
                try:
                    with open(full_path, 'r') as f:
                        content = f.read().strip()
                    if len(content) < 50:  # Arbitrary minimum content check
                        self.add_warning(f"README appears empty or too short: {full_path}")
                except Exception as e:
                    self.add_error(f"Cannot read README {full_path}: {e}")
                    
    def run_validation(self):
        """Run complete validation suite."""
        print(f"Running foundation validation for: {self.test_dir}")
        print("=" * 60)
        
        self.validate_directory_structure()
        self.validate_conftest_files()
        self.validate_pytest_configuration()
        self.validate_test_discovery()
        self.validate_readme_files()
        
        return self.generate_report()
        
    def generate_report(self):
        """Generate validation report."""
        print("\n" + "=" * 60)
        print("VALIDATION REPORT")
        print("=" * 60)
        
        if not self.errors and not self.warnings:
            print("✅ All validations passed successfully!")
            print("Foundation architecture is correctly implemented.")
            return True
            
        if self.warnings:
            print(f"\n⚠️  {len(self.warnings)} Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
                
        if self.errors:
            print(f"\n❌ {len(self.errors)} Errors:")
            for error in self.errors:
                print(f"  - {error}")
                
        success = len(self.errors) == 0
        status = "PASSED with warnings" if success else "FAILED"
        print(f"\nValidation Status: {status}")
        
        return success


def main():
    parser = argparse.ArgumentParser(description="Validate test architecture foundation")
    parser.add_argument("--verbose", "-v", action="store_true", 
                      help="Enable verbose output")
    parser.add_argument("--fix-issues", action="store_true",
                      help="Attempt to automatically fix issues")
    
    args = parser.parse_args()
    
    validator = FoundationValidator(verbose=args.verbose)
    success = validator.run_validation()
    
    if args.fix_issues and not success:
        print("\n⚙️  Auto-fix functionality not yet implemented")
        print("Please review errors and fix manually")
        
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
