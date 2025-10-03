# GitHub Actions Quality Gates Fix Proposal

## Summary

- **Goal:** Fix failing GitHub Actions quality gate workflows due to:
  1. Missing pytest plugins (pytest-benchmark, pytest-cov) in environment
  2. Incorrect exception type expectations in smoke tests (expecting FileNotFoundError but getting NameError)
  3. Workflow references to non-existent or incompatible test structure
  
- **Scope:**
  - **In Scope:** 
    - Add missing pytest plugins to environment.yml
    - Fix exception type assertions in test_smoke.py to match actual hazelbean behavior
    - Update workflow test paths to match current test structure
    - Verify workflow configuration matches current codebase state
  - **Out of Scope:**
    - Changing hazelbean's core exception handling behavior (NameError is intentional design)
    - Major workflow architecture changes
    - Performance optimization beyond fixing regressions
  
- **Assumptions/Constraints:**
  - Tests should adapt to hazelbean's actual behavior, not modify hazelbean to match test expectations [[memory:8070712]]
  - Conda environment must be activated for all development tasks [[memory:7783594]]
  - Packages should be installed via conda/mamba, not pip [[memory:7779366]]
  - Minimal changes preferred - fix specific issues, don't rebuild entire system (learned from micromamba v1→v2 fix)

---

## Current State (What Exists)

### Relevant Files/Modules:

1. **`.github/workflows/testing-quality-gates.yml`** (337 lines)
   - Implements 4-gate quality system: Infrastructure → Core → Integration → Performance
   - Uses mamba-org/setup-micromamba@v1 with environment.yml
   - References test paths that may not match current structure
   - Missing pytest plugin dependencies

2. **`.github/workflows/deploy-docs.yml`** (178 lines)
   - Deploys MkDocs documentation to GitHub Pages
   - Also uses environment.yml setup
   - Calls `tools/generate_complete_site.sh`
   - Currently works but may be affected by environment issues

3. **`.github/workflows/build-python.yml`** (91 lines)
   - Builds wheels for PyPI distribution
   - Uses mamba-org/setup-micromamba@v2 (correct version per previous fix)
   - Matrix builds across OS and Python versions
   - NOT affected by current issues

4. **`hazelbean_tests/system/test_smoke.py`** (498 lines)
   - Comprehensive smoke tests with documentation generation
   - **Line 139:** Expects `(FileNotFoundError, ValueError, RuntimeError)` but hazelbean raises `NameError`
   - Multiple test classes covering basic, documentation, system integration, and environment tests
   - Uses Google API stubs for testing without cloud dependencies

5. **`hazelbean/project_flow.py`** (~1400 lines)
   - **Line 618:** Explicitly raises `NameError` when path doesn't exist
   - This is intentional design, not a bug
   - Used consistently throughout ProjectFlow.get_path()

6. **`environment.yml`** (44 dependencies)
   - Contains core dependencies (geopandas, rasterstats, etc.)
   - **Missing:** pytest-benchmark, pytest-cov (needed by workflow)
   - Has basic pytest but not plugins

### Reusable Utilities/Patterns:

1. **Previous micromamba fix pattern** (docs/github-actions-research-and-fix-documentation.md)
   - Demonstrates: Research first, minimal changes, version-aware fixes
   - Lesson: Update versions before architectural changes
   - Success: 15-minute fix vs. multi-hour migration

2. **Workflow structure**
   - Good pattern: Progressive quality gates with dependencies
   - Good pattern: Separate jobs that can fail independently
   - Good pattern: Comprehensive status reporting

3. **Test organization**
   - `hazelbean_tests/unit/` - Core functionality tests
   - `hazelbean_tests/integration/` - Integration tests
   - `hazelbean_tests/system/` - System-level smoke tests
   - `hazelbean_tests/performance/` - Performance benchmarks

### Gaps:

1. **Environment configuration:**
   - Missing pytest-benchmark (required by test_smoke.py line 72)
   - Missing pytest-cov (required by workflow line 138)
   - Missing mkdocs plugins (may be needed for docs workflow)

