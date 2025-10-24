#!/bin/bash

# QMD Automation CLI Demo Workflow
# This script demonstrates typical usage patterns for the QMD Automation CLI

echo "🚀 QMD Automation CLI Demo Workflow"
echo "=================================="

echo ""
echo "1. 📊 Checking system status..."
python -m hazelbean_tests.qmd_automation.cli status

echo ""
echo "2. ✅ Validating configuration..."
python -m hazelbean_tests.qmd_automation.cli config validate

echo ""
echo "3. 🔍 Analyzing current test quality..."
python -m hazelbean_tests.qmd_automation.cli analyze

echo ""
echo "4. 📋 Showing current configuration..."
python -m hazelbean_tests.qmd_automation.cli config show

echo ""
echo "5. 🧪 Testing dry-run generation..."
python -m hazelbean_tests.qmd_automation.cli generate --dry-run --full

echo ""
echo "6. 📈 Generating quality report in JSON format..."
python -m hazelbean_tests.qmd_automation.cli quality-report --format json

echo ""
echo "7. 🔄 Demonstrating incremental generation with verbose output..."
python -m hazelbean_tests.qmd_automation.cli --verbose generate --incremental

echo ""
echo "8. 📊 Final status check..."
python -m hazelbean_tests.qmd_automation.cli status --format json

echo ""
echo "✅ Demo workflow completed!"
echo ""
echo "📚 For more information:"
echo "   • Full documentation: docs/cli_usage_guide.md"
echo "   • Quick reference: docs/cli_quick_reference.md"
echo "   • Help system: python -m hazelbean_tests.qmd_automation.cli --help"
