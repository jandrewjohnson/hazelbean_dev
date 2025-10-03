# Performance Regression Fix - Implementation Plan

## Overview

**Goal**: Fix CI performance regression tests by persisting baseline across branches using GitHub Artifacts

**Approach**: GitHub Artifacts (Option 1 from analysis document) - SIMPLIFIED

**Effort**: ~20 minutes  
**Risk Level**: Low (CI-only changes, easily reversible)  
**Files Modified**: 1 (`.github/workflows/testing-quality-gates.yml`)

---

## ✅ REVIEW COMPLETED - APPROVED

**Review Date**: October 3, 2025  
**Review Notes**: 
- Initial plan was slightly overcomplicated
- Removed unnecessary artifact renaming (Step 2e)
- Core logic is sound and will work as expected
- Verified all three scenarios (first run, main branch, PR branch)

## Pre-Implementation Checklist

- [x] Verified error exists in CI logs
- [x] Confirmed baseline file missing in CI environment
- [x] Confirmed baseline exists locally (`metrics/baselines/current_performance_baseline.json`)
- [x] Analyzed root cause (baseline not persisted between CI runs)
- [x] Review implementation plan (this document)
- [x] User approval to proceed
- [x] Simplified unnecessary complexity

---

## Implementation Steps

### Step 1: Add External Action Dependency

**What**: Add `dawidd6/action-download-artifact@v3` action to download artifacts from main branch

**Why**: GitHub's built-in `actions/download-artifact@v4` only downloads artifacts from the current workflow run. We need to download artifacts from main branch's previous runs.

**Action Details**:
- Repository: https://github.com/dawidd6/action-download-artifact
- Stars: 5,000+
- Last Updated: Active (2024)
- Purpose: Download artifacts from other workflow runs

**No code changes needed** - just add the action to workflow YAML.

---

### Step 2: Modify CI Workflow File

**File**: `.github/workflows/testing-quality-gates.yml`

**Section**: `performance-regression` job (lines 247-302)

**Changes**:

#### 2a. Add Baseline Download Step (After environment setup)

Insert new step after line 268 (after Mambaforge setup):

```yaml
- name: Download baseline from main branch
  uses: dawidd6/action-download-artifact@v3
  with:
    workflow: testing-quality-gates.yml
    branch: main
    name: performance-baseline
    path: metrics/baselines/
    if_no_artifact_found: warn
  continue-on-error: true
```

**Purpose**: Download the canonical baseline that was established on main branch

#### 2b. Add Baseline Verification Step

Insert new step immediately after download:

```yaml
- name: Ensure baseline exists
  run: |
    if [ ! -f metrics/baselines/current_performance_baseline.json ]; then
      echo "📊 No baseline from main - establishing baseline..."
      python scripts/run_performance_benchmarks.py --establish-baseline --runs 3
    else
      echo "✅ Using baseline from main branch"
      ls -lh metrics/baselines/current_performance_baseline.json
    fi
```

**Purpose**: Graceful fallback if baseline doesn't exist yet (first run scenario)

#### 2c. Keep Existing Regression Check (No Changes)

Lines 270-285 stay exactly as-is:

```yaml
- name: Run performance regression tests with STRICT enforcement
  id: performance
  run: |
    echo "⚡ Running STRICT performance regression tests..."
    
    # Run regression check with 10% threshold - FAIL on regression
    python scripts/run_performance_benchmarks.py --check-regression --threshold 10.0 --verbose || {
      echo "❌ BLOCKING: Performance regression > 10% detected"
      echo "📊 Review performance report for details"
      echo "🛑 This PR cannot be merged until performance is restored"
      echo "status=failed" >> $GITHUB_OUTPUT
      exit 1
    }
    
    echo "✅ Performance within acceptable limits"
    echo "status=passed" >> $GITHUB_OUTPUT
```

**No changes** - this already works correctly once baseline exists.

#### 2d. Add Baseline Upload Step (Main branch only)

Insert new step after baseline establishment (after line 291):

```yaml
- name: Upload baseline artifact for future runs
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  uses: actions/upload-artifact@v4
  with:
    name: performance-baseline
    path: metrics/baselines/current_performance_baseline.json
    retention-days: 90
    overwrite: true
```

**Purpose**: Persist baseline so PR branches can download and compare against it

#### ~~2e. Update Existing Upload Step (Add unique name)~~ - REMOVED

