#!/usr/bin/env python3
"""
Convert performance baseline JSON to markdown dashboard
Input: metrics/baselines/current_performance_baseline.json + snapshots/
Output: docs-site/docs/reports/performance-baselines.md

Follows Option 1 implementation plan for dynamic baseline reporting
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

def load_current_baseline(baseline_path: Path) -> Optional[Dict]:
    """Load current performance baseline data."""
    try:
        with open(baseline_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load baseline from {baseline_path}: {e}")
        return None

def load_baseline_snapshots(snapshots_dir: Path) -> List[Dict]:
    """Load recent baseline snapshots for trend analysis."""
    snapshots = []
    
    if not snapshots_dir.exists():
        return snapshots
    
    # Find snapshot files
    snapshot_files = sorted([f for f in snapshots_dir.glob('baseline_snapshot_*.json')], reverse=True)
    
    # Load up to 3 most recent snapshots
    for snapshot_file in snapshot_files[:3]:
        try:
            with open(snapshot_file, 'r') as f:
                snapshot_data = json.load(f)
                snapshot_data['filename'] = snapshot_file.name
                snapshots.append(snapshot_data)
        except Exception as e:
            print(f"Warning: Could not load snapshot {snapshot_file}: {e}")
            continue
    
    return snapshots

def calculate_trend(current: Dict, snapshots: List[Dict]) -> str:
    """Calculate performance trend indicator."""
    if not snapshots or not current.get('baseline_statistics'):
        return "➡️ No trend data"
    
    current_mean = current['baseline_statistics']['mean_execution_time']
    
    # Find the most recent previous snapshot with baseline_statistics
    for snapshot in snapshots:
        if snapshot.get('baseline_statistics') and snapshot.get('baseline_statistics', {}).get('mean_execution_time'):
            previous_mean = snapshot['baseline_statistics']['mean_execution_time']
            
            # Calculate percentage change
            change_pct = ((current_mean - previous_mean) / previous_mean * 100) if previous_mean > 0 else 0
            
            if change_pct < -5:  # 5% or more improvement (faster)
                return f"⬇️ {abs(change_pct):.1f}% improvement (faster)"
            elif change_pct > 10:  # 10% or more regression (slower)
                return f"⬆️ {change_pct:.1f}% regression (slower)"
            elif change_pct > 5:  # 5-10% slower
                return f"⚠️ {change_pct:.1f}% slower"
            else:
                return f"➡️ Stable (±{abs(change_pct):.1f}%)"
    
    return "➡️ No comparison data"

def format_time_ms(time_seconds: float) -> str:
    """Format time in seconds to milliseconds with appropriate precision."""
    ms = time_seconds * 1000
    if ms < 1:
        return f"{ms:.3f}ms"
    elif ms < 10:
        return f"{ms:.2f}ms"
    else:
        return f"{ms:.1f}ms"

def format_confidence_interval(interval: Dict) -> str:
    """Format confidence interval for display."""
    lower_ms = interval['lower'] * 1000
    upper_ms = interval['upper'] * 1000
    return f"[{lower_ms:.2f}, {upper_ms:.2f}]ms"

def generate_baseline_markdown(current_data: Optional[Dict], snapshots: List[Dict]) -> str:
    """Generate markdown dashboard from baseline data."""
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if not current_data:
        return f"""# Performance Baselines Dashboard

**Status:** ❌ No baseline data available

To establish performance baselines, run:
```bash
conda activate hazelbean_env
cd hazelbean_tests
python ../scripts/establish_performance_baseline.py
```

*Last Updated: {timestamp}*
"""

    stats = current_data.get('baseline_statistics', {})
    metadata = current_data.get('baseline_metadata', {})
    
    # Get key metrics
    mean_time = stats.get('mean_execution_time', 0)
    std_dev = stats.get('std_deviation', 0)
    confidence_interval = stats.get('confidence_interval', {})
    sample_size = stats.get('sample_size', 0)
    
    # Calculate trend
    trend = calculate_trend(current_data, snapshots)
    
    # Get establishment info
    established_at = metadata.get('established_at', 'Unknown')
    if established_at != 'Unknown':
        try:
            established_dt = datetime.fromisoformat(established_at.replace('Z', '+00:00'))
            established_str = established_dt.strftime('%Y-%m-%d %H:%M')
        except:
            established_str = established_at
    else:
        established_str = 'Unknown'
    
    confidence_level = metadata.get('statistical_confidence', '95%')
    
    markdown = f"""# Performance Baselines Dashboard

**Current Baseline:** {format_time_ms(mean_time)} ± {format_time_ms(std_dev)} ({confidence_level} confidence)  
**Trend:** {trend}  
**Last Updated:** {timestamp}

## Current Baseline Statistics

| Metric | Value | Details |
|--------|-------|---------|
| **Mean Execution Time** | {format_time_ms(mean_time)} | Average processing time |
| **Standard Deviation** | {format_time_ms(std_dev)} | Performance variability |
| **Confidence Interval** | {format_confidence_interval(confidence_interval)} | {confidence_level} confidence bounds |
| **Sample Size** | {sample_size} tests | Statistical reliability |
| **Established** | {established_str} | Baseline creation date |

