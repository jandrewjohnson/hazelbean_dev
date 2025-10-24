#!/bin/bash
#
# Complete Site Generation - Single Command Solution
# Generates the entire documentation site with the most up-to-date data
#
# Usage: ./tools/generate_complete_site.sh [--serve]
#   --serve: Start the mkdocs development server after generation
#

# Colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${BLUE}🚀 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we should serve the site
SERVE_SITE=false
if [[ "$1" == "--serve" ]]; then
    SERVE_SITE=true
fi

print_step "Starting complete site generation with fresh data..."

# Get script directory and ensure we're in the right place
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

print_step "Project root: $PROJECT_ROOT"

# Step 1: Check conda environment
if [[ "$CONDA_DEFAULT_ENV" != "hazelbean_env" ]]; then
    print_step "Activating hazelbean_env conda environment..."
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate hazelbean_env
else
    print_success "hazelbean_env conda environment already active"
fi

# Step 2: Generate fresh test results and coverage data
print_step "Running complete test suite with fresh coverage data..."
cd hazelbean_tests || exit 1

# Run tests with coverage to get the absolute latest data
pytest unit/ integration/ system/ \
    --cov=hazelbean \
    --cov-report=term-missing \
    --md-report \
    --md-report-flavor gfm \
    --md-report-output ../docs-site/docs/reports/test-results.md \
    --tb=short \
    --quiet || print_warning "Some tests failed, but continuing with report generation..."

print_success "Test execution completed, coverage data collected"

# Step 3: Generate all reports with fresh data
cd "$PROJECT_ROOT"

print_step "Generating coverage report from fresh data..."
python tools/generate_coverage_report.py

print_step "Generating performance baselines dashboard..."  
python tools/generate_baseline_report.py

print_step "Generating benchmark results summary..."
python tools/generate_benchmark_summary.py

print_step "Updating reports index and eliminating 'Coming Soon' text..."
python tools/update_reports_index.py

print_success "All reports generated with fresh data"

# Step 4: Verify all report files exist
print_step "Verifying all report files..."
REPORTS_DIR="$PROJECT_ROOT/docs-site/docs/reports"
REQUIRED_FILES=(
    "test-results.md"
    "coverage-report.md" 
    "performance-baselines.md"
    "benchmark-results.md"
    "index.md"
)

ALL_FILES_EXIST=true
for file in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$REPORTS_DIR/$file" ]]; then
        print_success "✓ $file generated"
    else
        print_error "✗ $file missing!"
        ALL_FILES_EXIST=false
    fi
done

if [[ "$ALL_FILES_EXIST" == "true" ]]; then
    print_success "All required report files generated successfully"
else
    print_error "Some report files are missing - check the generation logs above"
    exit 1
fi

# Step 5: Verify no "Coming Soon" text remains
print_step "Verifying 'Coming Soon' text elimination..."
if grep -q "Coming Soon" "$REPORTS_DIR/index.md"; then
    print_error "'Coming Soon' text still found in index.md!"
    exit 1
else
    print_success "'Coming Soon' text successfully eliminated"
fi

# Step 6: Display generation summary
print_step "Site generation summary:"
echo ""
echo "📊 Generated Reports:"
ls -la "$REPORTS_DIR/" | grep -E '\.md$' | while read -r line; do
    filename=$(echo "$line" | awk '{print $9}')
    filesize=$(echo "$line" | awk '{print $5}')
    timestamp=$(echo "$line" | awk '{print $6, $7, $8}')
    echo "  ✓ $filename (${filesize}B) - $timestamp"
done

# Get test metrics for summary
if [[ -f "$REPORTS_DIR/test-results.md" ]]; then
    echo ""
    echo "📋 Test Summary:"
    # Extract metrics from the generated test results
    if grep -q "TOTAL" "$REPORTS_DIR/test-results.md"; then
        TOTAL_LINE=$(grep "TOTAL" "$REPORTS_DIR/test-results.md" | head -1)
        echo "  Latest test results included in reports"
    fi
fi

print_success "Complete site generation finished!"

# Step 7: Optionally start the docs server
if [[ "$SERVE_SITE" == "true" ]]; then
    print_step "Starting mkdocs development server..."
    cd "$PROJECT_ROOT/docs-site" || exit 1
    
    echo ""
    echo "🌐 Site will be available at: http://127.0.0.1:8005/hazelbean_dev/reports/"
    echo "📋 Direct report links:"
    echo "  • Test Results: http://127.0.0.1:8005/hazelbean_dev/reports/test-results/"
    echo "  • Coverage Report: http://127.0.0.1:8005/hazelbean_dev/reports/coverage-report/"
    echo "  • Performance Baselines: http://127.0.0.1:8005/hazelbean_dev/reports/performance-baselines/"
    echo "  • Benchmark Results: http://127.0.0.1:8005/hazelbean_dev/reports/benchmark-results/"
    echo ""
    print_step "Press Ctrl+C to stop the server"
    echo ""
    
    mkdocs serve --dev-addr 127.0.0.1:8005
else
    echo ""
    echo "🌐 To view the generated site, run:"
    echo "  cd $PROJECT_ROOT/docs-site && mkdocs serve --dev-addr 127.0.0.1:8005"
    echo ""
    echo "📋 Or use this complete command to generate and serve:"
    echo "  $PROJECT_ROOT/tools/generate_complete_site.sh --serve"
fi
