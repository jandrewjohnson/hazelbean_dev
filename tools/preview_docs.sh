#!/bin/bash
# Convenience script to generate reports and preview Quarto docs
# This avoids the infinite loop that occurs when pre-render regenerates .qmd files

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Generating reports..."
python "$SCRIPT_DIR/generate_all_reports.py"

echo "Starting Quarto preview..."
cd "$PROJECT_ROOT/docs-site/quarto-docs"
quarto preview
