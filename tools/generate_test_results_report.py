#!/usr/bin/env python3
"""
Generate test results report from pytest JSON output
Input: pytest JSON report (from --json-report)
Output: docs-site/quarto-docs/reports/test-results.qmd

Usage:
    cd hazelbean_tests
    python -m pytest --json-report --json-report-file=test-results.json
    python ../tools/generate_test_results_report.py test-results.json
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

def load_test_results(json_path: Path) -> Optional[Dict]:
    """Load pytest JSON report data."""
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading test results from {json_path}: {e}")
        return None

def parse_test_results(data: Dict) -> Dict:
    """Parse pytest JSON data into summary statistics."""
    summary = data.get('summary', {})
    tests = data.get('tests', [])
    duration = data.get('duration', 0)
    
    # Count by outcome
    passed = summary.get('passed', 0)
    failed = summary.get('failed', 0)
    skipped = summary.get('skipped', 0)
    error = summary.get('error', 0)
    total = summary.get('total', 0)
    
    # Group tests by file
    by_file = {}
    for test in tests:
        nodeid = test.get('nodeid', '')
        outcome = test.get('outcome', 'unknown')
        
        # Extract file path from nodeid (e.g., "unit/test_arrayframe.py::test_something")
        if '::' in nodeid:
            filepath = nodeid.split('::')[0]
        else:
            filepath = 'unknown'
        
        if filepath not in by_file:
            by_file[filepath] = {'passed': 0, 'failed': 0, 'skipped': 0, 'error': 0, 'total': 0}
        
        by_file[filepath][outcome] = by_file[filepath].get(outcome, 0) + 1
        by_file[filepath]['total'] += 1
    
    return {
        'summary': {
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'error': error,
            'total': total,
            'duration': duration
        },
        'by_file': by_file,
        'tests': tests
    }

def get_status_indicator(passed: int, failed: int, error: int) -> str:
    """Get status indicator based on results."""
    if failed > 0 or error > 0:
        return "[FAIL]"
    elif passed > 0:
        return "[PASS]"
    else:
        return "[WARN]"

def generate_test_results_markdown(results: Dict) -> str:
    """Generate Quarto markdown from test results."""
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if not results:
        return f"""---
title: "Test Results"
---

**Status:** No test results available

Please run tests with JSON reporting enabled:

```bash
conda activate hazelbean_env
cd hazelbean_tests
python -m pytest --json-report --json-report-file=test-results.json
python ../tools/generate_test_results_report.py test-results.json
```

*Last Updated: {timestamp}*
"""
    
    summary = results['summary']
    by_file = results['by_file']
    
    # Calculate overall status
    if summary['failed'] > 0 or summary['error'] > 0:
        overall_status = "Some Tests Failed"
        status_color = "danger"
    elif summary['total'] == summary['passed']:
        overall_status = "All Tests Passed"
        status_color = "success"
    else:
        overall_status = "Some Tests Skipped"
        status_color = "warning"
    
    # Calculate pass rate
    if summary['total'] > 0:
        pass_rate = (summary['passed'] / summary['total']) * 100
    else:
        pass_rate = 0
    
    markdown = f"""---
title: "Test Results"
---

::: {{.callout-{status_color}}}
## {overall_status}

**Pass Rate:** {pass_rate:.1f}% ({summary['passed']}/{summary['total']} tests)  
**Duration:** {summary['duration']:.2f}s  
**Last Updated:** {timestamp}
:::

## Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| **Passed** | {summary['passed']} | {(summary['passed']/summary['total']*100) if summary['total'] > 0 else 0:.1f}% |
| **Failed** | {summary['failed']} | {(summary['failed']/summary['total']*100) if summary['total'] > 0 else 0:.1f}% |
| **Skipped** | {summary['skipped']} | {(summary['skipped']/summary['total']*100) if summary['total'] > 0 else 0:.1f}% |
| **Error** | {summary['error']} | {(summary['error']/summary['total']*100) if summary['total'] > 0 else 0:.1f}% |
| **Total** | {summary['total']} | 100% |

