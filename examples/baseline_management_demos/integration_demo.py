#!/usr/bin/env python3
"""
Benchmark Integration Testing Script

Shows how to integrate baseline management with existing benchmark infrastructure.
This script runs actual benchmarks and then establishes baselines from the results.
"""

import sys
import os
import subprocess
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.extend(['../..', '../../hazelbean_tests'])

# Import baseline manager from correct location  
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../hazelbean_tests'))
from performance.baseline_manager import BaselineManager

def run_simple_benchmarks():
    """Run simple benchmark tests and capture results"""
    print("🏃 Running Simple Benchmarks...")
    print("=" * 40)
    
    try:
        # Run specific benchmark tests  
        # Create benchmarks directory and save results there
        import os
        # Use absolute path from project root (since we cd to ../.. in subprocess)
        benchmark_file = 'metrics/benchmarks/temp_benchmark_results.json'
        
        # Create the directory structure from project root context
        subprocess.run(['mkdir', '-p', 'metrics/benchmarks'], 
                      capture_output=True, cwd='../..')
        
        result = subprocess.run([
            'python', '-m', 'pytest', 
            'hazelbean_tests/performance/benchmarks/test_simple_benchmarks.py',
            f'--benchmark-json={benchmark_file}',
            '-v'
        ], capture_output=True, text=True, cwd='../..')
        
        if result.returncode == 0:
            print("✅ Benchmarks completed successfully")
            
            # Check if benchmark file was created in benchmarks directory 
            full_benchmark_path = os.path.join('..', '..', benchmark_file)
            if os.path.exists(full_benchmark_path):
                print("✅ Benchmark results saved")
                return full_benchmark_path
            else:
                print("⚠️  No benchmark JSON file created")
                return None
        else:
            print("❌ Benchmark tests failed:")
            print(result.stderr)
            return None
            
    except FileNotFoundError:
        print("❌ Could not run pytest. Make sure it's installed.")
        return None
    except Exception as e:
        print(f"❌ Error running benchmarks: {e}")
        return None

def demonstrate_workflow_integration():
    """Demonstrate complete workflow integration"""
    print("🔄 COMPLETE WORKFLOW DEMONSTRATION")
    print("=" * 50)
    
    # Step 1: Run benchmarks
    print("\n📊 Step 1: Running Benchmarks")
    benchmark_file = run_simple_benchmarks()
    
    if not benchmark_file:
        print("❌ Cannot continue without benchmark results")
        return False
    
    # Step 2: Establish baseline
    print("\n🏗️  Step 2: Establishing Baseline")
    try:
        manager = BaselineManager('../..')
        
        with open(benchmark_file, 'r') as f:
            benchmark_data = json.load(f)
        
        baseline = manager.create_standardized_baseline_structure(benchmark_data)
        baseline_path = manager.save_baseline(baseline)
        
        print(f"✅ Baseline created: {baseline_path}")
        print(f"📊 Benchmarks processed: {baseline['validation_info']['total_benchmarks']}")
        
    except Exception as e:
        print(f"❌ Error creating baseline: {e}")
        return False
    
    # Step 3: Simulate running benchmarks again and compare
    print("\n⚖️  Step 3: Running Comparison")
    try:
        # In real scenario, this would be a new benchmark run
        # For demo, we'll slightly modify the data to simulate changes
        modified_data = benchmark_data.copy()
        
        # Simulate minor performance changes
        for benchmark in modified_data.get('benchmarks', []):
            stats = benchmark.get('stats', {})
            if 'mean' in stats:
                # Add small random variation (±2%)
                import random
                variation = random.uniform(0.98, 1.02)
                stats['mean'] *= variation
        
        comparison = manager.compare_with_baseline(modified_data)
        
        # Handle both 'status' and 'overall_status' keys for API compatibility
        status = comparison.get('overall_status', comparison.get('status', 'unknown'))
        print(f"📈 Comparison Status: {status}")
        
        if status == 'regression_detected':
            print("⚠️  Performance regressions detected:")
            for name, analysis in comparison.get('regression_analysis', {}).items():
                if analysis.get('is_regression'):
                    print(f"   🔻 {name}: {analysis['percent_change']:+.1f}%")
        else:
            print("✅ No performance regressions detected")
            
    except Exception as e:
        print(f"❌ Error in comparison: {e}")
        return False
    
    # Step 4: Generate report
    print("\n📋 Step 4: Generating Report")
    try:
        report = manager.generate_baseline_report(baseline)
        print("✅ Report generated")
        print("\n" + "="*50)
        print(report)
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        return False
    
    # Cleanup
    try:
        os.remove(benchmark_file)
        print(f"\n🧹 Cleaned up temporary file: {benchmark_file}")
    except:
        pass
    
    print("\n🎉 WORKFLOW DEMONSTRATION COMPLETE!")
    return True