2. **Test expectations vs. reality:**
   - Tests expect FileNotFoundError for missing paths
   - Hazelbean intentionally raises NameError (more specific semantic meaning)
   - This mismatch causes test failures in CI

3. **Workflow-codebase alignment:**
   - Workflow may reference old test paths
   - Core functionality matrix tests reference: get_path, tile_iterator, add_task, add_iterator
   - Need to verify these test files exist and are runnable

4. **Micromamba version consistency:**
   - testing-quality-gates.yml uses @v1 (has known issues)
   - build-python.yml uses @v2 (correct)
   - deploy-docs.yml uses @v1 (should be updated)

---

## Options

### Option 1: Minimal Fix - Update Tests & Environment (RECOMMENDED)

**Approach:** Fix the specific issues without changing hazelbean or workflow structure

**Steps:**
1. Add missing pytest plugins to environment.yml
2. Update exception type assertions in test_smoke.py to include NameError
3. Update micromamba action versions from @v1 to @v2 in testing-quality-gates.yml and deploy-docs.yml
4. Verify test file paths referenced in workflow exist
5. Run smoke tests locally to validate fixes

**Pros:**
- Minimal code changes (follows learned pattern from micromamba fix)
- Tests align with actual hazelbean behavior (correct approach per memory)
- Low risk - only fixing specific broken pieces
- Fast implementation (~30 minutes)
- Easy rollback if issues occur
- Respects hazelbean's intentional design decisions

**Cons:**
- Doesn't improve overall test quality
- May reveal other test issues once smoke tests pass
- Requires careful verification of all test paths

**Files Modified:**
- environment.yml (add 2-3 dependencies)
- hazelbean_tests/system/test_smoke.py (update 1 line for exception types)
- .github/workflows/testing-quality-gates.yml (version bump)
- .github/workflows/deploy-docs.yml (version bump)

### Option 2: Comprehensive Workflow Audit & Modernization

**Approach:** Review and update entire workflow system while fixing issues

**Steps:**
1. Complete audit of all workflow files
2. Standardize micromamba configuration across all workflows
3. Add comprehensive test discovery and validation
4. Implement workflow-level test verification
5. Add pre-commit hooks for workflow validation
6. Update all test references with path verification
7. Add exception type testing throughout test suite

**Pros:**
- Ensures all workflows are consistent and modern
- Catches potential future issues
- Comprehensive documentation of workflow behavior
- Better long-term maintainability

**Cons:**
- **Over-engineering for a specific problem** (red flag from previous lesson)
- 2-3 hours implementation vs. 30 minutes
- Higher risk of introducing new issues
- Changes working parts of the system unnecessarily
- May not be the root cause of current failures

**Files Modified:**
- All workflow files
- Multiple test files
- New pre-commit configuration
- New workflow validation scripts

### Option 3: Fix Exception Handling in Hazelbean (NOT RECOMMENDED)

**Approach:** Change hazelbean to raise FileNotFoundError instead of NameError

**Steps:**
1. Update hazelbean/project_flow.py line 618 to raise FileNotFoundError
2. Search for all other NameError raises in get_path logic
3. Update to FileNotFoundError consistently
4. Run full test suite to verify no breaking changes

**Pros:**
- Tests wouldn't need updating
- More "Pythonic" exception type (FileNotFoundError is standard library)

**Cons:**
- **VIOLATES memory [8070712]:** "prefer not to modify existing code in hazelbean environment when tests fail"
- NameError is intentionally more specific (path resolution vs. file existence)
- Changes production code to fix test expectations (wrong direction)
- May have unexpected impacts on dependent code
- Tests should adapt to code behavior, not vice versa

---

## Recommended Approach: Option 1 (Minimal Fix)

### Why This Option:

1. **Follows Proven Pattern:**
   - Previous micromamba fix: version bump + minimal config = success
   - Same principle: fix specific issues, don't rebuild system
   - Lesson learned: "Sometimes the right answer is just updating a version number"

