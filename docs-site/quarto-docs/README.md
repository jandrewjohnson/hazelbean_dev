# Quarto Documentation Site

This directory contains the Hazelbean documentation site built with Quarto, featuring comprehensive test documentation with **277 test functions** across 4 test categories.

## Quick Start

### Standalone Usage (Local Development)

```bash
# Render the site
quarto render

# Serve locally
quarto preview
```

### Using in a Monorepo

**See [Using in a Monorepo](#using-in-a-monorepo) section below for detailed instructions.**

### Adding New Tests to Documentation

**See [HOW-TO-ADD-TESTS.md](HOW-TO-ADD-TESTS.md) for complete instructions.**

**Quick version:**
1. Create test file: `hazelbean_tests/unit/test_my_feature.py`
2. Write tests (functions must start with `test_`)
3. Regenerate: `python generate_test_docs.py`
4. Render: `quarto render`

**The automation script automatically discovers new test files!** No configuration needed.

---

## Using in a Monorepo

This repo is designed to be pulled into a larger monorepo as a submodule or subfolder. Here's how to generate docs to the parent repository's documentation folder.

### Expected Monorepo Structure

```
parent-monorepo/
├── hazelbean_dev/                    # This repository
│   ├── docs-site/quarto-docs/        # Source .qmd files
│   └── tools/generate_complete_site.sh
├── other-project/
└── docs-site/                        # Parent's documentation output
    ├── hazelbean/                    # Hazelbean docs go here
    │   ├── index.html
    │   ├── reports/
    │   └── tests/
    └── other-project/                # Other projects' docs
```

### Option 1: Command-Line Approach (Temporary)

Generate directly to parent folder without modifying configuration:

```bash
# From hazelbean_dev/docs-site/quarto-docs/
quarto render --output-dir ../../../docs-site/hazelbean
```

**Explanation:**
- `../../../docs-site/hazelbean` = Go up 3 levels, into docs-site/hazelbean/
- Output structure: `parent-monorepo/docs-site/hazelbean/{index.html,reports/,tests/}`

### Option 2: Configuration Approach (Permanent)

Modify `_quarto.yml` to always output to the parent's docs folder:

```yaml
project:
  type: website
  output-dir: ../../../docs-site/hazelbean  # Add this line
```

Then simply run:
```bash
quarto render
```

**Advantages:**
- ✅ Don't need to remember the --output-dir flag
- ✅ Consistent output location
- ✅ Works with all Quarto commands

**Note:** If you commit this change, document it in your repo's README so contributors know docs generate to parent folder.

### Serving from Parent-Level docs-site

After generating to the parent's `docs-site/`, serve from there:

#### Option A: Simple HTTP Server
```bash
# From parent-monorepo/docs-site/
python -m http.server 8000

# View at:
# http://localhost:8000/hazelbean/
# http://localhost:8000/other-project/
```

#### Option B: Quarto Preview (if parent has _quarto.yml)
```bash
# From parent-monorepo/docs-site/
quarto preview
```

### Integrating with generate_complete_site.sh

If you want the full workflow (tests + reports + docs) to output to parent folder:

**Edit `tools/generate_complete_site.sh`:**

Find the reports generation section and add output directory:
```bash
# Around line 77-88, after generating reports:
cd "$PROJECT_ROOT"

# Generate reports to parent's docs-site
python tools/generate_test_results_report.py \
    --output ../docs-site/hazelbean/reports/test-results.qmd

# Similar for other reports...
```

Then render with output to parent:
```bash
cd docs-site/quarto-docs
quarto render --output-dir ../../../docs-site/hazelbean
```

### Complete Monorepo Workflow

```bash
# 1. Generate all reports and documentation
cd hazelbean_dev
./tools/generate_complete_site.sh

# 2. Generate test docs
cd docs-site/quarto-docs
python generate_test_docs.py

# 3. Render to parent's docs-site
quarto render --output-dir ../../../docs-site/hazelbean

# 4. Serve from parent level
cd ../../../docs-site
quarto preview
# or
python -m http.server 8000

# 5. View in browser
# http://localhost:8000/hazelbean/
```

### Monorepo Best Practices

**1. Namespace your documentation**
- Output to `docs-site/hazelbean/` (not `docs-site/`)
- Prevents conflicts with other projects

**2. Document the setup**
- Add monorepo instructions to your repo's main README
- Note if `_quarto.yml` is configured for monorepo output

**3. CI/CD considerations**
- Parent repo's CI can trigger builds for all subprojects
- Each subproject builds to its own namespace in docs-site/

**4. Linking between projects**
- Use relative paths: `../other-project/some-page.html`
- Or absolute paths if parent has unified navigation

---

## Site Structure

```
docs-site/quarto-docs/
├── _quarto.yml                    # Site configuration
├── generate_test_docs.py          # Automation script
├── index.qmd                      # Homepage
├── tests/
│   ├── index.qmd                  # Test overview
│   ├── unit.qmd                   # Unit tests (118 functions)
│   ├── integration.qmd            # Integration tests (87 functions)
│   ├── performance.qmd            # Performance tests (49 functions)
│   └── system.qmd                 # System tests (23 functions)
└── _site/                         # Generated HTML (local)
    # or
    ../../../docs-site/hazelbean/  # Generated HTML (monorepo)
```

---

## Files Overview

### Key Files

- **`_quarto.yml`** - Website configuration (navigation, sidebar, theme)
- **`generate_test_docs.py`** - Automation script that extracts test functions and generates QMD files
- **`HOW-TO-ADD-TESTS.md`** - Complete guide for adding tests to documentation
- **`MIGRATION-COMPLETE.md`** - Summary of MkDocs to Quarto migration

### Generated Files

All files in `tests/*.qmd` are **auto-generated** by `generate_test_docs.py`. Do not edit them manually - they will be overwritten when the script runs.

---

## Regenerating Documentation

When tests change, regenerate the documentation:

```bash
# From docs-site/quarto-docs directory
python generate_test_docs.py
quarto render

# Or for monorepo:
quarto render --output-dir ../../../docs-site/hazelbean
```

**What the script does:**
1. Scans `hazelbean_tests/` for all `test_*.py` files
2. Parses each file using Python's AST module
3. Extracts test functions with source code and docstrings
4. Generates QMD files with collapsible callout blocks
5. Groups tests by file and category

**Time:** ~2-3 seconds to generate + ~10 seconds to render

---

## Documentation Features

### What's Included

- ✅ **277 test functions** documented with full source code
- ✅ **Collapsible code sections** using Quarto callout blocks
- ✅ **Syntax highlighting** for Python code
- ✅ **Line numbers** in all code blocks
- ✅ **Copy code button** for easy copying
- ✅ **Search functionality** across all pages
- ✅ **Table of contents** on each page
- ✅ **Sidebar navigation** with test categories
- ✅ **Breadcrumb navigation** for easy traversal

### Test Categories

| Category | Files | Functions | Documentation |
|----------|-------|-----------|---------------|
| **Unit Tests** | 12 | 118 | [tests/unit.qmd](tests/unit.qmd) |
| **Integration Tests** | 5 | 87 | [tests/integration.qmd](tests/integration.qmd) |
| **Performance Tests** | 4 | 49 | [tests/performance.qmd](tests/performance.qmd) |
| **System Tests** | 2 | 23 | [tests/system.qmd](tests/system.qmd) |

---

## Automation Script Details

### How `generate_test_docs.py` Works

The script uses Python's `ast` module to parse test files:

```python
# Key steps:
1. Find all test_*.py files in each test directory
2. Parse each file to extract:
   - Test function names
   - Function docstrings (first line = description)
   - Complete source code (including decorators)
   - Pytest markers (@pytest.mark.unit, etc.)
3. Generate QMD files with:
   - Category overview
   - File sections
   - Individual test function blocks (collapsible)
   - Running instructions
```

### Configuration

Test categories are configured in the script's `main()` function:

```python
categories = [
    ('unit', 'Unit Tests', hazelbean_tests_dir / 'unit'),
    ('integration', 'Integration Tests', hazelbean_tests_dir / 'integration'),
    ('performance', 'Performance Tests', hazelbean_tests_dir / 'performance'),
    ('system', 'System Tests', hazelbean_tests_dir / 'system'),
]
```

To add a new category, add it to this list and the script will handle the rest.

---

## Quarto Configuration

### Site Settings (`_quarto.yml`)

Key configurations:

```yaml
project:
  type: website
  output-dir: _site              # Default (local)
  # output-dir: ../../../docs-site/hazelbean  # Monorepo setup

execute:
  enabled: false          # Don't execute code blocks

format:
  html:
    code-fold: false      # Code blocks visible by default
    code-line-numbers: true
    code-copy: true
    highlight-style: github
    toc: true
    toc-depth: 3
```

### Navigation

The site has both:
- **Navbar** - Top navigation with dropdown menu
- **Sidebar** - Left sidebar with test categories
- **TOC** - Right table of contents on each page

---

## Troubleshooting

### Tests not showing up?

**Check:**
1. File name starts with `test_` ✅
2. File is in correct directory (`unit/`, `integration/`, etc.) ✅
3. Functions start with `test_` ✅
4. File is valid Python (no syntax errors) ✅
5. Script ran successfully ✅

**Debug:**
```bash
# Run script and look for your file
python generate_test_docs.py | grep "test_your_file"

# Check Python syntax
python -m py_compile hazelbean_tests/unit/test_your_file.py
```

### Page not rendering?

**Clean and rebuild:**
```bash
# Remove old files
rm -rf _site/ tests/*.qmd

# Regenerate from scratch
python generate_test_docs.py
quarto render
```

### Wrong output directory in monorepo?

**Verify paths:**
```bash
# Check current directory
pwd
# Should be: .../hazelbean_dev/docs-site/quarto-docs

# Test output directory
ls -la ../../../docs-site/
# Should show parent's docs-site folder
```

---

## Deployment

### Standalone Repository

For standalone usage (not in monorepo), build and deploy the `_site/` directory to your web server or hosting platform.

### Monorepo

In a monorepo setup, the parent repository typically handles deployment:
1. All subprojects build to `parent-monorepo/docs-site/{project-name}/`
2. Parent repo deploys the entire `docs-site/` folder
3. Each project is accessible at its namespace URL

---

## Maintenance

### Regular Updates

Run these commands when:
- ✅ New test files are added
- ✅ Test functions are modified
- ✅ Docstrings are updated

```bash
python generate_test_docs.py
quarto render

# Monorepo:
quarto render --output-dir ../../../docs-site/hazelbean
```

### Version Control

**Commit to git:**
- ✅ `generate_test_docs.py` (the automation script)
- ✅ `_quarto.yml` (site configuration)
- ✅ `index.qmd` and `tests/index.qmd` (manually created pages)
- ✅ Documentation files (MD files)

**Do NOT commit:**
- ❌ `tests/*.qmd` (except `tests/index.qmd`) - auto-generated
- ❌ `_site/` - build output
- ❌ `_freeze/` - Quarto cache

---

## Resources

### Documentation

- **[HOW-TO-ADD-TESTS.md](HOW-TO-ADD-TESTS.md)** - Complete guide for adding tests
- **[MIGRATION-COMPLETE.md](MIGRATION-COMPLETE.md)** - Migration summary and statistics
- **[Quarto Documentation](https://quarto.org/docs/)** - Official Quarto docs
- **[Quarto Publishing](https://quarto.org/docs/publishing/)** - Deployment guides

### Tools

- **Quarto** - Documentation generator
- **Python AST** - Test code parsing
- **Cosmo Theme** - Site styling

---

## Questions?

1. Check [HOW-TO-ADD-TESTS.md](HOW-TO-ADD-TESTS.md) for common questions
2. Review [MIGRATION-COMPLETE.md](MIGRATION-COMPLETE.md) for technical details
3. For monorepo setup, see [Using in a Monorepo](#using-in-a-monorepo) section above

---

**Last Updated:** November 15, 2024  
**Version:** 1.1  
**Total Tests Documented:** 277