def test_real_metrics_integration():
    """Test integration with real metrics directory"""
    print("🔗 REAL METRICS INTEGRATION TEST")
    print("=" * 50)
    
    # Get absolute path to metrics directory
    script_dir = Path(__file__).parent
    metrics_dir = script_dir / "../../metrics"
    metrics_dir = metrics_dir.resolve()  # Convert to absolute path
    if not metrics_dir.exists():
        print("❌ No metrics directory found")
        return False
    
    # Find existing benchmark files
    benchmark_files = list(metrics_dir.glob("benchmark_*.json"))
    baseline_files = list(metrics_dir.glob("baseline_run_*.json"))
    
    all_files = benchmark_files + baseline_files
    if not all_files:
        print("❌ No benchmark files found in metrics/")
        return False
    
    print(f"📁 Found {len(all_files)} benchmark files")
    
    # Use most recent file
    latest_file = max(all_files, key=lambda f: f.stat().st_mtime)
    print(f"📊 Using: {latest_file}")
    
    try:
        manager = BaselineManager("../../metrics")
        
        # Load and process real data
        with open(latest_file, 'r') as f:
            real_data = json.load(f)
        
        # Create baseline
        print("\n🏗️  Creating baseline from real data...")
        baseline = manager.create_standardized_baseline_structure(real_data)
        
        # Save using BaselineManager's method (creates both main and historical files)
        baseline_path = manager.save_baseline(baseline)
        
        # Also save with unique name for reference
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reference_file = metrics_dir / f"test_baseline_{timestamp}.json"
        with open(reference_file, 'w') as f:
            json.dump(baseline, f, indent=2)
        
        print(f"✅ Baseline saved for comparison: {Path(baseline_path).name}")
        print(f"📄 Reference copy saved: {reference_file.name}")
        
        # Display summary
        validation = baseline['validation_info']
        quality = baseline['quality_metrics']
        
        print(f"\n📊 BASELINE SUMMARY:")
        print(f"   Total benchmarks: {validation['total_benchmarks']}")
        print(f"   Valid benchmarks: {validation['valid_benchmarks']}")
        print(f"   Quality score: {quality['baseline_quality_score']:.1f}/100")
        
        # Show categories
        categories = baseline['benchmark_categories']
        print(f"\n📋 CATEGORIES:")
        for category, benchmarks in categories.items():
            if benchmarks:
                print(f"   {category.replace('_', ' ').title()}: {len(benchmarks)}")
        
        # Test comparison with itself (should pass)
        print(f"\n⚖️  Testing self-comparison...")
        comparison = manager.compare_with_baseline(real_data)
        status = comparison.get('overall_status', comparison.get('status', 'unknown'))
        print(f"   Status: {status} (should be 'passed')")
        
        if status == 'no_baseline':
            print("   ℹ️  This is expected on first run - baseline was just created")
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing real data: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_performance_test_suite():
    """Create a mini performance test suite for demonstration"""
    print("⚡ PERFORMANCE TEST SUITE")
    print("=" * 30)
    
    import time
    import statistics
    
    def simple_benchmark_function(n=1000):
        """Simple function to benchmark"""
        start = time.perf_counter()
        # Simple computation
        result = sum(i*i for i in range(n))
        end = time.perf_counter()
        return end - start, result
    
    # Run multiple iterations
    print("🏃 Running performance tests...")
    times = []
    
    for i in range(10):
        duration, _ = simple_benchmark_function(1000)
        times.append(duration)
        print(f"   Run {i+1}: {duration:.6f}s")
    
    # Create benchmark-like data structure
    benchmark_data = {
        "machine_info": {
            "system": "Test",
            "python_version": "3.13.2"
        },
        "benchmarks": [
            {
                "name": "simple_computation_benchmark",
                "stats": {
                    "min": min(times),
                    "max": max(times),
                    "mean": statistics.mean(times),
                    "stddev": statistics.stdev(times) if len(times) > 1 else 0,
                    "rounds": len(times),
                    "median": statistics.median(times)
                }
            }
        ]
    }
    
    print(f"\n📊 Performance Results:")
    stats = benchmark_data["benchmarks"][0]["stats"]
    print(f"   Mean: {stats['mean']:.6f}s")
    print(f"   Std Dev: {stats['stddev']:.6f}s")
    print(f"   Min/Max: {stats['min']:.6f}s / {stats['max']:.6f}s")
    
    # Test with baseline manager
    print(f"\n🏗️  Testing with baseline manager...")
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = BaselineManager(temp_dir)
        
        baseline = manager.create_standardized_baseline_structure(benchmark_data)
        baseline_path = manager.save_baseline(baseline)
        
        print(f"✅ Baseline created: {Path(baseline_path).name}")
        print(f"🎯 Quality score: {baseline['quality_metrics']['baseline_quality_score']:.1f}/100")
    
    return benchmark_data

def main():
    """Main function with menu"""
    print("🧪 HAZELBEAN BENCHMARK INTEGRATION TESTER")
    print("=" * 55)
    
    while True:
        print("\nSelect a test to run:")
        print("1. Complete Workflow Demonstration")
        print("2. Real Metrics Integration Test")
        print("3. Create Mini Performance Test Suite")
        print("4. Run All Tests")
        print("5. Exit")
        
        try:
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == "1":
                demonstrate_workflow_integration()
            elif choice == "2":
                test_real_metrics_integration()
            elif choice == "3":
                create_performance_test_suite()
            elif choice == "4":
                print("\n🏃 Running all tests...")
                demonstrate_workflow_integration()
                test_real_metrics_integration() 
                create_performance_test_suite()
                print("\n🎉 All tests completed!")
            elif choice == "5":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice")
                
            try:
                input("\nPress Enter to continue...")
            except EOFError:
                print("\n📝 Non-interactive mode detected. Continuing...")
                break
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except EOFError:
            print("\n📝 Non-interactive mode detected. Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            try:
                input("Press Enter to continue...")
            except EOFError:
                print("\n📝 Non-interactive mode detected. Continuing...")

if __name__ == "__main__":
    main()
