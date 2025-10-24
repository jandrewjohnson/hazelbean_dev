# Hazelbean Baseline Management Demos

> **Story 6: Baseline Establishment** - Interactive Examples & Demonstrations

This directory contains interactive demonstration scripts that showcase the Hazelbean baseline management system capabilities. These are **educational examples** designed to help maintainers understand and explore the baseline functionality.

## 🎯 **What This Directory Contains**

### Interactive Demonstrations
- `interactive_baseline_demo.py` - Menu-driven exploration of baseline features
- `integration_demo.py` - Complete workflow demonstrations with real benchmark data

### Production Tools (located elsewhere)
- `../../scripts/establish_performance_baseline.py` - Production CLI tool
- `../../hazelbean_tests/performance/test_baseline_manager.py` - Unit test suite
- `../../docs/BASELINE_TESTING_GUIDE.md` - Complete documentation

## 🚀 **Quick Start**

### 1. Interactive Menu Demo
```bash
cd examples/baseline_management_demos
python interactive_baseline_demo.py
```

**Provides menu-driven access to:**
- ✅ Baseline creation with sample data
- ✅ Regression detection simulation (5% vs 15% scenarios)
- ✅ Trend analysis with historical data
- ✅ Real benchmark file processing
- ✅ Error handling demonstrations

### 2. Integration Workflow Demo
```bash
python integration_demo.py
```

**Demonstrates complete workflows:**
- 🔄 Run benchmarks → Establish baseline → Compare → Report
- 📊 Real metrics directory integration
- ⚡ Mini performance test suite creation

### 3. Production CLI (Recommended)
```bash
# From project root
python scripts/establish_performance_baseline.py --demo
```

## 📋 **Demo Menu Options**

### Interactive Demo Menu
```
🚀 HAZELBEAN BASELINE TESTING MENU
========================================
1. Test Baseline Creation
2. Test Regression Detection
3. Test Trend Analysis
4. Test with Real Benchmark Files
5. Test Error Handling
6. Run All Tests
7. Exit
```

### Integration Demo Menu
```
🧪 HAZELBEAN BENCHMARK INTEGRATION TESTER
=======================================================
1. Complete Workflow Demonstration
2. Real Metrics Integration Test
3. Create Mini Performance Test Suite
4. Run All Tests
5. Exit
```

## 🎓 **What You'll Learn**

### Baseline Creation (Demo 1)
- **JSON Structure**: Comprehensive v2.0.0 schema with metadata
- **Quality Scoring**: Statistical reliability assessment (0-100 scale)
- **Categorization**: Automatic benchmark grouping by functionality
- **Version Control**: Git integration and historical snapshots

**Example Output:**
```
✅ Baseline created: /tmp/.../performance_baseline_v2.json
📊 Total benchmarks: 3
🎯 Quality score: 30.0/100
```

### Regression Detection (Demo 2)
- **Threshold Testing**: 5% improvement vs 15% degradation
- **Severity Classification**: Minor/Major/Critical levels
- **Statistical Analysis**: Two-standard-deviation significance testing
- **Actionable Insights**: Automated recommendations

**Example Output:**
```
🔍 Testing: 15% degradation (should detect REGRESSION)
📈 Result: regression_detected
⚠️  Detected regressions:
   🔻 test_get_path_benchmark: +15.0% (minor_regression)
```

### Trend Analysis (Demo 3)
- **Historical Tracking**: Multi-baseline performance trends
- **Performance Health**: Good/Concerning/Poor classification
- **Benchmark Categorization**: Improving/Degrading/Stable groupings
- **Statistical Confidence**: Linear regression with trend detection

**Example Output:**
```
📊 Overall Trend: DEGRADING
📈 Performance Change: +12.0%
🏥 Performance Health: CONCERNING
```

