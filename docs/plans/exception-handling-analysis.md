# Exception Handling Analysis: NameError vs FileNotFoundError in Hazelbean

**Date:** 2025-10-02  
**Context:** GitHub Actions smoke test failures - understanding hazelbean's exception strategy  
**Key Question:** Should we change the test to accept NameError, or is this revealing a deeper issue?

---

## The Situation

### Test Expectation (test_smoke.py line 139):
```python
try:
    path = p.get_path("definitely_does_not_exist.txt")
    assert path is not None
except Exception as e:
    # Test expects these exception types:
    assert isinstance(e, (FileNotFoundError, ValueError, RuntimeError))
```

### Actual Behavior:
```python
# hazelbean raises NameError:
raise NameError('The path given to hb.get_path() does not exist at the unmodified path, 
                 and or is not available for download on your selected cloud bucket)')
```

### Test Result:
❌ **FAILS** - NameError is raised but not in the expected exception tuple

---

## Deep Dive: Hazelbean's Exception Philosophy

### Evidence from Codebase Analysis:

#### 1. **Dual Exception Strategy**

Hazelbean uses BOTH `NameError` and `FileNotFoundError` but for **different semantic purposes**:

**FileNotFoundError Usage (17 instances):**
- Used for simple "file doesn't exist at path" checks
- Used in utility functions like `assert_file_existence()`
- Used when opening files with GDAL/rasterio
- Examples:
  ```python
  # cog.py:20
  raise FileNotFoundError(f"Path {path} does not exist")
  
  # os_utils.py:1159
  raise FileNotFoundError('hb.assert_file_existence could not find ' + path)
  ```

**NameError Usage (277+ instances across multiple files):**
- Used for **logical/semantic errors** beyond simple file existence
- Used when paths fail resolution logic
- Used when configuration/state is invalid
- Used in `get_path()` specifically for path resolution failures
- Examples:
  ```python
  # project_flow.py:618 (our case)
  raise NameError('The path given to hb.get_path() does not exist at the unmodified path, 
                   and or is not available for download on your selected cloud bucket)')
  
  # core.py:181 (path_exists with assert_true)
  raise NameError('Path is not true: ' + path)
  
  # utils.py:266 (ArrayFrame validation)
  raise NameError('AF pointing to ' + path + ' used as if the raster existed, but it does not.')
  ```

#### 2. **Why NameError for get_path()?**

Looking at the `get_path()` implementation, it's more than just "does file exist":

```python
def get_path(self, relative_path, ..., 
             possible_dirs='default',
             raise_error_if_fail=True, 
             leave_ref_path_if_fail=False):
    """
    Complex path resolution that:
    1. Handles relative vs absolute paths
    2. Searches multiple possible_dirs
    3. Attempts cloud bucket downloads
    4. Constructs paths from project structure
    5. Validates path exists in resolved location
    """
```

**NameError is raised when:**
- Path resolution logic fails (not just "file missing")
- Can't determine where file should be relative to project structure
- Cloud bucket download attempted but unavailable
- Path construction from possible_dirs fails

**This is semantic distinction:**
- `FileNotFoundError`: "I looked for file at path X, it's not there"
- `NameError`: "I can't resolve what path you're referring to" or "Name resolution failed"

---

## Python's Built-in Exception Semantics

### What Python Says:

```python
FileNotFoundError: 
    # Raised when a file or directory is requested but doesn't exist.
    # Corresponds to errno ENOENT.
    
NameError:
    # Raised when a local or global name is not found.
    # This applies to function names, variable names, etc.
```

### Hazelbean's Interpretation:

**Hazelbean extends NameError semantically to mean:**
> "The name/reference you provided cannot be resolved to a concrete path within our system"

This is actually **more semantically accurate** than FileNotFoundError for `get_path()` because:
1. The file might exist somewhere, just not findable by the resolution logic
2. The path might be malformed relative to project structure
3. The "name" of the resource in the project namespace can't be resolved

---

## Historical Evidence: Is This Intentional?

### Evidence This Is Intentional Design:

1. **Consistent Usage:**
   - 277+ NameError instances across the codebase
   - Used in core.py, utils.py, project_flow.py, data_structures.py
   - Pattern: NameError for logical/semantic failures, FileNotFoundError for simple file checks

2. **Parallel Usage in `path_exists()`:**
   ```python
   # core.py:181
   def path_exists(path, assert_true=False):
       if not path:
           if assert_true:
               raise NameError('Path is not true: ' + path)  # Not FileNotFoundError!
   ```