2. **Respects Project Conventions:**
   - Memory [8070712]: Don't modify hazelbean when tests fail
   - Memory [7779366]: Use conda/mamba for package installation
   - NameError in get_path() is intentional semantic design (path resolution error vs. file not existing)

3. **Root Cause Resolution:**
   - Missing dependencies → Add to environment.yml
   - Wrong exception expectations → Update test assertions
   - Outdated action versions → Bump to v2 (proven fix)
   - Wrong test paths → Verify and correct

4. **Risk Assessment:**
   ```
   Minimal Fix:
   ✅ Low risk - surgical changes to broken pieces
   ✅ Fast - ~30 minute implementation
   ✅ Proven pattern from previous success
   ✅ Easy validation - run tests locally first
   ✅ Simple rollback if needed
   
   Comprehensive Audit:
   ⚠️ Medium risk - changes working parts
   ⚠️ Slow - 2-3 hour implementation
   ⚠️ May introduce new issues
   ⚠️ Over-engineering for specific problem
   
   Change Hazelbean:
   ❌ High risk - changes production code
   ❌ Wrong direction - code should drive tests
   ❌ Violates project memory/conventions
   ```

### Estimated Impact:

**Modules Touched:**
- environment.yml (1 file, +3-5 lines)
- test_smoke.py (1 file, 1 line change)
- testing-quality-gates.yml (1 file, 2 lines)
- deploy-docs.yml (1 file, 1 line)

**Risk Level:** LOW
- Only fixing specific broken functionality
- Not changing architecture or working systems
- Follows proven fix pattern from previous issues
- Changes are isolated and reversible

---

## Core Proof Tests (3 tests)

**Intent:** Prove that the fixes resolve the CI failures without breaking existing functionality.

### Test 1: Environment Setup (Happy Path)
**Trigger:** Create fresh conda environment from updated environment.yml  
**Expected Observable:**
```bash
conda env create -f environment.yml -n test_env
conda activate test_env
python -c "import pytest_benchmark; import pytest_cov; print('✅ Plugins available')"
# Expected output: ✅ Plugins available (no import errors)
```

### Test 2: Smoke Test Exception Handling (Edge/Validation)
**Trigger:** Run smoke tests locally with fixed exception assertions  
**Expected Observable:**
```bash
conda activate hazelbean_env
python -m pytest hazelbean_tests/system/test_smoke.py::TestBasicSmokeTests::test_basic_error_handling -v
# Expected: PASSED (accepts NameError as valid exception)
```

### Test 3: CI Workflow Integration (Interface)
**Trigger:** Push changes to feature branch and run GitHub Actions  
**Expected Observable:**
- Infrastructure validation (Gate 1): ✅ PASSED
- Core functionality tests (Gate 2): ✅ PASSED or properly identified failures
- Quality gate summary: Shows accurate status of all gates
- No ImportError for pytest plugins
- No NameError assertion failures in smoke tests

**How to run locally:**
```bash
# Activate environment
conda activate hazelbean_env

# Test 1: Environment validation
conda list | grep pytest-benchmark
conda list | grep pytest-cov

# Test 2: Smoke tests
python -m pytest hazelbean_tests/system/test_smoke.py -v --tb=short

# Test 3: Full infrastructure gate simulation
python -m pytest hazelbean_tests/system/test_smoke.py -v --tb=short
python -m pytest hazelbean_tests/unit/test_get_path.py -v --cov=hazelbean --cov-report=term-missing

# Test 4: Verify no NameError assertion failures
python -m pytest hazelbean_tests/system/test_smoke.py -k "error_handling" -v
```

---

## Implementation Plan (Detailed)

### Phase 1: Environment Dependencies (5 minutes)

**File:** `environment.yml`

Add after line 40 (after pytest):
```yaml
  - pytest
  - pytest-benchmark  # Required for performance smoke tests
  - pytest-cov        # Required for coverage reporting in workflows
  - mkdocs            # Required for documentation generation
  - mkdocs-material   # Material theme for documentation
```

