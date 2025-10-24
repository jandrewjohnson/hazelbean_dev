# Test Results and Metrics

Automated reporting of test execution results, performance metrics, and system validation.

## 📊 Live Test Dashboard

For the most current test results, see our **[Latest Test Results](test-results.md)** with real-time metrics and detailed analysis.

## Current Status

### Test Execution Summary

!!! info "Live Test Metrics"
    For the most current test metrics, see **[Latest Test Results](test-results.md)** - automatically updated with each test run.

### Performance Metrics
- **Benchmark Results** - Latest performance measurements
- **Memory Usage** - Resource utilization tracking
- **Execution Speed** - Processing time analysis
- **Scalability Metrics** - Large dataset processing performance

## 📋 Available Reports

### 🔍 **[Test Results](test-results.md)**
- Detailed test execution results with timing analysis
- Failed test analysis and error reporting  
- Performance metrics for all test categories
- Generated automatically from pytest JSON output

### 📈 **Performance Baselines**
**Available** - [View Performance Baselines](performance-baselines.md)
- Real-time performance baseline tracking with trend analysis
- Statistical confidence intervals and machine context
- Historical snapshot comparisons and regression detection

### 📊 **Coverage Reports**
**Available** - [View Coverage Report](coverage-report.md)
- Module-by-module coverage analysis with detailed breakdowns
- Coverage trends and quality gate monitoring
- Missing line identification and improvement suggestions

### ⚡ **Benchmark Results**
**Available** - [View Benchmark Results](benchmark-results.md)
- Latest benchmark execution results with performance analysis
- Historical trend tracking and regression detection
- Detailed timing statistics and system information

## 🔄 Report Generation

### Automated Updates
Reports are automatically generated from:
- **pytest JSON output** → Test result tables and metrics
- **Performance benchmarks** → Timing and efficiency analysis  
- **Code coverage tools** → Coverage percentage and gap analysis
- **CI/CD pipelines** → Build and deployment status

### Manual Report Generation
To update test reports manually:
```bash
# From hazelbean_tests directory
conda activate hazelbean_env
pytest unit/ integration/ --json-report --json-report-file=test-results.json --quiet
python ../tools/generate_test_report_md.py test-results.json -o ../docs-site/docs/reports/test-results.md
```

### Report Schedule
- **Test Results**: Updated after each test run
- **Performance Metrics**: Updated during development cycles
- **Coverage Analysis**: Updated with major releases
- **Quality Gates**: Continuous monitoring

---

*Reports reflect the most recent test execution and system analysis. All data is generated from actual test runs and system measurements.*
