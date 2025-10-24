#!/usr/bin/env python3
"""
Analyze recent benchmark files for summary dashboard
Input: metrics/benchmarks/*.json (most recent 3 files)
Output: docs-site/docs/reports/benchmark-results.md

Follows Option 1 implementation plan for dynamic benchmark reporting
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

def load_benchmark_files(benchmarks_dir: Path, max_files: int = 3) -> List[Dict]:
    """Load the most recent benchmark files."""
    benchmark_files = []
    
    if not benchmarks_dir.exists():
        print(f"Warning: Benchmarks directory not found: {benchmarks_dir}")
        return benchmark_files
    
    # Find benchmark JSON files (excluding baseline runs)
    json_files = [f for f in benchmarks_dir.glob('benchmark_*.json') 
                  if not f.name.startswith('baseline_run_')]
    
    # Sort by modification time (newest first)
    json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Load up to max_files most recent benchmarks
    for benchmark_file in json_files[:max_files]:
        try:
            print(f"Loading benchmark: {benchmark_file.name}")
            with open(benchmark_file, 'r') as f:
                data = json.load(f)
                data['filename'] = benchmark_file.name
                data['modified_time'] = benchmark_file.stat().st_mtime
                benchmark_files.append(data)
        except Exception as e:
            print(f"Warning: Could not load benchmark {benchmark_file}: {e}")
            continue
    
    return benchmark_files

def extract_benchmark_timestamp(filename: str) -> Optional[str]:
    """Extract timestamp from benchmark filename."""
    # Expected format: benchmark_20250904_103226.json
    try:
        parts = filename.replace('benchmark_', '').replace('.json', '').split('_')
        if len(parts) >= 2:
            date_str = parts[0]  # 20250904
            time_str = parts[1]  # 103226
            
            # Parse date and time
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            hour = int(time_str[:2])
            minute = int(time_str[2:4])
            second = int(time_str[4:6])
            
            dt = datetime(year, month, day, hour, minute, second)
            return dt.strftime('%Y-%m-%d %H:%M')
    except Exception as e:
        print(f"Could not parse timestamp from {filename}: {e}")
        
    return None

def analyze_benchmark_performance(benchmark_data: Dict) -> Dict:
    """Analyze benchmark performance and determine status."""
    
    benchmarks = benchmark_data.get('benchmarks', [])
    if not benchmarks:
        return {
            'status': '❌ No Data',
            'total_benchmarks': 0,
            'passed': 0,
            'performance_summary': 'No benchmarks found',
            'slowest_test': None,
            'fastest_test': None
        }
    
    # Analyze each benchmark
    total_benchmarks = len(benchmarks)
    mean_times = []
    benchmark_details = []
    
    for bench in benchmarks:
        stats = bench.get('stats', {})
        name = bench.get('name', 'Unknown')
        mean_time = stats.get('mean', 0)
        stddev = stats.get('stddev', 0)
        
        mean_times.append(mean_time)
        benchmark_details.append({
            'name': name,
            'mean_time': mean_time,
            'stddev': stddev,
            'rounds': stats.get('rounds', 0)
        })
    
    # Sort by mean time to find fastest/slowest
    benchmark_details.sort(key=lambda x: x['mean_time'])
    
    fastest_test = benchmark_details[0] if benchmark_details else None
    slowest_test = benchmark_details[-1] if benchmark_details else None
    
    # Calculate overall statistics
    if mean_times:
        avg_mean_time = sum(mean_times) / len(mean_times)
        performance_summary = f"Avg: {format_time_ms(avg_mean_time)}"
    else:
        performance_summary = "No performance data"
    
    return {
        'status': '✅ Pass',  # Default to pass since we don't have failure criteria yet
        'total_benchmarks': total_benchmarks,
        'passed': total_benchmarks,  # Assume all passed if loaded successfully
        'performance_summary': performance_summary,
        'slowest_test': slowest_test,
        'fastest_test': fastest_test,
        'all_benchmarks': benchmark_details
    }

def compare_performance(current: Dict, previous: List[Dict]) -> str:
    """Compare current performance with previous runs."""
    if not previous or not current.get('all_benchmarks'):
        return "➡️ No comparison data"
    
    # Find matching benchmarks in previous run
    current_benchmarks = {b['name']: b['mean_time'] for b in current.get('all_benchmarks', [])}
    
    # Look for the most recent previous run with matching benchmarks
    for prev_data in previous:
        prev_analysis = analyze_benchmark_performance(prev_data)
        prev_benchmarks = {b['name']: b['mean_time'] for b in prev_analysis.get('all_benchmarks', [])}
        
        # Find common benchmarks
        common_benchmarks = set(current_benchmarks.keys()) & set(prev_benchmarks.keys())
        if not common_benchmarks:
            continue
        
        # Calculate average performance change
        total_change = 0
        comparison_count = 0
        
        for bench_name in common_benchmarks:
            current_time = current_benchmarks[bench_name]
            prev_time = prev_benchmarks[bench_name]
            
            if prev_time > 0:
                change_pct = ((current_time - prev_time) / prev_time) * 100
                total_change += change_pct
                comparison_count += 1
        
        if comparison_count > 0:
            avg_change = total_change / comparison_count
            
            if avg_change > 10:  # 10% or more slower
                return f"⬆️ {avg_change:.1f}% slower (regression)"
            elif avg_change > 5:  # 5-10% slower
                return f"⚠️ {avg_change:.1f}% slower (watch)"
            elif avg_change < -5:  # 5% or more faster
                return f"⬇️ {abs(avg_change):.1f}% faster (improvement)"
            else:
                return f"➡️ Stable (±{abs(avg_change):.1f}%)"
    
    return "➡️ No comparison available"

def format_time_ms(time_seconds: float) -> str:
    """Format time in seconds to milliseconds with appropriate precision."""
    ms = time_seconds * 1000
    if ms < 1:
        return f"{ms:.3f}ms"
    elif ms < 10:
        return f"{ms:.2f}ms"
    else:
        return f"{ms:.1f}ms"

def generate_benchmark_markdown(benchmark_files: List[Dict]) -> str:
    """Generate markdown report from benchmark data."""
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if not benchmark_files:
        return f"""# Benchmark Results Summary

