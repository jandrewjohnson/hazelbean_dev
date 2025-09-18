# Hazelbean Documentation Site

This directory contains the complete MkDocs-powered documentation site for Hazelbean, featuring automated test documentation extraction, educational content, and comprehensive test reporting.

## 🏗️ Site Architecture

```
docs-site/
├── 📄 mkdocs.yml              # Site configuration
├── 📄 README.md               # This file - site maintenance guide
├── 📁 docs/                   # All documentation content
│   ├── 📄 index.md           # Homepage
│   ├── 📁 educational/       # Tutorial and learning content
│   ├── 📁 tests/             # Automated test documentation
│   ├── 📁 reports/           # Test reports and metrics
│   ├── 📁 javascripts/       # Custom JavaScript
│   └── 📁 stylesheets/       # Custom CSS styling
├── 📁 site/                   # Generated static site (auto-generated)
└── 📄 setup-github-pages.sh  # GitHub Pages deployment script
```

## 🚀 Quick Start Guide

### Local Development

1. **Activate Environment:**
   ```bash
   conda activate hazelbean_env
   cd docs-site
   ```

2. **Install Dependencies (if needed):**
   ```bash
   # MkDocs and plugins should already be in environment
   conda install -c conda-forge mkdocs-material mkdocstrings-python
   ```

3. **Serve Locally:**
   ```bash
   mkdocs serve
   # Site available at http://127.0.0.1:8000
   ```

4. **Build Static Site:**
   ```bash
   mkdocs build
   # Output in site/ directory
   ```

### Content Updates

#### Fully Automated Content (Zero Manual Intervention)
- **Test Reports:** Fresh test execution results with pass/fail metrics
- **Coverage Analysis:** Module-by-module coverage from coverage.py API  
- **Performance Baselines:** Statistical analysis with confidence intervals
- **Benchmark Results:** Performance regression detection and timing analysis

#### Semi-Automated Content (Manual Trigger for New Files)
- **Test Documentation Structure:** Auto-extracted from `../hazelbean_tests/`
  - ✅ **Automatic:** Updates to existing test docstrings and results
  - ⚠️ **Manual Trigger Required:** When new test files are added
- **API References:** Auto-generated from docstrings

> **🔄 Reports Auto-Generated:** All files in `/docs/reports/` are dynamically generated - never edit manually!
> 
> **📁 Test Structure:** Run `python tools/generate_clean_test_docs.py` after adding new test files

#### Manual Content Updates
- **Educational Content:** Edit files in `docs/educational/`
- **Homepage:** Edit `docs/index.md`
- **Site Configuration:** Edit `mkdocs.yml`

## 🚀 **Complete Site Generation System**

> **New! One-Command Solution** - Generate the entire site with the most up-to-date data from tests, coverage, and performance metrics.

### **Quick Generation (Recommended)**

#### **macOS/Linux:**
```bash
# Generate complete site with latest data
./tools/generate_complete_site.sh

# Generate and serve immediately
./tools/generate_complete_site.sh --serve
```

#### **Windows PowerShell:**
```powershell
# Generate complete site with latest data
.\tools\generate_complete_site.ps1

# Generate and serve immediately
.\tools\generate_complete_site.ps1 -Serve
```

#### **Windows Command Prompt:**
```cmd
# Generate complete site with latest data
tools\generate_complete_site.cmd

# Generate and serve immediately
tools\generate_complete_site.cmd serve
```

### **What Complete Generation Includes**

✅ **Fresh test execution** with coverage collection  
✅ **Dynamic report generation** from live data:
   - Test results with pass/fail metrics
   - Code coverage analysis (module-by-module)
   - Performance baselines with trend analysis
   - Benchmark results and regression detection  
✅ **Index updates** - eliminates "Coming Soon" placeholders  
✅ **Verification** - confirms all reports generated successfully  
✅ **Optional serving** - starts mkdocs server on completion

### **Generated Reports Structure**

```
docs/reports/
├── index.md                    # Reports hub (auto-updated, no "Coming Soon" text)
├── test-results.md            # Fresh test execution (129 tests, 89.9% pass rate)
├── coverage-report.md         # Code coverage (23.2%, 47 modules analyzed)
├── performance-baselines.md   # Performance tracking (5.46ms baseline)
└── benchmark-results.md       # Benchmark analysis (5 benchmarks)
```

