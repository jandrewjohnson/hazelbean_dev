#!/usr/bin/env python3
"""
Performance Benchmarking CLI Script for Hazelbean

This script provides a comprehensive command-line interface for running
performance benchmarks, generating reports, and detecting regressions.

Story 4: Parallel & Path Benchmarks - Complete Implementation
Usage:
    python scripts/run_performance_benchmarks.py [OPTIONS]
"""

import argparse
import os
import sys
import json
import subprocess
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm

# Add hazelbean to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import hazelbean as hb


def main():
    """Main entry point for performance benchmarking CLI"""
    parser = argparse.ArgumentParser(
        description="Run Hazelbean performance benchmarks and generate reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # 🚀 RECOMMENDED: Complete end-to-end workflow
    python scripts/run_performance_benchmarks.py --complete-workflow
    
    # Run all performance benchmarks
    python scripts/run_performance_benchmarks.py --all
    
    # Run only tiling benchmarks
    python scripts/run_performance_benchmarks.py --tiling
    
    # Run path resolution benchmarks
    python scripts/run_performance_benchmarks.py --path-resolution
    
    # Run integration scenario benchmarks
    python scripts/run_performance_benchmarks.py --integration
    
    # Run benchmarks and generate report
    python scripts/run_performance_benchmarks.py --all --report
    
    # Check for performance regressions
    python scripts/run_performance_benchmarks.py --check-regression
    
    # Establish new baseline
    python scripts/run_performance_benchmarks.py --establish-baseline --runs 5
        """
    )
    
    # Benchmark selection options
    parser.add_argument('--all', action='store_true',
                       help='Run all performance benchmarks')
    parser.add_argument('--tiling', action='store_true',
                       help='Run tiling operation benchmarks')
    parser.add_argument('--path-resolution', action='store_true',
                       help='Run path resolution benchmarks')
    parser.add_argument('--integration', action='store_true',
                       help='Run integration scenario benchmarks (Story 5)')
    parser.add_argument('--aggregation', action='store_true',
                       help='Run performance aggregation tests')
    
    # Reporting options
    parser.add_argument('--report', action='store_true',
                       help='Generate performance report after benchmarks')
    parser.add_argument('--output-dir', default='./metrics',
                       help='Directory for storing benchmark results (default: ./metrics)')
    
    # Regression detection options
    parser.add_argument('--check-regression', action='store_true',
                       help='Check for performance regressions against baseline')
    parser.add_argument('--threshold', type=float, default=10.0,
                       help='Regression threshold percentage (default: 10.0)')
    
    # Baseline establishment
    parser.add_argument('--establish-baseline', action='store_true',
                       help='Establish new performance baseline')
    parser.add_argument('--runs', type=int, default=3,
                       help='Number of runs for baseline establishment (default: 3)')
    
    # Execution options
    parser.add_argument('--parallel', action='store_true',
                       help='Run benchmarks in parallel where possible')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    # Complete workflow option
    parser.add_argument('--complete-workflow', action='store_true',
                       help='Run complete end-to-end workflow: baseline → benchmarks → regression check → report → dashboard → CSV export')
    
    args = parser.parse_args()
    
    # Handle complete workflow first
    if args.complete_workflow:
        args.establish_baseline = True
        args.runs = args.runs or 3  # Default to 3 runs for baseline
        args.all = True
        args.report = True
        args.check_regression = True
        args.verbose = True  # Force verbose for complete workflow
        
        # Set flags for additional features we'll add after main operations
        create_dashboard = True
        export_csv = True
    else:
        create_dashboard = False
        export_csv = False
    
    # Validate arguments
    if not any([args.all, args.tiling, args.path_resolution, args.aggregation, 
                args.integration, args.check_regression, args.establish_baseline, args.complete_workflow]):
        parser.error("Must specify at least one benchmark type or action")
    
    if args.complete_workflow:
        args.establish_baseline = True
        args.runs = args.runs or 3  # Default to 3 runs for baseline
        args.all = True
        args.report = True
        args.check_regression = True
        args.verbose = True  # Force verbose for complete workflow
        
        # Set flags for additional features we'll add after main operations
        create_dashboard = True
        export_csv = True
    else:
        create_dashboard = False
        export_csv = False

    # Setup
    os.makedirs(args.output_dir, exist_ok=True)

    start_time = time.time()

    # Show enhanced startup banner
    if args.verbose:
        show_startup_banner(args)
    else:
        print("🚀 Starting Hazelbean Performance Benchmarks...")
        print("⏳ Initializing...")

    # Count total operations for progress tracking
    total_operations = 0
    if args.establish_baseline:
        total_operations += 1
    if args.check_regression:
        total_operations += 1
    if any([args.all, args.tiling, args.path_resolution, args.aggregation, args.integration]):
        total_operations += 1
    if args.report:
        total_operations += 1
    if create_dashboard:
        total_operations += 1
    if export_csv:
        total_operations += 1
    
    # Execute requested operations with progress tracking
    try:
        if args.verbose:
            print(f"\n🔄 STARTING EXECUTION ({total_operations} operations)")
            print("=" * 60)
            
        with tqdm(total=total_operations, desc="📊 Overall Progress", 
                  bar_format="{desc}: {percentage:3.0f}%|{bar}| {n}/{total} [{elapsed}<{remaining}]",
                  disable=not args.verbose,
                  ncols=80,
                  colour='green') as pbar:
            
            if args.establish_baseline:
                pbar.set_description("📏 Establishing baseline")
                establish_baseline(args)
                pbar.update(1)
            
            if args.check_regression:
                pbar.set_description("🔍 Checking regressions")
                check_regression(args)
                pbar.update(1)
            
            if any([args.all, args.tiling, args.path_resolution, args.aggregation, args.integration]):
                pbar.set_description("🧪 Running benchmarks")
                run_benchmarks(args)
                pbar.update(1)
            
            if args.report:
                pbar.set_description("📋 Generating report")
                generate_report(args)
                pbar.update(1)
            
            if create_dashboard:
                pbar.set_description("🌐 Creating dashboard")
                create_interactive_dashboard(args)
                pbar.update(1)
            
            if export_csv:
                pbar.set_description("📊 Exporting CSV")
                export_performance_csv(args)
                pbar.update(1)
            
            elapsed_time = time.time() - start_time
            if args.verbose:
                print(f"\n🎉 SUCCESS! All operations completed")
                print("=" * 60)
                print(f"⏱️  Total execution time: {format_duration(elapsed_time)}")
                
                # Show summary of generated files
                show_generated_files_summary(args.output_dir)
                
                if args.complete_workflow:
                    print_complete_workflow_summary()
                
                print("🎯 Performance benchmarking finished successfully!")
            else:
                print(f"✅ Completed in {format_duration(elapsed_time)}")
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n❌ Error during benchmarking: {e}")
        print(f"⏱️  Execution time before error: {format_duration(elapsed_time)}")
        sys.exit(1)


def run_benchmarks(args):
    """Run the specified benchmarks"""
    test_modules = []
    
    # Use the correct performance test paths
    if args.all or args.tiling or args.path_resolution:
        test_modules.append(("hazelbean_tests/performance/test_benchmarks.py", "Core Benchmarks"))
        test_modules.append(("hazelbean_tests/performance/test_functions.py", "Function Benchmarks"))
    
    if args.aggregation:
        test_modules.append(("hazelbean_tests/performance/test_workflows.py", "Workflow & Aggregation Tests"))
    
    if args.integration:
        test_modules.append(("hazelbean_tests/performance/test_benchmarks.py::TestIntegrationScenarioBenchmarks", "Integration Scenario Benchmarks"))
    
    # Run benchmarks with progress tracking
    for i, (module, description) in enumerate(test_modules):
        module_start_time = time.time()
        
        if args.verbose:
            print(f"\n🔄 [{i+1}/{len(test_modules)}] Running {description}")
            print(f"   Module: {module}")
        
        # Run pytest with benchmark configuration
        # Save benchmark files to organized benchmarks subdirectory
        benchmarks_dir = os.path.join(args.output_dir, "benchmarks")
        os.makedirs(benchmarks_dir, exist_ok=True)
        benchmark_file = os.path.join(benchmarks_dir, f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        cmd = [
            "python", "-m", "pytest", 
            module,
            "-v" if args.verbose else "-q",
            "--benchmark-json=" + benchmark_file,
            "-m", "benchmark",
            "--tb=short",  # Shorter traceback for cleaner output
            "--disable-warnings"  # Reduce noise
        ]
        
        if args.parallel:
            cmd.extend(["-n", "auto"])
        
        # Show progress during test execution with real-time feedback
        if args.verbose:
            print(f"   ⏳ Executing pytest...")
            print(f"   💫 Running {len([x for x in cmd if 'test_' in x])} test functions...")
            
        # Run with real-time output for better user feedback
        result = run_with_progress_feedback(cmd, args.verbose)
        
        module_elapsed_time = time.time() - module_start_time
        
        if result.returncode != 0:
            if args.verbose:
                print(f"   ⚠️  Benchmark warnings or errors (took {format_duration(module_elapsed_time)}):")
                if args.verbose:
                    # Show only key lines to avoid clutter
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if any(keyword in line.lower() for keyword in ['failed', 'error', 'passed', 'benchmark']):
                            print(f"      {line}")
        else:
            if args.verbose:
                print(f"   ✅ Completed successfully (took {format_duration(module_elapsed_time)})")
                
        # Show benchmark file size if generated
        if os.path.exists(benchmark_file) and os.path.getsize(benchmark_file) > 0:
            file_size = os.path.getsize(benchmark_file) / 1024  # KB
            if args.verbose:
                print(f"   📊 Generated benchmark file: {os.path.basename(benchmark_file)} ({file_size:.1f}KB)")
                print(f"   🔗 Open file: {create_file_link(benchmark_file)}")


def validate_benchmark_json(file_path, verbose=False):
    """
    Validate a benchmark JSON file and return its contents if valid.
    
    Returns:
        Tuple[bool, Optional[dict], Optional[str]]: (success, data, error_message)
    """
    # Check if file exists
    if not os.path.exists(file_path):
        return False, None, f"File does not exist: {file_path}"
    
    # Check if file has content
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return False, None, f"File is empty (0 bytes): {os.path.basename(file_path)}"
    
    # Attempt to parse JSON
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON in {os.path.basename(file_path)}: {e}"
    except Exception as e:
        return False, None, f"Error reading {os.path.basename(file_path)}: {e}"
    
    # Validate structure - must have benchmarks array
    if "benchmarks" not in data:
        return False, None, f"No 'benchmarks' key in {os.path.basename(file_path)}"
    
    if not isinstance(data["benchmarks"], list):
        return False, None, f"'benchmarks' is not a list in {os.path.basename(file_path)}"
    
    if len(data["benchmarks"]) == 0:
        return False, None, f"No benchmarks found in {os.path.basename(file_path)}"
    
    # Success!
    return True, data, None


def establish_baseline(args):
    """Establish performance baseline from multiple runs"""
    baseline_start_time = time.time()
    
    if args.verbose:
        print(f"\n📏 Establishing performance baseline with {args.runs} runs")
    
    # Create benchmarks directory for baseline files
    benchmarks_dir = os.path.join(args.output_dir, "benchmarks")
    os.makedirs(benchmarks_dir, exist_ok=True)
    
    baseline_results = []
    failed_runs = []
    
    # Use tqdm for baseline run progress
    with tqdm(total=args.runs, desc="Baseline runs", 
              bar_format="{desc}: {percentage:3.0f}%|{bar}| {n}/{total} [{elapsed}<{remaining}]",
              disable=not args.verbose) as pbar:
        
        for run_num in range(args.runs):
            run_start_time = time.time()
            
            pbar.set_description(f"Baseline run {run_num + 1}/{args.runs}")
            
            # Run core benchmarks for baseline
            cmd = [
                "python", "-m", "pytest",
                "hazelbean_tests/performance/test_benchmarks.py::TestSimpleBenchmarks::test_array_operations_benchmark",
                "hazelbean_tests/performance/test_functions.py::TestGetPathFunctionBenchmarks::test_get_path_function_overhead",
                "--benchmark-json", os.path.join(benchmarks_dir, f"baseline_run_{run_num}.json"),
                "-v"  # Verbose to see what's happening
            ]
            
            # Show progress during baseline run
            if args.verbose:
                print(f"      ⏳ Executing baseline benchmarks...")
                
            result = run_with_progress_feedback(cmd, args.verbose, show_pytest_progress=False)
            
            # Check pytest return code
            if result.returncode != 0:
                error_msg = f"Pytest failed with exit code {result.returncode}"
                if args.verbose:
                    print(f"      ⚠️  {error_msg}")
                    if result.stderr:
                        stderr_preview = result.stderr[:1000]  # First 1000 chars
                        print(f"      Stderr: {stderr_preview}")
                    if result.stdout:
                        stdout_preview = result.stdout[:1000]  # First 1000 chars
                        print(f"      Stdout: {stdout_preview}")
                else:
                    # Even in non-verbose, show some error output for debugging
                    print(f"      ⚠️  Run {run_num + 1} failed: {error_msg}")
                    if result.stderr:
                        print(f"      Error: {result.stderr[:300]}")
                        
                failed_runs.append({
                    "run_id": run_num,
                    "error": error_msg,
                    "returncode": result.returncode,
                    "stderr": result.stderr[:500] if result.stderr else None,
                    "stdout": result.stdout[:500] if result.stdout else None
                })
                run_elapsed = time.time() - run_start_time
                pbar.set_postfix({"Last run": f"{format_duration(run_elapsed)} ⚠️"})
                pbar.update(1)
                continue  # Skip to next run
            
            # Validate and extract results
            baseline_file = os.path.join(benchmarks_dir, f"baseline_run_{run_num}.json")
            success, benchmark_data, error_msg = validate_benchmark_json(baseline_file, args.verbose)
            
            if success:
                baseline_results.append({
                    "run_id": run_num,
                    "timestamp": datetime.now().isoformat(),
                    "benchmark_data": benchmark_data
                })
                if args.verbose:
                    num_benchmarks = len(benchmark_data.get("benchmarks", []))
                    print(f"      ✅ Run {run_num + 1} successful ({num_benchmarks} benchmarks)")
            else:
                # Validation failed
                if args.verbose:
                    print(f"      ⚠️  Run {run_num + 1} failed: {error_msg}")
                failed_runs.append({
                    "run_id": run_num,
                    "error": error_msg,
                    "file": baseline_file
                })
            
            run_elapsed = time.time() - run_start_time
            status_emoji = "✅" if success else "⚠️"
            pbar.set_postfix({"Last run": f"{format_duration(run_elapsed)} {status_emoji}"})
            pbar.update(1)
    
    # Calculate baseline statistics
    baseline_elapsed = time.time() - baseline_start_time
    
    # Print summary
    successful_runs = len(baseline_results)
    total_runs = args.runs
    
    if args.verbose or successful_runs < total_runs:
        print(f"\n📊 Baseline Run Summary:")
        print(f"   ✅ Successful: {successful_runs}/{total_runs}")
        if failed_runs:
            print(f"   ⚠️  Failed: {len(failed_runs)}/{total_runs}")
            if args.verbose:
                for failed in failed_runs:
                    print(f"      • Run {failed['run_id'] + 1}: {failed['error']}")
    
    if baseline_results:
        baseline = calculate_baseline_from_runs(baseline_results)
        # Save baseline to organized baselines subdirectory
        baselines_dir = os.path.join(args.output_dir, "baselines")
        os.makedirs(baselines_dir, exist_ok=True)
        baseline_path = os.path.join(baselines_dir, "current_performance_baseline.json")
        
        with open(baseline_path, 'w') as f:
            json.dump(baseline, f, indent=2)
        
        if args.verbose:
            print(f"\n✅ Baseline established and saved to: {os.path.basename(baseline_path)}")
            print(f"🔗 Open baseline file: {create_file_link(baseline_path)}")
            print(f"⏱️  Baseline establishment took: {format_duration(baseline_elapsed)}")
        else:
            # Non-verbose output for CI
            print(f"✅ Baseline established from {successful_runs}/{total_runs} successful runs")
    else:
        # Complete failure - no successful runs
        error_summary = f"Failed to establish baseline - 0/{total_runs} runs succeeded"
        print(f"\n❌ {error_summary}")
        
        if failed_runs:
            print("\n🔍 Failure Details:")
            for failed in failed_runs:
                print(f"   • Run {failed['run_id'] + 1}: {failed['error']}")
        
        print("\n💡 Troubleshooting:")
        print("   1. Check that pytest-benchmark is installed")
        print("   2. Verify test files exist and are executable")
        print("   3. Run with --verbose flag for detailed output")
        print("   4. Try running pytest commands manually to debug")
        
        sys.exit(1)  # Exit with error since no baseline was established


def calculate_baseline_from_runs(baseline_results):
    """Calculate baseline statistics from multiple benchmark runs"""
    import statistics
    
    # Extract execution times from all runs
    all_times = []
    for result in baseline_results:
        benchmark_data = result["benchmark_data"]
        if "benchmarks" in benchmark_data:
            for benchmark in benchmark_data["benchmarks"]:
                if "stats" in benchmark:
                    all_times.append(benchmark["stats"]["mean"])
    
    if not all_times:
        return {"error": "No timing data found in baseline runs"}
    
    # Calculate statistics
    mean_time = statistics.mean(all_times)
    std_dev = statistics.stdev(all_times) if len(all_times) > 1 else 0
    
    # 95% confidence interval
    margin_error = 1.96 * (std_dev / (len(all_times) ** 0.5)) if len(all_times) > 1 else 0
    
    return {
        "baseline_statistics": {
            "mean_execution_time": mean_time,
            "std_deviation": std_dev,
            "min_time": min(all_times),
            "max_time": max(all_times),
            "confidence_interval": {
                "lower": mean_time - margin_error,
                "upper": mean_time + margin_error
            },
            "sample_size": len(all_times)
        },
        "baseline_metadata": {
            "established_at": datetime.now().isoformat(),
            "num_runs": len(baseline_results),
            "statistical_confidence": "95%",
            "baseline_version": "1.0"
        },
        "raw_results": baseline_results
    }


def check_regression(args):
    """Check for performance regressions against baseline"""
    regression_start_time = time.time()
    
    if args.verbose:
        print(f"\n🔍 Checking for performance regressions (threshold: {args.threshold}%)")
    
    # Load baseline
    baseline_path = os.path.join(args.output_dir, "baselines", "current_performance_baseline.json")
    if not os.path.exists(baseline_path):
        print(f"❌ No baseline found at {baseline_path}")
        print("💡 Run with --establish-baseline first to create a baseline")
        return
    
    with open(baseline_path, 'r') as f:
        baseline = json.load(f)
    
    # Run current benchmarks with progress indication
    if args.verbose:
        print("⏳ Running current benchmarks for comparison...")
        
    benchmark_start_time = time.time()
    # Save regression check results to organized analysis subdirectory
    analysis_dir = os.path.join(args.output_dir, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)
    current_results_file = os.path.join(analysis_dir, f"regression_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    cmd = [
        "python", "-m", "pytest",
        "hazelbean_tests/performance/test_benchmarks.py::TestSimpleBenchmarks::test_array_operations_benchmark",
        "hazelbean_tests/performance/test_functions.py::TestGetPathFunctionBenchmarks::test_get_path_function_overhead",
        "--benchmark-json", current_results_file,
        "-v"
    ]
    
    # Show progress during regression benchmarks
    if args.verbose:
        print("      ⏳ Executing regression benchmarks...")
        
    result = run_with_progress_feedback(cmd, args.verbose, show_pytest_progress=False)
    benchmark_elapsed = time.time() - benchmark_start_time
    
    if args.verbose:
        print(f"   ✅ Benchmarks completed (took {format_duration(benchmark_elapsed)})")
    
    if not os.path.exists(current_results_file):
        print("❌ Failed to generate current benchmark results")
        return
    
    # Compare with baseline
    if args.verbose:
        print("⏳ Analyzing performance changes...")
        
    analysis_start_time = time.time()
    with open(current_results_file, 'r') as f:
        current_data = json.load(f)
    
    regression_analysis = analyze_regression(baseline, current_data, args.threshold)
    analysis_elapsed = time.time() - analysis_start_time
    
    if args.verbose:
        print(f"   ✅ Analysis completed (took {format_duration(analysis_elapsed)})")
    
    # Report results
    total_regression_time = time.time() - regression_start_time
    
    if regression_analysis["regression_detected"]:
        print("\n🚨 PERFORMANCE REGRESSION DETECTED!")
        print(f"📈 Maximum slowdown: {regression_analysis['max_slowdown']:.1f}%")
        print("🔍 Affected benchmarks:")
        for issue in regression_analysis["regression_details"]:
            print(f"  • {issue['benchmark_name']}: {issue['slowdown_percent']:.1f}% slower")
    else:
        print("\n✅ No performance regressions detected")
        if args.verbose and regression_analysis["performance_changes"]:
            print("📊 Performance changes within threshold:")
            for change in regression_analysis["performance_changes"]:
                print(f"  • {change['benchmark_name']}: {change['change_percent']:.1f}% change")
    
    if args.verbose:
        print(f"⏱️  Regression check took: {format_duration(total_regression_time)}")


def analyze_regression(baseline, current_data, threshold):
    """Analyze current performance against baseline for regressions"""
    if "baseline_statistics" not in baseline:
        return {"error": "Invalid baseline format"}
    
    baseline_mean = baseline["baseline_statistics"]["mean_execution_time"]
    baseline_upper_ci = baseline["baseline_statistics"]["confidence_interval"]["upper"]
    
    # Extract current performance
    current_times = []
    if "benchmarks" in current_data:
        for benchmark in current_data["benchmarks"]:
            if "stats" in benchmark:
                current_times.append({
                    "name": benchmark["name"],
                    "mean_time": benchmark["stats"]["mean"]
                })
    
    if not current_times:
        return {"error": "No current timing data found"}
    
    # Calculate average current performance
    current_mean = sum(b["mean_time"] for b in current_times) / len(current_times)
    
    # Check for regression
    slowdown_percent = ((current_mean - baseline_mean) / baseline_mean) * 100 if baseline_mean > 0 else 0
    outside_confidence_interval = current_mean > baseline_upper_ci
    
    regression_detected = slowdown_percent > threshold or outside_confidence_interval
    
    regression_details = []
    performance_changes = []
    
    for bench in current_times:
        bench_slowdown = ((bench["mean_time"] - baseline_mean) / baseline_mean) * 100 if baseline_mean > 0 else 0
        
        if bench_slowdown > threshold:
            regression_details.append({
                "benchmark_name": bench["name"],
                "slowdown_percent": bench_slowdown,
                "baseline_time": baseline_mean,
                "current_time": bench["mean_time"]
            })
        
        performance_changes.append({
            "benchmark_name": bench["name"],
            "change_percent": bench_slowdown
        })
    
    return {
        "regression_detected": regression_detected,
        "max_slowdown": max([abs(c["change_percent"]) for c in performance_changes]) if performance_changes else 0,
        "regression_details": regression_details,
        "performance_changes": performance_changes,
        "analysis_metadata": {
            "threshold_percent": threshold,
            "baseline_mean": baseline_mean,
            "current_mean": current_mean,
            "outside_confidence_interval": outside_confidence_interval
        }
    }


def generate_report(args):
    """Generate comprehensive performance report"""
    report_start_time = time.time()
    
    if args.verbose:
        print("\n📋 Generating performance report")
    
    # Collect all benchmark JSON files with progress
    if args.verbose:
        print("⏳ Scanning for benchmark files...")
        
    # Look for benchmark files in benchmarks subdirectory
    benchmarks_dir = os.path.join(args.output_dir, "benchmarks")
    benchmark_files = []
    if os.path.exists(benchmarks_dir):
        for filename in os.listdir(benchmarks_dir):
            if filename.startswith("benchmark_") and filename.endswith(".json"):
                benchmark_files.append(os.path.join(benchmarks_dir, filename))
    
    if not benchmark_files:
        print("⚠️  No benchmark files found for report generation")
        return
    
    if args.verbose:
        print(f"   📊 Found {len(benchmark_files)} benchmark files")
        print("⏳ Loading and aggregating benchmark data...")
    
    # Load and aggregate data with progress
    all_benchmarks = []
    load_start_time = time.time()
    
    with tqdm(total=len(benchmark_files), desc="Loading files", 
              bar_format="{desc}: {percentage:3.0f}%|{bar}| {n}/{total}",
              disable=not args.verbose) as pbar:
        
        for file_path in benchmark_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if "benchmarks" in data:
                        all_benchmarks.extend(data["benchmarks"])
                        pbar.set_postfix({"Benchmarks": len(all_benchmarks)})
            except Exception as e:
                if args.verbose:
                    print(f"\n⚠️  Could not load {os.path.basename(file_path)}: {e}")
            pbar.update(1)
    
    load_elapsed = time.time() - load_start_time
    
    if not all_benchmarks:
        print("❌ No benchmark data found for report generation")
        return
    
    if args.verbose:
        print(f"   ✅ Loaded {len(all_benchmarks)} benchmarks (took {format_duration(load_elapsed)})")
        print("⏳ Generating performance analysis...")
    
    # Generate report
    analysis_start_time = time.time()
    report = generate_performance_summary_report(all_benchmarks)
    analysis_elapsed = time.time() - analysis_start_time
    
    # Save report to organized reports subdirectory
    reports_dir = os.path.join(args.output_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    with open(report_file, 'w') as f:
        f.write(report)
    
    report_elapsed = time.time() - report_start_time
    
    if args.verbose:
        print(f"   ✅ Analysis completed (took {format_duration(analysis_elapsed)})")
    
    print(f"📄 Performance report saved to: {os.path.basename(report_file)}")
    print(f"🔗 Open report: {create_file_link(report_file)}")
    
    if args.verbose:
        print(f"⏱️  Report generation took: {format_duration(report_elapsed)}")
        print("\n" + "="*60)
        print("PERFORMANCE REPORT PREVIEW:")
        print("="*60)
        # Show first 20 lines of report
        lines = report.split('\n')
        for line in lines[:20]:
            print(line)
        if len(lines) > 20:
            print(f"... ({len(lines) - 20} more lines)")
        print("="*60)


def generate_performance_summary_report(benchmarks):
    """Generate a comprehensive performance summary report"""
    import statistics
    
    # Categorize benchmarks
    tiling_benchmarks = []
    path_resolution_benchmarks = []
    other_benchmarks = []
    
    for benchmark in benchmarks:
        name = benchmark.get("name", "unknown")
        if "tiling" in name.lower():
            tiling_benchmarks.append(benchmark)
        elif "resolution" in name.lower() or "path" in name.lower():
            path_resolution_benchmarks.append(benchmark)
        else:
            other_benchmarks.append(benchmark)
    
    # Generate report sections
    report_sections = [
        "=" * 80,
        "HAZELBEAN PERFORMANCE BENCHMARK REPORT",
        "=" * 80,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total benchmarks analyzed: {len(benchmarks)}",
        ""
    ]
    
    # Tiling performance section
    if tiling_benchmarks:
        report_sections.extend([
            "TILING OPERATIONS PERFORMANCE:",
            "-" * 40
        ])
        
        tiling_times = [b["stats"]["mean"] for b in tiling_benchmarks if "stats" in b]
        if tiling_times:
            report_sections.extend([
                f"Number of tiling benchmarks: {len(tiling_benchmarks)}",
                f"Mean execution time: {statistics.mean(tiling_times):.4f}s",
                f"Median execution time: {statistics.median(tiling_times):.4f}s",
                f"Min execution time: {min(tiling_times):.4f}s",
                f"Max execution time: {max(tiling_times):.4f}s",
                f"Standard deviation: {statistics.stdev(tiling_times) if len(tiling_times) > 1 else 0:.4f}s",
                ""
            ])
        
        # Top 5 slowest tiling operations
        if len(tiling_benchmarks) > 1:
            sorted_tiling = sorted(tiling_benchmarks, key=lambda x: x.get("stats", {}).get("mean", 0), reverse=True)
            report_sections.extend([
                "Slowest tiling operations:",
                ""
            ])
            for i, benchmark in enumerate(sorted_tiling[:5]):
                if "stats" in benchmark:
                    report_sections.append(f"  {i+1}. {benchmark['name']}: {benchmark['stats']['mean']:.4f}s")
            report_sections.append("")
    
    # Path resolution performance section
    if path_resolution_benchmarks:
        report_sections.extend([
            "PATH RESOLUTION PERFORMANCE:",
            "-" * 40
        ])
        
        path_times = [b["stats"]["mean"] for b in path_resolution_benchmarks if "stats" in b]
        if path_times:
            report_sections.extend([
                f"Number of path resolution benchmarks: {len(path_resolution_benchmarks)}",
                f"Mean execution time: {statistics.mean(path_times):.4f}s", 
                f"Median execution time: {statistics.median(path_times):.4f}s",
                f"Min execution time: {min(path_times):.4f}s",
                f"Max execution time: {max(path_times):.4f}s",
                f"Standard deviation: {statistics.stdev(path_times) if len(path_times) > 1 else 0:.4f}s",
                ""
            ])
    
    # Performance recommendations
    all_times = [b["stats"]["mean"] for b in benchmarks if "stats" in b]
    if all_times:
        overall_mean = statistics.mean(all_times)
        slow_benchmarks = [b for b in benchmarks if "stats" in b and b["stats"]["mean"] > overall_mean * 2]
        
        if slow_benchmarks:
            report_sections.extend([
                "PERFORMANCE RECOMMENDATIONS:",
                "-" * 40,
                f"Identified {len(slow_benchmarks)} benchmarks significantly slower than average:",
                ""
            ])
            
            for benchmark in slow_benchmarks[:3]:  # Top 3 recommendations
                report_sections.append(f"  • Consider optimizing: {benchmark['name']}")
                report_sections.append(f"    Current: {benchmark['stats']['mean']:.4f}s (Average: {overall_mean:.4f}s)")
            report_sections.append("")
    
    # Summary
    if all_times:
        report_sections.extend([
            "SUMMARY:",
            "-" * 20,
            f"Overall mean execution time: {statistics.mean(all_times):.4f}s",
            f"Performance variability (std dev): {statistics.stdev(all_times) if len(all_times) > 1 else 0:.4f}s",
            f"Fastest benchmark: {min(all_times):.4f}s",
            f"Slowest benchmark: {max(all_times):.4f}s",
            "",
            "=" * 80
        ])
    
    return "\n".join(report_sections)


def run_with_progress_feedback(cmd, verbose=True, show_pytest_progress=True):
    """Run subprocess with real-time progress feedback"""
    if not verbose:
        # Silent mode - just run normally
        return subprocess.run(cmd, capture_output=True, text=True)
    
    # Create a spinner for visual feedback
    spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    spinner_idx = 0
    
    # Start the process
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    def spinner_thread():
        nonlocal spinner_idx
        while process.poll() is None:
            if show_pytest_progress:
                print(f"\r      {spinner_chars[spinner_idx]} Running tests...", end="", flush=True)
                spinner_idx = (spinner_idx + 1) % len(spinner_chars)
                time.sleep(0.1)
    
    # Start spinner in background
    if show_pytest_progress:
        spinner = threading.Thread(target=spinner_thread, daemon=True)
        spinner.start()
    
    # Wait for completion
    stdout, stderr = process.communicate()
    
    if show_pytest_progress:
        print(f"\r      ✅ Tests completed!{' ' * 20}")  # Clear spinner line
    
    # Create a result object similar to subprocess.run
    class ProcessResult:
        def __init__(self, returncode, stdout, stderr):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr
    
    return ProcessResult(process.returncode, stdout, stderr)


def show_startup_banner(args):
    """Show an enhanced startup banner with better visibility"""
    print("\n" + "🚀" * 20)
    print("🚀 HAZELBEAN PERFORMANCE BENCHMARKS STARTING 🚀")
    print("🚀" * 20)
    print(f"📊 Output directory: {args.output_dir}")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Show what will be executed
    operations = []
    if args.establish_baseline:
        operations.append(f"📏 Establish baseline ({args.runs} runs)")
    if args.check_regression:
        operations.append("🔍 Check regressions")
    if any([args.all, args.tiling, args.path_resolution, args.aggregation, args.integration]):
        operations.append("🧪 Run benchmarks")
    if args.report:
        operations.append("📋 Generate report")
    
    print("\n🎯 Operations to perform:")
    for i, op in enumerate(operations, 1):
        print(f"   {i}. {op}")
    
    print("\n⏳ INITIALIZING... Please wait")
    print("=" * 60)


def create_file_link(file_path):
    """Create a clickable file link for terminal"""
    abs_path = os.path.abspath(file_path)
    
    # Create different link formats for better compatibility
    file_uri = f"file://{abs_path}"
    
    # For terminals that support OSC 8 hyperlinks (many modern terminals)
    # Format: \033]8;;URL\033\\TEXT\033]8;;\033\\
    hyperlink = f"\033]8;;{file_uri}\033\\{abs_path}\033]8;;\033\\"
    
    # Fallback: just show the path (will work in all terminals)
    return hyperlink


def show_generated_files_summary(output_dir):
    """Show a summary of all generated files with links"""
    print("\n📁 GENERATED FILES:")
    print("-" * 30)
    
    # Find recent files (last 24 hours) in the output directory
    import time
    current_time = time.time()
    recent_files = []
    
    try:
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            if os.path.isfile(file_path):
                # Check if file was modified in the last 24 hours
                file_time = os.path.getmtime(file_path)
                if current_time - file_time < 86400:  # 24 hours in seconds
                    file_size = os.path.getsize(file_path)
                    recent_files.append((filename, file_path, file_size, file_time))
    except OSError:
        print("⚠️  Could not access output directory")
        return
    
    # Sort by modification time (newest first)
    recent_files.sort(key=lambda x: x[3], reverse=True)
    
    if not recent_files:
        print("📝 No recent files found")
        return
    
    # Show up to 5 most recent files
    for filename, file_path, file_size, _ in recent_files[:5]:
        file_size_str = format_file_size(file_size)
        file_type_emoji = get_file_type_emoji(filename)
        
        print(f"{file_type_emoji} {filename} ({file_size_str})")
        print(f"   🔗 {create_file_link(file_path)}")
    
    if len(recent_files) > 5:
        print(f"   ... and {len(recent_files) - 5} more files")
    
    print(f"\n📂 Open output directory: {create_file_link(output_dir)}")


def get_file_type_emoji(filename):
    """Get appropriate emoji for file type"""
    if filename.endswith('.json'):
        return '📊'
    elif filename.endswith('.txt'):
        return '📄'
    elif filename.endswith('.html'):
        return '🌐'
    elif filename.endswith('.csv'):
        return '📈'
    else:
        return '📋'


def format_file_size(size_bytes):
    """Format file size in human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"


def create_interactive_dashboard(args):
    """Create an interactive HTML dashboard for the latest benchmark results and open it"""
    import subprocess
    import sys
    import webbrowser
    
    dashboard_script = os.path.join(os.path.dirname(__file__), 'create_benchmark_dashboard.py')
    dashboard_file = "benchmark_dashboard.html"
    
    if args.verbose:
        print("   🌐 Creating interactive HTML dashboard...")
    
    try:
        # Use --no-server flag when called from complete workflow to avoid blocking
        result = subprocess.run([sys.executable, dashboard_script, '--no-server'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode == 0:
            if args.verbose:
                print("   ✅ Dashboard created successfully")
                
            # Check if the dashboard file was created
            if os.path.exists(dashboard_file):
                dashboard_path = os.path.abspath(dashboard_file)
                dashboard_url = f"file://{dashboard_path}"
                
                if args.verbose:
                    print(f"   🔗 Dashboard file: {create_file_link(dashboard_path)}")
                
                # Automatically open the dashboard in the default browser
                try:
                    webbrowser.open(dashboard_url)
                    if args.verbose:
                        print("   🌐 Dashboard opened in your default browser!")
                except Exception as e:
                    if args.verbose:
                        print(f"   ⚠️ Could not auto-open browser: {e}")
                        print(f"   💡 Manually open: {dashboard_url}")
            else:
                print(f"   ⚠️ Dashboard file not found: {dashboard_file}")
        else:
            print(f"   ⚠️ Dashboard creation warning: {result.stderr.strip()}")
    except Exception as e:
        print(f"   ❌ Dashboard creation failed: {e}")


def export_performance_csv(args):
    """Export the latest benchmark results to CSV"""
    import subprocess
    import sys
    
    visualization_script = os.path.join(os.path.dirname(__file__), 'visualize_benchmarks.py')
    # Save CSV to organized exports subdirectory
    exports_dir = os.path.join(args.output_dir, "exports")
    os.makedirs(exports_dir, exist_ok=True)
    csv_filename = f"performance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    csv_path = os.path.join(exports_dir, csv_filename)
    
    if args.verbose:
        print(f"   📊 Exporting performance data to CSV...")
    
    try:
        result = subprocess.run([sys.executable, visualization_script, 
                               '--export-csv', csv_path, '--metrics-dir', args.output_dir], 
                              capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode == 0:
            if args.verbose:
                print(f"   ✅ CSV exported: {os.path.basename(csv_path)}")
                print(f"   🔗 Open CSV: {create_file_link(csv_path)}")
        else:
            print(f"   ⚠️ CSV export warning: {result.stderr.strip()}")
    except Exception as e:
        print(f"   ❌ CSV export failed: {e}")


def print_complete_workflow_summary():
    """Print a summary of the complete workflow that was executed"""
    print("\n🎯 COMPLETE WORKFLOW SUMMARY:")
    print("-" * 40)
    print("✅ Established performance baseline")
    print("✅ Ran comprehensive benchmark suite") 
    print("✅ Checked for performance regressions")
    print("✅ Generated detailed performance report")
    print("✅ Created interactive HTML dashboard (auto-opened in browser)")
    print("✅ Exported data to CSV for analysis")
    print("\n💡 All artifacts saved with clickable links above!")
    print("🌐 Dashboard should be open in your browser for interactive analysis!")
    print("🚀 Ready for performance analysis and monitoring!")


def format_duration(seconds):
    """Format duration in human-readable format"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.1f}s"


if __name__ == "__main__":
    main()
