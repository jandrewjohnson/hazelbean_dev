# Test Documentation Automation - How It Works

**Date:** November 15, 2024  
**Question:** What happens when a new test is added to a Python file?

---

## 📊 Overview: Two Documentation Types

When you add a new test, it appears in **TWO different places** with **different levels of automation**:

### 1. Reports Section (✅ **FULLY AUTOMATED**)
**Location:** `docs-site/quarto-docs/reports/test-results.qmd`  
**Shows:** Test statistics, pass/fail counts, runtime metrics  
**Automation Level:** 100% automatic

### 2. Tests Section (⚠️ **SEMI-AUTOMATED**)
**Location:** `docs-site/quarto-docs/tests/{unit,integration,performance,system}.qmd`  
**Shows:** Test descriptions, source code, docstrings  
**Automation Level:** Manual trigger required

---

## 🔄 Complete Workflow: Adding a New Test

### Step 1: Write Your Test
```python
# hazelbean_tests/unit/test_my_feature.py

def test_my_new_feature():
    """
    Validates that my_new_feature() works correctly.
    
    This test ensures:
    - Feature returns expected output
    - Handles edge cases
    - Validates input parameters
    """
    result = my_feature.do_something()
    assert result == expected_value
```

### Step 2: Run Tests (Generates JSON Data)
```bash
cd hazelbean_tests
conda activate hazelbean_env
pytest unit/test_my_feature.py --json-report --json-report-file=test-results.json
```

**What happens:**
- ✅ Test executes
- ✅ `test-results.json` created/updated with test metadata
- ✅ `coverage.json` updated (if running with --cov)

### Step 3A: Update Report Statistics (AUTOMATIC)
```bash
# This happens automatically when you run:
./tools/generate_complete_site.sh
```

**What happens:**
1. ✅ Runs all tests with JSON reporting
2. ✅ Calls `generate_test_results_report.py`
3. ✅ Reads `test-results.json`
4. ✅ Generates `reports/test-results.qmd` with:
   - Total test count (**automatically includes your new test**)
   - Pass/fail statistics
   - Test execution times
   - Status by file

**Result:** Your new test **immediately appears** in the test count and statistics!

### Step 3B: Update Test Documentation (MANUAL TRIGGER)
```bash
# You must explicitly run this:
cd docs-site/quarto-docs
python generate_test_docs.py
```

**What happens:**
1. ✅ Scans all test files in `hazelbean_tests/`
2. ✅ Extracts test functions using AST parsing
3. ✅ Reads docstrings and source code
4. ✅ Generates `tests/{unit,integration,performance,system}.qmd` with:
   - Test function names
   - Full docstrings
   - Source code in collapsible blocks
   - Organized by test file

**Result:** Your new test **appears in the Tests section** with full documentation!

### Step 4: Render the Site
```bash
cd docs-site/quarto-docs
quarto preview
```

**What happens:**
- ✅ Quarto renders all .qmd files to HTML
- ✅ Site available at http://localhost:XXXX
- ✅ Both Reports and Tests sections updated

---

## 🎯 Automation Levels Explained

### Reports Section: 100% Automatic ✅

| Action | Automation | Command |
|--------|-----------|---------|
| Run tests | Automatic | `./tools/generate_complete_site.sh` |
| Generate JSON | Automatic | Part of test run |
| Parse JSON → QMD | Automatic | `generate_test_results_report.py` |
| Update test counts | Automatic | Reads from JSON |
| Render HTML | Automatic (if using --serve) | `quarto render` |

**You do:** Write test + run `generate_complete_site.sh`  
**System does:** Everything else

### Tests Section: Semi-Automatic ⚠️

| Action | Automation | Command |
|--------|-----------|---------|
| Write test | Manual | You write the code |
| Extract functions | **MANUAL TRIGGER** | `python generate_test_docs.py` |
| Parse docstrings | Automatic | AST parsing |
| Generate QMD | Automatic | Script generates .qmd |
| Render HTML | Automatic | `quarto render` |

**You do:** Write test + run `generate_test_docs.py` + run site generator  
**System does:** Extraction and rendering

---

## 📋 Step-by-Step: Complete Process

### For a New Test Function

1. **Write the test:**
   ```python
   # hazelbean_tests/unit/test_arrayframe.py
   def test_new_arrayframe_feature():
       """Test new feature in ArrayFrame."""
       # Your test code
   ```

2. **Update reports (AUTOMATIC):**
   ```bash
   ./tools/generate_complete_site.sh
   ```
   - ✅ Test appears in report statistics
   - ✅ Test count incremented
   - ✅ Pass/fail status shown

3. **Update test docs (MANUAL TRIGGER):**
   ```bash
   cd docs-site/quarto-docs
   python generate_test_docs.py
   ```
   - ✅ Test extracted with docstring
   - ✅ Source code included
   - ✅ Added to `tests/unit.qmd`