### **Individual Report Generators** 

For granular control, use individual generators:

```bash
# Individual report generation
python tools/generate_coverage_report.py         # Coverage analysis
python tools/generate_baseline_report.py         # Performance baselines  
python tools/generate_benchmark_summary.py       # Benchmark results
python tools/update_reports_index.py             # Index updates
```

### **Integration with Existing Workflows**

**Before major commits:**
```bash
# Full site refresh with latest data
./tools/generate_complete_site.sh --serve
# Review all reports at http://127.0.0.1:8005/hazelbean_dev/reports/
```

**CI/CD Integration:**
```yaml
# GitHub Actions example
- name: Generate Complete Site
  run: |
    conda activate hazelbean_env
    ./tools/generate_complete_site.sh
```

### **Cross-Platform Compatibility**

All scripts provide identical functionality across platforms:

| Platform | Script | Features |
|----------|--------|----------|
| **macOS/Linux** | `generate_complete_site.sh` | Full-featured bash version |
| **Windows PowerShell** | `generate_complete_site.ps1` | Native Windows with colored output |
| **Windows Batch** | `generate_complete_site.cmd` | Universal Windows compatibility |
| **Git Bash/WSL** | `generate_complete_site.sh` | Use bash version on Windows |

### **Detailed Documentation**

📚 **Complete tool documentation:** [`../docs/site-generation-tools.md`](../docs/site-generation-tools.md)  
📚 **Windows-specific guide:** [`../tools/README_Windows.md`](../tools/README_Windows.md)

---

## 📝 Content Management

### Educational Content Updates

The educational system follows a progressive learning structure:

```bash
# Edit tutorial content
vim docs/educational/examples.md

# Update learning path
vim docs/educational/index.md

# Test changes locally
mkdocs serve
```

**Content Guidelines:**
- Keep examples runnable and self-contained
- Include error handling for missing data
- Use consistent code formatting
- Add platform-specific instructions using content tabs

### Test Documentation Updates

Test documentation is **automatically generated** - do not edit manually:

```bash
# Regenerate test docs (if needed)
cd ..
python tools/generate_clean_test_docs.py

# Regenerate test reports
conda activate hazelbean_env
cd hazelbean_tests
pytest unit/ --json-report --json-report-file=test-results.json --quiet
python ../tools/generate_test_report_md.py test-results.json -o ../docs-site/docs/reports/test-results.md
```

## 🛠️ Maintenance Workflows

### 1. Regular Content Updates

**🚀 NEW: Simplified Maintenance (Recommended)**
```bash
#!/bin/bash
# Weekly site maintenance - One Command Solution

cd /path/to/hazelbean_dev

# 1. Activate environment
conda activate hazelbean_env

# 2. Check if new test files were added since last run
TEST_DOCS_STALE=$(find hazelbean_tests -name "*.py" -newer docs-site/docs/tests/index.md 2>/dev/null | wc -l)

if [ "$TEST_DOCS_STALE" -gt 0 ]; then
    echo "🔄 New test files detected - regenerating test documentation..."
    python tools/generate_clean_test_docs.py
else
    echo "✅ Test documentation structure up to date"
fi

# 3. Complete site generation with fresh data (always includes latest test results)
./tools/generate_complete_site.sh

# 4. Test site locally
cd docs-site
mkdocs serve --dev-addr 127.0.0.1:8000 &
sleep 5
curl -f http://127.0.0.1:8000 > /dev/null && echo "✅ Site loads successfully" || echo "❌ Site loading failed"
pkill -f "mkdocs serve"

# 5. Build and validate
mkdocs build --strict
echo "✅ Site updated successfully with fresh data"
```

**Manual Override (if you know new tests were added):**
```bash
#!/bin/bash
# Force regeneration of test documentation structure

cd /path/to/hazelbean_dev
conda activate hazelbean_env

# Always regenerate test docs (use when you've added new test files)
python tools/generate_clean_test_docs.py
./tools/generate_complete_site.sh
```

