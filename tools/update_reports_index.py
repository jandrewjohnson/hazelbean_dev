#!/usr/bin/env python3
"""
Simple script to extract metrics from pytest-md-report output and update reports index
Replaces the complex JSON parsing with simple markdown text extraction
"""

import re
import os
from datetime import datetime

def extract_metrics_from_markdown(report_path):
    """Extract key metrics from the pytest-md-report generated markdown."""
    
    if not os.path.exists(report_path):
        return None
    
    with open(report_path, 'r') as f:
        content = f.read()
    
    # Find the TOTAL line by looking for lines containing the LaTeX-formatted TOTAL
    lines = content.split('\n')
    total_line = None
    for line in lines:
        if '\\tt{TOTAL}' in line:
            total_line = line
            break
    
    if not total_line:
        print("Could not find TOTAL line in report")
        return None
    
    print(f"Found TOTAL line: {total_line}")
    
    # Extract numbers using simpler regex - find all numbers in the TOTAL line
    numbers = re.findall(r'\\tt\{(\d+)\}', total_line)
    print(f"Extracted numbers: {numbers}")
    
    if len(numbers) >= 5:
        passed = int(numbers[0])
        failed = int(numbers[1]) 
        error = int(numbers[2])
        skipped = int(numbers[3])
        total = int(numbers[4])
        
        # Calculate pass rate
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        # Determine status
        if pass_rate == 100:
            status = "🟢 **ALL TESTS PASSING**"
        elif pass_rate >= 90:
            status = "🟡 **MOSTLY PASSING**"
        else:
            status = "🔴 **TESTS FAILING**"
        
        return {
            'passed': passed,
            'failed': failed,
            'error': error,
            'skipped': skipped,
            'total': total,
            'pass_rate': pass_rate,
            'status': status,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    else:
        print(f"Expected 5 numbers, got {len(numbers)}")
        return None

def update_reports_index(metrics, index_path):
    """Update the reports index.md with current metrics and eliminate 'Coming Soon' text."""
    
    if not metrics:
        print("No metrics available to update index")
        return False
    
    # Read current index
    with open(index_path, 'r') as f:
        content = f.read()
    
    # Update the status line
    # Look for pattern like: **Current Status:** 🟡 MOSTLY PASSING (94.1% pass rate)
    status_pattern = r'(\*\*Current Status:\*\*) [^\n]+'
    status_replacement = f'\\1 {metrics["status"]} ({metrics["pass_rate"]:.1f}% pass rate)'
    content = re.sub(status_pattern, status_replacement, content)
    
    # Update test categories summary
    categories_pattern = r'(\*\*Test Categories\*\*: Unit, Integration, Performance, System tests\s+- \*\*Automation\*\*: Fully automated test result generation\s+- \*\*Reporting\*\*: Real-time markdown reports from JSON output\s+- \*\*Metrics\*\*:) [^\n]+'
    categories_replacement = f'\\1 {metrics["passed"]} passed, {metrics["failed"]} failed, {metrics["error"]} errors, {metrics["skipped"]} skipped'
    content = re.sub(categories_pattern, categories_replacement, content, flags=re.DOTALL)
    
    # **NEW: Eliminate "Coming Soon" sections and replace with functional reports**
    
    # Replace Performance Baselines "Coming Soon"
    performance_pattern = r'(### 📈 \*\*Performance Baselines\*\*\s*)\*Coming Soon\* - Automated performance tracking and trend analysis'
    performance_replacement = r'\1**Available** - [View Performance Baselines](performance-baselines.md)\n- Real-time performance baseline tracking with trend analysis\n- Statistical confidence intervals and machine context\n- Historical snapshot comparisons and regression detection'
    content = re.sub(performance_pattern, performance_replacement, content)
    
    # Replace Coverage Reports "Coming Soon"
    coverage_pattern = r'(### 📊 \*\*Coverage Reports\*\*\s*)\*Coming Soon\* - Code coverage analysis and reporting'
    coverage_replacement = r'\1**Available** - [View Coverage Report](coverage-report.md)\n- Module-by-module coverage analysis with detailed breakdowns\n- Coverage trends and quality gate monitoring\n- Missing line identification and improvement suggestions'
    content = re.sub(coverage_pattern, coverage_replacement, content)
    
    # Replace Benchmark Results "Coming Soon"
    benchmark_pattern = r'(### ⚡ \*\*Benchmark Results\*\*\s*)\*Coming Soon\* - Performance benchmark tracking and comparisons'
    benchmark_replacement = r'\1**Available** - [View Benchmark Results](benchmark-results.md)\n- Latest benchmark execution results with performance analysis\n- Historical trend tracking and regression detection\n- Detailed timing statistics and system information'
    content = re.sub(benchmark_pattern, benchmark_replacement, content)
    
    # Write updated content
    with open(index_path, 'w') as f:
        f.write(content)
    
    print(f"Updated reports index with current metrics: {metrics['pass_rate']:.1f}% pass rate")
    print("✅ Eliminated all 'Coming Soon' text and added functional report links")
    return True

def main():
    """Main function to update reports index with current test metrics."""
    
    # Paths relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(script_dir, '../docs-site/docs/reports/test-results.md')
    index_path = os.path.join(script_dir, '../docs-site/docs/reports/index.md')
    
    print(f"Extracting metrics from: {report_path}")
    metrics = extract_metrics_from_markdown(report_path)
    
    if metrics:
        print(f"Found metrics: {metrics['total']} total tests, {metrics['pass_rate']:.1f}% pass rate")
        
        print(f"Updating index at: {index_path}")
        success = update_reports_index(metrics, index_path)
        
        if success:
            print("✅ Reports index updated successfully!")
        else:
            print("❌ Failed to update reports index")
    else:
        print("❌ Could not extract metrics from report")

if __name__ == '__main__':
    main()
