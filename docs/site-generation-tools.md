# Site Generation Tools & Scripts

Complete documentation for all site generation, reporting, and documentation tools in the hazelbean project.

## 🚀 **Quick Start - Single Command Solution**

### **For macOS/Linux:**
```bash
./tools/generate_complete_site.sh --serve
```

### **For Windows (PowerShell):**
```powershell
.\tools\generate_complete_site.ps1 -Serve
```

### **For Windows (Command Prompt):**
```cmd
tools\generate_complete_site.cmd serve
```

---

## 📋 **Complete Tool Inventory**

### **🌟 Primary Site Generation Scripts**

| Script | Platform | Purpose | Usage |
|--------|----------|---------|-------|
| `tools/generate_complete_site.sh` | macOS/Linux | **Main script** - Complete site generation | `./tools/generate_complete_site.sh [--serve]` |
| `tools/generate_complete_site.ps1` | Windows PowerShell | **Main script** - Windows PowerShell version | `.\tools\generate_complete_site.ps1 [-Serve]` |
| `tools/generate_complete_site.cmd` | Windows Batch | **Main script** - Windows batch version | `tools\generate_complete_site.cmd [serve]` |

### **🔧 Individual Report Generators**

| Script | Purpose | Output File | Auto-Discovery |
|--------|---------|-------------|----------------|
| `tools/generate_coverage_report.py` | Code coverage analysis from coverage.py API | `docs-site/docs/reports/coverage-report.md` | ✅ New tests auto-included |
| `tools/generate_baseline_report.py` | Performance baseline dashboard | `docs-site/docs/reports/performance-baselines.md` | ✅ New data auto-included |
| `tools/generate_benchmark_summary.py` | Recent benchmark results summary | `docs-site/docs/reports/benchmark-results.md` | ✅ New benchmarks auto-included |
| `tools/update_reports_index.py` | Updates index and eliminates "Coming Soon" text | `docs-site/docs/reports/index.md` | ✅ Current metrics auto-updated |

### **📚 Documentation Structure Generators**

| Script | Purpose | Output Files | Auto-Discovery |
|--------|---------|-------------|----------------|
| `tools/generate_clean_test_docs.py` | Test documentation from docstrings | `docs-site/docs/tests/*.md` | ⚠️ **Manual trigger needed for new test files** |

### **📊 Legacy/Component Scripts**

| Script | Purpose | Notes |
|--------|---------|-------|
| `tools/generate_reports.sh` | Original test + report generation | Now integrated into complete site scripts |

### **📚 Documentation**

| File | Purpose |
|------|---------|
| `tools/README_Windows.md` | Windows-specific setup and usage guide |
| `docs/site-generation-tools.md` | This comprehensive guide |

---

## 🎯 **What The Complete Site Generation Does**

### **Step-by-Step Process:**

1. **🧪 Fresh Test Execution**
   - Runs complete test suite: `unit/`, `integration/`, `system/`
   - Collects fresh coverage data with `--cov=hazelbean`
   - Generates test results markdown with `pytest-md-report`

2. **📊 Dynamic Report Generation**
   - **Coverage Report**: Direct from coverage.py API (19.4% coverage, 47 modules)
   - **Performance Baselines**: From `/metrics/baselines/*.json` (5.46ms baseline)
   - **Benchmark Results**: From `/metrics/benchmarks/*.json` (5 benchmarks analyzed)
   - **Test Results**: Fresh pytest execution results (129 tests, 89.9% pass rate)

3. **🔄 Index Updates**
   - Eliminates all "Coming Soon" placeholder text
   - Updates current metrics and pass rates
   - Adds functional links to all reports

4. **✅ Verification**
   - Confirms all 5 report files exist
   - Verifies no "Coming Soon" text remains
   - Displays generation summary with timestamps

5. **🌐 Optional Server**
   - Starts mkdocs development server on `127.0.0.1:8005`
   - Provides direct URLs to all reports

---

## 🛠 **Individual Tool Usage**

### **Coverage Report Generator**
```bash
python tools/generate_coverage_report.py
```
- **Input**: Coverage data from `.coverage` file (created by `pytest --cov`)
- **Output**: `docs-site/docs/reports/coverage-report.md`
- **Features**: Module breakdown, coverage percentages, quality gates, missing line analysis
- **Auto-Discovery**: ✅ Automatically includes new test files that run with `--cov`

