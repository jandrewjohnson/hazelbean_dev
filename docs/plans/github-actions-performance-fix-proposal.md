# GitHub Actions Performance Benchmarking Fix Proposal

## Summary
- **Goal:** Fix GitHub Actions to use proper performance regression detection with 10% threshold enforcement
- **Scope:** Update `testing-quality-gates.yml` to match the sophisticated benchmarking system described in the performance guide
- **Current Issue:** Workflows use basic pytest benchmarking instead of the advanced regression detection system

## Current State (What's Wrong)

### Current Implementation in `.github/workflows/testing-quality-gates.yml`:
```yaml
# Lines 227-250 - PROBLEMATIC current implementation
python -m pytest hazelbean_tests/performance/test_benchmarks.py \
  -v --benchmark-only \
  --benchmark-json=performance-results.json \
  --tb=short || {
    echo "status=warning" >> $GITHUB_OUTPUT  
    echo "⚠️ Performance regression detected"
    # Don't fail - performance issues need investigation, not blocking
  }
```

**Issues:**
- ❌ Uses basic pytest instead of sophisticated regression system
- ❌ Only warns, doesn't block PRs on 10% regression
- ❌ No threshold-based comparison to baseline
- ❌ Missing the `scripts/run_performance_benchmarks.py` integration
- ❌ No proper baseline establishment/comparison

## Recommended Fix

### Replace Performance Job (lines 205-260) with:

```yaml
# Quality Gate 4: Performance Regression Testing
performance-regression:
  name: "Quality Gate 4: Performance Regression"
  runs-on: ubuntu-22.04  # Lock specific OS version for consistency
  needs: core-functionality
  timeout-minutes: 15
  
  steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      
    - name: Setup Mambaforge with hazelbean_env
      uses: mamba-org/setup-micromamba@v1
      with:
        environment-file: environment.yml
        environment-name: hazelbean_env
        cache-environment: true
        
    - name: Run performance regression tests with STRICT enforcement
      run: |
        echo "⚡ Running STRICT performance regression tests..."
        
        # Run regression check with 10% threshold - FAIL on regression
        python scripts/run_performance_benchmarks.py --check-regression --threshold 10.0 --verbose || {
          echo "❌ BLOCKING: Performance regression > 10% detected"
          echo "📊 Review performance report for details"
          echo "🛑 This PR cannot be merged until performance is restored"
          exit 1
        }
        
        echo "✅ Performance within acceptable limits"
        
    - name: Establish baseline for main branch
      if: github.ref == 'refs/heads/main' && github.event_name == 'push'
      run: |
        echo "📊 Establishing performance baseline for main branch..."
        python scripts/run_performance_benchmarks.py --establish-baseline --runs 3
        
    - name: Upload performance artifacts
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: performance-regression-results
        path: |
          metrics/reports/performance_report_*.txt
          metrics/exports/performance_export_*.csv
          metrics/analysis/regression_check_*.json
        retention-days: 90
```

### Key Changes:
1. **✅ Use proper regression script:** `scripts/run_performance_benchmarks.py --check-regression`
2. **✅ Enforce 10% threshold:** `--threshold 10.0` 
3. **✅ Fail builds on regression:** `exit 1` when regression detected
4. **✅ Upload organized artifacts:** Use new organized paths from guide
5. **✅ Lock OS version:** `ubuntu-22.04` instead of `ubuntu-latest`

## Machine Consistency Solution

### Problem:
Current workflows run on `ubuntu-latest` which varies between runs, causing inconsistent performance baselines and false regression alerts.

### Solution Options (in order of preference):

#### Option 1: Self-Hosted Runners (RECOMMENDED)
```yaml
performance-regression:
  runs-on: self-hosted  # or [self-hosted, linux, performance-testing]
```

**Benefits:**
- ✅ Identical hardware for all runs
- ✅ No virtualization overhead  
- ✅ Consistent environment
- ✅ Faster execution

**Requirements:**
- Dedicated machine for CI
- GitHub runner software installed
- Consistent conda environment

#### Option 2: Locked Runner Specifications
```yaml
performance-regression:
  runs-on: ubuntu-22.04  # Lock specific version instead of ubuntu-latest
```

**Benefits:**
- ✅ More consistent than `ubuntu-latest`
- ✅ No infrastructure changes needed
- ✅ Still some variation but reduced

#### Option 3: Docker Containerization
```yaml
performance-regression:
  runs-on: ubuntu-22.04
  container:
    image: continuumio/mambaforge:latest
    options: --cpus="2" --memory="4g"  # Lock resources
```

**Benefits:**
- ✅ Reproducible environment
- ✅ Resource constraints
- ✅ Controlled dependencies

## Core Proof Tests (2-3 only)

**Test 1 (Regression Detection):** 
- Trigger: PR with intentionally slower code
- Expected: Build fails with "Performance regression > 10% detected"

**Test 2 (Baseline Establishment):**
- Trigger: Push to main branch  
- Expected: New baseline created in `metrics/baselines/`

**Test 3 (No Regression):**
- Trigger: PR with no performance impact
- Expected: Build passes with "Performance within acceptable limits"

## Rollback Plan

If the new system causes issues:
1. Revert to current pytest-based approach temporarily
2. Set performance job to `continue-on-error: true` during transition
3. Run both systems in parallel for comparison period

## Implementation Steps

1. **Backup current workflow:** Copy existing to `testing-quality-gates-backup.yml`
2. **Update performance job** with the new configuration above
3. **Test on feature branch** before merging to main
4. **Monitor for false positives** in first week after deployment
5. **Consider self-hosted runner setup** for long-term consistency

## Expected Outcome

After implementation:
- ✅ PRs automatically blocked when performance degrades > 10%
- ✅ Consistent performance baselines across runs
- ✅ Proper integration with the sophisticated benchmarking system
- ✅ Organized performance artifacts and reports
- ✅ Reliable quality gate enforcement

This will transform the current "warning-only" system into a proper performance quality gate that actually protects against regressions.
