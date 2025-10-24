#!/usr/bin/env python
"""
Test Failure Rate Tracking Tool

Generates reports from pytest JSON output showing:
- Pass/fail/xfail/xpass counts and percentages
- Trends over time
- Alerts for unexpected changes

Usage:
    python tools/test_failure_tracking.py test-results.json
    python tools/test_failure_tracking.py test-results.json --compare-to metrics/test-failures/baseline.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

def parse_pytest_json(json_path: str) -> Dict:
    """Parse pytest JSON report and extract statistics"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    summary = data.get('summary', {})
    
    return {
        'total': summary.get('total', 0),
        'passed': summary.get('passed', 0),
        'failed': summary.get('failed', 0),
        'xfailed': summary.get('xfailed', 0),
        'xpassed': summary.get('xpassed', 0),
        'skipped': summary.get('skipped', 0),
        'timestamp': datetime.now().isoformat(),
        'duration': data.get('duration', 0)
    }

def calculate_percentages(stats: Dict) -> Dict:
    """Calculate percentage breakdown"""
    total = stats['total']
    if total == 0:
        return stats
    
    stats['passed_pct'] = (stats['passed'] / total) * 100
    stats['failed_pct'] = (stats['failed'] / total) * 100
    stats['xfailed_pct'] = (stats['xfailed'] / total) * 100
    stats['xpassed_pct'] = (stats['xpassed'] / total) * 100
    
    return stats

def generate_markdown_report(stats: Dict, baseline: Optional[Dict] = None) -> str:
    """Generate markdown report"""
    report = ["# Test Results Report", ""]
    report.append(f"**Generated:** {stats['timestamp']}")
    report.append(f"**Duration:** {stats['duration']:.2f}s")
    report.append("")
    
    # Summary table
    report.append("## Summary")
    report.append("")
    report.append("| Status | Count | Percentage |")
    report.append("|--------|-------|------------|")
    report.append(f"| ✅ Passed | {stats['passed']} | {stats['passed_pct']:.1f}% |")
    report.append(f"| ❌ Failed | {stats['failed']} | {stats['failed_pct']:.1f}% |")
    report.append(f"| ⚠️ XFailed (Known Bugs) | {stats['xfailed']} | {stats['xfailed_pct']:.1f}% |")
    report.append(f"| 🎉 XPassed (Bugs Fixed!) | {stats['xpassed']} | {stats['xpassed_pct']:.1f}% |")
    report.append(f"| **Total** | **{stats['total']}** | **100%** |")
    report.append("")
    
    # Health indicators
    report.append("## Health Indicators")
    report.append("")
    
    if stats['failed'] == 0:
        report.append("✅ **No unexpected failures** - All tests passing or failing as expected")
    else:
        report.append(f"⚠️ **{stats['failed']} unexpected failure(s)** - Investigate immediately")
    
    if stats['xpassed'] > 0:
        report.append(f"🎉 **{stats['xpassed']} bug(s) fixed!** - Remove xfail markers from these tests")
    
    if stats['xfailed'] > 0:
        report.append(f"📝 **{stats['xfailed']} known bug(s)** - See KNOWN_BUGS.md for details")
    
    report.append("")
    
    # Trend comparison if baseline provided
    if baseline:
        report.append("## Trend Analysis")
        report.append("")
        report.append("| Metric | Current | Baseline | Change |")
        report.append("|--------|---------|----------|--------|")
        
        for key in ['passed', 'failed', 'xfailed', 'xpassed']:
            current = stats[key]
            base = baseline.get(key, 0)
            change = current - base
            emoji = "🔴" if change < 0 and key == 'passed' else "🟢" if change > 0 and key == 'passed' else "➖"
            change_str = f"+{change}" if change > 0 else str(change)
            report.append(f"| {key.title()} | {current} | {base} | {emoji} {change_str} |")
        
        report.append("")
    
    return "\n".join(report)

def generate_github_actions_summary(stats: Dict) -> str:
    """Generate summary for GitHub Actions $GITHUB_STEP_SUMMARY"""
    lines = [
        "## 🧪 Test Results Summary",
        "",
        f"**Total Tests:** {stats['total']} | **Duration:** {stats['duration']:.2f}s",
        "",
        "| Status | Count | % |",
        "|--------|-------|---|",
        f"| ✅ Passed | {stats['passed']} | {stats['passed_pct']:.1f}% |",
        f"| ❌ Failed | {stats['failed']} | {stats['failed_pct']:.1f}% |",
        f"| ⚠️ Known Bugs | {stats['xfailed']} | {stats['xfailed_pct']:.1f}% |",
        f"| 🎉 Bugs Fixed | {stats['xpassed']} | {stats['xpassed_pct']:.1f}% |",
        ""
    ]
    
    if stats['failed'] > 0:
        lines.append("### ⚠️ Action Required")
        lines.append(f"**{stats['failed']} unexpected failure(s) detected!**")
        lines.append("")
    elif stats['xpassed'] > 0:
        lines.append("### 🎉 Good News")
        lines.append(f"**{stats['xpassed']} bug(s) appear to be fixed!** Remove xfail markers.")
        lines.append("")
    
    return "\n".join(lines)

def save_baseline(stats: Dict, output_path: str):
    """Save current stats as baseline for future comparison"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(stats, f, indent=2)

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_failure_tracking.py <pytest-json-file> [--compare-to baseline.json] [--save-baseline output.json]")
        sys.exit(1)
    
    json_file = sys.argv[1]
    baseline_file = None
    save_baseline_file = None
    
    # Parse arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--compare-to' and i + 1 < len(sys.argv):
            baseline_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--save-baseline' and i + 1 < len(sys.argv):
            save_baseline_file = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    # Parse current results
    stats = parse_pytest_json(json_file)
    stats = calculate_percentages(stats)
    
    # Load baseline if provided
    baseline = None
    if baseline_file and Path(baseline_file).exists():
        baseline = parse_pytest_json(baseline_file)
        baseline = calculate_percentages(baseline)
    
    # Generate reports
    markdown_report = generate_markdown_report(stats, baseline)
    github_summary = generate_github_actions_summary(stats)
    
    # Print reports
    print(markdown_report)
    print("\n" + "="*80 + "\n")
    print("GitHub Actions Summary:")
    print(github_summary)
    
    # Save baseline if requested
    if save_baseline_file:
        save_baseline(stats, save_baseline_file)
        print(f"\n✅ Baseline saved to {save_baseline_file}")
    
    # Exit with error if unexpected failures
    if stats['failed'] > 0:
        sys.exit(1)
    
    sys.exit(0)

if __name__ == '__main__':
    main()