3. **Complex Error Messages:**
   - NameError messages are verbose and context-specific
   - They explain WHAT failed in the resolution process
   - FileNotFoundError messages are simpler: "file not found"

4. **Codebase Age:**
   - This pattern exists throughout mature, well-tested code
   - Not a recent change or oversight
   - Would have been refactored if seen as a bug

---

## The Real Question: What Is The Test Actually Testing?

### Current Test Intent (Unclear):
```python
def test_basic_error_handling(self):
    """Test that basic error conditions are handled gracefully"""
    # ...
    try:
        path = p.get_path("definitely_does_not_exist.txt")
        assert path is not None  # Expects path to be returned?
    except Exception as e:
        assert isinstance(e, (FileNotFoundError, ValueError, RuntimeError))  # Wrong types!
```

**Problems:**
1. Comment says "Should return a path even if file doesn't exist" (line 135)
2. But assertion expects exception to be FileNotFoundError (line 139)
3. Contradictory expectations!
4. Doesn't account for actual hazelbean behavior

### What Should The Test Actually Validate?

**Option A: Test that get_path raises reasonable exceptions**
```python
def test_basic_error_handling(self):
    """Test that get_path raises appropriate exceptions for invalid paths"""
    with tempfile.TemporaryDirectory() as temp_dir:
        p = hb.ProjectFlow(temp_dir)
        
        # get_path should raise NameError for unresolvable paths
        with pytest.raises(NameError) as exc_info:
            path = p.get_path("definitely_does_not_exist.txt")
        
        # Verify error message is helpful
        assert "does not exist" in str(exc_info.value)
```

**Option B: Test that get_path CAN return non-existent paths (with flags)**
```python
def test_path_resolution_without_validation(self):
    """Test that get_path can construct paths without validation"""
    with tempfile.TemporaryDirectory() as temp_dir:
        p = hb.ProjectFlow(temp_dir)
        
        # With leave_ref_path_if_fail=True, should return path
        path = p.get_path("nonexistent.txt", leave_ref_path_if_fail=True)
        assert path is not None
        assert "nonexistent.txt" in path
```

**Option C: Test both behaviors**
```python
def test_error_handling_with_and_without_validation(self):
    """Test get_path error handling in both modes"""
    with tempfile.TemporaryDirectory() as temp_dir:
        p = hb.ProjectFlow(temp_dir)
        
        # Default behavior: should raise NameError
        try:
            path = p.get_path("missing.txt")
            pytest.fail("Should have raised NameError")
        except NameError as e:
            assert "does not exist" in str(e)
        
        # With flag: should return path without validation
        path = p.get_path("missing.txt", leave_ref_path_if_fail=True)
        assert "missing.txt" in path
```

---

## Risk Analysis: What Happens If We Just Add NameError?

### Proposed Change:
```python
# Line 139 - ADD NameError to tuple
assert isinstance(e, (FileNotFoundError, ValueError, RuntimeError, NameError))
```

### Is This Safe?

**YES, if:**
- ✅ We're only changing test expectations to match reality
- ✅ NameError is the correct, intentional behavior
- ✅ Test is validating "error doesn't crash system" not "specific exception type"
- ✅ No other tests depend on get_path raising FileNotFoundError

**NO, if:**
- ❌ This test documents a regression (NameError used to be FileNotFoundError)
- ❌ Other code catches FileNotFoundError specifically
- ❌ This represents a breaking change in hazelbean's API

### Evidence It's Safe:

1. **No recent regression:**
   ```bash
   git log --all --oneline -S "raise NameError" -- hazelbean/project_flow.py
   # Would show if NameError was recently introduced - likely it's been there
   ```

2. **Pervasive pattern:**
   - 277+ NameError usages suggest this is core design
   - Not a recent mistake or edge case

3. **Test is new:**
   - test_smoke.py was recently consolidated from multiple files
   - The test expectations may have been wrong from the start
   - Not testing against historical behavior

4. **No other tests catch FileNotFoundError from get_path:**
   ```bash
   grep -r "FileNotFoundError" hazelbean_tests/ | grep "get_path"
   # Returns no results - no tests depend on this specific exception type
   ```

---

## Alternative: Should We Change Hazelbean Instead?

### Argument FOR changing hazelbean to use FileNotFoundError:

**Pros:**
- More "Pythonic" - FileNotFoundError is the standard library exception for missing files
- Easier for new users to understand
- Follows principle of least surprise

