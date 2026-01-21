# How to Add Tests to Documentation

When you add a new test, it appears in **two places** with different automation levels.

## Quick Start

### Option 1: Just Statistics (Fastest - Automatic)
```bash
# Your test immediately appears in Reports → Test Results
./tools/generate_complete_site.sh --serve
```

### Option 2: Full Documentation (Includes Source Code)
```bash
# Step 1: Run tests and generate reports (automatic)
./tools/generate_complete_site.sh

# Step 2: Generate test documentation (manual trigger)
cd docs-site/quarto-docs
python generate_test_docs.py

# Step 3: View the site
cd ../..
./tools/quarto_serve.sh
```

---

## Understanding the Two Documentation Types

### Reports Section (Automatic)
**Location:** http://localhost:XXXX/reports/test-results.html

**Shows:**
- Test counts and pass/fail rates
- Execution times
- Coverage metrics

**Updates:** Automatically when you run `./tools/generate_complete_site.sh`

**Your new test:** Appears immediately in statistics!

### Tests Section (Manual Trigger)
**Location:** http://localhost:XXXX/tests/unit.html

**Shows:**
- Test descriptions and docstrings
- Full source code (collapsible)
- Organized by test file

**Updates:** When you run `python generate_test_docs.py`

**Your new test:** Appears with full documentation and source code!

---

## Step-by-Step: Adding a New Test

### 1. Create Your Test File

**Location:** Must be in the correct directory

| Directory | Documentation Page |
|-----------|-------------------|
| `hazelbean_tests/unit/` | Unit Tests |
| `hazelbean_tests/integration/` | Integration Tests |
| `hazelbean_tests/performance/` | Performance Tests |
| `hazelbean_tests/system/` | System Tests |

**Naming:** File must start with `test_` (e.g., `test_my_feature.py`)

```bash
# Example: Create a unit test
touch hazelbean_tests/unit/test_my_feature.py
```

### 2. Write Your Test

**Requirements:**
- Function name must start with `test_`
- Include docstrings (first line becomes description)

```python
"""Tests for my new feature."""
import pytest
import hazelbean as hb

@pytest.mark.unit
def test_my_new_feature():
    """Test that my_new_feature works correctly."""
    result = hb.my_new_feature()
    assert result is not None
```

### 3. Generate Documentation

#### For Statistics Only (Fast):
```bash
./tools/generate_complete_site.sh --serve
```
Test appears in **Reports -> Test Results**

#### For Full Documentation (Complete):
```bash
# Generate reports + statistics
./tools/generate_complete_site.sh

# Generate test documentation
cd docs-site/quarto-docs
python generate_test_docs.py

# Serve the site
cd ../..
./tools/quarto_serve.sh
```
Test appears in **both Reports AND Tests sections**

---

## Viewing Your Changes

After generation, the server will show you the URL (usually http://localhost:XXXX)

**Navigate to:**
- **Reports → Test Results** - See statistics
- **Tests → Unit/Integration/etc** - See full documentation

---

## Troubleshooting

### My test isn't showing up in statistics

**Check:** Did you run the complete site generator?
```bash
./tools/generate_complete_site.sh
```

**Verify:** Check the output shows your test file was processed

### My test isn't in the Tests documentation

**Check 1:** File naming
```bash
# Correct
hazelbean_tests/unit/test_my_feature.py

# Wrong
hazelbean_tests/unit/my_feature_test.py
tests/unit/test_my_feature.py
```

**Check 2:** Function naming
```python
# Will appear
def test_my_function():
    pass

# Won't appear
def my_function():
    pass
```

**Check 3:** Did you run the test docs generator?
```bash
cd docs-site/quarto-docs
python generate_test_docs.py
```

### Regenerate everything from scratch

```bash
# Full refresh
./tools/generate_complete_site.sh
cd docs-site/quarto-docs
python generate_test_docs.py
cd ../..
./tools/quarto_serve.sh
```

---

## Complete Example

Adding a test for raster validation:

```bash
# 1. Create test file
cat > hazelbean_tests/unit/test_raster_validation.py << 'EOF'
"""Tests for raster validation."""
import pytest
import hazelbean as hb

@pytest.mark.unit
def test_validate_raster():
    """Test basic raster validation."""
    # Your test code here
    assert True
EOF

# 2. Generate everything
./tools/generate_complete_site.sh
cd docs-site/quarto-docs
python generate_test_docs.py

# 3. View
cd ../..
./tools/quarto_serve.sh
```

Open the URL shown and navigate to:
- **Reports → Test Results** (statistics)
- **Tests → Unit Tests** (full documentation)

---

## When to Use Each Command

### During Development (Quick):
```bash
# Just check if tests pass and see statistics
./tools/generate_complete_site.sh --serve
```

### Before Committing (Complete):
```bash
# Full documentation update
./tools/generate_complete_site.sh
cd docs-site/quarto-docs
python generate_test_docs.py
cd ../..
./tools/quarto_serve.sh
```

---

## Key Points

**Reports (Automatic):**
- Updates every time you run `generate_complete_site.sh`
- Shows test counts and statistics
- Perfect for quick checks during development

**Tests Documentation (Manual):**
- Requires running `generate_test_docs.py`
- Shows source code and detailed docstrings
- Update before commits or releases

**Why two levels?**
- Statistics change frequently (every test run)
- Detailed docs don't need to regenerate as often
- Gives you control over when to update detailed documentation

---

## Related Documentation

- **Server Commands:** `docs-site/README.md`
- **Transition Guide:** `docs/plans/mkdocs-to-quarto-transition-guide.md`
- **Detailed Automation Explanation:** `docs/plans/test-documentation-automation-explained.md`

---

**Last Updated:** November 15, 2024
