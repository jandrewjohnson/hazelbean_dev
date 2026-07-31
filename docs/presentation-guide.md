# Hazelbean Presentation Guide

**Duration**: ~50 minutes

---

## Before You Start

**Activate the conda environment first:**

```bash
conda activate hazelbean_env
```

Once activated, you can use `python` directly instead of the full path.

If conda activation doesn't work in your shell, use the full path:
```
/opt/homebrew/Caskroom/mambaforge/base/envs/hazelbean_env/bin/python
```

---

## Section 1: Introduction (5 mins)

---

## Section 2: Git Workflow & IDE Demo (5 mins)

**Say**: "Here's how I organize my work with Git and my IDE setup."

**Talking points**:
- Feature branches for isolated work
- Commit messages describe the "why"

---

## Section 3: Hazelbean Overview (10 mins)

### A. Package Structure

How the codebase is organized.

```bash
ls -la
ls hazelbean/
ls hazelbean_tests/
```

### B. Ex imports

```bash
python -c "import hazelbean as hb; print('Sample functions:', dir(hb)[:15])"
```

### C. Key Concepts to Mention

- **ProjectFlow**: Task-based project management with dependencies
- **Cython extensions**: `calculation_core/` for performance-critical code
- **Module organization**: `core.py`, `project_flow.py`, `geoprocessing.py`

### D. Show Examples

```bash
ls examples/
head -50 examples/step_1_project_setup.py
```

---

## Section 4: Testing & Documentation (15 mins)

### Test Types

| Type | Purpose | When to Use |
|------|---------|-------------|
| **Smoke** | Quick sanity check that basic imports and core functions work | After environment setup, before deeper testing |
| **Unit** | Test individual functions/classes in isolation | When changing a specific component |
| **Integration** | Test multiple components working together | When changing workflows or data pipelines |
| **System** | End-to-end workflows, CLI, environment validation | Before releases, after major changes |
| **Performance** | Benchmarks to catch speed regressions | When optimizing or changing algorithms |

### Test Commands

```bash
# Smoke test - quick sanity check (~2 seconds)
python -m pytest hazelbean_tests/system/test_smoke.py -v

# Unit tests - test individual components
python -m pytest hazelbean_tests/unit/ -v

# Integration tests - test cross-component workflows
python -m pytest hazelbean_tests/integration/ -v

# System tests - end-to-end workflows
python -m pytest hazelbean_tests/system/ -v

# Performance tests - benchmarks
python -m pytest hazelbean_tests/performance/ -v --benchmark-only

# Run everything
python -m pytest hazelbean_tests/ -v
```

### Common Flags

| Flag | Purpose |
|------|---------|
| `-v` | Verbose - show each test name |
| `-x` | Stop on first failure |
| `--tb=short` | Shorter error tracebacks |
| `-k "pattern"` | Run only tests matching pattern |
| `--collect-only` | List tests without running them |
| `--benchmark-only` | Run only benchmark tests |

**Why `python -m pytest`?** Ensures correct Python interpreter and avoids import issues with taskgraph.

### Documentation

```bash
quarto preview  # from earth_economy_devstack/docs
./tools/generate_complete_site.sh --serve  # Full build + preview
```

---

## Section 5: CI Quick Mention (2-3 mins)

**Say**: "Tests run automatically on every push via GitHub Actions."

```bash
ls .github/workflows/
head -40 .github/workflows/tests.yml
```

**Mention**:
- Multi-platform builds (Linux, Windows, macOS)
- Automated PyPI release on tag

---

## Section 6: Your Next Steps Opinion (10 mins)

**Recommended priorities:**

1. **Fix known bugs in ProjectFlow** (4 documented in KNOWN_BUGS.md)
   - `add_task` and `add_iterator` have edge cases
   - These block reliable task dependency graphs

2. **Improve integration test pass rate** (currently ~37%)
   - Many failures are data path issues, not code bugs
   - Fix: standardize test data fixtures

3. **Expand test coverage** (~20% currently)
   - Priority modules: `geoprocessing.py`, `project_flow.py`
   - These are the most-used and least-tested

4. **Establish CI performance baselines**
   - Benchmarks run but don't fail on regression
   - Add threshold-based assertions

5. **Documentation gaps**
   - API reference docs (autodoc from docstrings)
   - More tutorials in educational section

**Discussion prompt**: "What would be most valuable for the lab's workflow?"

---

## Section 7: Onboarding Recap (5 mins)

**Say**: "Here's how someone new would get started."

```bash
# Quick start commands
git clone <repo-url>
cd hazelbean_dev
conda env create -f environment.yml
conda activate hazelbean_env
pip install -e . --no-deps
python scripts/verify_installation.py
python -m pytest hazelbean_tests/system/test_smoke.py -v
```

**Point them to**:
- `CLAUDE.md` - Development instructions
- `examples/` - Step-by-step learning scripts

---

## Quick Reference Commands

```bash
# First, activate the environment
conda activate hazelbean_env

# Verify installation
python scripts/verify_installation.py

# Smoke tests
python -m pytest hazelbean_tests/system/test_smoke.py -v

# Unit tests
python -m pytest hazelbean_tests/unit/test_get_path.py -v --tb=short

# All test collection
python -m pytest hazelbean_tests/ --collect-only | tail -20

# Single benchmark
python -m pytest hazelbean_tests/performance/test_benchmarks.py::TestSimpleBenchmarks::test_hazelbean_temp_benchmark -v

# Full build - run tests + generate reports + render docs
./tools/generate_complete_site.sh

# Quick preview - use existing test data
quarto preview  # from earth_economy_devstack/docs
```

---

## Pytest Flags Explained

| Flag | What it does |
|------|--------------|
| `-v` | **Verbose** - Shows each test name as it runs instead of just dots |
| `-vv` | **Extra verbose** - Even more detail, shows full assertion diffs |
| `--tb=short` | **Short traceback** - Shows brief error info when tests fail |
| `--tb=long` | **Long traceback** - Shows full stack trace on failure |
| `--tb=no` | **No traceback** - Hides error details, just shows pass/fail |
| `--collect-only` | **Dry run** - Lists all tests without running them |
| `-x` | **Stop on first failure** - Exits immediately when a test fails |
| `-k "name"` | **Filter by name** - Only runs tests matching "name" |
| `--cov=hazelbean` | **Coverage** - Measures which code lines are tested |
| `--cov-report=term-missing` | **Coverage report** - Shows which lines weren't covered |
| `--benchmark-only` | **Benchmarks only** - Skips regular tests, runs only benchmarks |

### Why `python -m pytest` instead of just `pytest`?

Using `python -m pytest` ensures pytest runs with the correct Python interpreter and can find all installed packages. Running `pytest` directly can sometimes fail to find `taskgraph` or other dependencies.

### Common Combinations

```bash
# Quick check - verbose, stop on first failure
python -m pytest hazelbean_tests/unit/ -v -x

# Debug a failure - verbose with full traceback
python -m pytest hazelbean_tests/unit/test_get_path.py -v --tb=long

# Run specific test by name
python -m pytest hazelbean_tests/ -k "test_hazelbean_imports" -v

# Coverage report
python -m pytest hazelbean_tests/unit/ -v --cov=hazelbean --cov-report=term-missing
```

---

## If Something Fails

```bash
# Show test results file
cat hazelbean_tests/test-results.json | python -m json.tool | head -50

# Show a test file directly
cat hazelbean_tests/unit/test_get_path.py | head -80
```