**SIMPLIFIED**: This step was removed as unnecessary. The existing artifact upload works fine as-is.

---

### Step 3: Update Workflow Comments

Add explanatory comments to document the baseline persistence strategy:

```yaml
# Quality Gate 4: Performance Regression Testing
# 
# Strategy: 
# 1. Main branch establishes canonical baseline and uploads as artifact
# 2. PR branches download baseline from main for comparison
# 3. Bootstrap: If no baseline exists, establish temporary one (limited regression detection)
# 4. Strict enforcement: >10% regression blocks merge
```

---

## Complete Modified Section

Here's the complete `performance-regression` job after changes:

```yaml
# Quality Gate 4: Performance Regression Testing
performance-regression:
  name: "Quality Gate 4: Performance Regression"
  runs-on: ubuntu-22.04  # Lock specific OS version for consistency
  needs: core-functionality
  if: ${{ !cancelled() && (needs.core-functionality.result == 'success' || github.event.inputs.test_level == 'full') }}
  timeout-minutes: 15
  
  outputs:
    performance-status: ${{ steps.performance.outputs.status }}
    
  steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      
    - name: Setup Mambaforge with hazelbean_env
      uses: mamba-org/setup-micromamba@v2
      with:
        environment-file: environment.yml
        environment-name: hazelbean_env
        cache-environment: true
        cache-downloads: true
    
    # NEW: Download baseline from main branch for regression comparison
    - name: Download baseline from main branch
      uses: dawidd6/action-download-artifact@v3
      with:
        workflow: testing-quality-gates.yml
        branch: main
        name: performance-baseline
        path: metrics/baselines/
        if_no_artifact_found: warn
      continue-on-error: true
    
    # NEW: Ensure baseline exists (download or establish)
    - name: Ensure baseline exists
      run: |
        if [ ! -f metrics/baselines/current_performance_baseline.json ]; then
          echo "📊 No baseline from main - establishing baseline..."
          python scripts/run_performance_benchmarks.py --establish-baseline --runs 3
        else
          echo "✅ Using baseline from main branch"
          ls -lh metrics/baselines/current_performance_baseline.json
        fi
        
    # EXISTING: Run regression check (no changes)
    - name: Run performance regression tests with STRICT enforcement
      id: performance
      run: |
        echo "⚡ Running STRICT performance regression tests..."
        
        # Run regression check with 10% threshold - FAIL on regression
        python scripts/run_performance_benchmarks.py --check-regression --threshold 10.0 --verbose || {
          echo "❌ BLOCKING: Performance regression > 10% detected"
          echo "📊 Review performance report for details"
          echo "🛑 This PR cannot be merged until performance is restored"
          echo "status=failed" >> $GITHUB_OUTPUT
          exit 1
        }
        
        echo "✅ Performance within acceptable limits"
        echo "status=passed" >> $GITHUB_OUTPUT
        
    # EXISTING: Establish baseline on main branch (no changes)
    - name: Establish baseline for main branch
      if: github.ref == 'refs/heads/main' && github.event_name == 'push'
      run: |
        echo "📊 Establishing performance baseline for main branch..."
        python scripts/run_performance_benchmarks.py --establish-baseline --runs 3
    
    # NEW: Upload baseline artifact for PR branches to use
    - name: Upload baseline artifact for future runs
      if: github.ref == 'refs/heads/main' && github.event_name == 'push'
      uses: actions/upload-artifact@v4
      with:
        name: performance-baseline
        path: metrics/baselines/current_performance_baseline.json
        retention-days: 90
        overwrite: true
        
    # EXISTING: Upload performance artifacts (no changes needed)
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

---

## Testing Plan

### Phase 1: Verify Changes Work on Main Branch

1. **Push to main branch** (merge this fix)
2. **Verify in Actions**:
   - [ ] Baseline establishment runs successfully
   - [ ] Baseline artifact is uploaded
   - [ ] Artifact appears in Actions artifacts tab
3. **Check artifact**:
   - [ ] Download artifact manually from GitHub UI
   - [ ] Verify JSON is valid and non-empty

### Phase 2: Test PR Branch with Baseline

1. **Create test PR branch** from updated main
2. **Trigger CI** (push to branch)
3. **Verify in Actions**:
   - [ ] Baseline download step succeeds
   - [ ] "✅ Baseline downloaded from main branch" message appears
   - [ ] Regression check runs successfully
   - [ ] No JSON parsing errors

### Phase 3: Test Bootstrap Scenario

1. **Manually delete artifact** from GitHub (or wait for it to expire)
2. **Create new PR branch**
3. **Verify in Actions**:
   - [ ] Baseline download fails gracefully (warning, not error)
   - [ ] "⚠️ No baseline found" message appears
   - [ ] Temporary baseline is established
   - [ ] Regression check runs (with limited detection)
   - [ ] CI passes (doesn't block)

### Phase 4: Test Regression Detection

1. **Create test branch** with intentionally slow code:
   ```python
   # Add to a tested function
   import time
   time.sleep(0.5)  # Artificial slowdown
   ```
2. **Push and verify**:
   - [ ] Regression check detects slowdown
   - [ ] CI fails with "Performance regression detected"
   - [ ] Error message shows which benchmarks regressed

---

## Rollback Plan

If anything goes wrong, rollback is simple:

### Option A: Revert Git Commit
```bash
git revert <commit-hash>
git push
```

### Option B: Quick Fix - Disable Performance Gate
```yaml
# Comment out the entire performance-regression job
# performance-regression:
#   name: "Quality Gate 4: Performance Regression"
#   ...
```

### Option C: Make Non-Blocking
```yaml
# Change regression check to warning only
- name: Run performance regression tests with STRICT enforcement
  continue-on-error: true  # Add this line