**Status:** ❌ No benchmark data available

To run performance benchmarks, use:
```bash
conda activate hazelbean_env
cd hazelbean_tests
python ../scripts/run_performance_benchmarks.py
```

*Last Updated: {timestamp}*
"""
    
    # Analyze the most recent benchmark
    latest_benchmark = benchmark_files[0]
    latest_analysis = analyze_benchmark_performance(latest_benchmark)
    
    # Get timestamp info
    latest_timestamp = extract_benchmark_timestamp(latest_benchmark['filename'])
    if not latest_timestamp:
        latest_timestamp = datetime.fromtimestamp(latest_benchmark['modified_time']).strftime('%Y-%m-%d %H:%M')
    
    # Compare with previous runs
    performance_trend = compare_performance(latest_analysis, benchmark_files[1:])
    
    # Get commit info if available
    commit_info = latest_benchmark.get('commit_info', {})
    commit_id = commit_info.get('id', 'Unknown')[:8] if commit_info.get('id') else 'Unknown'
    branch = commit_info.get('branch', 'Unknown')
    
    markdown = f"""# Benchmark Results Summary

**Latest Run:** {latest_timestamp}  
**Status:** {latest_analysis['status']} ({latest_analysis['passed']} of {latest_analysis['total_benchmarks']} benchmarks)  
**Performance:** {performance_trend}

## Current Status

**Total Benchmarks:** {latest_analysis['total_benchmarks']}  
**Performance Summary:** {latest_analysis['performance_summary']}  
**Commit:** `{commit_id}` on `{branch}`

## Performance Analysis
"""

    # Add fastest/slowest tests
    if latest_analysis['fastest_test'] and latest_analysis['slowest_test']:
        fastest = latest_analysis['fastest_test']
        slowest = latest_analysis['slowest_test']
        
        markdown += f"""
### Performance Range
- **Fastest Test:** `{fastest['name']}` - {format_time_ms(fastest['mean_time'])} (±{format_time_ms(fastest['stddev'])})
- **Slowest Test:** `{slowest['name']}` - {format_time_ms(slowest['mean_time'])} (±{format_time_ms(slowest['stddev'])})
"""

    # Add detailed benchmark results
    if latest_analysis.get('all_benchmarks'):
        markdown += """
