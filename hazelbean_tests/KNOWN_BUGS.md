# Known Bugs in Hazelbean

This document tracks known bugs discovered through comprehensive testing. These bugs cause certain tests to fail intentionally - the test failures are **correct and valuable** as they document bugs that need fixing.

## 🔍 Important Distinction: CI Infrastructure vs Hazelbean Bugs

### CI Infrastructure Issues (Test Framework - Our Responsibility)
These are problems with the test infrastructure, build process, or CI configuration - NOT bugs in hazelbean functionality:

- ✅ **RESOLVED: Cython Extension Import in CI**
  - **Problem:** Cython extensions not importable in CI environment, causing `ImportError: cannot import name 'cython_functions'`
  - **Root Cause:** Package not installed before running tests - extensions existed but weren't in Python's import path
  - **Solution:** Added `pip install -e .` step in CI workflow to build and install package before tests
  - **Status:** Fixed in `.github/workflows/testing-quality-gates.yml` (lines 88-111, 159-163, 248-251, 302-305)
  - **Impact:** This was blocking ALL tests from running - now resolved
  - **Note:** This is a packaging/build issue, not a hazelbean logic bug

### Known Hazelbean Bugs (Core Software - Upstream Responsibility)
These are actual bugs in hazelbean's core functionality that need fixing by maintainers:

## Bug Status Legend
- 🐛 **Open** - Bug exists and needs fixing
- ✅ **Fixed** - Bug has been resolved (tests will pass)
- 🔄 **In Progress** - Bug fix is being worked on

---

## 🐛 Error Handling Bug in ProjectFlow add_task() and add_iterator()

**Status:** 🐛 Open  
**Discovered:** 2025-09-18  
**Severity:** Medium  
**Component:** `hazelbean/project_flow.py`

### Description
The `add_task()` and `add_iterator()` methods have incorrect error handling logic that causes `AttributeError` instead of the intended `TypeError` when non-callable objects are passed as function parameters.

### Root Cause
The error handling code tries to access the `__name__` attribute of invalid objects before checking if they are callable:

**Lines 593 & 707 in `project_flow.py`:**
```python
if not hasattr(function, '__call__'):
    raise TypeError(
        'Fuction passed to add_task() must be callable. ' + str(function.__name__) + ' was not.')
        #                                                    ^^^^^^^^^^^^^^^^^
        #                                                    This causes AttributeError!
```

### Reproduction
```python
import hazelbean as hb

p = hb.ProjectFlow('/tmp/test')

# These should raise TypeError but raise AttributeError instead
p.add_task("not_a_function")  # AttributeError: 'str' object has no attribute '__name__'
p.add_task(None)              # AttributeError: 'NoneType' object has no attribute '__name__'
p.add_iterator("not_a_function")  # Same issue
p.add_iterator(None)          # Same issue
```

### Expected Behavior
Should raise `TypeError` with message like:
```
TypeError: Function passed to add_task() must be callable. 'not_a_function' was not.
```

### Actual Behavior
Raises `AttributeError` with message like:
```
AttributeError: 'str' object has no attribute '__name__'. Did you mean: '__ne__'?
```

### Affected Code Locations
1. **`hazelbean/project_flow.py:593`** - `add_task()` method
2. **`hazelbean/project_flow.py:707`** - `add_iterator()` method

### Failing Tests (Intentionally)
These tests fail because they expect correct behavior:

**Story 1 & 2 Core Proof Tests:**
- `unit/test_add_task.py::TestAddTaskErrorHandling::test_add_task_invalid_function_error`
- `unit/test_add_task.py::TestAddTaskErrorHandling::test_add_task_none_function_error`
- `unit/test_add_iterator.py::TestAddIteratorErrorHandling::test_add_iterator_invalid_function_error` ⚠️ **xfail**
- `unit/test_add_iterator.py::TestAddIteratorErrorHandling::test_add_iterator_none_function_error` ⚠️ **xfail**