4. **View changes:**
   ```bash
   ./tools/quarto_serve.sh
   ```
   - Open http://localhost:XXXX/reports/test-results.html
   - Open http://localhost:XXXX/tests/unit.html

---

## 🔍 Where Things Live

### Source Test Files
```
hazelbean_tests/
├── unit/test_*.py           # Your test code
├── integration/test_*.py
├── performance/test_*.py
└── system/test_*.py
```

### Generated JSON Data
```
hazelbean_tests/
├── test-results.json        # Test execution data
└── coverage.json            # Coverage metrics
```

### Documentation Generation Scripts
```
tools/
├── generate_test_results_report.py    # Reports automation
├── generate_coverage_report.py
├── generate_baseline_report.py
└── generate_benchmark_summary.py

docs-site/quarto-docs/
└── generate_test_docs.py              # Tests documentation automation
```

### Generated Documentation
```
docs-site/quarto-docs/
├── reports/
│   ├── test-results.qmd      # AUTOMATIC: Test statistics
│   ├── coverage-report.qmd   # AUTOMATIC: Coverage metrics
│   └── ...
└── tests/
    ├── unit.qmd              # MANUAL TRIGGER: Test documentation
    ├── integration.qmd
    ├── performance.qmd
    └── system.qmd
```

### Rendered Site
```
docs-site/quarto-docs/_site/
├── reports/
│   └── test-results.html     # Statistics view
└── tests/
    └── unit.html             # Documentation view
```

---

## ⚡ Quick Reference

### I just added a test, what do I run?

#### Minimum (just statistics):
```bash
./tools/generate_complete_site.sh --serve
```
**Result:** Test appears in **Reports → Test Results**

#### Complete (statistics + documentation):
```bash
# Step 1: Generate reports with test counts
./tools/generate_complete_site.sh

# Step 2: Generate test documentation
cd docs-site/quarto-docs
python generate_test_docs.py

# Step 3: Serve the site
cd ../..
./tools/quarto_serve.sh
```
**Result:** Test appears in **both Reports AND Tests sections**

---

## 🤔 Why Two Levels of Automation?

### Reports (Fully Automatic)
- **Purpose:** Show test health metrics
- **Data Source:** JSON from pytest
- **Update Frequency:** Every test run
- **Why Automatic:** Always need current stats

### Tests (Manual Trigger)
- **Purpose:** Educational/reference documentation
- **Data Source:** Python source code AST parsing
- **Update Frequency:** When adding significant tests
- **Why Manual:** Doesn't change as often, gives you control

---

## 💡 Best Practices

### When to Update Test Documentation

**Run `generate_test_docs.py` when:**
- ✅ Adding new test functions
- ✅ Significantly changing test docstrings
- ✅ Adding new test files
- ✅ Before creating documentation for release

**Don't need to run when:**
- ❌ Just fixing a bug in existing test
- ❌ Making small code changes
- ❌ Running tests during development
- ❌ CI/CD test runs (reports are enough)

### Recommended Workflow

#### During Development:
```bash
# Quick testing - just run tests
pytest unit/test_my_feature.py

# Check statistics
./tools/generate_complete_site.sh --serve
# View reports section only
```

#### Before Committing:
```bash
# Full documentation update
./tools/generate_complete_site.sh
cd docs-site/quarto-docs
python generate_test_docs.py
cd ../..
./tools/quarto_serve.sh

# Review both Reports and Tests sections
```

---

## 🚀 Future Automation Ideas

### Could Be Fully Automated:
1. **Git hook:** Run `generate_test_docs.py` on pre-commit
2. **Watch mode:** Auto-regenerate when test files change
3. **CI integration:** Generate docs in GitHub Actions
4. **Makefile target:** Single command for everything

### Example Future Setup:
```bash
# One command does everything
make docs

# Or even better - watches for changes
make docs-watch
```

---

## 📚 Related Documentation

- **Server Commands:** `docs-site/README.md`
- **Transition Guide:** `docs/plans/mkdocs-to-quarto-transition-guide.md`
- **Implementation Details:** `docs/plans/quarto-consolidation-implementation-COMPLETE.md`
- **Test Documentation Script:** `docs-site/quarto-docs/generate_test_docs.py`

---

## Summary

| Documentation Type | Automation | Script | When Updates |
|-------------------|------------|---------|--------------|
| **Reports** (statistics) | ✅ Automatic | `generate_test_results_report.py` | Every `generate_complete_site.sh` run |
| **Tests** (code/docs) | ⚠️ Manual trigger | `generate_test_docs.py` | When you explicitly run it |

**Bottom Line:** 
- New tests **automatically appear in statistics** 
- But you need to **manually trigger** full documentation generation

This gives you flexibility to update detailed docs only when needed while keeping stats always current!