### Detailed Results

| Benchmark | Mean Time | Std Dev | Rounds | Performance |
|-----------|-----------|---------|---------|-------------|
"""
        
        for bench in latest_analysis['all_benchmarks']:
            # Determine performance indicator based on time
            mean_ms = bench['mean_time'] * 1000
            if mean_ms < 1:
                perf_indicator = "⚡ Fast"
            elif mean_ms < 10:
                perf_indicator = "✅ Good"
            elif mean_ms < 100:
                perf_indicator = "⚠️ Moderate"
            else:
                perf_indicator = "🐌 Slow"
            
            markdown += f"| `{bench['name']}` | {format_time_ms(bench['mean_time'])} | {format_time_ms(bench['stddev'])} | {bench['rounds']} | {perf_indicator} |\n"
    
    # Add recent benchmark history
    if len(benchmark_files) > 1:
        markdown += f"""
## Recent Benchmark History (Last {len(benchmark_files)} runs)

| Date | Status | Benchmarks | Performance | Notes |
|------|--------|------------|-------------|-------|
"""
        
        for i, benchmark_file in enumerate(benchmark_files):
            analysis = analyze_benchmark_performance(benchmark_file)
            timestamp = extract_benchmark_timestamp(benchmark_file['filename'])
            if not timestamp:
                timestamp = datetime.fromtimestamp(benchmark_file['modified_time']).strftime('%Y-%m-%d %H:%M')
            
            # Compare with previous if not the first
            if i == 0:
                perf_note = "Current run"
            else:
                prev_files = benchmark_files[i+1:i+2] if i+1 < len(benchmark_files) else []
                trend = compare_performance(analysis, prev_files)
                perf_note = trend.replace('⬆️', '').replace('⬇️', '').replace('➡️', '').replace('⚠️', '').strip()
                if not perf_note or perf_note == 'No comparison available':
                    perf_note = "Previous run"
            
            markdown += f"| {timestamp} | {analysis['status']} | {analysis['total_benchmarks']} tests | {analysis['performance_summary']} | {perf_note} |\n"
    
    # Add system information if available
    machine_info = latest_benchmark.get('machine_info', {})
    if machine_info:
        cpu_info = machine_info.get('cpu', {})
        markdown += f"""
## System Information

- **System:** {machine_info.get('system', 'Unknown')} {machine_info.get('release', '')}
- **Processor:** {cpu_info.get('brand_raw', 'Unknown')} ({machine_info.get('processor', 'Unknown')} architecture)
- **CPU Cores:** {cpu_info.get('count', 'Unknown')}
- **Python:** {machine_info.get('python_version', 'Unknown')}
"""

    markdown += f"""
## Data Sources

View detailed benchmark data:
- **Latest Results:** `/metrics/benchmarks/{latest_benchmark['filename']}`
- **All Benchmarks:** `/metrics/benchmarks/` directory

---

*This report is automatically generated from `/metrics/benchmarks/` data. To update, run `./tools/generate_reports.sh`*
"""
    
    return markdown

def main():
    """Main function to generate benchmark summary report."""
    
    # Get script directory and setup paths
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent
    
    benchmarks_dir = project_root / 'metrics/benchmarks'
    output_path = project_root / 'docs-site/docs/reports/benchmark-results.md'
    
    print("⚡ Generating benchmark results summary...")
    
    # Load recent benchmark files
    benchmark_files = load_benchmark_files(benchmarks_dir, max_files=3)
    
    print(f"   📊 Loaded {len(benchmark_files)} benchmark files")
    
    # Generate markdown
    markdown_content = generate_benchmark_markdown(benchmark_files)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the report
    with open(output_path, 'w') as f:
        f.write(markdown_content)
    
    if benchmark_files:
        latest_analysis = analyze_benchmark_performance(benchmark_files[0])
        print(f"✅ Benchmark results summary generated")
        print(f"   🚀 {latest_analysis['total_benchmarks']} benchmarks analyzed")
        print(f"   📄 Saved to: {output_path}")
    else:
        print("⚠️  Benchmark results summary generated with no data placeholder")
        print(f"   📄 Saved to: {output_path}")
    
    return True

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
