# Remaining Smoke Test Fixes Proposal

## Summary

- **Goal:** Fix 4 remaining smoke test failures that are blocking GitHub Actions infrastructure validation
- **Scope:**
  - **In Scope:**
    - Fix `test_relative_vs_absolute_paths` 
    - Fix `test_special_characters_in_paths`
    - Fix `test_concurrent_access`
    - Fix `test_python_version_compatibility`
    - Ensure all tests align with hazelbean's actual NameError behavior
  - **Out of Scope:**
    - Changing hazelbean core behavior
    - Modifying exception types raised by hazelbean
    - Major test architecture changes
    
- **Assumptions/Constraints:**
  - Tests must adapt to hazelbean behavior, not vice versa [[memory:8070712]]
  - `get_path()` intentionally raises `NameError` for path resolution failures (established in exception-handling-analysis.md)
  - Tests should validate real-world usage patterns
  - Must pass in both local and CI environments

---

## Current State (What Exists)

### Relevant Files:
1. **`hazelbean_tests/system/test_smoke.py`** (518 lines)
   - **Lines 374-386:** `test_relative_vs_absolute_paths` - Expects get_path to work without files
   - **Lines 389-412:** `test_special_characters_in_paths` - Expects ValueError/OSError, gets NameError
   - **Lines 415-457:** `test_concurrent_access` - Expects get_path to work without files
   - **Lines 464-474:** `test_python_version_compatibility` - Expects get_path to work without files

2. **`hazelbean/project_flow.py`** (line 618)
   - Raises `NameError` when path cannot be resolved (intentional design)
   - Parameters: `raise_error_if_fail=True` (default), `leave_ref_path_if_fail=False`

3. **`docs/plans/exception-handling-analysis.md`**
   - Documents hazelbean's dual exception strategy
   - NameError for path resolution failures (277+ instances)
   - FileNotFoundError for simple file checks (17 instances)

### Current Test Results:
```
✅ 15/19 tests passing
❌ 4/19 tests failing:
   1. test_relative_vs_absolute_paths - NameError for missing file
   2. test_special_characters_in_paths - Wrong exception assertion
   3. test_concurrent_access - NameError for missing files
   4. test_python_version_compatibility - NameError for missing file
```

### Root Cause Analysis:

**All 4 tests share the same fundamental issue:**
- They call `get_path()` on non-existent files
- `get_path()` with default parameters requires files to exist
- Tests don't create files or use `raise_error_if_fail=False`

**Why This Matters for CI:**
- Infrastructure validation gate requires smoke tests to pass
- Failed smoke tests = `infra_status="failed"` 
- Workflow exits with code 1 (blocking)

---

## Options

### Option 1: Use raise_error_if_fail=False for Path Construction Tests (RECOMMENDED)

**Approach:** Tests that only need path construction (not validation) should use `raise_error_if_fail=False`

**Steps:**
1. Update `test_relative_vs_absolute_paths` to use `raise_error_if_fail=False`
2. Update `test_concurrent_access` to use `raise_error_if_fail=False`
3. Update `test_python_version_compatibility` to use `raise_error_if_fail=False`
4. Update `test_special_characters_in_paths` to accept NameError in exception assertion

**Pros:**
- Minimal changes (4-5 lines total)
- Tests validate path construction logic without file I/O
- Aligns with get_path's design (has flag for this exact use case)
- Fast - no file creation overhead
- Works in any environment (no file system dependencies)

**Cons:**
- Doesn't test full get_path behavior (file validation)
- Less realistic than creating actual files

**Code Changes:**
```python
# test_relative_vs_absolute_paths (line 380)
rel_path = p.get_path("relative_file.txt", raise_error_if_fail=False)

# test_concurrent_access (line 429)
path = p.get_path(f"thread_{thread_id}_file_{i}.txt", raise_error_if_fail=False)

# test_python_version_compatibility (line 473)
path = p.get_path("test.txt", raise_error_if_fail=False)

# test_special_characters_in_paths (line 412)
assert isinstance(e, (ValueError, OSError, NameError))
```

### Option 2: Create Files Before Testing (SELECTED) ✅

**Approach:** Create temporary files before calling get_path() to test full validation behavior

**Steps:**
1. Create files in test setup for each test
2. Keep existing get_path() calls (with default validation)
3. Update exception assertions to include NameError where needed

