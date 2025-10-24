# Hazelbean Documentation Site

This directory contains the MkDocs-based documentation site for Hazelbean, including:
- Educational tutorials with live code examples
- Test documentation 
- Performance reports and metrics
- API reference documentation

## Quick Start

```bash
# Activate environment
conda activate hazelbean_env

# Serve documentation locally
cd docs-site
mkdocs serve

# Build static site
mkdocs build
```

The site will be available at http://127.0.0.1:8000

## Current Configuration

### MkDocs Handler Version

**Currently using:** `mkdocstrings-python-legacy=0.2.7`

This project uses the **legacy mkdocstrings handler** (not the modern griffe-based handler) because:
- The modern handler (griffe 1.14.0) requires ALL imports to be explicitly resolved
- Standard library imports (`os`, `sys`, etc.) in example files cause build failures with modern handler
- Legacy handler is more lenient about import resolution

### Future Upgrade Path

To upgrade to the modern `mkdocstrings-python` handler in the future:

1. Add all standard library modules to `preload_modules` in `mkdocs.yml`:
   ```yaml
   preload_modules: [pytest, hazelbean, os, sys, pathlib, logging, json, datetime]
   ```

2. Remove legacy handler and install modern:
   ```bash
   conda remove mkdocstrings-python-legacy
   conda install mkdocstrings-python -c conda-forge
   ```

3. Test and add any missing modules to preload list

**See:** `docs/plans/mkdocs-griffe-import-resolution-fix.md` for complete details.

## Structure

```
docs-site/
├── docs/
│   ├── index.md                    # Homepage
│   ├── educational/
│   │   ├── index.md
│   │   └── examples.md             # Tutorial examples with live code
│   ├── tests/
│   │   ├── index.md
│   │   ├── integration.md
│   │   ├── unit.md
│   │   ├── performance.md
│   │   └── system.md
│   └── reports/
│       ├── index.md
│       ├── test-results.md
│       ├── coverage-report.md
│       ├── performance-baselines.md
│       └── benchmark-results.md
├── mkdocs.yml                      # Site configuration
├── site/                           # Generated site (gitignored)
└── README.md                       # This file
```

## Auto-Documentation

The site uses `mkdocstrings` to auto-generate documentation from Python code:

### Examples (Working ✅)
- `educational/examples.md` - Automatically extracts and displays code from `examples/step_*.py` files
- Shows complete Python code with syntax highlighting
- Includes docstrings and function signatures

### Test Documentation (Partial)
- Some test auto-doc directives are commented out (see integration.md)
- Manual descriptions are still present and comprehensive
- Full auto-docs will be restored when upgrading to modern handler

## Troubleshooting

### "Could not resolve alias" errors

If you see errors like:
```
ERROR - Could not resolve alias examples.step_1_project_setup.os pointing at os
```

This means the modern handler got installed. Revert to legacy:
```bash
conda activate hazelbean_env
conda remove mkdocstrings-python
conda install mkdocstrings-python-legacy=0.2.7 -c conda-forge
```

### Build fails on test documentation

Some test documentation directives are intentionally commented out. Check:
- `docs/tests/integration.md` - Lines with `<!-- TODO: Re-enable` comments
- These will be restored when upgrading to modern handler

### Server won't start

Check if port 8000 is already in use:
```bash
lsof -i :8000
# Kill any existing process
kill <PID>
```

## Dependencies

Managed via `environment.yml` in project root:
- `mkdocs=1.6.1`
- `mkdocs-material>=9.0.0`
- `mkdocstrings=0.30.1`
- `mkdocstrings-python-legacy=0.2.7` ⭐ **Pinned to legacy**

## Related Documentation

- **Root cause analysis:** `../docs/plans/mkdocs-griffe-import-resolution-fix.md`
- **Fresh start summary:** `../docs/plans/mkdocs-documentation-site-fresh-start.md`
- **Getting started guide:** `../docs/getting-started.md`

## GitHub Pages Deployment

The documentation is automatically deployed to GitHub Pages via GitHub Actions workflow.

**Live site:** https://jandrewjohnson.github.io/hazelbean_dev/

Deployment happens automatically on push to `main` branch.

---

**Last Updated:** October 3, 2025  
**Handler Version:** mkdocstrings-python-legacy 0.2.7  
**Status:** ✅ Working - examples show complete Python code
