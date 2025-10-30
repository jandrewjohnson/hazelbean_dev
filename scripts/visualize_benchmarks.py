#!/usr/bin/env python3
"""
Benchmark Visualization Tool for Hazelbean Performance Data

This script provides multiple ways to visualize and analyze pytest-benchmark JSON files
in a more human-friendly format.

Usage:
    python scripts/visualize_benchmarks.py [JSON_FILE] [OPTIONS]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add hazelbean to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def main():
    """Main entry point for benchmark visualization"""
    parser = argparse.ArgumentParser(
        description="Visualize pytest-benchmark JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('json_file', nargs='?', 
                       help='Path to benchmark JSON file (or latest if not specified)')
    parser.add_argument('--summary', '-s', action='store_true',
                       help='Show summary information only')
    parser.add_argument('--detailed', '-d', action='store_true',
                       help='Show detailed benchmark results')
    parser.add_argument('--system-info', action='store_true',
                       help='Show system and environment information')
    parser.add_argument('--export-csv', metavar='CSV_FILE',
                       help='Export benchmark data to CSV file')
    parser.add_argument('--compare', metavar='JSON_FILE2',
                       help='Compare with another benchmark file')
    parser.add_argument('--metrics-dir', default='./metrics',
                       help='Directory containing benchmark files (default: ./metrics)')
    
    args = parser.parse_args()
    
    # Find the JSON file to analyze
    if not args.json_file:
        json_file = find_latest_benchmark_file(args.metrics_dir)
        if not json_file:
            print("❌ No benchmark files found in metrics directory")
            return
        print(f"📊 Using latest benchmark file: {os.path.basename(json_file)}")
    else:
        json_file = args.json_file
    
    if not os.path.exists(json_file):
        print(f"❌ File not found: {json_file}")
        return
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading JSON file: {e}")
        return
    
    print("\n" + "=" * 80)
    print("BENCHMARK ANALYSIS REPORT")
    print("=" * 80)
    print(f"📁 File: {os.path.basename(json_file)}")
    print(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Show different views based on arguments
    if args.system_info:
        show_system_info(data)
    
    if args.summary or (not args.detailed and not args.system_info):
        show_benchmark_summary(data)
    
    if args.detailed:
        show_detailed_benchmarks(data)
    
    if args.export_csv:
        export_to_csv(data, args.export_csv)
        print(f"\n✅ Data exported to: {args.export_csv}")
    
    if args.compare:
        compare_benchmarks(data, args.compare)


def find_latest_benchmark_file(metrics_dir):
    """Find the most recent benchmark JSON file"""
    if not os.path.exists(metrics_dir):
        return None
    
    # Look for benchmark files in organized benchmarks subdirectory
    benchmarks_dir = os.path.join(metrics_dir, 'benchmarks')
    benchmark_files = []
    
    if os.path.exists(benchmarks_dir):
        for filename in os.listdir(benchmarks_dir):
            if filename.startswith('benchmark_') and filename.endswith('.json'):
                filepath = os.path.join(benchmarks_dir, filename)
                if os.path.getsize(filepath) > 0:  # Only non-empty files
                    benchmark_files.append((filepath, os.path.getmtime(filepath)))
    
    if not benchmark_files:
        return None
    
    # Return the most recent file
    return max(benchmark_files, key=lambda x: x[1])[0]


def show_system_info(data):
    """Display system and environment information"""
    print("\n🖥️  SYSTEM INFORMATION:")
    print("-" * 40)
    
    if 'machine_info' in data:
        machine = data['machine_info']
        print(f"💻 Machine: {machine.get('node', 'Unknown')}")
        print(f"🔧 Processor: {machine.get('processor', 'Unknown')} ({machine.get('machine', 'Unknown')})")
        print(f"🐍 Python: {machine.get('python_version', 'Unknown')}")
        print(f"⚙️  Implementation: {machine.get('python_implementation', 'Unknown')}")
        
        if 'cpu' in machine:
            cpu = machine['cpu']
            print(f"🔥 CPU: {cpu.get('brand_raw', 'Unknown')}")
            print(f"⚡ Cores: {cpu.get('count', 'Unknown')}")
            print(f"📐 Architecture: {cpu.get('arch_string_raw', 'Unknown')} ({cpu.get('bits', 'Unknown')}-bit)")
    
    if 'commit_info' in data:
        commit = data['commit_info']
        print(f"\n📝 Git Info:")
        print(f"   Branch: {commit.get('branch', 'Unknown')}")
        print(f"   Commit: {commit.get('id', 'Unknown')[:8]}...")
        print(f"   Time: {commit.get('time', 'Unknown')}")
        print(f"   Dirty: {'Yes' if commit.get('dirty') else 'No'}")


def show_benchmark_summary(data):
    """Display a summary of benchmark results"""
    print("\n📊 BENCHMARK SUMMARY:")
    print("-" * 40)
    
    if 'benchmarks' not in data:
        print("❌ No benchmark data found")
        return
    
    benchmarks = data['benchmarks']
    print(f"🧪 Total benchmarks: {len(benchmarks)}")
    
    # Group benchmarks by name for summary
    by_name = {}
    for bench in benchmarks:
        name = bench.get('name', 'unknown')
        if name not in by_name:
            by_name[name] = []
        by_name[name].append(bench)
    
    print(f"🔢 Unique test functions: {len(by_name)}")
    print()
    
    # Show summary statistics for each benchmark
    for name, bench_list in by_name.items():
        print(f"📋 {name}:")
        
        if bench_list and 'stats' in bench_list[0]:
            stats = bench_list[0]['stats']
            mean_time = stats.get('mean', 0)
            min_time = stats.get('min', 0)
            max_time = stats.get('max', 0)
            rounds = stats.get('rounds', 0)
            
            print(f"   ⏱️  Mean: {format_time(mean_time)}")
            print(f"   ⚡ Min: {format_time(min_time)}")
            print(f"   🐌 Max: {format_time(max_time)}")
            print(f"   🔄 Rounds: {rounds}")
            
            # Performance classification
            if mean_time < 0.001:
                performance = "🚀 Excellent"
            elif mean_time < 0.01:
                performance = "✅ Good"
            elif mean_time < 0.1:
                performance = "⚠️  Moderate"
            else:
                performance = "🐌 Slow"
            
            print(f"   📈 Performance: {performance}")
        print()


def show_detailed_benchmarks(data):
    """Display detailed benchmark information"""
    print("\n🔍 DETAILED BENCHMARK RESULTS:")
    print("-" * 50)
    
    if 'benchmarks' not in data:
        print("❌ No benchmark data found")
        return
    
    for i, bench in enumerate(data['benchmarks'], 1):
        print(f"\n📊 Benchmark #{i}: {bench.get('name', 'Unknown')}")
        print(f"📁 Full name: {bench.get('fullname', 'Unknown')}")
        
        if 'stats' in bench:
            stats = bench['stats']
            print(f"⏱️  Statistics:")
            print(f"   Mean: {format_time(stats.get('mean', 0))}")
            print(f"   Median: {format_time(stats.get('median', 0))}")
            print(f"   Standard deviation: {format_time(stats.get('stddev', 0))}")
            print(f"   Min: {format_time(stats.get('min', 0))}")
            print(f"   Max: {format_time(stats.get('max', 0))}")
            print(f"   IQR: {format_time(stats.get('iqr', 0))}")
            print(f"   Rounds: {stats.get('rounds', 0)}")
            print(f"   Iterations: {stats.get('iterations', 0)}")
        
        if 'options' in bench:
            options = bench['options']
            print(f"🔧 Options:")
            print(f"   Timer: {options.get('timer', 'Unknown')}")
            print(f"   Min rounds: {options.get('min_rounds', 'Unknown')}")
            print(f"   Min time: {options.get('min_time', 'Unknown')}")
            print(f"   Max time: {options.get('max_time', 'Unknown')}")


def export_to_csv(data, csv_file):
    """Export benchmark data to CSV format"""
    import csv
    
    if 'benchmarks' not in data:
        print("❌ No benchmark data to export")
        return
    
    fieldnames = [
        'name', 'fullname', 'mean_time', 'median_time', 'min_time', 'max_time',
        'stddev_time', 'rounds', 'iterations', 'timer'
    ]
    
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for bench in data['benchmarks']:
            stats = bench.get('stats', {})
            options = bench.get('options', {})
            
            row = {
                'name': bench.get('name', ''),
                'fullname': bench.get('fullname', ''),
                'mean_time': stats.get('mean', 0),
                'median_time': stats.get('median', 0),
                'min_time': stats.get('min', 0),
                'max_time': stats.get('max', 0),
                'stddev_time': stats.get('stddev', 0),
                'rounds': stats.get('rounds', 0),
                'iterations': stats.get('iterations', 0),
                'timer': options.get('timer', '')
            }
            writer.writerow(row)


def compare_benchmarks(data1, file2):
    """Compare two benchmark files"""
    print(f"\n🔄 COMPARING WITH: {os.path.basename(file2)}")
    print("-" * 50)
    
    try:
        with open(file2, 'r') as f:
            data2 = json.load(f)
    except Exception as e:
        print(f"❌ Error loading comparison file: {e}")
        return
    
    if 'benchmarks' not in data1 or 'benchmarks' not in data2:
        print("❌ Missing benchmark data in one or both files")
        return
    
    # Create lookup for benchmarks by name
    benchmarks1 = {b['name']: b for b in data1['benchmarks']}
    benchmarks2 = {b['name']: b for b in data2['benchmarks']}
    
    common_names = set(benchmarks1.keys()) & set(benchmarks2.keys())
    
    if not common_names:
        print("❌ No common benchmarks found between files")
        return
    
    print(f"📊 Comparing {len(common_names)} common benchmarks:")
    print()
    
    for name in sorted(common_names):
        b1 = benchmarks1[name]
        b2 = benchmarks2[name]
        
        if 'stats' in b1 and 'stats' in b2:
            mean1 = b1['stats'].get('mean', 0)
            mean2 = b2['stats'].get('mean', 0)
            
            if mean1 > 0:
                change_pct = ((mean2 - mean1) / mean1) * 100
                if abs(change_pct) < 5:
                    status = "📊 Similar"
                elif change_pct > 0:
                    status = f"🐌 Slower ({change_pct:+.1f}%)"
                else:
                    status = f"⚡ Faster ({change_pct:+.1f}%)"
                
                print(f"📋 {name}:")
                print(f"   File 1: {format_time(mean1)}")
                print(f"   File 2: {format_time(mean2)}")
                print(f"   Change: {status}")
                print()


def format_time(seconds):
    """Format time in human-readable format"""
    if seconds < 0.000001:  # Less than 1 microsecond
        return f"{seconds * 1000000000:.1f}ns"
    elif seconds < 0.001:   # Less than 1 millisecond
        return f"{seconds * 1000000:.1f}μs"
    elif seconds < 1:       # Less than 1 second
        return f"{seconds * 1000:.1f}ms"
    else:                   # 1 second or more
        return f"{seconds:.3f}s"


if __name__ == "__main__":
    main()
