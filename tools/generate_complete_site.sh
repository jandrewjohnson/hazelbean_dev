#!/bin/bash
#
# Complete Site Generation - Single Command Solution (Quarto)
# Generates the entire Quarto documentation site with the most up-to-date data
#
# Usage: ./tools/generate_complete_site.sh [--serve]
#   --serve: Start the Quarto preview server after generation
#
# This script:
# 1. Runs pytest with JSON reporting (for Quarto generators)
# 2. Generates all .qmd reports in docs-site/quarto-docs/reports/
# 3. Optionally serves with Quarto preview
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

# Run tests with coverage and JSON reporting for Quarto
python -m pytest unit/ integration/ system/ \
    --cov=hazelbean \
    --cov-report=json:coverage.json \
    --cov-report=term-missing \
    --json-report \
    --json-report-file=test-results.json \
    --tb=short \
    --quiet || print_warning "Some tests failed, but continuing with report generation..."

print_success "Test execution completed, JSON reports generated for Quarto"

# Step 3: Generate all reports with fresh data
cd "$PROJECT_ROOT"

print_step "Generating test results report from JSON data..."
python tools/generate_test_results_report.py hazelbean_tests/test-results.json

print_step "Generating coverage report from JSON data..."
python tools/generate_coverage_report.py

print_step "Generating performance baselines dashboard..."  
python tools/generate_baseline_report.py

print_step "Generating benchmark results summary..."
python tools/generate_benchmark_summary.py

print_success "All Quarto reports generated with fresh data"

# Step 4: Verify all report files exist
print_step "Verifying all report files..."
REPORTS_DIR="$PROJECT_ROOT/docs-site/quarto-docs/reports"
REQUIRED_FILES=(
    "test-results.qmd"
    "coverage-report.qmd" 
    "performance-baselines.qmd"
    "benchmark-results.qmd"
    "index.qmd"
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

# Step 5: Verify no "Coming Soon" text remains (removed - not applicable to current setup)

# Step 6: Display generation summary
print_step "Site generation summary:"
echo ""
echo "📊 Generated Reports:"
ls -la "$REPORTS_DIR/" | grep -E '\.qmd$' | while read -r line; do
    filename=$(echo "$line" | awk '{print $9}')
    filesize=$(echo "$line" | awk '{print $5}')
    timestamp=$(echo "$line" | awk '{print $6, $7, $8}')
    echo "  ✓ $filename (${filesize}B) - $timestamp"
done

# Get test metrics for summary
RESULTS_FILE="$PROJECT_ROOT/hazelbean_tests/test-results.json"
if [[ -f "$RESULTS_FILE" ]]; then
    echo ""
    echo "📋 Test Summary:"
    # Extract metrics from JSON using Python
    METRICS=$(python -c "import json; data=json.load(open('$RESULTS_FILE')); s=data.get('summary',{}); print(f\"Passed: {s.get('passed',0)}, Failed: {s.get('failed',0)}, Skipped: {s.get('skipped',0)}, Total: {s.get('total',0)}\")" 2>/dev/null)
    if [[ -n "$METRICS" ]]; then
        echo "  $METRICS"
    else
        echo "  Latest test results included in reports"
    fi
fi

print_success "Complete site generation finished!"

# Step 7: Optionally start the docs server
if [[ "$SERVE_SITE" == "true" ]]; then
    print_step "Starting Quarto preview server..."
    cd "$PROJECT_ROOT/docs-site/quarto-docs" || exit 1
    
    echo ""
    echo "🌐 Quarto site will be available at: http://localhost:XXXX (Quarto assigns port)"
    echo "📋 Direct report links will be shown by Quarto"
    echo ""
    print_step "Press Ctrl+C to stop the server"
    echo ""
    
    quarto preview
else
    echo ""
    echo "🌐 To view the generated site, run:"
    echo "  cd $PROJECT_ROOT/docs-site/quarto-docs && quarto preview"
    echo ""
    echo "📋 Or use this complete command to generate and serve:"
    echo "  $PROJECT_ROOT/tools/generate_complete_site.sh --serve"
    echo ""
    echo "💡 You can also use the dedicated serve script:"
    echo "  $PROJECT_ROOT/tools/quarto_serve.sh"
fi