**Story 3 Comprehensive Unit Tests:**
- `unit/test_add_iterator.py::TestErrorHandlingB5::test_non_callable_function_parameter` ⚠️ **xfail**
- `unit/test_add_iterator.py::TestErrorHandlingB5::test_none_function_parameter` ⚠️ **xfail**

**Note:** When this bug is fixed, these tests will automatically start passing.

### Test Status & xfail Markers

**These tests are marked with `@pytest.mark.xfail` to allow CI to pass while documenting the bug:**

- ✅ Tests still run and validate correct behavior
- ✅ CI passes (xfailed tests don't fail builds)
- ✅ Automatic alert when bug is fixed (tests will show XPASSED)
- ✅ Clear tracking of failure rates

**When this bug is fixed in hazelbean:**
1. These tests will show as "XPASSED" (unexpected pass)
2. Remove the `@pytest.mark.xfail` decorators
3. Tests will run as normal passing tests
4. Update this bug status to ✅ Fixed

**xfail marker format:**
```python
@pytest.mark.xfail(
    reason="Known bug: project_flow.py:772 - See KNOWN_BUGS.md",
    strict=True,  # Alert on unexpected pass
    raises=AttributeError  # Current buggy behavior
)
```

### Suggested Fix
Check if the function is callable before trying to access its `__name__` attribute:

```python
if not hasattr(function, '__call__'):
    # Safe way to get function name/description for error message
    func_desc = getattr(function, '__name__', repr(function))
    raise TypeError(
        f'Function passed to add_task() must be callable. {func_desc} was not.')
```

### Additional Notes
- There's also a typo: "Fuction" should be "Function" 
- The same pattern exists in both `add_task()` and `add_iterator()` methods
- This bug affects error message quality but doesn't break core functionality
- Tests correctly expose this issue by expecting the proper `TypeError`

---

## 🐛 Inconsistent task_names_defined Tracking Between Methods

**Status:** 🐛 Open  
**Discovered:** 2025-09-18  
**Severity:** Medium  
**Component:** `hazelbean/project_flow.py`

### Description
The `add_task()` and `add_iterator()` methods have inconsistent behavior when tracking function names in the `task_names_defined` list. This creates unpredictable behavior when code relies on this list for runtime conditionals.

### Root Cause
Only `add_task()` adds function names to the `task_names_defined` list, while `add_iterator()` does not:

**Line 596 in `add_task()`:**
```python
self.task_names_defined.append(function.__name__)  # ✅ Adds name to list
```

**Lines 700-732 in `add_iterator()`:**
```python
# No corresponding line - missing task_names_defined.append()  # ❌ Missing
```

### Reproduction
```python
import hazelbean as hb

p = hb.ProjectFlow('/tmp/test')

def test_task(p): pass
def test_iterator(p): 
    p.iterator_replacements = {'test': ['val'], 'cur_dir_parent_dir': [p.intermediate_dir]}

# add_task() adds to task_names_defined
p.add_task(test_task)
print(len(p.task_names_defined))  # 1 - name added

# add_iterator() does NOT add to task_names_defined  
p.add_iterator(test_iterator)
print(len(p.task_names_defined))  # Still 1 - name not added!
```

### Expected Behavior
Both methods should consistently track function names:
```python
assert 'test_task' in p.task_names_defined      # ✅ Works
assert 'test_iterator' in p.task_names_defined  # ❌ Fails - should work
```

### Actual Behavior
Only task names are tracked, iterator names are silently ignored.

### Affected Code Locations
1. **`hazelbean/project_flow.py:596`** - `add_task()` properly tracks names
2. **`hazelbean/project_flow.py:700-732`** - `add_iterator()` missing name tracking

### Failing Tests (Intentionally)
This bug causes these tests to fail - the failures are CORRECT and expose the bug:

**Story 4 Integration Tests:**
- `integration/test_project_flow_task_management.py::TestMixedHierarchyConstruction::test_iterator_with_child_tasks_hierarchy`
- `integration/test_project_flow_task_management.py::TestCrossMethodAttributeManagement::test_task_names_defined_tracking_across_methods`

### Suggested Fix
Add consistent name tracking to `add_iterator()`:

```python
def add_iterator(self, function, project=None, parent=None, run_in_parallel=False, type='iterator', **kwargs):
    # ... existing code ...
    
    # Add this line after iterator creation (around line 713):
    self.task_names_defined.append(function.__name__)
    
    # ... rest of method ...
```

### Additional Notes
- The `task_names_defined` list is used for runtime conditionals (see line 1159 in `execute()`)
- Current inconsistency means iterator-based conditional logic won't work as expected
- Both methods should have identical behavior for name tracking

---

## 🐛 Task Attributes Not Inheriting Project-Level Settings

**Status:** 🐛 Open  
**Discovered:** 2025-09-18  
**Severity:** Low  
**Component:** `hazelbean/project_flow.py`

### Description
Tasks hardcode certain attributes instead of inheriting them from project-level settings, making it impossible to configure task behavior at the project level.

### Root Cause
The `Task` class constructor hardcodes `report_time_elapsed_when_task_completed = True` instead of inheriting from the project:

**Line 168 in `Task.__init__()`:**
```python
self.report_time_elapsed_when_task_completed = True  # ❌ Hardcoded
```

### Reproduction
```python
import hazelbean as hb

p = hb.ProjectFlow('/tmp/test')

# Set project-level setting
p.report_time_elapsed_when_task_completed = False

def test_task(p): pass

# Task should inherit project setting but doesn't
task = p.add_task(test_task)
print(task.report_time_elapsed_when_task_completed)  # True - should be False!
```

### Expected Behavior
Tasks should inherit project-level settings by default:
```python
p.report_time_elapsed_when_task_completed = False
task = p.add_task(test_task)
assert task.report_time_elapsed_when_task_completed == False  # Should inherit
```

### Actual Behavior
Task attributes are hardcoded and ignore project settings.

### Affected Code Locations
1. **`hazelbean/project_flow.py:168`** - `Task.__init__()` hardcodes attribute
2. **Similar pattern may exist for other task attributes**

### Failing Tests (Intentionally)
This bug causes these tests to fail - the failures are CORRECT and expose the bug:

**Story 4 Integration Tests:**
- `integration/test_project_flow_task_management.py::TestConfigurationInheritanceAcrossMethods::test_project_level_settings_respect`

### Suggested Fix
Inherit from project settings with hardcoded value as fallback:

```python
def __init__(self, function, project=None, parent=None, type='task', run=1, skip_existing=0, **kwargs):
    # ... existing code ...
    
    # Replace line 168 with:
    self.report_time_elapsed_when_task_completed = getattr(
        project, 'report_time_elapsed_when_task_completed', True
    )
    
    # ... rest of constructor ...
```

### Additional Notes
- This pattern should be applied to other configurable task attributes
- Logging level inheritance works correctly (good example to follow)
- Iterator tasks may have the same issue
- Default values should still be preserved as fallbacks

---

## 🐛 Error Handling Bug in ProjectFlow.add_task() {#add_task_error_handling}

**Status:** 🐛 Open  
**Discovered:** 2025-10-03  
**Severity:** Medium  
**Component:** `hazelbean/project_flow.py`

### Description
The `add_task()` method has incorrect error handling logic that causes `AttributeError` instead of the intended `TypeError` when non-callable objects are passed as function parameters. This is the same bug pattern as `add_iterator()` but in a different method.

### Root Cause
The error handling code tries to access the `__name__` attribute of invalid objects before checking if they are callable:

**Lines 655-658 in `project_flow.py`:**
```python
if not hasattr(function, '__call__'):
    raise TypeError(
        'Fuction passed to add_task() must be callable. ' + str(function.__name__) + ' was not.')
        #                                                    ^^^^^^^^^^^^^^^^^
        #                                                    This causes AttributeError!
```

### Reproduction
```python
import hazelbean as hb

p = hb.ProjectFlow('/tmp/test')

# These should raise TypeError but raise AttributeError instead
p.add_task("not_a_function")  # AttributeError: 'str' object has no attribute '__name__'
p.add_task(None)              # AttributeError: 'NoneType' object has no attribute '__name__'
```

### Expected Behavior
Should raise `TypeError` with message like:
```
TypeError: Function passed to add_task() must be callable. 'not_a_function' was not.
```

### Actual Behavior
Raises `AttributeError` with message like:
```
AttributeError: 'str' object has no attribute '__name__'. Did you mean: '__ne__'?
```

### Affected Code Locations
1. **`hazelbean/project_flow.py:655-658`** - `add_task()` method error handler

### Failing Tests (Intentionally)
These tests fail because they expect correct behavior - **the test failures are valuable and correct**:

**Core Proof Tests (Story 1):**
- `unit/test_add_task.py::TestAddTaskErrorHandling::test_add_task_invalid_function_error` ⚠️ **xfail**
- `unit/test_add_task.py::TestAddTaskErrorHandling::test_add_task_none_function_error` ⚠️ **xfail**

### Test Status & xfail Markers

**These tests are marked with `@pytest.mark.xfail` to allow CI to pass while documenting the bug:**

- ✅ Tests still run and validate expected (correct) behavior
- ✅ CI passes (xfailed tests don't fail builds)
- ✅ Automatic alert when bug is fixed (tests will show XPASSED)
- ✅ Bug is tracked and documented

**When this bug is fixed in hazelbean:**
1. These tests will show as "XPASSED" (unexpected pass)
2. Remove the `@pytest.mark.xfail` decorators
3. Tests will run as normal passing tests
4. Update this bug status to ✅ Fixed

**xfail marker format:**
```python
@pytest.mark.xfail(
    reason="Known bug: project_flow.py:655-658 - See KNOWN_BUGS.md #add_task_error_handling",
    strict=True,  # Alert on unexpected pass
    raises=AttributeError  # Current buggy behavior
)
```

### Suggested Fix
Check if the function is callable before trying to access its `__name__` attribute:

```python
if not hasattr(function, '__call__'):
    # Safe way to get function name/description for error message
    func_desc = getattr(function, '__name__', repr(function))
    raise TypeError(
        f'Function passed to add_task() must be callable. {func_desc} was not.')
```

### Additional Notes
- There's also a typo: "Fuction" should be "Function"
- This is the same bug pattern as in `add_iterator()` (see bug above)
- This bug affects error message quality but doesn't break core functionality
- Tests correctly expose this issue by expecting the proper `TypeError`
- Related to existing `add_iterator()` bug - same root cause, different method

---

## 🐛 Unusual Exception Type in get_path() for Missing Files {#get_path_exception_type}

**Status:** 🐛 Open - Investigation Needed  
**Discovered:** 2025-10-03  
**Severity:** Medium  
**Component:** `hazelbean/project_flow.py` (lines 612, 618)

### Description
The `get_path()` method raises `NameError` when files are not found, which violates Python conventions. The standard Python exception for missing files is `FileNotFoundError` (available since Python 3.3). Using `NameError` is confusing because this exception is typically reserved for undefined variables/names in code, not file system operations.

### Investigation Needed
**It is unclear whether this is:**
1. **Intentional design** - Using `NameError` deliberately to distinguish hazelbean's path resolution from OS-level errors
2. **A bug** - Should be using `FileNotFoundError` to follow Python conventions

**The method has no docstring**, making it impossible to determine intended behavior from documentation.

### Root Cause (If Bug)
The error handling code explicitly raises `NameError`:

**Lines 612, 618 in `project_flow.py`:**
```python
raise NameError('The path given to hb.get_path() does not exist...')
```

**Python convention would be:**
```python
raise FileNotFoundError('The path given to hb.get_path() does not exist...')
```

### Investigation Results (2025-10-03)

**Tested behavior:**
1. ✅ `NameError` is raised for missing files (confirmed)
2. ✅ `leave_ref_path_if_fail=True` works correctly (returns constructed path)
3. ✅ `raise_error_if_fail=False` works correctly (returns constructed path)
4. ❌ No docstring exists for the method
5. ❌ Error message has grammatical issues ("and or is not available")

**Conclusion:** The parameters work correctly, but the exception type choice is questionable and undocumented.

### Affected Tests
These tests are marked xfail while investigation is pending:

**Edge Case Tests:**
- `unit/test_get_path.py::TestErrorHandlingAndEdgeCases::test_invalid_characters_in_path` ⚠️ **xfail**
- `unit/test_get_path.py::TestErrorHandlingAndEdgeCases::test_path_with_special_characters` ⚠️ **xfail**
- `unit/test_get_path.py::TestErrorHandlingAndEdgeCases::test_missing_file_fallback` ⚠️ **xfail**
- `unit/test_get_path.py::TestErrorHandlingAndEdgeCases::test_very_long_path` ⚠️ **xfail**

**Cloud Storage Tests:**
- `unit/test_get_path.py::TestCloudStorageIntegration::test_google_cloud_bucket_integration` ⚠️ **xfail**
- `unit/test_get_path.py::TestCloudStorageIntegration::test_cloud_path_fallback` ⚠️ **xfail**

### Test Status & xfail Markers

**These tests are marked with `@pytest.mark.xfail` while investigation is pending:**

- ✅ Tests still run (not skipped)
- ✅ CI passes (xfailed tests don't fail builds)
- ✅ Alerts when behavior changes
- ✅ Investigation needed to determine intended behavior

**xfail marker format:**
```python
@pytest.mark.xfail(
    reason="Investigation needed: get_path() raises NameError for missing files (unusual - Python convention is FileNotFoundError). Need to determine if this is intended behavior. See KNOWN_BUGS.md #get_path_exception_type",
    strict=False,
    raises=NameError
)
```

### Possible Fixes (Pending Investigation Results)

**If NameError is a bug (recommended if no strong reason exists):**
```python
# In project_flow.py, lines 612, 618:
if file_not_found:
    if raise_error_if_fail:
        raise FileNotFoundError(f'The path given to hb.get_path() does not exist...')
```

**If NameError is intentional:**
1. Add comprehensive docstring documenting the exception type and why
2. Update tests to expect `NameError`
3. Improve error message grammar ("and or" → proper phrasing)

### Additional Notes
- Parameters (`leave_ref_path_if_fail`, `raise_error_if_fail`) work correctly
- Main issues: unusual exception type, no docstring, poor error message
- Impact: Confusion for users expecting standard Python exceptions
- Decision needed from hazelbean maintainers on whether `NameError` is intentional

---

## How to Use This Document

### For Hazelbean Maintainers
1. **Fixing Bugs:** Each section provides exact locations and suggested fixes
2. **Verifying Fixes:** Run the listed failing tests - they should pass after fixes
3. **Status Updates:** Change status from 🐛 to ✅ when bugs are resolved

### For Developers
1. **Understanding Test Failures:** Check this file if tests fail unexpectedly
2. **Contributing:** Add new discovered bugs to this file with full documentation
3. **Testing:** Don't modify tests to accommodate bugs - document bugs here instead

### For Test Infrastructure
1. **Test failures listed here are expected and valuable**
2. **Don't adjust tests to hide bugs - let them expose real issues**
3. **When bugs are fixed, corresponding tests will automatically pass**

---

## Bug Report Template

When adding new bugs, use this template:

```markdown
## 🐛 [Bug Title]

**Status:** 🐛 Open  
**Discovered:** [Date]  
**Severity:** [Low/Medium/High/Critical]  
**Component:** [File path]

### Description
[Clear description of the bug]

### Root Cause
[Technical explanation of what's wrong]

### Reproduction
[Code example showing how to trigger the bug]

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happens]

### Affected Code Locations
[Specific file and line numbers]

### Failing Tests (Intentionally)
[List of test names that expose this bug]

### Suggested Fix
[Proposed solution]

### Additional Notes
[Any other relevant information]
```

---

*Last Updated: 2025-10-03 (Added add_task error handling bug and get_path test design issues for CI fix)*  
*Next Review: When hazelbean bugs are addressed*