```

---

## Risk Assessment

### Low Risk Areas ✅
- **CI workflow only** - No production code changes
- **Isolated to one job** - Other quality gates unaffected
- **Graceful degradation** - Bootstrap fallback if artifact missing
- **External action is reputable** - 5k+ stars, actively maintained
- **Easy rollback** - Simple git revert

### Potential Issues ⚠️

| Issue | Likelihood | Impact | Mitigation |
|-------|-----------|--------|------------|
| Artifact download fails | Low | Medium | Bootstrap fallback establishes temp baseline |
| External action breaks | Very Low | Low | Pin to specific version (`@v3.1.4`) |
| Baseline becomes stale | Medium | Low | 90-day retention + age warning in future |
| Cross-workflow artifact not found | Low | Low | Bootstrap handles first run gracefully |
| Artifact name collision | Very Low | Low | Use unique run IDs in artifact names |

### Success Criteria ✅

- [ ] Main branch successfully uploads baseline artifact
- [ ] PR branches download and use main branch baseline
- [ ] No more "Expecting value: line 1 column 1" JSON errors
- [ ] Regression detection works correctly
- [ ] Bootstrap scenario handled gracefully
- [ ] CI logs show clear messages about baseline status

---

## Timeline

### Implementation: 15 minutes
1. Modify `.github/workflows/testing-quality-gates.yml` (10 min)
2. Review changes (3 min)
3. Commit and push (2 min)

### Testing: 20-30 minutes
1. Wait for main branch CI to complete (~10 min)
2. Verify artifact uploaded (2 min)
3. Create test PR and wait for CI (~10 min)
4. Verify baseline downloaded correctly (2 min)
5. Review logs (5 min)

### Total: ~45 minutes end-to-end

---

## Post-Implementation Notes

### Future Enhancements (Not in Scope)

1. **Baseline age warning**: Warn if baseline is >30 days old
2. **Multi-platform baselines**: Separate baselines for Ubuntu/macOS/Windows
3. **Baseline versioning**: Track baseline changes over time
4. **Performance trends**: Graph performance over multiple PRs
5. **Automatic baseline refresh**: Re-establish baseline weekly

### Documentation Updates Needed

1. Update `README.md` - Add note about performance regression testing
2. Update `docs/plans/performance-regression-ci-fix-proposal.md` - Mark as implemented
3. Add troubleshooting guide for "baseline not found" scenarios

---

## Approval & Sign-off

**Implementation Plan**: Ready for review  
**Awaiting Approval**: Yes ✋

**Questions for User**:

1. ✅ Is the GitHub Artifacts approach acceptable? (external action dependency)
2. ✅ Is 90-day retention period sufficient for baseline?
3. ✅ Is bootstrap fallback behavior acceptable for first runs?
4. ⚠️ Any concerns about using external action `dawidd6/action-download-artifact`?

**Once approved, I will**:
1. Make the changes to the workflow file
2. Commit with descriptive message
3. Push to current branch
4. Wait for your instruction to create PR or merge to main

---

**Ready to proceed? Please review and approve, or let me know if you have questions or want any changes.**