**Validation:**
```bash
conda env update -f environment.yml -n hazelbean_env
conda list | grep pytest-
# Should show: pytest, pytest-benchmark, pytest-cov
```

### Phase 2: Fix Exception Type Expectations (2 minutes)

**File:** `hazelbean_tests/system/test_smoke.py`

**Line 139:** Update exception type assertion
```python
# Before:
assert isinstance(e, (FileNotFoundError, ValueError, RuntimeError))

# After:
assert isinstance(e, (FileNotFoundError, ValueError, RuntimeError, NameError))
```

**Rationale:** 
- Hazelbean uses **dual exception strategy** (see docs/plans/exception-handling-analysis.md):
  - `FileNotFoundError`: Simple "file at path X doesn't exist" (17 instances)
  - `NameError`: Complex "path/name resolution failed" (277+ instances)
- `get_path()` intentionally raises NameError because it's more than file existence check:
  - Resolves paths relative to project structure
  - Searches multiple possible_dirs
  - Attempts cloud bucket downloads
  - "Name resolution failed" is semantically more accurate than "file not found"
- This is consistent, intentional design across hazelbean (not a bug or regression)
- Test should validate exception is reasonable, not dictate implementation
- Verified safe: No other tests depend on FileNotFoundError from get_path()

**Validation:**
```bash
python -m pytest hazelbean_tests/system/test_smoke.py::TestBasicSmokeTests::test_basic_error_handling -v
# Expected: PASSED
```

### Phase 3: Update Micromamba Versions (5 minutes)

**File:** `.github/workflows/testing-quality-gates.yml`

**Lines 71-77:** Update infrastructure validation setup
```yaml
# Before:
- name: Setup Mambaforge with hazelbean_env
  uses: mamba-org/setup-micromamba@v1
  with:
    environment-file: environment.yml
    environment-name: hazelbean_env
    cache-environment: true
    init-shell: bash

# After:
- name: Setup Mambaforge with hazelbean_env
  uses: mamba-org/setup-micromamba@v2  # v2 has macOS fixes and better caching
  with:
    environment-file: environment.yml
    environment-name: hazelbean_env
    cache-environment: true
    cache-downloads: true  # Additional v2 feature
    init-shell: bash
```

**Lines 123-128:** Update core functionality setup (same change)

**File:** `.github/workflows/deploy-docs.yml`

**Lines 54-60:** Update documentation deployment setup (same change)

**Rationale:**
- v2 fixes known macOS issues (per previous research doc)
- Adds built-in download caching for faster builds
- Proven fix from previous micromamba issue

### Phase 4: Verify Test Path References (10 minutes)

**Workflow References to Verify:**

1. **Line 94:** `hazelbean_tests/system/test_smoke.py` ✅ EXISTS (verified)
2. **Line 136:** `hazelbean_tests/unit/test_${{ matrix.test-category }}.py`
   - ✅ test_get_path.py EXISTS (verified)
   - ✅ test_tile_iterator.py EXISTS (verified)
   - ✅ test_add_task.py EXISTS (verified)
   - ✅ test_add_iterator.py EXISTS (verified)

**Verification Results:**
All test files referenced in the workflow matrix exist in `hazelbean_tests/unit/`:
```
✅ unit/test_get_path.py
✅ unit/test_tile_iterator.py
✅ unit/test_add_task.py
✅ unit/test_add_iterator.py
```

**Local Validation Commands:**
```bash
# Verify tests are runnable and can be collected
python -m pytest hazelbean_tests/unit/test_get_path.py --collect-only
python -m pytest hazelbean_tests/unit/test_tile_iterator.py --collect-only
python -m pytest hazelbean_tests/unit/test_add_task.py --collect-only
python -m pytest hazelbean_tests/unit/test_add_iterator.py --collect-only
```

**Action Required:**
- ✅ No workflow test path changes needed - all referenced files exist
- Focus only on environment dependencies and exception type fixes

### Phase 5: Local Validation (10 minutes)