**Pros:**
- ✅ Tests full get_path behavior including file validation
- ✅ More realistic usage patterns (SELECTED FOR THIS REASON)
- ✅ Better integration testing
- ✅ Validates actual file system interactions

**Cons:**
- ⚠️ More code changes (~20-30 lines) - Acceptable tradeoff
- ⚠️ Slower tests (file I/O overhead) - Minimal impact
- ⚠️ More complex test setup - Worth it for realism
- ⚠️ Concurrent test needs file creation synchronization - Manageable

**Code Changes:**
```python
# test_relative_vs_absolute_paths
def test_relative_vs_absolute_paths(self):
    with tempfile.TemporaryDirectory() as temp_dir:
        p = hb.ProjectFlow(temp_dir)
        
        # Create test files
        rel_file = os.path.join(temp_dir, "relative_file.txt")
        with open(rel_file, 'w') as f:
            f.write("test")
        
        abs_file = os.path.join(temp_dir, "absolute_file.txt")
        with open(abs_file, 'w') as f:
            f.write("test")
        
        # Now test (existing code works)
        rel_path = p.get_path("relative_file.txt")
        ...
```

### Option 3: Mixed Approach (Test Both Modes)

**Approach:** Some tests use `raise_error_if_fail=False`, others create files

**Steps:**
1. Path construction tests → `raise_error_if_fail=False`
2. Path validation tests → create files
3. Error handling tests → verify NameError behavior

**Pros:**
- Tests both get_path modes
- More comprehensive coverage
- Each test uses appropriate pattern

**Cons:**
- Inconsistent approach across tests
- More complex to maintain

---

## Recommended Approach: Option 2 (Create Files Before Testing) - APPROVED

**User Decision:** Option 2 selected - create actual files to test full validation behavior.

### Why This Option (User's Reasoning):

1. **More Realistic Testing:**
   - Tests validate full get_path behavior including file validation
   - Real-world usage patterns (files actually exist)
   - Better integration testing of file system interactions
   - Validates complete path resolution → validation flow

2. **Comprehensive Coverage:**
   - Tests both path construction AND file existence validation
   - Catches issues in file lookup logic
   - Validates error messages when files truly missing
   - Better smoke test quality overall

3. **Worth The Tradeoff:**
   - ~20-30 line changes acceptable for better test quality
   - File I/O overhead minimal for smoke tests
   - More complex setup justified by realistic scenarios
   - Concurrent test synchronization manageable with proper setup

4. **Long-term Value:**
   - Future maintainers see realistic usage patterns
   - Tests serve as better documentation
   - Catches more potential issues
   - Sets better precedent for new tests

### Risk Assessment:

```
Option 1 (raise_error_if_fail=False):
✅ Very low risk - using existing API parameter
✅ Fast - 5 minute implementation
✅ Minimal changes - 4-5 lines
✅ Clear intent - path construction tests
✅ Environment independent

Option 2 (Create Files):
⚠️ Low-medium risk - more complex setup
⚠️ Slower - file I/O overhead
⚠️ More changes - 20-30 lines
⚠️ Environment dependent - file system

Option 3 (Mixed):
⚠️ Medium risk - inconsistent patterns
⚠️ Complex - different approaches per test
⚠️ Maintenance burden - harder to understand
```

### Estimated Impact (Option 2):

**Files Modified:** 1 file (test_smoke.py)
**Lines Changed:** ~25-30 lines
**Risk Level:** LOW
**Implementation Time:** 10-15 minutes
**Test Time Impact:** Minimal (slightly slower but more thorough)

---

## Core Proof Tests

**Intent:** Verify that the fixes resolve all 4 failing tests without breaking existing passing tests.

### Test 1: Fixed Tests Pass Locally (Happy Path)
**Trigger:** Run the 4 fixed tests locally
```bash
conda activate hazelbean_env
python -m pytest hazelbean_tests/system/test_smoke.py::TestSystemIntegration::test_relative_vs_absolute_paths \
  hazelbean_tests/system/test_smoke.py::TestSystemIntegration::test_special_characters_in_paths \
  hazelbean_tests/system/test_smoke.py::TestSystemIntegration::test_concurrent_access \
  hazelbean_tests/system/test_smoke.py::TestSystemEnvironment::test_python_version_compatibility \
  -v
```
**Expected Observable:** All 4 tests PASS

### Test 2: Full Smoke Suite Passes (Integration)
**Trigger:** Run complete smoke test suite
```bash
python -m pytest hazelbean_tests/system/test_smoke.py -v
```
**Expected Observable:** 19/19 tests PASS (no regressions)

