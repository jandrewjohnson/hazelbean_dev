# ⚠️ DEPRECATED: MkDocs Documentation System

**Status:** Legacy / Deprecated  
**Replaced By:** Quarto Documentation System (`docs-site/quarto-docs/`)  
**Deprecation Date:** November 15, 2024

---

## ⚠️ IMPORTANT NOTICE

**This MkDocs-based documentation system is deprecated and will be removed in a future release.**

### Please Use Quarto Instead

**Primary Documentation:** `docs-site/quarto-docs/`

```bash
# New recommended workflow
./tools/generate_complete_site.sh --serve

# Or just serve
./tools/quarto_serve.sh
```

---

## Why We're Migrating

The project has migrated to **Quarto** for the following reasons:

1. ✅ **Better Report Integration** - Seamless automated report generation from test/benchmark data
2. ✅ **Modern Features** - Superior code highlighting, callouts, and interactive elements
3. ✅ **Educational Content** - Better suited for tutorial and example content
4. ✅ **Single Source** - One system for all documentation needs
5. ✅ **Active Development** - Quarto is actively developed and maintained

## What Remains Here

This directory contains the legacy MkDocs setup:
- `mkdocs.yml` - Old configuration
- `docs/` - Old content (mostly migrated to Quarto)
- `site/` - Old generated site

**These files are kept temporarily for:**
- Backward compatibility during transition
- Reference for remaining migration tasks
- Historical documentation

## Migration Status

| Content Type | Status | Location |
|-------------|--------|----------|
| Reports | ✅ Migrated | `quarto-docs/reports/` |
| Test Docs | ✅ Migrated | `quarto-docs/tests/` |
| Educational | ✅ Migrated | `quarto-docs/educational/` |
| Troubleshooting | ✅ Migrated | `quarto-docs/troubleshooting.qmd` |
| GitHub Pages | ⏳ Pending | Needs workflow update |

## Removal Timeline

- **Current (Nov 2024):** Both systems available, MkDocs deprecated
- **Next Release:** Quarto becomes sole documentation system
- **Future Release:** MkDocs files removed entirely

---

## If You Must Use MkDocs (Not Recommended)

### Quick Start

```bash
conda activate hazelbean_env
cd docs-site
mkdocs serve
```

Site available at http://127.0.0.1:8000

### Known Issues

1. **Import Resolution** - Uses legacy mkdocstrings handler with limited import resolution
2. **Manual Updates** - Reports not auto-generated, requires manual edits
3. **Stale Content** - Content may be outdated compared to Quarto version
4. **No Active Development** - Only critical bug fixes will be applied

### Dependencies

Pinned to legacy versions:
- `mkdocs=1.6.1`
- `mkdocs-material>=9.0.0`
- `mkdocstrings=0.30.1`
- `mkdocstrings-python-legacy=0.2.7`

---

## Feedback

If you have concerns about the Quarto migration or need specific MkDocs features:

1. Open an issue on GitHub
2. Contact the maintainers
3. Review the transition guide: `docs/plans/mkdocs-to-quarto-transition-guide.md`

---

**For all new documentation work, please use the Quarto system.**

See `docs-site/README.md` for current documentation.

