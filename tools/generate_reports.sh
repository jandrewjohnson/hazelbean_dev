#!/bin/bash
#
# Simplified Test Report Generation Workflow
# Replaces complex 2-step JSON process with elegant single-step solution
#
# Story 5: Site Polish & Validation - Using pytest-md-report plugin
#

# Note: Removed 'set -e' so we continue report generation even if tests fail

echo "🚀 Starting simplified test report generation..."

# Ensure we're in the right directory
cd "$(dirname "$0")/../hazelbean_tests" || exit 1

# Check if conda environment is already active
if [[ "$CONDA_DEFAULT_ENV" != "hazelbean_env" ]]; then
    echo "📦 Activating hazelbean_env conda environment..."
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate hazelbean_env
else
    echo "📦 hazelbean_env conda environment already active"
fi

# Step 1: Run tests with pytest-md-report (replaces complex 2-step process)
echo "🧪 Running tests and generating markdown report directly..."
pytest unit/ integration/ system/ \
    --md-report \
    --md-report-flavor gfm \
    --md-report-output ../docs-site/docs/reports/test-results.md \
    --tb=short

# Step 2: Generate all missing report components directly to markdown
echo "📊 Generating coverage reports (direct to markdown)..."
cd ..
python tools/generate_coverage_report.py

echo "⚡ Generating performance baselines..."  
python tools/generate_baseline_report.py

echo "📈 Generating benchmark summary..."
python tools/generate_benchmark_summary.py

# Step 3: Update dynamic index with current metrics and eliminate "Coming Soon"
echo "📋 Updating reports index with current metrics..."
python tools/update_reports_index.py

echo "✅ Report generation complete!"
echo ""
echo "📋 Generated files:"
echo "   - docs-site/docs/reports/test-results.md (detailed test report)"
echo "   - docs-site/docs/reports/coverage-report.md (code coverage analysis)"
echo "   - docs-site/docs/reports/performance-baselines.md (performance tracking)"
echo "   - docs-site/docs/reports/benchmark-results.md (benchmark summary)"
echo "   - docs-site/docs/reports/index.md (updated with current metrics - no more 'Coming Soon')"
echo ""
echo "🌐 View reports at: http://127.0.0.1:8005/hazelbean_dev/reports/"
echo "   (Start docs server with: cd docs-site && mkdocs serve --dev-addr 127.0.0.1:8005)"
