# Test Failure Tracking Metrics

This directory contains baseline metrics and historical tracking data for test failure rates.

## Purpose

Track test pass/fail/xfail/xpass rates over time to:
- Monitor test health trends
- Detect unexpected new failures
- Alert when known bugs are fixed (xpass)
- Provide visibility into testing quality

## Files

### Baseline Files (`baseline-*.json`)

Initial baseline metrics for each test category. Used for trend comparison.

**Format:**
```json
{
  "total": 22,
  "passed": 19,
  "failed": 0,
  "xfailed": 3,
  "xpassed": 0,
  "skipped": 0,
  "passed_pct": 86.4,
  "failed_pct": 0.0,
  "xfailed_pct": 13.6,
  "xpassed_pct": 0.0,
  "timestamp": "2025-10-03T00:00:00",
  "duration": 7.21,
  "notes": "Description of baseline"
}
```

### Current Files (`current-*.json`)

Most recent test run metrics, updated by CI on each run.

## Test Categories

- **add_iterator** - ProjectFlow add_iterator() method tests
- **add_task** - ProjectFlow add_task() method tests
- **get_path** - Path resolution and file discovery tests
- **tile_iterator** - Parallel tiling iterator tests

## Usage

### Generate Report Locally

```bash
# Run tests with JSON output
pytest hazelbean_tests/unit/test_add_iterator.py \
  --json-report \
  --json-report-file=test-results.json

# Generate report comparing to baseline
python tools/test_failure_tracking.py test-results.json \
  --compare-to metrics/test-failures/baseline-add_iterator.json \
  --save-baseline metrics/test-failures/current-add_iterator.json
```

### Interpret Results

**Passing Metrics (Good):**
- `passed`: Tests passing normally
- `xfailed`: Known bugs (expected failures) - see KNOWN_BUGS.md

**Warning Metrics (Investigate):**
- `failed > 0`: New unexpected failures - investigate immediately
- `xpassed > 0`: Known bugs appear fixed - remove xfail markers

**Percentage Targets:**
- `passed_pct`: Should trend upward as bugs are fixed
- `xfailed_pct`: Should trend downward as bugs are fixed
- `failed_pct`: Should always be 0%

## CI Integration

GitHub Actions automatically:
1. Runs tests with JSON reporting
2. Generates failure rate reports
3. Compares to baselines
4. Updates current metrics
5. Uploads artifacts

View reports in: Actions → Workflow run → Artifacts → test-results-*

## Updating Baselines

Update baselines when:
- Intentionally adding new tests
- Fixing bugs (remove xfail markers)
- Restructuring test suite

**Don't update baselines for:**
- New unexpected failures
- Temporary test issues
- Local development runs

## Historical Tracking

Future enhancement: Track metrics over time to show trends.

Planned:
- `history/` directory with timestamped snapshots
- Trend graphs and analysis
- Regression detection algorithms