**📊 Legacy Method (Manual Control):**
```bash
#!/bin/bash
# Manual maintenance with individual steps

cd /path/to/hazelbean_dev/docs-site

# 1. Activate environment
conda activate hazelbean_env

# 2. Update test reports manually
cd ../hazelbean_tests
pytest unit/ integration/ system/ --cov=hazelbean --cov-report=term-missing --md-report --md-report-output ../docs-site/docs/reports/test-results.md --quiet

# 3. Generate individual reports
cd ..
python tools/generate_coverage_report.py
python tools/generate_baseline_report.py
python tools/generate_benchmark_summary.py
python tools/update_reports_index.py

# 4. Rebuild test documentation
python tools/generate_clean_test_docs.py

# 5. Build and validate
cd docs-site
mkdocs build --strict
echo "✅ Site updated successfully"
```

### 2. Adding New Test Modules

When new test files are added to `hazelbean_tests/`:

1. **⚠️ Manual Step Required:** Test *structure* documentation needs regeneration
2. **Regenerate Test Documentation:**
   ```bash
   python tools/generate_clean_test_docs.py
   ```
3. **Generate Fresh Reports (includes new tests automatically):**
   ```bash
   ./tools/generate_complete_site.sh
   ```
4. **Verify Results:**
   - New tests appear in site navigation
   - New tests included in coverage reports  
   - New tests included in test execution results
   - Content renders correctly

**What Happens Automatically vs Manually:**

| Content Type | New Test Files | Test Changes | Test Results |
|--------------|----------------|--------------|--------------|
| **Test Documentation Pages** | ⚠️ Manual `generate_clean_test_docs.py` | ✅ Auto-updated | ✅ Auto-updated |
| **Test Execution Reports** | ✅ Auto-included | ✅ Auto-updated | ✅ Auto-updated |
| **Coverage Analysis** | ✅ Auto-included | ✅ Auto-updated | ✅ Auto-updated |
| **Performance Reports** | ✅ Auto-included | ✅ Auto-updated | ✅ Auto-updated |

**Complete Workflow for New Tests:**
```bash
# 1. Add your test file
touch hazelbean_tests/unit/test_new_feature.py

# 2. Regenerate test documentation structure (REQUIRED)
python tools/generate_clean_test_docs.py

# 3. Generate complete site with new test included in all reports
./tools/generate_complete_site.sh --serve

# 4. Verify at http://127.0.0.1:8005/hazelbean_dev/
```

### 3. Performance Optimization

**Site Performance Checklist:**
- ✅ Images optimized and properly sized
- ✅ Mermaid diagrams render efficiently  
- ✅ Code highlighting performs well
- ✅ Search functionality responsive
- ✅ Page load times < 2 seconds

**Performance Monitoring:**
```bash
# Build with timing info
mkdocs build --verbose

# Test build performance
time mkdocs build

# Check site size
du -sh site/
```

## 🎨 Customization Guide

### Theme Configuration

Key customization areas in `mkdocs.yml`:

```yaml
theme:
  name: material
  features:
    - navigation.tabs        # Top-level navigation tabs
    - content.code.copy      # Code copy buttons
    - search.highlight       # Search result highlighting
  palette:                   # Light/dark theme toggle
    - scheme: default        # Light mode
    - scheme: slate          # Dark mode
```

### Custom Styling

**CSS Customizations:** `docs/stylesheets/extra.css`
- Test function collapse/expand behavior
- Educational content styling
- Responsive design adjustments

**JavaScript Enhancements:** `docs/javascripts/`
- `mathjax.js` - Mathematical notation support
- `helper-methods-collapse.js` - Test method organization

### Content Tabs

Use Material Design tabs for platform-specific content:

```markdown
=== "macOS"
    ```bash
    # macOS-specific commands
    ```

=== "Windows"
    ```cmd
    REM Windows-specific commands
    ```

=== "Linux"
    ```bash
    # Linux-specific commands
    ```
```

## 🔍 Troubleshooting

### Common Issues & Solutions

#### 1. MkDocs Build Failures

**Error:** `Config value: 'plugins'. Error: The "mkdocstrings" plugin is not installed`
```bash
# Solution: Install missing plugins
conda activate hazelbean_env
conda install -c conda-forge mkdocstrings-python
```

**Error:** `Documentation file 'path/to/file.md' does not exist`
```bash
# Solution: Regenerate test documentation
python tools/generate_clean_test_docs.py
```

#### 2. Test Documentation Issues