### **Test Documentation Generator**
```bash
python tools/generate_clean_test_docs.py
```
- **Input**: All Python test files in `hazelbean_tests/` directory structure
- **Output**: `docs-site/docs/tests/*.md` documentation pages
- **Features**: Auto-discovery of test functions, docstring extraction, navigation generation
- **⚠️ Manual Trigger Required**: Must run when new test files are added

### **Performance Baseline Generator**
```bash
python tools/generate_baseline_report.py
```
- **Input**: `metrics/baselines/current_performance_baseline.json` + snapshots
- **Output**: `docs-site/docs/reports/performance-baselines.md`
- **Features**: Statistical analysis, confidence intervals, trend detection, machine context

### **Benchmark Summary Generator**
```bash
python tools/generate_benchmark_summary.py
```
- **Input**: Recent files from `metrics/benchmarks/*.json`
- **Output**: `docs-site/docs/reports/benchmark-results.md`
- **Features**: Performance comparison, regression detection, timing analysis

### **Reports Index Updater**
```bash
python tools/update_reports_index.py
```
- **Input**: Current test results from `test-results.md`
- **Output**: Updated `docs-site/docs/reports/index.md`
- **Features**: Eliminates "Coming Soon" text, updates metrics, adds functional links

---

## 🌍 **Cross-Platform Compatibility**

### **macOS/Linux (Bash)**
- **Requirements**: bash, conda environment, Python tools
- **Command**: `./tools/generate_complete_site.sh [--serve]`
- **Features**: Full-featured with colored output and error handling

### **Windows PowerShell**
- **Requirements**: PowerShell 5.0+, conda environment, Python tools
- **Command**: `.\tools\generate_complete_site.ps1 [-Serve]`
- **Features**: Native Windows support, colored output, error handling
- **Setup**: May require `Set-ExecutionPolicy RemoteSigned` for first run

### **Windows Command Prompt**
- **Requirements**: Any Windows version, conda environment, Python tools
- **Command**: `tools\generate_complete_site.cmd [serve]`
- **Features**: Universal Windows compatibility, simple interface

### **Git Bash/WSL Alternative**
- **Requirements**: Git Bash, WSL, or Cygwin on Windows
- **Command**: `./tools/generate_complete_site.sh --serve`
- **Features**: Use the bash version on Windows

---

## 📁 **Generated Output Structure**

```
docs-site/docs/reports/
├── index.md                    # Main reports hub (no "Coming Soon" text)
├── test-results.md            # Fresh test execution results
├── coverage-report.md         # Code coverage analysis 
├── performance-baselines.md   # Performance baseline dashboard
└── benchmark-results.md       # Benchmark results summary
```

### **Report Content Examples:**

**Coverage Report:**
- Overall: 23.2% coverage (4,740 of 20,422 lines)
- Module breakdown with status indicators
- Quality gate status (above/below thresholds)

**Performance Baselines:**
- Current: 5.46ms ± 6.29ms (95% confidence)
- Trend analysis and historical snapshots
- System information (M1 Pro, 10 cores, etc.)

**Benchmark Results:**
- Latest: 5 benchmarks analyzed
- Performance range: 0.013ms to 10.5ms
- Status tracking and regression detection

**Test Results:**
- Current: 129 tests (116 passed, 11 failed, 1 error, 1 skipped)
- Detailed breakdown by test file
- Color-coded status indicators

---

## 🔧 **Environment Setup**

### **Required Conda Environment:**
```bash
conda activate hazelbean_env
```

### **Key Dependencies (should already be installed):**
- `pytest` - Test execution framework
- `pytest-cov` - Coverage collection
- `pytest-md-report` - Markdown test reports
- `coverage` - Coverage.py API access
- `mkdocs-material` - Documentation site generation

### **Verification:**
```bash
# Check if environment is properly set up
pytest --version
coverage --version
mkdocs --version
```

---

## 🌐 **Accessing Generated Site**

### **Local Development Server:**
```bash
# After generation, serve the site
cd docs-site
mkdocs serve --dev-addr 127.0.0.1:8005
```

### **Direct URLs (when serving):**
- **Main Reports Hub**: http://127.0.0.1:8005/hazelbean_dev/reports/
- **Test Results**: http://127.0.0.1:8005/hazelbean_dev/reports/test-results/
- **Coverage Report**: http://127.0.0.1:8005/hazelbean_dev/reports/coverage-report/
- **Performance Baselines**: http://127.0.0.1:8005/hazelbean_dev/reports/performance-baselines/
- **Benchmark Results**: http://127.0.0.1:8005/hazelbean_dev/reports/benchmark-results/

