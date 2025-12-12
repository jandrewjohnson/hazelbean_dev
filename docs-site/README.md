# Hazelbean Documentation Site

This directory contains **TWO documentation systems** for Hazelbean:

## 🎯 PRIMARY: Quarto Documentation (RECOMMENDED)

**Location:** `docs-site/quarto-docs/`

Modern documentation system with automated report generation:
- 📊 **Reports**: Test results, coverage, performance baselines, benchmarks
- 📚 **Educational**: Tutorials with live code examples
- 🧪 **Test Documentation**: Auto-generated from test files
- 🔧 **Troubleshooting**: Common issues and solutions

### Quick Start (Quarto)

```bash
# Option 1: Generate reports and serve site
./tools/generate_complete_site.sh --serve

# Option 2: Just serve the site
./tools/quarto_serve.sh

# Option 3: Manual workflow
cd docs-site/quarto-docs
quarto preview
```

### Full Generation Workflow

```bash
# Generate all reports with fresh data and serve
cd /path/to/hazelbean_dev
conda activate hazelbean_env
./tools/generate_complete_site.sh --serve
```

This will:
1. ✅ Run full test suite with JSON reporting
2. ✅ Generate test results report
3. ✅ Generate coverage report  
4. ✅ Generate performance baselines
5. ✅ Generate benchmark results
6. ✅ Verify all reports created
7. ✅ Start Quarto preview server

---

## 🗄️ LEGACY: MkDocs Site (Deprecated)

**Location:** `docs-site/` (root files)

⚠️ **This system is deprecated and will be removed in a future release.**

The MkDocs-based documentation is **no longer actively maintained**. It remains for:
- Backward compatibility during transition period
- Reference for migration

### Legacy Quick Start (Not Recommended)

```bash
conda activate hazelbean_env
cd docs-site
mkdocs serve
```

Site available at http://127.0.0.1:8000

---

## 📁 Directory Structure

```
docs-site/
├── quarto-docs/              # ⭐ PRIMARY - Quarto documentation
│   ├── _quarto.yml           # Quarto configuration
│   ├── _site/                # Generated site (gitignored)
│   ├── reports/              # Auto-generated reports
│   │   ├── test-results.qmd
│   │   ├── coverage-report.qmd
│   │   ├── performance-baselines.qmd
│   │   └── benchmark-results.qmd
│   ├── tests/                # Test documentation
│   ├── educational/          # Tutorials and examples
│   └── index.qmd             # Homepage
│
├── docs/                     # 🗄️ LEGACY - MkDocs content
├── mkdocs.yml                # 🗄️ LEGACY - MkDocs config
└── README.md                 # This file
```

## 🚀 Report Generation

Reports are auto-generated from test runs:

```bash
# Generate individual reports
python tools/generate_test_results_report.py
python tools/generate_coverage_report.py
python tools/generate_baseline_report.py
python tools/generate_benchmark_summary.py

# Or generate everything at once
./tools/generate_complete_site.sh
```

### Report Sources

| Report | Source Data | Generator |
|--------|------------|-----------|
| Test Results | `hazelbean_tests/test-results.json` | `generate_test_results_report.py` |
| Coverage | `hazelbean_tests/coverage.json` | `generate_coverage_report.py` |
| Performance | `baselines/current_performance_baseline.json` | `generate_baseline_report.py` |
| Benchmarks | `metrics/benchmarks/*.json` | `generate_benchmark_summary.py` |

## 🔄 Migration Status

**Phase:** Transition to Quarto (Nov 2024)

### What's Working ✅
- ✅ Quarto site renders completely
- ✅ All report generators working
- ✅ Automated test → report pipeline
- ✅ Navigation and structure
- ✅ Educational content migrated
- ✅ Cross-platform scripts (Bash + Windows)

### Migration Timeline
- **Current:** Both systems available (MkDocs marked as legacy)
- **Next Release:** Quarto becomes default
- **Future Release:** Remove MkDocs entirely

## 📝 Configuration Files

### Quarto (_quarto.yml)
Primary configuration for modern site:
- Theme: Cosmo
- Navigation structure
- Sidebar organization
- Code highlighting and features

### MkDocs (mkdocs.yml) - LEGACY
Legacy configuration (deprecated):
- Uses `mkdocstrings-python-legacy=0.2.7`
- See file for upgrade path to modern handler
- **Not recommended for new work**

## 🛠️ Available Scripts

### Primary Scripts (Quarto)
```bash
./tools/generate_complete_site.sh [--serve]  # Generate all reports + optionally serve
./tools/quarto_serve.sh [--render]           # Serve site + optionally render first
```

### Windows Support
```cmd
tools\generate_complete_site.cmd            # Windows version
tools\quarto_serve.cmd                      # Windows version
```

### Legacy Scripts (Deprecated)
- Old mkdocs-based scripts in `tools/` directory
- Not recommended for new work

## 🐛 Troubleshooting

### Quarto Issues

**Quarto not found:**
```bash
conda activate hazelbean_env
conda install quarto -c conda-forge
```

**Reports not updating:**
```bash
# Regenerate with fresh test data
./tools/generate_complete_site.sh
```

**Links broken in rendered site:**
- Check `_quarto.yml` navigation structure
- Verify file paths relative to `quarto-docs/` directory

### Legacy MkDocs Issues

**"Could not resolve alias" errors:**
```bash
# Revert to legacy handler
conda activate hazelbean_env
conda remove mkdocstrings-python
conda install mkdocstrings-python-legacy=0.2.7 -c conda-forge
```

**Port 8000 in use:**
```bash
lsof -i :8000
kill <PID>
```

## 📦 Dependencies

Managed via `environment.yml`:

### Quarto System (Active)
- `quarto` - Documentation generation
- `pytest-json-report` - Test result JSON export
- `pytest-cov` - Coverage reporting

### MkDocs System (Legacy)
- `mkdocs=1.6.1` - Site generator
- `mkdocs-material>=9.0.0` - Theme
- `mkdocstrings=0.30.1` - Auto-doc
- `mkdocstrings-python-legacy=0.2.7` - Legacy handler

## 📚 Related Documentation

- **Migration Plan:** `../docs/plans/quarto-consolidation-implementation.md`
- **Transition Guide:** `../docs/plans/mkdocs-to-quarto-transition-guide.md`
- **Phase 0 Results:** `../docs/plans/phase0-verification-results.md`
- **Getting Started:** `../docs/getting-started.md`

## 🌐 GitHub Pages Deployment

**Live site:** https://jandrewjohnson.github.io/hazelbean_dev/

Deployment via GitHub Actions (currently points to MkDocs):
- **TODO:** Update workflow to deploy Quarto site instead
- Automatic deployment on push to `main`

---

**Last Updated:** November 15, 2024  
**Primary System:** Quarto  
**Status:** ✅ Quarto fully operational, MkDocs deprecated  
**Next Steps:** Update GitHub Actions to deploy Quarto site