## Results by Test File

| Test File | Status | Passed | Failed | Skipped | Error | Total |
|-----------|--------|--------|--------|---------|-------|-------|
"""
    
    # Sort files by status (failed/error first, then by name)
    sorted_files = sorted(
        by_file.items(),
        key=lambda x: (
            -(x[1]['failed'] + x[1]['error']),  # Failed/error first (negative for descending)
            x[0]  # Then alphabetically
        )
    )
    
    for filepath, stats in sorted_files:
        status = get_status_indicator(stats['passed'], stats['failed'], stats['error'])
        markdown += f"| `{filepath}` | {status} | {stats['passed']} | {stats['failed']} | {stats['skipped']} | {stats['error']} | {stats['total']} |\n"
    
    # Add failed tests details if any
    failed_tests = [t for t in results['tests'] if t.get('outcome') in ['failed', 'error']]
    
    if failed_tests:
        markdown += f"""
## Failed Tests Details

::: {{.callout-warning collapse="true"}}
### {len(failed_tests)} Test(s) Failed or Errored

"""
        for test in failed_tests:
            nodeid = test.get('nodeid', 'Unknown')
            outcome = test.get('outcome', 'unknown')
            duration = test.get('duration', 0)
            
            markdown += f"""
#### {outcome.upper()}: `{nodeid}`

**Duration:** {duration:.3f}s

"""
            
            # Add error/failure message if available
            call = test.get('call', {})
            if call:
                longrepr = call.get('longrepr', '')
                if longrepr:
                    markdown += f"""
```
{longrepr[:500]}{'...' if len(longrepr) > 500 else ''}
```

"""
        
        markdown += ":::\n"
    
    markdown += f"""
---

## How to Update This Report

To regenerate this report with latest test results:

```bash
# 1. Run tests with JSON reporting
cd hazelbean_tests
conda activate hazelbean_env
pytest --json-report --json-report-file=test-results.json --quiet

# 2. Generate markdown report
python ../tools/generate_test_results_report.py test-results.json

# 3. Render Quarto site
cd ../docs-site/quarto-docs
quarto render
```

---

*This report is automatically generated from pytest JSON output. Run the commands above to update with latest results.*
"""
    
    return markdown

def main():
    """Main function to generate test results report."""
    
    # Get script directory and setup paths
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent
    
    # Determine input path (from args or default)
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
        if not input_path.is_absolute():
            # Try relative to current directory first
            if input_path.exists():
                pass
            # Then try relative to hazelbean_tests
            elif (project_root / 'hazelbean_tests' / input_path).exists():
                input_path = project_root / 'hazelbean_tests' / input_path
            else:
                print(f"Error: Could not find test results at {input_path}")
                sys.exit(1)
    else:
        # Default path
        input_path = project_root / 'hazelbean_tests' / 'test-results.json'
    
    output_path = project_root / 'docs-site/quarto-docs/reports/test-results.qmd'
    
    print("📊 Generating test results report...")
    print(f"   📄 Input: {input_path}")
    
    # Load test results
    if input_path.exists():
        test_data = load_test_results(input_path)
        if test_data:
            results = parse_test_results(test_data)
        else:
            results = None
    else:
        print(f"⚠️  No test results found at {input_path}")
        print("   Generating placeholder report...")
        results = None
    
    # Generate markdown
    markdown_content = generate_test_results_markdown(results)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the report
    with open(output_path, 'w') as f:
        f.write(markdown_content)
    
    if results:
        summary = results['summary']
        print(f"✅ Test results report generated")
        print(f"   ✓ {summary['passed']} passed, ✗ {summary['failed']} failed, ⊘ {summary['skipped']} skipped")
        print(f"   📄 Saved to: {output_path}")
    else:
        print("⚠️  Test results report generated with placeholder content")
        print(f"   📄 Saved to: {output_path}")
        print("   Run tests with --json-report to generate actual data")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)


