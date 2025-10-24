#!/usr/bin/env python3
"""
Establish Performance Baseline Script

This script integrates the baseline manager with existing benchmark infrastructure
to establish comprehensive performance baselines for Hazelbean.

Story 6: Baseline Establishment - Task 6.4 Integration
"""

import sys
import os
import json
import argparse
from pathlib import Path

# Add hazelbean and tests to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.extend([str(project_root), str(project_root / 'hazelbean_tests')])

from performance.baseline_manager import BaselineManager

def find_latest_benchmark_file(metrics_dir: str) -> str:
    """Find the most recent benchmark JSON file"""
    metrics_path = Path(metrics_dir)
    
    # Look for recent benchmark files in organized directory structure
    benchmarks_dir = metrics_path / "benchmarks"
    benchmark_files = list(benchmarks_dir.glob("benchmark_*.json")) if benchmarks_dir.exists() else []
    baseline_files = list(benchmarks_dir.glob("baseline_run_*.json")) if benchmarks_dir.exists() else []
    
    # Combine and sort by modification time
    all_files = benchmark_files + baseline_files
    
    if not all_files:
        raise FileNotFoundError(f"No benchmark files found in {metrics_dir}")
    
    # Return most recent file
    latest_file = max(all_files, key=lambda f: f.stat().st_mtime)
    return str(latest_file)

def establish_baseline(metrics_dir: str = None, benchmark_file: str = None, 
                      output_report: bool = True) -> str:
    """
    Establish performance baseline from existing benchmark data
    
    Args:
        metrics_dir: Directory containing metrics and benchmark files
        benchmark_file: Specific benchmark file to use (optional)
        output_report: Whether to output human-readable report
        
    Returns:
        Path to created baseline file
    """
    print("🔧 Establishing Hazelbean Performance Baseline...")
    print("=" * 50)
    
    # Initialize baseline manager
    if metrics_dir is None:
        # Default to project metrics directory
        script_dir = Path(__file__).parent
        metrics_dir = script_dir.parent / "metrics"
    
    manager = BaselineManager(str(metrics_dir))
    
    # Load benchmark data
    if benchmark_file is None:
        print("📁 Searching for latest benchmark file...")
        benchmark_file = find_latest_benchmark_file(str(metrics_dir))
        print(f"   Found: {benchmark_file}")
    
    print(f"📊 Loading benchmark data from: {benchmark_file}")
    
    with open(benchmark_file, 'r') as f:
        benchmark_data = json.load(f)
    
    # Create standardized baseline structure
    print("🏗️  Creating standardized baseline structure...")
    baseline_structure = manager.create_standardized_baseline_structure(benchmark_data)
    
    # Save baseline with version control integration  
    print("💾 Saving baseline with version control integration...")
    baseline_path = manager.save_baseline(baseline_structure)
    
    # Output summary information
    validation_info = baseline_structure["validation_info"]
    print(f"✅ Baseline established successfully!")
    print(f"   📄 Baseline file: {baseline_path}")
    print(f"   📊 Total benchmarks: {validation_info['total_benchmarks']}")
    print(f"   ✅ Valid benchmarks: {validation_info['valid_benchmarks']}")
    
    # Output quality metrics
    quality_score = baseline_structure["quality_metrics"]["baseline_quality_score"]
    print(f"   🎯 Quality score: {quality_score:.1f}/100")
    
    # Generate and display report if requested
    if output_report:
        print("\n📋 BASELINE ESTABLISHMENT REPORT")
        print("=" * 50)
        report = manager.generate_baseline_report(baseline_structure)
        print(report)
    
    return baseline_path