**Complete Validation Sequence:**
```bash
# 1. Update environment
conda env update -f environment.yml -n hazelbean_env
conda activate hazelbean_env

# 2. Verify pytest plugins
python -c "import pytest_benchmark; import pytest_cov; print('✅ Plugins OK')"

# 3. Run smoke tests
python -m pytest hazelbean_tests/system/test_smoke.py -v --tb=short

# 4. Run core functionality tests (if files exist)
python -m pytest hazelbean_tests/unit/test_get_path.py -v --cov=hazelbean

# 5. Simulate infrastructure gate
timeout 300 python -m pytest hazelbean_tests/system/test_smoke.py -v --tb=short

# 6. Check for remaining issues
python -m pytest hazelbean_tests/ --collect-only | grep ERROR
```

**Success Criteria:**
- ✅ All pytest plugins import successfully
- ✅ Smoke tests pass without NameError assertion failures
- ✅ Core functionality tests can be collected and run
- ✅ No import errors or missing dependencies

---

## Risks & Mitigation

### Risk 1: Additional Hidden Test Issues
**Likelihood:** Medium  
**Impact:** Medium  
**Symptom:** Smoke tests pass but core/integration tests fail

**Mitigation:**
- Run full test suite locally before pushing
- Use `--collect-only` to verify test discovery
- Check KNOWN_BUGS.md for documented issues
- Quality gates are designed to fail gracefully - integration issues don't block infrastructure validation

### Risk 2: Environment Dependency Conflicts
**Likelihood:** Low  
**Impact:** Medium  
**Symptom:** Conda cannot resolve environment after adding pytest plugins

**Mitigation:**
- pytest-benchmark and pytest-cov are well-established plugins
- Already used in many conda environments
- If conflicts occur, can specify versions explicitly
- Easy rollback via git

### Risk 3: Workflow Still References Non-Existent Tests
**Likelihood:** Medium  
**Impact:** High  
**Symptom:** Core functionality gate fails due to missing test files

**Mitigation:**
- Phase 4 explicitly verifies test file existence
- Can update matrix to use existing test files
- Alternative: Skip non-existent tests temporarily while fixing

### Risk 4: NameError Is Raised Elsewhere in Tests
**Likelihood:** Low  
**Impact:** Low  
**Symptom:** Other tests fail with unexpected NameError

**Mitigation:**
- Only updating one specific assertion in test_smoke.py
- Other tests may have correct exception expectations already
- Can search codebase for other similar assertions: `grep -r "FileNotFoundError.*ValueError.*RuntimeError" hazelbean_tests/`

---

## Alternatives Considered

### Alternative 1: Fix Only Environment, Leave Tests Failing
**Rejected because:** 
- Doesn't resolve the core issue (wrong exception expectations)
- Smoke tests would continue to fail in CI
- Incomplete fix leaves system in broken state

### Alternative 2: Disable Smoke Tests in CI
**Rejected because:**
- Hides real issues rather than fixing them
- Reduces test coverage and confidence
- Smoke tests are valuable for infrastructure validation

### Alternative 3: Make NameError Optional in ProjectFlow
**Rejected because:**
- Adds complexity to production code for test convenience
- NameError is intentional semantic choice
- Tests should adapt to code, not vice versa

### Alternative 4: Use Pytest Fixtures to Mock Exceptions
**Rejected because:**
- Over-engineers a simple assertion fix
- Adds test complexity without benefit
- The exception is real, not mocked behavior

---

## Success Criteria

### Immediate Success (Within 1 CI Run):
1. ✅ Infrastructure validation (Gate 1) passes
2. ✅ No ImportError for pytest-benchmark or pytest-cov
3. ✅ No NameError assertion failures in smoke tests
4. ✅ Quality gate summary generates correctly

### Short-term Success (Within 1 Week):
1. ✅ Core functionality tests run successfully (or fail for correct reasons)
2. ✅ Integration tests complete (with known acceptable failures)
3. ✅ Performance regression tests execute
4. ✅ Documentation deployment works

