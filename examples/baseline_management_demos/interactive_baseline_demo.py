#!/usr/bin/env python3
"""
Interactive Baseline Management Testing Script

This script provides an interactive way to test all baseline management
functionality with sample data and real benchmark files.
"""

import sys
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Add paths
sys.path.extend(['../..', '../../hazelbean_tests'])
from performance.baseline_manager import BaselineManager

def create_sample_benchmark_data():
    """Create sample benchmark data for testing"""
    return {
        "machine_info": {
            "node": "test-machine",
            "processor": "arm",
            "machine": "arm64", 
            "python_version": "3.13.2",
            "system": "Darwin",
            "cpu": {"arch": "ARM_8", "count": 8, "brand_raw": "Test CPU"}
        },
        "commit_info": {
            "id": "sample_commit_12345",
            "time": datetime.now().isoformat(),
            "dirty": False,
            "branch": "test_branch"
        },
        "benchmarks": [
            {
                "name": "test_get_path_benchmark",
                "stats": {"min": 0.01, "max": 0.02, "mean": 0.015, "stddev": 0.002, "rounds": 50}
            },
            {
                "name": "test_tiling_benchmark",
                "stats": {"min": 0.05, "max": 0.08, "mean": 0.065, "stddev": 0.005, "rounds": 30}
            },
            {
                "name": "test_array_operations_benchmark",
                "stats": {"min": 0.001, "max": 0.003, "mean": 0.002, "stddev": 0.0003, "rounds": 100}
            }
        ]
    }

def test_baseline_creation():
    """Test 1: Baseline Creation with Sample Data"""
    print("🧪 TEST 1: Baseline Creation")
    print("=" * 40)
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = BaselineManager(temp_dir)
        sample_data = create_sample_benchmark_data()
        
        print("📊 Creating baseline structure...")
        baseline = manager.create_standardized_baseline_structure(sample_data)
        
        print("💾 Saving baseline...")
        baseline_path = manager.save_baseline(baseline)
        
        print("📋 Generating report...")
        report = manager.generate_baseline_report(baseline)
        
        print(f"✅ Baseline created: {baseline_path}")
        print(f"📊 Total benchmarks: {baseline['validation_info']['total_benchmarks']}")
        print(f"🎯 Quality score: {baseline['quality_metrics']['baseline_quality_score']:.1f}/100")
        
        print("\n📋 BASELINE REPORT:")
        print("-" * 20)
        print(report[:500] + "..." if len(report) > 500 else report)
        
        return baseline_path