### Test 3: CI Infrastructure Gate Passes (CI Validation)
**Trigger:** Push changes and monitor GitHub Actions workflow
**Expected Observable:**
- Infrastructure validation gate: ✅ PASSED
- `infra_status="passed"`
- Workflow completes successfully
- Quality gate summary shows all gates green

---

## Detailed Implementation Plan (Option 2 - APPROVED)

### Change 1: test_relative_vs_absolute_paths - Complete Rewrite

**New Implementation:**
```python
@pytest.mark.smoke
def test_relative_vs_absolute_paths(self):
    """Test handling of relative vs absolute paths with actual files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        p = hb.ProjectFlow(temp_dir)
        
        # Create test file for relative path testing
        rel_file = os.path.join(temp_dir, "relative_file.txt")
        with open(rel_file, 'w') as f:
            f.write("relative test content")
        
        # Test relative path
        rel_path = p.get_path("relative_file.txt")
        assert "relative_file.txt" in rel_path
        assert os.path.exists(rel_path)
        
        # Create test file for absolute path testing
        abs_file = os.path.join(temp_dir, "absolute_file.txt")
        with open(abs_file, 'w') as f:
            f.write("absolute test content")
        
        # Test absolute path
        abs_input = os.path.abspath(abs_file)
        abs_path = p.get_path(abs_input)
        assert "absolute_file.txt" in abs_path
        assert os.path.exists(abs_path)
```

**Rationale:** Tests full get_path behavior with real files, validates both path resolution and file existence

### Change 2: test_special_characters_in_paths - Create Files + Fix Exception

**Current Code:**
```python
except Exception as e:
    # Some special characters might not be supported
    # That's OK as long as we don't crash
    assert isinstance(e, (ValueError, OSError))
```

**Fixed Code:**
```python
except Exception as e:
    # Some special characters might not be supported
    # That's OK as long as we don't crash
    # NameError indicates path resolution failure (hazelbean's design)
    assert isinstance(e, (ValueError, OSError, NameError))
```