### Real Data Processing (Demo 4)
- **Metrics Integration**: Works with existing benchmark files
- **Production Quality**: Handles real benchmark complexity
- **Validation**: Shows valid vs invalid benchmark processing
- **Quality Assessment**: Real-world quality scoring

## 🔧 **Advanced Usage Examples**

### Programmatic Baseline Creation
```python
from performance.baseline_manager import BaselineManager

# Initialize with custom directory
manager = BaselineManager("custom/metrics/dir")

# Create baseline from benchmark data
baseline = manager.create_standardized_baseline_structure(benchmark_data)
baseline_path = manager.save_baseline(baseline)

# Generate human-readable report
report = manager.generate_baseline_report(baseline)
print(report)
```

### Automated Regression Detection
```python
# Load current benchmark results
comparison = manager.compare_with_baseline(current_data)

# Handle regressions programmatically
if comparison["overall_status"] == "regression_detected":
    for benchmark, analysis in comparison["regression_analysis"].items():
        if analysis["is_regression"]:
            severity = analysis["severity"]
            change = analysis["percent_change"]
            print(f"🔻 {benchmark}: {change:+.1f}% ({severity})")
```

### Performance Trend Monitoring
```python
# Analyze trends over time
trends = manager.analyze_trends(lookback_days=30)
trajectory = trends["performance_trajectory"]

# Get health assessment
health = trajectory["performance_health"]  # good/concerning/poor
change = trajectory["overall_change_percent"]
trend = trajectory["overall_trend"]        # improving/degrading/stable
```

## 📊 **Understanding Output**

### Quality Score Interpretation
- **90-100**: Excellent baseline quality, low variance, good sample size
- **70-89**: Good quality, acceptable variance, sufficient data
- **50-69**: Moderate quality, may have higher variance
- **30-49**: Poor quality, investigate variance or sample size
- **0-29**: Very poor quality, baseline may not be reliable

### Regression Severity Levels
- **No Regression**: <10% performance change (default threshold)
- **Minor Regression**: 10-20% performance degradation  
- **Major Regression**: 20-50% performance degradation
- **Critical Regression**: >50% performance degradation

### Performance Health Categories
- **Good**: <5% overall performance change
- **Concerning**: 5-15% performance degradation
- **Poor**: >15% performance degradation

## 🔗 **Integration with Production**

These demos are designed to complement the production tooling:

### For Development Workflow:
1. **Use demos** to understand capabilities and explore features
2. **Use CLI script** for production baseline establishment
3. **Use unit tests** for validation and CI/CD integration

### For CI/CD Pipeline:
```bash
# Establish baseline
python scripts/establish_performance_baseline.py --establish

# Compare against baseline
python scripts/establish_performance_baseline.py --compare

# Analyze trends
python scripts/establish_performance_baseline.py --trends --lookback-days 14
```

## 🎉 **Next Steps**

After exploring these demos:

1. **Read the comprehensive guide**: `../../docs/BASELINE_TESTING_GUIDE.md`
2. **Run the unit tests**: `pytest ../../hazelbean_tests/performance/test_baseline_manager.py -v`
3. **Integrate with your workflow**: Use the production CLI for real baseline management
4. **Customize thresholds**: Adjust regression detection sensitivity for your needs

## 📁 **File Structure**
```
examples/baseline_management_demos/
├── README.md                     # This documentation
├── interactive_baseline_demo.py  # Menu-driven exploration
└── integration_demo.py          # Workflow demonstrations

Related files:
├── ../../scripts/establish_performance_baseline.py  # Production CLI
├── ../../hazelbean_tests/performance/
│   ├── baseline_manager.py                         # Core implementation  
│   └── test_baseline_manager.py                    # Unit tests
└── ../../docs/BASELINE_TESTING_GUIDE.md           # Complete guide
```

---

**These examples demonstrate the complete Story 6: Baseline Establishment implementation, providing maintainers with comprehensive tools for performance monitoring, regression detection, and trend analysis within the Hazelbean development workflow.**
