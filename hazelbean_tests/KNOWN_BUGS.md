# Known Bugs in Hazelbean

This document tracks known bugs discovered through comprehensive testing. These bugs cause certain tests to fail intentionally - the test failures are **correct and valuable** as they document bugs that need fixing.

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
- `unit/test_add_iterator.py::TestAddIteratorErrorHandling::test_add_iterator_invalid_function_error`
- `unit/test_add_iterator.py::TestAddIteratorErrorHandling::test_add_iterator_none_function_error`

**Story 3 Comprehensive Unit Tests:**
- `unit/test_add_iterator.py::TestErrorHandlingB5::test_non_callable_function_parameter`
- `unit/test_add_iterator.py::TestErrorHandlingB5::test_none_function_parameter`

**Note:** When this bug is fixed, these tests will automatically start passing.

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

*Last Updated: 2025-09-18 (Added Story 4 integration bugs)*  
*Next Review: When hazelbean bugs are addressed*
