#
# Complete Site Generation - Windows PowerShell Version
# Generates the entire documentation site with the most up-to-date data
#
# Usage: .\tools\generate_complete_site.ps1 [-Serve]
#   -Serve: Start the mkdocs development server after generation
#

param(
    [switch]$Serve
)

# Function to print colored output
function Write-Step {
    param($Message)
    Write-Host "🚀 $Message" -ForegroundColor Blue
}

function Write-Success {
    param($Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warning {
    param($Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Error {
    param($Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

Write-Step "Starting complete site generation with fresh data..."

# Get script directory and ensure we're in the right place
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Step "Project root: $ProjectRoot"

# Step 1: Check conda environment
$CurrentEnv = $env:CONDA_DEFAULT_ENV
if ($CurrentEnv -ne "hazelbean_env") {
    Write-Step "Activating hazelbean_env conda environment..."
    
    # Try to activate conda environment
    try {
        # Initialize conda for PowerShell if not already done
        & conda shell.powershell hook | Invoke-Expression
        conda activate hazelbean_env
        Write-Success "hazelbean_env conda environment activated"
    }
    catch {
        Write-Warning "Could not activate conda environment automatically."
        Write-Host "Please run 'conda activate hazelbean_env' manually before running this script."
        exit 1
    }
} else {
    Write-Success "hazelbean_env conda environment already active"
}

# Step 2: Generate fresh test results and coverage data
Write-Step "Running complete test suite with fresh coverage data..."
Set-Location "hazelbean_tests"

# Run tests with coverage to get the absolute latest data
$TestArgs = @(
    "unit/", "integration/", "system/",
    "--cov=hazelbean",
    "--cov-report=term-missing",
    "--md-report",
    "--md-report-flavor", "gfm",
    "--md-report-output", "../docs-site/docs/reports/test-results.md",
    "--tb=short",
    "--quiet"
)

try {
    & pytest @TestArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Some tests failed, but continuing with report generation..."
    }
    Write-Success "Test execution completed, coverage data collected"
}
catch {
    Write-Warning "Test execution had issues, but continuing with report generation..."
}

# Step 3: Generate all reports with fresh data
Set-Location $ProjectRoot

Write-Step "Generating coverage report from fresh data..."
& python tools/generate_coverage_report.py

Write-Step "Generating performance baselines dashboard..."  
& python tools/generate_baseline_report.py

Write-Step "Generating benchmark results summary..."
& python tools/generate_benchmark_summary.py

Write-Step "Updating reports index and eliminating 'Coming Soon' text..."
& python tools/update_reports_index.py

Write-Success "All reports generated with fresh data"

# Step 4: Verify all report files exist
Write-Step "Verifying all report files..."
$ReportsDir = Join-Path $ProjectRoot "docs-site\docs\reports"
$RequiredFiles = @(
    "test-results.md",
    "coverage-report.md", 
    "performance-baselines.md",
    "benchmark-results.md",
    "index.md"
)

$AllFilesExist = $true
foreach ($file in $RequiredFiles) {
    $FilePath = Join-Path $ReportsDir $file
    if (Test-Path $FilePath) {
        Write-Success "✓ $file generated"
    } else {
        Write-Error "✗ $file missing!"
        $AllFilesExist = $false
    }
}

if (-not $AllFilesExist) {
    Write-Error "Some report files are missing - check the generation logs above"
    exit 1
}

Write-Success "All required report files generated successfully"

# Step 5: Verify no "Coming Soon" text remains
Write-Step "Verifying 'Coming Soon' text elimination..."
$IndexPath = Join-Path $ReportsDir "index.md"
$IndexContent = Get-Content $IndexPath -Raw
if ($IndexContent -match "Coming Soon") {
    Write-Error "'Coming Soon' text still found in index.md!"
    exit 1
} else {
    Write-Success "'Coming Soon' text successfully eliminated"
}

# Step 6: Display generation summary
Write-Step "Site generation summary:"
Write-Host ""
Write-Host "📊 Generated Reports:"

Get-ChildItem -Path $ReportsDir -Filter "*.md" | ForEach-Object {
    $SizeKB = [math]::Round($_.Length / 1KB, 1)
    $Timestamp = $_.LastWriteTime.ToString("MMM dd HH:mm")
    Write-Host "  ✓ $($_.Name) ($($SizeKB)KB) - $Timestamp"
}

# Get test metrics for summary
$TestResultsPath = Join-Path $ReportsDir "test-results.md"
if (Test-Path $TestResultsPath) {
    Write-Host ""
    Write-Host "📋 Test Summary:"
    $TestContent = Get-Content $TestResultsPath -Raw
    if ($TestContent -match "TOTAL") {
        Write-Host "  Latest test results included in reports"
    }
}

Write-Success "Complete site generation finished!"

# Step 7: Optionally start the docs server
if ($Serve) {
    Write-Step "Starting mkdocs development server..."
    $DocsDir = Join-Path $ProjectRoot "docs-site"
    Set-Location $DocsDir
    
    Write-Host ""
    Write-Host "🌐 Site will be available at: http://127.0.0.1:8005/hazelbean_dev/reports/"
    Write-Host "📋 Direct report links:"
    Write-Host "  • Test Results: http://127.0.0.1:8005/hazelbean_dev/reports/test-results/"
    Write-Host "  • Coverage Report: http://127.0.0.1:8005/hazelbean_dev/reports/coverage-report/"
    Write-Host "  • Performance Baselines: http://127.0.0.1:8005/hazelbean_dev/reports/performance-baselines/"
    Write-Host "  • Benchmark Results: http://127.0.0.1:8005/hazelbean_dev/reports/benchmark-results/"
    Write-Host ""
    Write-Step "Press Ctrl+C to stop the server"
    Write-Host ""
    
    & mkdocs serve --dev-addr 127.0.0.1:8005
} else {
    Write-Host ""
    Write-Host "🌐 To view the generated site, run:"
    Write-Host "  cd $ProjectRoot\docs-site"
    Write-Host "  mkdocs serve --dev-addr 127.0.0.1:8005"
    Write-Host ""
    Write-Host "📋 Or use this complete command to generate and serve:"
    Write-Host "  .\tools\generate_complete_site.ps1 -Serve"
}
