# Hazelbean Documentation Site

This directory contains the Quarto documentation system for Hazelbean.

## Location

**Primary:** `docs-site/quarto-docs/`

Modern documentation system with automated report generation:
- **Reports**: Test results, coverage, performance baselines, benchmarks
- **Educational**: Tutorials with live code examples
- **Test Documentation**: Auto-generated from test files
- **Troubleshooting**: Common issues and solutions

## Quick Start

```bash
# Option 1: Generate reports and serve site
./tools/generate_complete_site.sh --serve

# Option 2: Just serve the site
./tools/quarto_serve.sh

# Option 3: Manual workflow
cd docs-site/quarto-docs
quarto preview
```

## Full Generation Workflow

```bash
# Generate all reports with fresh data and serve
cd /path/to/hazelbean_dev
conda activate hazelbean_env
./tools/generate_complete_site.sh --serve
```

This will:
1. Run full test suite with JSON reporting
2. Generate test results report
3. Generate coverage report
4. Generate performance baselines
5. Generate benchmark results
6. Verify all reports created
7. Start Quarto preview server

## Directory Structure

```
docs-site/
├── quarto-docs/              # Quarto documentation
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
├── README.md                 # This file
└── setup-github-pages.sh     # Deployment script
```

## Report Generation

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

## Configuration

### Quarto (_quarto.yml)
Primary configuration for the documentation site:
- Theme: Cosmo
- Navigation structure
- Sidebar organization
- Code highlighting and features

## Available Scripts

### Primary Scripts
```bash
./tools/generate_complete_site.sh [--serve]  # Generate all reports + optionally serve
./tools/quarto_serve.sh [--render]           # Serve site + optionally render first
```

### Windows Support
```cmd
tools\generate_complete_site.cmd            # Windows version
tools\quarto_serve.cmd                      # Windows version
```

## Troubleshooting

### Quarto not found
```bash
conda activate hazelbean_env
conda install quarto -c conda-forge
```

### Reports not updating
```bash
# Regenerate with fresh test data
./tools/generate_complete_site.sh
```

### Links broken in rendered site
- Check `_quarto.yml` navigation structure
- Verify file paths relative to `quarto-docs/` directory

### Port in use
```bash
lsof -i :4848
kill <PID>
```

## Dependencies

Managed via `environment.yml`:

- `quarto` - Documentation generation
- `pytest-json-report` - Test result JSON export
- `pytest-cov` - Coverage reporting

## Related Documentation

- **Getting Started:** `../docs/getting-started.md`
- **Active Plans:** `../docs/plans/`
- **Archived Plans:** `../docs/archive/`

## GitHub Pages Deployment

**Live site:** https://jandrewjohnson.github.io/hazelbean_dev/

Deployment via GitHub Actions:
- Automatic deployment on push to `main`