**Rationale:** Accept NameError as valid exception type (per hazelbean's design)

**Additionally - Create files for testing:**
```python
@pytest.mark.smoke
def test_special_characters_in_paths(self):
    """Test handling of special characters in file paths with actual files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        p = hb.ProjectFlow(temp_dir)
        
        # Test various special characters (that are valid in file names)
        special_files = [
            "file_with_underscores.txt",
            "file-with-hyphens.txt",
            "file.with.dots.txt",
            "file with spaces.txt",
            "file123numbers.txt",
            "UPPERCASE.TXT",
            "mixedCase.TxT"
        ]
        
        for special_file in special_files:
            # Create file with special characters
            file_path = os.path.join(temp_dir, special_file)
            try:
                with open(file_path, 'w') as f:
                    f.write(f"test content for {special_file}")
                
                # Test get_path with actual file
                path = p.get_path(special_file)
                assert special_file in path or os.path.basename(path) == special_file
                assert os.path.exists(path)
            except Exception as e:
                # Some special characters might not be supported on some systems
                # NameError indicates path resolution failure (hazelbean's design)
                assert isinstance(e, (ValueError, OSError, NameError))
```

### Change 3: test_concurrent_access - Create Files with Thread Safety

**New Implementation:**
```python
@pytest.mark.smoke
def test_concurrent_access(self):
    """Test basic concurrent access patterns with actual files"""
    import threading
    import time
    
    with tempfile.TemporaryDirectory() as temp_dir:
        p = hb.ProjectFlow(temp_dir)
        
        results = []
        errors = []
        
        # Pre-create all files before threads start (avoid race conditions)
        for thread_id in range(3):
            for i in range(10):
                file_path = os.path.join(temp_dir, f"thread_{thread_id}_file_{i}.txt")
                with open(file_path, 'w') as f:
                    f.write(f"Thread {thread_id} file {i}")
        
        def worker_thread(thread_id):
            try:
                for i in range(10):
                    path = p.get_path(f"thread_{thread_id}_file_{i}.txt")
                    results.append((thread_id, path))
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append((thread_id, e))
        
        # Create and start threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=worker_thread, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors in concurrent access: {errors}"
        assert len(results) == 30, f"Expected 30 results, got {len(results)}"
        
        # Verify all paths exist and are unique per thread
        thread_paths = {}
        for thread_id, path in results:
            assert os.path.exists(path), f"Path {path} doesn't exist"
            if thread_id not in thread_paths:
                thread_paths[thread_id] = []
            thread_paths[thread_id].append(path)
        
        assert len(thread_paths) == 3, "Should have results from all 3 threads"
```

**Rationale:** Tests thread safety with real files, validates concurrent file system access patterns

### Change 4: test_python_version_compatibility - Create File

**New Implementation:**
```python
@pytest.mark.smoke
def test_python_version_compatibility(self):
    """Test Python version compatibility with actual file"""
    import sys
    
    # Should work with Python 3.7+
    assert sys.version_info >= (3, 7), f"Python version {sys.version_info} may not be supported"
    
    # Test that hazelbean works with current Python version
    with tempfile.TemporaryDirectory() as temp_dir:
        p = hb.ProjectFlow(temp_dir)
        
        # Create test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Python version compatibility test")
        
        # Test basic get_path functionality
        path = p.get_path("test.txt")
        assert path is not None
        assert os.path.exists(path)
```

**Rationale:** Tests API compatibility with real file operations

---

## Validation Steps

### Local Validation (Pre-Push):

```bash
# Step 1: Activate environment
conda activate hazelbean_env

# Step 2: Test the 4 fixed tests
python -m pytest hazelbean_tests/system/test_smoke.py::TestSystemIntegration::test_relative_vs_absolute_paths -v
python -m pytest hazelbean_tests/system/test_smoke.py::TestSystemIntegration::test_special_characters_in_paths -v
python -m pytest hazelbean_tests/system/test_smoke.py::TestSystemIntegration::test_concurrent_access -v
python -m pytest hazelbean_tests/system/test_smoke.py::TestSystemEnvironment::test_python_version_compatibility -v

# Step 3: Run full smoke suite
python -m pytest hazelbean_tests/system/test_smoke.py -v

# Step 4: Verify no regressions in other test categories
python -m pytest hazelbean_tests/unit/test_get_path.py -v

# Expected: All tests PASS
```

### CI Validation (Post-Push):

```bash
# Push changes
git add hazelbean_tests/system/test_smoke.py
git commit -m "fix: Align remaining smoke tests with hazelbean NameError behavior

- Use raise_error_if_fail=False for path construction tests
- Accept NameError in special characters test exception assertion
- Tests now validate path construction logic without file I/O
- Fixes 4 remaining smoke test failures blocking CI infrastructure gate

Related: docs/plans/exception-handling-analysis.md"
git push origin feature/test-infra

# Monitor GitHub Actions
# Expected:
# ✅ Infrastructure validation (Gate 1): PASSED
# ✅ Core functionality (Gate 2): PASSED  
# ✅ Integration testing (Gate 3): COMPLETED
# ✅ Quality gate summary: SUCCESS
```

---

## Risks & Mitigation

### Risk 1: Tests No Longer Validate File Existence
**Likelihood:** N/A (intentional)  
**Impact:** Low  
**Mitigation:**
- These tests were never designed to validate file existence
- They validate path construction logic
- File validation is tested in other tests (test_projectflow_basic_functionality, test_get_path_generates_doc, etc.)
- If needed, add separate file validation tests later

### Risk 2: False Positives (Tests Pass But Logic Broken)
**Likelihood:** Very Low  
**Impact:** Medium  
**Mitigation:**
- Tests still validate path string construction
- Tests verify expected path components are present
- Integration tests validate full file I/O behavior
- CI runs multiple test suites (unit, integration, system)

### Risk 3: Concurrent Test Doesn't Catch File I/O Race Conditions
**Likelihood:** Low  
**Impact:** Low  
**Mitigation:**
- Test's intent is thread-safe path **construction**, not file I/O
- File I/O race conditions are better tested in integration tests
- Current test design (no files) actually eliminates file system race conditions
- More focused test = clearer intent

### Risk 4: CI Still Fails Due to Other Issues
**Likelihood:** Low  
**Impact:** High  
**Mitigation:**
- All pytest plugins now installed (pytest-benchmark, pytest-cov)
- Micromamba versions updated (@v1 → @v2)
- Exception handling aligned across all tests
- Local validation confirms tests pass
- If CI still fails, logs will show new specific issue

---

## Alternatives Considered

### Alternative 1: Delete These 4 Tests
**Rejected because:**
- Tests validate useful behavior (path construction patterns)
- Smoke test coverage would decrease
- Simple fix available (Option 1)
- Would set bad precedent (delete tests when they fail)

### Alternative 2: Mock get_path() to Return Fake Paths
**Rejected because:**
- Doesn't test real get_path behavior
- Adds complexity (mocking infrastructure)
- Option 1 uses real API with appropriate parameter
- Mocking should be last resort

### Alternative 3: Make All Tests Use leave_ref_path_if_fail=True
**Rejected because:**
- `leave_ref_path_if_fail` returns input unchanged (different semantics)
- Doesn't test path resolution logic
- `raise_error_if_fail=False` is more appropriate (returns constructed path)

### Alternative 4: Skip These Tests in CI
**Rejected because:**
- Hides problems rather than fixing them
- Reduces test coverage
- Easy fix available
- Violates project conventions (fix tests, don't skip them)

---

## Success Criteria

### Immediate Success (Within 1 CI Run):
1. ✅ All 4 fixed tests pass locally
2. ✅ Full smoke suite (19/19) passes locally
3. ✅ Infrastructure validation gate passes in CI
4. ✅ `infra_status="passed"` in workflow
5. ✅ No regression in other test categories

### Short-term Success (Within 1 Week):
1. ✅ CI runs consistently green on feature branch
2. ✅ Quality gate summary shows all gates passing
3. ✅ No smoke test failures in subsequent PRs
4. ✅ Documentation explains path construction vs. validation testing

### Long-term Success (Ongoing):
1. ✅ Future tests follow correct pattern (use raise_error_if_fail appropriately)
2. ✅ Exception handling documentation prevents similar issues
3. ✅ Test intent is clear from test names and comments

---

## Rollback Plan

**If Issues Occur:**

1. **Immediate rollback:**
   ```bash
   git revert <commit-hash>
   git push origin feature/test-infra
   ```

2. **Selective revert:**
   ```bash
   # Revert just test_smoke.py
   git checkout HEAD~1 hazelbean_tests/system/test_smoke.py
   git commit -m "Revert smoke test changes"
   git push origin feature/test-infra
   ```

3. **Alternative fix:**
   - Can switch to Option 2 (create files) if Option 1 proves insufficient
   - Can disable specific tests temporarily while investigating
   - Can add more detailed logging to understand failures

**Rollback Confidence:** HIGH
- Changes are isolated to one file
- Only 4-5 lines modified
- No dependency changes
- No workflow changes

---

## Post-Implementation Documentation

### Update exception-handling-analysis.md

Add section on test patterns:

```markdown
## Test Patterns for get_path()

### Path Construction Tests
When testing path construction logic (not file validation):
```python
path = p.get_path("file.txt", raise_error_if_fail=False)
assert "file.txt" in path
```

### Path Validation Tests  
When testing file existence validation:
```python
# Create file first
with open(os.path.join(temp_dir, "file.txt"), 'w') as f:
    f.write("content")

path = p.get_path("file.txt")  # Will validate file exists
assert os.path.exists(path)
```

### Error Handling Tests
When testing exception behavior:
```python
with pytest.raises(NameError) as exc_info:
    path = p.get_path("missing.txt")  # raise_error_if_fail=True by default

assert "does not exist" in str(exc_info.value)
```
```

---

## Questions for Clarification

**None** - The issue is clear:
1. Tests call get_path() without files
2. get_path() raises NameError (by design)
3. Tests need to either create files OR use raise_error_if_fail=False
4. Option 1 is simpler, faster, and aligns with test intent

Ready to implement upon approval.

---

## Timeline

**Total Estimated Time: 15 minutes (Option 2)**

- Implementation: 10 minutes (~25-30 line changes)
- Local validation: 3 minutes (run test suite)
- Documentation: 2 minutes (update comments)
- Push and monitor: Immediate

**Blocking/Non-Blocking:**
- Can implement all changes sequentially
- Local validation before push
- CI validation after push (5-10 minutes)

---

## ✅ APPROVED - OPTION 2 SELECTED

**User Decision:** Proceed with Option 2 (Create Files Before Testing)

**Rationale:** More realistic testing with actual files provides better validation of full get_path behavior including file system interactions. Worth the additional complexity for higher quality smoke tests.

**Status:** Ready for implementation

This proposal follows the pre-implementation protocol and provides a realistic testing solution to unblock CI.