**Problem:** Test functions not appearing in documentation
```bash
# Check mkdocstrings configuration in mkdocs.yml
# Ensure filters are correct: ["^test_", "!^setUp", ...]

# Regenerate with debug info
python tools/generate_clean_test_docs.py --verbose
```

**Problem:** Test docstrings not rendering properly
```bash
# Verify docstring format (Google-style expected)
# Check that test files have proper imports
```

#### 3. Site Performance Issues

**Problem:** Slow page loads or search
```bash
# Check for large files
find docs/ -size +1M -type f

# Optimize images if found
# Consider lazy loading for heavy content
```

#### 4. GitHub Pages Deployment

**Error:** Site not updating on GitHub Pages
```bash
# Check deployment script
bash setup-github-pages.sh

# Verify GitHub Actions workflow
# Ensure proper permissions and secrets
```

### Debug Mode

Run site in debug mode for detailed error information:

```bash
# Serve with detailed logging
mkdocs serve --verbose --dev-addr 127.0.0.1:8000

# Build with strict checking
mkdocs build --strict --verbose
```

## 📈 Analytics & Monitoring

### Site Metrics

**Key Performance Indicators:**
- Page load times
- Search usage patterns  
- Most visited documentation sections
- User navigation flows

**Monitoring Setup:**
```yaml
# Add to mkdocs.yml
extra:
  analytics:
    provider: google
    property: G-XXXXXXXXXX  # Replace with actual GA4 ID
```

### Content Quality Metrics

**Documentation Coverage:**
```bash
# Check test coverage
find ../hazelbean_tests -name "*.py" -exec grep -l "def test_" {} \; | wc -l

# Compare with documented tests
grep -r ":::" docs/tests/ | wc -l
```

**Link Validation:**
```bash
# Install link checker
pip install linkchecker

# Check internal links
linkchecker --check-extern site/
```

## 🚀 Deployment Guide

### Local to Production Workflow

1. **Content Development:**
   ```bash
   # Make content changes
   # Test locally with mkdocs serve
   ```

2. **Quality Assurance:**
   ```bash
   # Run full test suite
   pytest hazelbean_tests/ --html=test-report.html
   
   # Update test reports
   python tools/generate_test_report_md.py test-results.json -o docs-site/docs/reports/test-results.md
   
   # Build with strict checking
   mkdocs build --strict
   ```

3. **Deployment:**
   ```bash
   # GitHub Pages (recommended)
   bash setup-github-pages.sh
   
   # Manual deployment
   mkdocs gh-deploy --force
   ```

### GitHub Pages Configuration

The site is configured for GitHub Pages deployment:

- **Source:** `gh-pages` branch (auto-generated)
- **Domain:** Custom domain configured in repository settings
- **SSL:** Automatically enforced
- **Build:** Automated via GitHub Actions

## 👥 Team Collaboration

### Content Contributor Guide

**For Educational Content:**
1. Follow existing tutorial structure
2. Test all code examples locally
3. Use consistent formatting and voice
4. Include error handling examples

**For Test Documentation:**
- ❌ Don't edit generated test docs manually
- ✅ Improve test docstrings in source files
- ✅ Run regeneration after test changes

### Review Process

**Content Review Checklist:**
- [ ] All links work correctly
- [ ] Code examples execute successfully  
- [ ] Platform-specific instructions are accurate
- [ ] Search functionality finds relevant content
- [ ] Site builds without warnings
- [ ] Mobile responsiveness maintained

## 📚 Additional Resources

### MkDocs Material Documentation
- **Official Docs:** https://squidfunk.github.io/mkdocs-material/
- **Reference:** https://mkdocs.org/user-guide/
- **Plugin Docs:** https://mkdocstrings.github.io/

### Project-Specific Resources
- **Test Documentation:** `../hazelbean_tests/README.md`
- **Project Architecture:** `../docs/technical_architecture.md` 
- **Contributing Guide:** `../contributor_license_agreement.md`

### Support & Questions

For site maintenance questions or issues:
1. Check this README first
2. Review existing GitHub issues
3. Test with `mkdocs serve --verbose`
4. Create detailed issue report if needed

---

**Last Updated:** Documentation system with automated test extraction and comprehensive guides  
**Maintainer:** Development Team  
**Site Version:** Auto-versioned with project releases