### Long-term Success (Ongoing):
1. ✅ CI remains stable without workflow-related failures
2. ✅ New tests added follow correct exception expectations
3. ✅ Environment dependencies stay current
4. ✅ Quality gates continue to provide meaningful feedback

---

## Rollback Plan

**If Issues Occur:**

1. **Immediate rollback:**
   ```bash
   git revert <commit-hash>
   git push origin feature/test-infra
   ```

2. **Partial rollback options:**
   - Revert environment.yml only: `git checkout HEAD~1 environment.yml`
   - Revert test changes only: `git checkout HEAD~1 hazelbean_tests/system/test_smoke.py`
   - Revert workflow changes only: `git checkout HEAD~1 .github/workflows/`

3. **Emergency bypass:**
   - Temporarily disable failing quality gates in workflow
   - Add `if: false` to problematic job
   - Investigate and fix properly before re-enabling

**Rollback Testing:**
- Each component can be rolled back independently
- Changes are isolated and don't have cascading dependencies
- Git history provides clear revert points

---

## Questions for Clarification

### Before Implementation:

1. **Test File Verification:** Should I proceed with updating the workflow if some test files in the matrix don't exist, or should I first create missing test files?

2. **Exception Type Philosophy:** Is there a reason hazelbean uses NameError for path resolution failures instead of FileNotFoundError? Should this be documented?

3. **Workflow Coverage:** Should I also check and potentially fix the deploy-docs.yml workflow, or focus only on testing-quality-gates.yml?

4. **Environment Recreation:** Should I test with a completely fresh conda environment, or is updating the existing hazelbean_env sufficient?

5. **Known Issues:** Should I review KNOWN_BUGS.md before proceeding to avoid fixing tests that are expected to fail?

---

## Timeline

**Total Estimated Time: 30-40 minutes**

- Phase 1 (Environment): 5 minutes
- Phase 2 (Test fixes): 2 minutes  
- Phase 3 (Workflow updates): 5 minutes
- Phase 4 (Path verification): 10 minutes
- Phase 5 (Local validation): 10 minutes
- Documentation: 5 minutes

**Blocking/Non-Blocking:**
- All phases must complete sequentially
- Local validation must pass before pushing to GitHub
- CI validation occurs after push (additional 5-10 minutes)

---

## Post-Implementation Tasks

### Immediate (Same Session):
1. ✅ Push changes to feature branch
2. ✅ Monitor GitHub Actions run
3. ✅ Verify all quality gates complete
4. ✅ Review quality gate summary output

### Follow-up (Next Session):
1. 📋 Document exception type conventions in project guidelines
2. 📋 Add pre-commit check for pytest plugin imports
3. 📋 Review and update KNOWN_BUGS.md if issues are resolved
4. 📋 Consider adding exception type tests to unit test suite

### Optional Improvements (Future):
1. 💡 Add workflow validation script to verify test paths before CI runs
2. 💡 Create developer documentation for quality gate system
3. 💡 Add badge to README showing quality gate status
4. 💡 Implement notification system for quality gate failures

---

## References

### Documentation:
- Previous fix: `docs/github-actions-research-and-fix-documentation.md`
- Known issues: `hazelbean_tests/KNOWN_BUGS.md`
- Performance guide: `docs/performance-benchmarking-guide.md`

### Related Memories:
- [8070712]: Don't modify hazelbean when tests fail
- [7779366]: Use conda/mamba for package installation
- [7783594]: Activate conda environment before commands

### External Resources:
- mamba-org/setup-micromamba@v2 documentation
- pytest-benchmark documentation
- pytest-cov documentation
- GitHub Actions quality gate patterns

---

## Approval Checklist

Before implementation, confirm:

- [ ] Approach follows minimal change principle
- [ ] Respects project conventions and memories
- [ ] Risks are identified and mitigated
- [ ] Success criteria are measurable
- [ ] Rollback plan is clear and tested
- [ ] Timeline is realistic
- [ ] Questions are answered or deferred appropriately

**AWAITING APPROVAL: Please review and respond with "APPROVED" or provide feedback.**

