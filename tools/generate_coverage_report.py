#!/usr/bin/env python3
"""
Generate markdown coverage report directly from coverage.py API
Input: coverage.py data (no HTML intermediary)
Output: docs-site/docs/reports/coverage-report.md

Follows Option 1 implementation plan for dynamic coverage reporting
"""

import coverage
import os
import sys
from datetime import datetime
from pathlib import Path

def get_coverage_data():
    """Get coverage data directly from coverage.py API."""
    try:
        # Initialize coverage object and load data
        # Check for coverage file in hazelbean_tests directory first
        script_dir = Path(__file__).parent.absolute()
        hazelbean_tests_dir = script_dir.parent / 'hazelbean_tests'
        
        # Change to the directory where coverage was run
        original_cwd = os.getcwd()
        if hazelbean_tests_dir.exists():
            os.chdir(hazelbean_tests_dir)
        
        cov = coverage.Coverage()
        cov.load()
        
        # Change back to original directory
        os.chdir(original_cwd)
        
        # Get overall coverage statistics
        total_statements = 0
        total_missing = 0
        modules_data = []
        
        # Analyze each measured file
        for filename in cov.get_data().measured_files():
            try:
                # Get analysis for this file using the correct API
                filename_str = str(filename)
                analysis = cov.analysis2(filename_str)
                
                # Handle different return formats from coverage.py
                if hasattr(analysis, 'statements'):
                    # Newer API format
                    statements = len(analysis.statements)
                    missing = len(analysis.missing)
                    missing_lines = list(analysis.missing)
                else:
                    # Older API format - returns tuple
                    statements = len(analysis[1])  # statements
                    missing = len(analysis[3])     # missing
                    missing_lines = list(analysis[3])  # missing lines
                
                covered = statements - missing
                coverage_pct = (covered / statements * 100) if statements > 0 else 0
                
                # Only include files in the hazelbean package
                if 'hazelbean' in filename_str and not filename_str.endswith('__pycache__'):
                    # Clean up the module path for display
                    module_name = filename_str.replace('\\', '/').split('/')[-1]
                    if module_name.endswith('.py'):
                        module_name = module_name[:-3]
                    
                    modules_data.append({
                        'module': f'hazelbean/{module_name}.py',
                        'coverage_pct': coverage_pct,
                        'lines_covered': covered,
                        'lines_total': statements,
                        'lines_missing': missing,
                        'missing_line_numbers': sorted(missing_lines) if missing_lines else []
                    })
                    
                    total_statements += statements
                    total_missing += missing
                    
            except Exception as e:
                print(f"Warning: Could not analyze {filename}: {e}")
                continue
        
        # Calculate overall coverage
        total_covered = total_statements - total_missing
        overall_coverage = (total_covered / total_statements * 100) if total_statements > 0 else 0
        
        return {
            'overall_coverage': overall_coverage,
            'total_lines': total_statements,
            'covered_lines': total_covered,
            'missing_lines': total_missing,
            'modules': sorted(modules_data, key=lambda x: x['coverage_pct'], reverse=True)
        }
        
    except Exception as e:
        print(f"Error loading coverage data: {e}")
        print("Make sure you've run tests with coverage enabled first:")
        print("  pytest --cov=hazelbean")
        return None

def get_status_emoji(coverage_pct):
    """Get status emoji and text based on coverage percentage."""
    if coverage_pct >= 90:
        return "✅ Excellent"
    elif coverage_pct >= 80:
        return "✅ Good"  
    elif coverage_pct >= 60:
        return "⚠️ Fair"
    else:
        return "❌ Needs Attention"

def generate_coverage_markdown(coverage_data):
    """Generate markdown report from coverage data."""
    
    if not coverage_data:
        return """# Code Coverage Report

**Status:** ❌ No coverage data available

Please run tests with coverage enabled:
```bash
conda activate hazelbean_env
cd hazelbean_tests
pytest unit/ --cov=hazelbean --cov-report=term-missing
```

*Last Updated: {}*
""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # Calculate trend (placeholder - could be enhanced with historical data)
    trend_indicator = "➡️ Stable"  # Default placeholder
    
    # Quality gate status
    quality_gate = "✅ Above 60% threshold" if coverage_data['overall_coverage'] >= 60 else "❌ Below 60% threshold"
    
    markdown = f"""# Code Coverage Report

**Overall Coverage:** {coverage_data['overall_coverage']:.1f}% ({coverage_data['covered_lines']:,} of {coverage_data['total_lines']:,} lines)  
**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

**Coverage Trend:** {trend_indicator}  
**Quality Gate:** {quality_gate}  
**Missing Lines:** {coverage_data['missing_lines']:,}

## Module Breakdown

| Module | Coverage | Lines Covered | Total Lines | Missing | Status |
|--------|----------|---------------|-------------|---------|---------|
"""

    # Add module rows
    for module in coverage_data['modules']:
        status = get_status_emoji(module['coverage_pct'])
        markdown += f"| {module['module']} | {module['coverage_pct']:.1f}% | {module['lines_covered']} | {module['lines_total']} | {module['lines_missing']} | {status} |\n"
    
    # Add footer
    markdown += f"""
## Coverage Analysis

### High Coverage Modules (≥90%)
"""
    high_coverage = [m for m in coverage_data['modules'] if m['coverage_pct'] >= 90]
    if high_coverage:
        for module in high_coverage:
            markdown += f"- **{module['module']}**: {module['coverage_pct']:.1f}% ({module['lines_covered']}/{module['lines_total']} lines)\n"
    else:
        markdown += "- No modules with ≥90% coverage\n"
    
    markdown += "\n### Modules Needing Attention (<60%)\n"
    low_coverage = [m for m in coverage_data['modules'] if m['coverage_pct'] < 60]
    if low_coverage:
        for module in low_coverage:
            markdown += f"- **{module['module']}**: {module['coverage_pct']:.1f}% ({module['lines_missing']} lines missing coverage)\n"
    else:
        markdown += "- All modules above 60% coverage threshold ✅\n"
    
    markdown += f"""
---

*This report is automatically generated from coverage.py data. To update, run `./tools/generate_reports.sh`*
"""
    
    return markdown

def main():
    """Main function to generate coverage report."""
    
    # Get script directory and setup paths
    script_dir = Path(__file__).parent.absolute()
    output_path = script_dir.parent / 'docs-site/docs/reports/coverage-report.md'
    
    print("📊 Generating coverage report from coverage.py data...")
    
    # Get coverage data
    coverage_data = get_coverage_data()
    
    # Generate markdown
    markdown_content = generate_coverage_markdown(coverage_data)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the report
    with open(output_path, 'w') as f:
        f.write(markdown_content)
    
    if coverage_data:
        print(f"✅ Coverage report generated: {coverage_data['overall_coverage']:.1f}% overall coverage")
        print(f"   📄 Saved to: {output_path}")
        print(f"   📈 {len(coverage_data['modules'])} modules analyzed")
    else:
        print("⚠️  Coverage report generated with no data placeholder")
        print(f"   📄 Saved to: {output_path}")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
