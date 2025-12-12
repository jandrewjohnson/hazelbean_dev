#!/usr/bin/env python3
"""
Master script to generate all report pages for Quarto documentation
Runs all report generation scripts and provides summary output

Usage:
    python tools/generate_all_reports.py
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

def run_script(script_name: str, script_path: Path) -> tuple[bool, str]:
    """Run a report generation script and return success status and output."""
    try:
        print(f"\n{'='*60}")
        print(f"Running: {script_name}")
        print(f"{'='*60}")
        
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Print stdout
        if result.stdout:
            print(result.stdout)
        
        # Print stderr if there were issues
        if result.stderr:
            print(f"Warnings/Errors:\n{result.stderr}", file=sys.stderr)
        
        success = result.returncode == 0
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {script_name}: {'SUCCESS' if success else 'FAILED'}")
        
        return success, result.stdout
        
    except subprocess.TimeoutExpired:
        print(f"❌ {script_name}: TIMEOUT (>60s)")
        return False, ""
    except Exception as e:
        print(f"❌ {script_name}: ERROR - {e}")
        return False, ""

def main():
    """Generate all reports."""
    
    print("="*60)
    print("🚀 Hazelbean Documentation Report Generator")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get script directory
    script_dir = Path(__file__).parent.absolute()
    
    # Define all report scripts
    report_scripts = [
        ("Test Results Report", script_dir / "generate_test_results_report.py"),
        ("Performance Baselines Report", script_dir / "generate_baseline_report.py"),
        ("Coverage Report", script_dir / "generate_coverage_report.py"),
        ("Benchmark Results Report", script_dir / "generate_benchmark_summary.py"),
    ]
    
    # Run each script and track results
    results = {}
    for script_name, script_path in report_scripts:
        if not script_path.exists():
            print(f"⚠️  {script_name}: Script not found at {script_path}")
            results[script_name] = False
            continue
        
        success, output = run_script(script_name, script_path)
        results[script_name] = success
    
    # Print summary
    print("\n" + "="*60)
    print("📊 Report Generation Summary")
    print("="*60)
    
    total = len(results)
    successful = sum(1 for success in results.values() if success)
    failed = total - successful
    
    for script_name, success in results.items():
        icon = "✅" if success else "❌"
        print(f"{icon} {script_name}")
    
    print()
    print(f"Total: {total} reports")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print()
    
    if failed == 0:
        print("🎉 All reports generated successfully!")
        print()
        print("Next steps:")
        print("  cd docs-site/quarto-docs")
        print("  quarto render")
        return_code = 0
    else:
        print("⚠️  Some reports failed to generate.")
        print("   Reports with missing data will have placeholder content.")
        print()
        print("To generate data:")
        print("  - Test results: cd hazelbean_tests && python -m pytest --json-report")
        print("  - Performance baselines: python scripts/establish_performance_baseline.py")
        print("  - Coverage: cd hazelbean_tests && python -m pytest --cov=hazelbean")
        print("  - Benchmarks: python scripts/run_performance_benchmarks.py")
        return_code = 1
    
    print()
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return return_code

if __name__ == '__main__':
    sys.exit(main())