---

## 🐛 **Troubleshooting**

### **Common Issues:**

#### **"conda activate hazelbean_env" fails**
```bash
# Initialize conda for your shell
conda init
# Restart terminal, then try again
conda activate hazelbean_env
```

#### **"No module named coverage/pytest" errors**
```bash
# Install missing dependencies in conda environment
conda activate hazelbean_env
conda install -c conda-forge coverage pytest pytest-cov pytest-md-report
```

#### **Test failures prevent report generation**
- This is expected and normal
- Scripts continue report generation even with test failures
- GDAL/data file issues are environment-specific, not code issues

#### **Windows PowerShell execution policy**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### **"mkdocs command not found"**
```bash
conda activate hazelbean_env
conda install -c conda-forge mkdocs-material
```

### **Debug Mode:**
Run individual components to isolate issues:
```bash
# Test coverage collection
pytest unit/ --cov=hazelbean --cov-report=term-missing

# Test individual generators
python tools/generate_coverage_report.py
python tools/generate_baseline_report.py
python tools/generate_benchmark_summary.py
```

---

## 🚀 **Integration & Automation**

### **CI/CD Integration:**
These scripts are designed to integrate with GitHub Actions or other CI systems:

```yaml
# Example GitHub Action step
- name: Generate Documentation Site
  run: |
    conda activate hazelbean_env
    ./tools/generate_complete_site.sh
```

### **Pre-commit Hooks:**
```bash
# Add to .pre-commit-config.yaml
- repo: local
  hooks:
    - id: generate-docs
      name: Generate documentation site
      entry: ./tools/generate_complete_site.sh
      language: system
```

### **Development Workflow:**
```bash
# Typical development cycle
1. Make code changes
2. ./tools/generate_complete_site.sh --serve
3. Review reports at http://127.0.0.1:8005/hazelbean_dev/reports/
4. Commit changes
```

---

## 📈 **Performance & Metrics**

### **Generation Speed:**
- **Full test suite + reports**: ~8-10 seconds
- **Reports only (no tests)**: ~2-3 seconds
- **Individual report**: <1 second each

### **Data Sources:**
- **Test Results**: Live pytest execution
- **Coverage**: Fresh coverage.py data collection
- **Baselines**: JSON files in `/metrics/baselines/`
- **Benchmarks**: JSON files in `/metrics/benchmarks/`

### **File Sizes (typical):**
- `test-results.md`: ~4-5KB
- `coverage-report.md`: ~6-7KB  
- `performance-baselines.md`: ~1-2KB
- `benchmark-results.md`: ~1-2KB
- `index.md`: ~3KB

---

## 🎯 **Best Practices**

### **Regular Usage:**
- Run complete site generation before major commits
- Use `--serve` flag for immediate review of changes
- Check all reports are generating successfully

### **Development:**
- Always activate `hazelbean_env` before running scripts
- Run from project root directory
- Use individual generators for debugging specific report issues

### **Maintenance:**
- Reports are automatically generated - never edit manually
- "Coming Soon" text elimination is automatic
- All data sources are dynamic and update automatically

---

## 🤝 **Contributing**

### **Adding New Test Files:**
```bash
# 1. Create your test file in the appropriate directory
touch hazelbean_tests/unit/test_new_feature.py

# 2. Write tests with proper docstrings
# (Tests will be automatically included in reports)

# 3. Regenerate test documentation structure
python tools/generate_clean_test_docs.py

# 4. Regenerate complete site to include new tests
./tools/generate_complete_site.sh

# 5. Verify new tests appear in navigation and reports
```

**What's Automatic vs Manual:**
- ✅ **Automatic**: Test execution results, coverage analysis, performance metrics
- ⚠️ **Manual Trigger Required**: Test documentation structure when adding new test files

### **Adding New Reports:**
1. Create generator script in `tools/`
2. Add to complete site generation scripts
3. Add output verification
4. Update this documentation

### **Modifying Existing Reports:**
1. Edit the appropriate generator script
2. Test with individual generator first
3. Test with complete site generation
4. Update documentation if interface changes

### **Platform Support:**
- Bash script: Primary reference implementation
- PowerShell: Windows-native equivalent
- Batch: Universal Windows compatibility
- All should maintain feature parity

---

*This documentation covers all site generation tools as of 2025-09-18. For the most up-to-date information, see the actual script files and their inline comments.*