## Performance Analysis

### Baseline Quality
"""

    # Assess baseline quality
    cv = (std_dev / mean_time * 100) if mean_time > 0 else float('inf')
    if cv < 10:
        quality_status = "✅ Excellent (low variability)"
    elif cv < 25:
        quality_status = "✅ Good (moderate variability)"
    elif cv < 50:
        quality_status = "⚠️ Fair (high variability)"
    else:
        quality_status = "❌ Poor (very high variability)"
    
    markdown += f"""
**Coefficient of Variation:** {cv:.1f}%  
**Quality Assessment:** {quality_status}

### System Information
"""

    # Add system info if available in current baseline
    if current_data.get('raw_results') and len(current_data['raw_results']) > 0:
        machine_info = current_data['raw_results'][0].get('benchmark_data', {}).get('machine_info', {})
        if machine_info:
            system = machine_info.get('system', 'Unknown')
            processor = machine_info.get('processor', 'Unknown')
            cpu_brand = machine_info.get('cpu', {}).get('brand_raw', 'Unknown')
            cpu_count = machine_info.get('cpu', {}).get('count', 'Unknown')
            
            markdown += f"""
- **System:** {system}
- **Processor:** {cpu_brand} ({processor} architecture)
- **CPU Cores:** {cpu_count}
- **Python Version:** {machine_info.get('python_version', 'Unknown')}
"""
    
    # Add snapshot history if available
    if snapshots:
        markdown += f"""
## Recent Snapshots (Last {len(snapshots)} runs)

| Date | Mean Time | Std Dev | Change | Notes |
|------|-----------|---------|---------|-------|
"""
        
        # Add current baseline as first row
        markdown += f"| {established_str} | {format_time_ms(mean_time)} | {format_time_ms(std_dev)} | ✅ Current | Current baseline |\n"
        
        # Add previous snapshots
        for i, snapshot in enumerate(snapshots):
            snap_stats = snapshot.get('baseline_statistics', {})
            snap_metadata = snapshot.get('baseline_metadata', {})
            
            if not snap_stats:
                continue
                
            snap_mean = snap_stats.get('mean_execution_time', 0)
            snap_std = snap_stats.get('std_deviation', 0)
            snap_date = snap_metadata.get('established_at', 'Unknown')
            
            if snap_date != 'Unknown':
                try:
                    snap_dt = datetime.fromisoformat(snap_date.replace('Z', '+00:00'))
                    snap_date_str = snap_dt.strftime('%Y-%m-%d %H:%M')
                except:
                    snap_date_str = snap_date
            else:
                snap_date_str = 'Unknown'
            
            # Calculate change from current
            if snap_mean > 0:
                change_pct = ((mean_time - snap_mean) / snap_mean * 100)
                if change_pct < -5:
                    change_indicator = f"⬇️ {abs(change_pct):.1f}%"
                elif change_pct > 5:
                    change_indicator = f"⬆️ {change_pct:.1f}%"
                else:
                    change_indicator = f"➡️ {change_pct:+.1f}%"
            else:
                change_indicator = "❓"
            
            markdown += f"| {snap_date_str} | {format_time_ms(snap_mean)} | {format_time_ms(snap_std)} | {change_indicator} | Previous run |\n"
    
    else:
        markdown += """
## Recent Snapshots

No snapshot history available. Snapshots will appear here after multiple baseline runs.
"""
    
    markdown += f"""
---

*This dashboard is automatically generated from `/metrics/baselines/` data. To update, run `./tools/generate_reports.sh`*
"""
    
    return markdown

def main():
    """Main function to generate performance baseline report."""
    
    # Get script directory and setup paths
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent
    
    baseline_path = project_root / 'metrics/baselines/current_performance_baseline.json'
    snapshots_dir = project_root / 'baselines/snapshots'  # Based on project layout
    output_path = project_root / 'docs-site/docs/reports/performance-baselines.md'
    
    print("📈 Generating performance baselines dashboard...")
    
    # Load current baseline data
    current_data = load_current_baseline(baseline_path)
    
    # Load recent snapshots
    snapshots = load_baseline_snapshots(snapshots_dir)
    
    print(f"   📊 Loaded baseline: {'✅' if current_data else '❌'}")
    print(f"   📸 Found {len(snapshots)} snapshots")
    
    # Generate markdown
    markdown_content = generate_baseline_markdown(current_data, snapshots)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the report
    with open(output_path, 'w') as f:
        f.write(markdown_content)
    
    if current_data:
        stats = current_data.get('baseline_statistics', {})
        mean_time = stats.get('mean_execution_time', 0)
        print(f"✅ Performance baselines dashboard generated")
        print(f"   ⚡ Current baseline: {format_time_ms(mean_time)}")
        print(f"   📄 Saved to: {output_path}")
    else:
        print("⚠️  Performance baselines dashboard generated with no data placeholder")
        print(f"   📄 Saved to: {output_path}")
    
    return True

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