def compare_with_baseline(metrics_dir: str = None, current_file: str = None) -> dict:
    """
    Compare current benchmark results with established baseline
    
    Args:
        metrics_dir: Directory containing metrics and baseline files
        current_file: Current benchmark file to compare
        
    Returns:
        Comparison results dictionary
    """
    print("\n🔍 Comparing with Established Baseline...")
    print("=" * 40)
    
    # Initialize baseline manager
    if metrics_dir is None:
        script_dir = Path(__file__).parent
        metrics_dir = script_dir.parent / "metrics"
    
    manager = BaselineManager(str(metrics_dir))
    
    # Load current benchmark data
    if current_file is None:
        current_file = find_latest_benchmark_file(str(metrics_dir))
    
    print(f"📊 Loading current data from: {current_file}")
    
    with open(current_file, 'r') as f:
        current_data = json.load(f)
    
    # Perform comparison
    print("⚖️  Performing baseline comparison...")
    comparison_results = manager.compare_with_baseline(current_data)
    
    # Display results
    status = comparison_results["overall_status"]
    print(f"📈 Comparison Status: {status.upper()}")
    
    if status == "regression_detected":
        print("⚠️  PERFORMANCE REGRESSIONS DETECTED:")
        for benchmark_name, analysis in comparison_results["regression_analysis"].items():
            if analysis["is_regression"]:
                percent_change = analysis["percent_change"]
                severity = analysis["severity"]
                print(f"   🔻 {benchmark_name}: {percent_change:+.1f}% ({severity})")
                
        # Display recommendations
        recommendations = comparison_results.get("recommendations", [])
        if recommendations:
            print("\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
    else:
        print("✅ No performance regressions detected")
    
    return comparison_results

def analyze_performance_trends(metrics_dir: str = None, lookback_days: int = 30) -> dict:
    """
    Analyze performance trends over time
    
    Args:
        metrics_dir: Directory containing historical baseline files
        lookback_days: Number of days to analyze
        
    Returns:
        Trend analysis results
    """
    print(f"\n📈 Analyzing Performance Trends (last {lookback_days} days)...")
    print("=" * 50)
    
    # Initialize baseline manager
    if metrics_dir is None:
        script_dir = Path(__file__).parent
        metrics_dir = script_dir.parent / "metrics"
    
    manager = BaselineManager(str(metrics_dir))
    
    # Perform trend analysis
    print("📊 Analyzing historical baseline data...")
    trend_results = manager.analyze_trends(lookback_days)
    
    if trend_results.get("status") == "insufficient_data":
        print("⚠️  Insufficient historical data for trend analysis")
        print(f"   {trend_results.get('message', 'Unknown error')}")
        return trend_results
    
    # Display trend summary
    trajectory = trend_results.get("performance_trajectory", {})
    overall_trend = trajectory.get("overall_trend", "unknown")
    change_percent = trajectory.get("overall_change_percent", 0)
    health = trajectory.get("performance_health", "unknown")
    
    print(f"📈 Overall Trend: {overall_trend.upper()}")
    print(f"📊 Performance Change: {change_percent:+.1f}%")
    print(f"🏥 Performance Health: {health.upper()}")
    
    # Display benchmark trend categories
    summary = trend_results.get("trend_summary", {})
    print(f"\n📋 Benchmark Trend Summary:")
    print(f"   📈 Improving: {len(summary.get('improving_benchmarks', []))}")
    print(f"   📉 Degrading: {len(summary.get('degrading_benchmarks', []))}")
    print(f"   📊 Stable: {len(summary.get('stable_benchmarks', []))}")
    print(f"   ⚠️  Anomalous: {len(summary.get('anomalous_benchmarks', []))}")
    
    # Show specific degrading benchmarks if any
    degrading = summary.get('degrading_benchmarks', [])
    if degrading:
        print(f"\n🔻 Degrading Benchmarks:")
        for benchmark in degrading[:5]:  # Show first 5
            print(f"   - {benchmark}")
        if len(degrading) > 5:
            print(f"   ... and {len(degrading) - 5} more")
    
    return trend_results

def create_baseline_integration_demo():
    """Demonstrate complete baseline management workflow"""
    print("🚀 HAZELBEAN BASELINE MANAGEMENT DEMONSTRATION")
    print("=" * 55)
    print("This demo shows the complete baseline establishment workflow")
    print()
    
    try:
        # Step 1: Establish baseline
        baseline_path = establish_baseline()
        
        # Step 2: Compare with baseline (using same data for demo)
        comparison_results = compare_with_baseline()
        
        # Step 3: Analyze trends
        trend_results = analyze_performance_trends()
        
        print("\n🎉 DEMONSTRATION COMPLETE!")
        print("=" * 30)
        print("✅ Baseline established with version control integration")
        print("✅ Comparison logic validated")
        print("✅ Trend analysis capabilities demonstrated")
        print("✅ All components working together successfully")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main CLI interface for baseline establishment"""
    parser = argparse.ArgumentParser(
        description="Establish and manage Hazelbean performance baselines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Establish baseline from latest benchmark data
  python establish_performance_baseline.py --establish
  
  # Compare current results with baseline
  python establish_performance_baseline.py --compare
  
  # Analyze performance trends
  python establish_performance_baseline.py --trends
  
  # Run complete demonstration
  python establish_performance_baseline.py --demo
  
  # Establish baseline from specific file
  python establish_performance_baseline.py --establish --benchmark-file /path/to/benchmark.json
        """
    )
    
    parser.add_argument("--establish", action="store_true", 
                       help="Establish new performance baseline")
    parser.add_argument("--compare", action="store_true",
                       help="Compare current results with baseline")
    parser.add_argument("--trends", action="store_true",
                       help="Analyze performance trends")
    parser.add_argument("--demo", action="store_true",
                       help="Run complete baseline management demonstration")
    
    parser.add_argument("--metrics-dir", type=str,
                       help="Metrics directory path (default: ../metrics)")
    parser.add_argument("--benchmark-file", type=str,
                       help="Specific benchmark file to use")
    parser.add_argument("--lookback-days", type=int, default=30,
                       help="Days to analyze for trends (default: 30)")
    parser.add_argument("--no-report", action="store_true",
                       help="Skip generating human-readable report")
    
    args = parser.parse_args()
    
    # Default to demo if no specific action specified
    if not any([args.establish, args.compare, args.trends, args.demo]):
        args.demo = True
    
    try:
        if args.demo:
            success = create_baseline_integration_demo()
            return 0 if success else 1
            
        if args.establish:
            establish_baseline(
                metrics_dir=args.metrics_dir,
                benchmark_file=args.benchmark_file,
                output_report=not args.no_report
            )
            
        if args.compare:
            compare_with_baseline(
                metrics_dir=args.metrics_dir,
                current_file=args.benchmark_file
            )
            
        if args.trends:
            analyze_performance_trends(
                metrics_dir=args.metrics_dir,
                lookback_days=args.lookback_days
            )
            
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