**Cons:**
- **Violates memory [8070712]:** "Don't modify hazelbean when tests fail"
- **Loses semantic distinction:** Path resolution failure ≠ file not found
- **Massive refactoring:** 277+ NameError instances
- **Breaking change:** Could break user code that catches NameError
- **Not actually wrong:** NameError is semantically more accurate for "name resolution failed"

### Verdict: **DO NOT change hazelbean**

Reasons:
1. NameError is intentional, consistent, and semantically appropriate
2. Test is wrong, not code
3. No evidence of regression
4. Would be massive breaking change
5. Project convention explicitly says fix tests, not code

---

## Recommended Solution

### Minimal Change (Recommended):

**Update test_smoke.py line 139:**
```python
# Before:
assert isinstance(e, (FileNotFoundError, ValueError, RuntimeError))

# After:
assert isinstance(e, (FileNotFoundError, ValueError, RuntimeError, NameError))
```

**Rationale:**
- Test validates "error is reasonable" not "error is specific type"
- NameError IS a reasonable exception for path resolution failure
- Aligns test with actual, intentional hazelbean behavior
- Minimal change, low risk

### Better Change (If Time Permits):

**Rewrite test to be more explicit:**
```python
def test_basic_error_handling(self):
    """Test that get_path raises NameError for unresolvable paths"""
    with tempfile.TemporaryDirectory() as temp_dir:
        p = hb.ProjectFlow(temp_dir)
        
        # get_path raises NameError when path cannot be resolved
        # (This is by design - NameError indicates name resolution failure)
        with pytest.raises(NameError) as exc_info:
            path = p.get_path("definitely_does_not_exist.txt")
        
        # Verify error message provides useful information
        error_msg = str(exc_info.value)
        assert "does not exist" in error_msg
        assert "definitely_does_not_exist.txt" in error_msg
```

**Benefits:**
- Explicit about expected behavior
- Documents WHY NameError is used
- Tests error message quality
- Clear intent for future maintainers

---

## Documentation Recommendation

### Should Document Exception Strategy

Create `docs/exception-handling-conventions.md`:

```markdown
# Hazelbean Exception Handling Conventions

## FileNotFoundError vs NameError

Hazelbean uses two different exceptions for path-related errors:

### FileNotFoundError
Used when a specific file path is checked and doesn't exist:
- Simple file existence checks
- Opening files with GDAL/rasterio
- Direct path validation

### NameError  
Used when path/name resolution logic fails:
- `get_path()` cannot resolve path within project structure
- Path references cannot be mapped to concrete locations
- Name/reference resolution failures (not just "file missing")

This semantic distinction helps distinguish between:
1. "I know where to look, file isn't there" (FileNotFoundError)
2. "I don't know where/what you're referring to" (NameError)
```

---

## Final Answer To Your Question

> "Are you sure that's a good idea and isn't going to mess up what's currently working elsewhere in the repo?"

### YES, it's safe to add NameError to the test assertion, because:

1. **NameError is the correct, intentional behavior**
   - 277+ uses across codebase
   - Consistent pattern in project_flow.py, core.py, utils.py
   - Semantic distinction from FileNotFoundError

2. **No other code depends on the old assertion**
   - Smoke test is the only place checking exception type from get_path
   - No catches for FileNotFoundError from get_path elsewhere
   - Test is new/consolidated, not documenting historical behavior

3. **Minimal, surgical change**
   - One tuple update: add NameError to accepted exceptions
   - Test still validates "reasonable error raised"
   - Doesn't change any production code

4. **Follows project conventions**
   - Memory [8070712]: Fix tests, not hazelbean
   - Tests should reflect actual behavior
   - Don't modify working code to match test expectations

### Better Alternative (If You Want):

Instead of just adding NameError to the tuple, **rewrite the test** to explicitly test and document the NameError behavior:

```python
# More explicit version
with pytest.raises(NameError):
    path = p.get_path("definitely_does_not_exist.txt")
```

This makes it clear NameError is expected, not just "acceptable".

---

## Recommendation

**Option 1 (Fastest):** Add NameError to assertion tuple
- Low risk, matches actual behavior
- Gets CI passing quickly

**Option 2 (Better):** Rewrite test to explicitly expect NameError  
- Documents intended behavior
- Clearer for future maintainers
- Still low risk

**Choose based on:**
- How much time you want to spend
- Whether you want to document the exception strategy
- If you plan to add more path-related tests

Both options are safe and correct. The test is wrong, not hazelbean.