def test_regression_detection():
    """Test 2: Regression Detection"""
    print("\n🧪 TEST 2: Regression Detection")
    print("=" * 40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = BaselineManager(temp_dir)
        
        # Create and save baseline
        baseline_data = create_sample_benchmark_data()
        baseline = manager.create_standardized_baseline_structure(baseline_data)
        manager.save_baseline(baseline)
        
        print("✅ Baseline established")
        
        # Test 1: No regression (5% improvement)
        print("\n🔍 Testing: 5% improvement (should PASS)")
        better_data = create_sample_benchmark_data()
        for bench in better_data["benchmarks"]:
            bench["stats"]["mean"] *= 0.95  # 5% faster
        
        comparison = manager.compare_with_baseline(better_data)
        print(f"📈 Result: {comparison['overall_status']}")
        
        # Test 2: Minor regression (15% slower)
        print("\n🔍 Testing: 15% degradation (should detect REGRESSION)")
        worse_data = create_sample_benchmark_data()
        for bench in worse_data["benchmarks"]:
            bench["stats"]["mean"] *= 1.15  # 15% slower
            
        comparison = manager.compare_with_baseline(worse_data)
        print(f"📈 Result: {comparison['overall_status']}")
        
        if comparison["overall_status"] == "regression_detected":
            print("⚠️  Detected regressions:")
            for name, analysis in comparison["regression_analysis"].items():
                if analysis["is_regression"]:
                    print(f"   🔻 {name}: {analysis['percent_change']:+.1f}% ({analysis['severity']})")
        
        return comparison

def test_trend_analysis():
    """Test 3: Trend Analysis with Historical Data"""
    print("\n🧪 TEST 3: Trend Analysis")
    print("=" * 40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = BaselineManager(temp_dir)
        
        # Create multiple historical baselines with gradual degradation
        print("📊 Creating historical baseline data...")
        for i in range(5):
            historical_data = create_sample_benchmark_data()
            
            # Simulate gradual performance degradation
            degradation = 1.0 + (i * 0.03)  # 3% degradation per iteration
            for bench in historical_data["benchmarks"]:
                bench["stats"]["mean"] *= degradation
            
            # Create baseline with timestamp
            baseline = manager.create_standardized_baseline_structure(historical_data)
            timestamp = (datetime.now() - timedelta(days=4-i))
            baseline["baseline_metadata"]["created_at"] = timestamp.isoformat()
            
            # Save to historical directory
            filename = f"baseline_{timestamp.strftime('%Y%m%d_%H%M%S')}_hist{i:02d}.json"
            filepath = manager.historical_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(baseline, f)
            
            print(f"   📅 Created historical baseline {i+1}/5")
        
        # Analyze trends
        print("\n📈 Analyzing trends...")
        trends = manager.analyze_trends()
        
        if trends.get("status") != "insufficient_data":
            trajectory = trends.get("performance_trajectory", {})
            summary = trends.get("trend_summary", {})
            
            print(f"📊 Overall Trend: {trajectory.get('overall_trend', 'unknown').upper()}")
            print(f"📈 Performance Change: {trajectory.get('overall_change_percent', 0):+.1f}%")
            print(f"🏥 Performance Health: {trajectory.get('performance_health', 'unknown').upper()}")
            
            print(f"\n📋 Benchmark Categories:")
            print(f"   📈 Improving: {len(summary.get('improving_benchmarks', []))}")
            print(f"   📉 Degrading: {len(summary.get('degrading_benchmarks', []))}")
            print(f"   📊 Stable: {len(summary.get('stable_benchmarks', []))}")
        else:
            print(f"⚠️  {trends.get('message', 'Insufficient data')}")
        
        return trends

def test_with_real_benchmark_files():
    """Test 4: Test with Real Benchmark Files from metrics/"""
    print("\n🧪 TEST 4: Real Benchmark Files")
    print("=" * 40)
    
    metrics_dir = Path("../../metrics")
    if not metrics_dir.exists():
        print("❌ No metrics/ directory found. Run some benchmarks first.")
        return None
    
    # Find benchmark files
    benchmark_files = list(metrics_dir.glob("benchmark_*.json")) + list(metrics_dir.glob("baseline_run_*.json"))
    
    if not benchmark_files:
        print("❌ No benchmark files found in metrics/")
        return None
    
    latest_file = max(benchmark_files, key=lambda f: f.stat().st_mtime)
    print(f"📁 Using file: {latest_file}")
    
    manager = BaselineManager("../../metrics")
    
    try:
        # Load real benchmark data
        with open(latest_file, 'r') as f:
            real_data = json.load(f)
        
        print("📊 Creating baseline from real data...")
        baseline = manager.create_standardized_baseline_structure(real_data)
        
        print(f"✅ Successfully processed {baseline['validation_info']['total_benchmarks']} benchmarks")
        print(f"✅ Valid benchmarks: {baseline['validation_info']['valid_benchmarks']}")
        print(f"🎯 Quality score: {baseline['quality_metrics']['baseline_quality_score']:.1f}/100")
        
        # Show benchmark categories
        categories = baseline["benchmark_categories"]
        print("\n📋 Benchmark Categories:")
        for category, benchmarks in categories.items():
            if benchmarks:
                print(f"   {category.replace('_', ' ').title()}: {len(benchmarks)}")
        
        return baseline
        
    except Exception as e:
        print(f"❌ Error processing real data: {e}")
        return None

def test_error_handling():
    """Test 5: Error Handling and Edge Cases"""
    print("\n🧪 TEST 5: Error Handling")
    print("=" * 40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = BaselineManager(temp_dir)
        
        # Test 1: Empty data
        print("🔍 Testing empty benchmark data...")
        empty_data = {"benchmarks": []}
        try:
            baseline = manager.create_standardized_baseline_structure(empty_data)
            print(f"✅ Handled empty data: {baseline['baseline_statistics'].get('error', 'no error')}")
        except Exception as e:
            print(f"❌ Failed on empty data: {e}")
        
        # Test 2: Invalid data
        print("\n🔍 Testing invalid benchmark data...")
        invalid_data = {
            "benchmarks": [
                {"name": "invalid", "stats": {"mean": "not_a_number"}},
                {"name": "valid", "stats": {"mean": 0.05, "rounds": 10}}
            ]
        }
        try:
            baseline = manager.create_standardized_baseline_structure(invalid_data)
            validation = baseline['validation_info']
            print(f"✅ Handled mixed data: {validation['valid_benchmarks']}/{validation['total_benchmarks']} valid")
        except Exception as e:
            print(f"❌ Failed on invalid data: {e}")
        
        # Test 3: Comparison with no baseline
        print("\n🔍 Testing comparison without baseline...")
        try:
            sample_data = create_sample_benchmark_data()
            result = manager.compare_with_baseline(sample_data)
            print(f"✅ Handled missing baseline: {result.get('status', 'unknown')}")
        except Exception as e:
            print(f"❌ Failed on missing baseline: {e}")

def interactive_menu():
    """Interactive menu for testing"""
    while True:
        print("\n🚀 HAZELBEAN BASELINE TESTING MENU")
        print("=" * 40)
        print("1. Test Baseline Creation")
        print("2. Test Regression Detection") 
        print("3. Test Trend Analysis")
        print("4. Test with Real Benchmark Files")
        print("5. Test Error Handling")
        print("6. Run All Tests")
        print("7. Exit")
        
        try:
            choice = input("\nEnter your choice (1-7): ").strip()
            
            if choice == "1":
                test_baseline_creation()
            elif choice == "2":
                test_regression_detection()
            elif choice == "3":
                test_trend_analysis()
            elif choice == "4":
                test_with_real_benchmark_files()
            elif choice == "5":
                test_error_handling()
            elif choice == "6":
                print("\n🏃 Running All Tests...")
                test_baseline_creation()
                test_regression_detection()
                test_trend_analysis()
                test_with_real_benchmark_files()
                test_error_handling()
                print("\n🎉 All Tests Completed!")
            elif choice == "7":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please enter 1-7.")
                
            input("\nPress Enter to continue...")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            input("Press Enter to continue...")

if __name__ == "__main__":
    print("🧪 HAZELBEAN BASELINE MANAGEMENT TESTER")
    print("=" * 50)
    print("This script tests all baseline management functionality")
    print("with both sample data and real benchmark files.")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        print("\n🏃 Running all tests automatically...")
        test_baseline_creation()
        test_regression_detection()
        test_trend_analysis()
        test_with_real_benchmark_files()
        test_error_handling()
        print("\n🎉 All tests completed!")
    else:
        interactive_menu()
