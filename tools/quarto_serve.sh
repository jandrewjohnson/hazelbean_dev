#!/bin/bash
#
# Quarto Site Preview Server
# Serves the Quarto documentation site with live reload
#
# Usage: ./tools/quarto_serve.sh [--render]
#   --render: Render the site before serving
#

# Colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Check if we should render first
RENDER_FIRST=false
if [[ "$1" == "--render" ]]; then
    RENDER_FIRST=true
fi

# Get script directory and navigate to quarto-docs
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
QUARTO_DIR="$PROJECT_ROOT/docs-site/quarto-docs"

if [[ ! -d "$QUARTO_DIR" ]]; then
    print_error "Quarto directory not found at: $QUARTO_DIR"
    exit 1
fi

cd "$QUARTO_DIR" || exit 1

print_step "Quarto Documentation Server"
echo ""

# Check conda environment
if [[ "$CONDA_DEFAULT_ENV" != "hazelbean_env" ]]; then
    print_warning "Not in hazelbean_env conda environment"
    print_step "Activating hazelbean_env..."
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate hazelbean_env
else
    print_success "hazelbean_env conda environment active"
fi

# Optionally render first
if [[ "$RENDER_FIRST" == "true" ]]; then
    print_step "Rendering site before serving..."
    quarto render
    if [[ $? -ne 0 ]]; then
        print_error "Rendering failed!"
        exit 1
    fi
    print_success "Site rendered successfully"
    echo ""
fi

# Start the preview server
echo "🌐 Starting Quarto preview server..."
echo ""
echo "📋 The site will be available at a local address (Quarto will display it below)"
echo "🔄 Live reload is enabled - changes will update automatically"
echo ""
print_step "Press Ctrl+C to stop the server"
echo ""

quarto preview

