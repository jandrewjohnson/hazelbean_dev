@echo off
REM Complete Site Generation - Windows Batch Version
REM Generates the entire documentation site with the most up-to-date data
REM
REM Usage: tools\generate_complete_site.cmd [serve]
REM   serve: Start the mkdocs development server after generation

setlocal enabledelayedexpansion

echo 🚀 Starting complete site generation with fresh data...

REM Get script directory and ensure we're in the right place
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
cd /d "%PROJECT_ROOT%"

echo 🚀 Project root: %PROJECT_ROOT%

REM Step 1: Check conda environment
if not "%CONDA_DEFAULT_ENV%"=="hazelbean_env" (
    echo 📦 Activating hazelbean_env conda environment...
    call conda activate hazelbean_env
    if errorlevel 1 (
        echo ❌ Could not activate conda environment
        echo Please run 'conda activate hazelbean_env' manually before running this script.
        exit /b 1
    )
    echo ✅ hazelbean_env conda environment activated
) else (
    echo ✅ hazelbean_env conda environment already active
)

REM Step 2: Generate fresh test results and coverage data
echo 🚀 Running complete test suite with fresh coverage data...
cd hazelbean_tests

pytest unit/ integration/ system/ --cov=hazelbean --cov-report=term-missing --md-report --md-report-flavor gfm --md-report-output ../docs-site/docs/reports/test-results.md --tb=short --quiet
if errorlevel 1 (
    echo ⚠️  Some tests failed, but continuing with report generation...
) else (
    echo ✅ Test execution completed, coverage data collected
)

REM Step 3: Generate all reports with fresh data
cd "%PROJECT_ROOT%"

echo 🚀 Generating coverage report from fresh data...
python tools/generate_coverage_report.py

echo 🚀 Generating performance baselines dashboard...  
python tools/generate_baseline_report.py

echo 🚀 Generating benchmark results summary...
python tools/generate_benchmark_summary.py

echo 🚀 Updating reports index and eliminating 'Coming Soon' text...
python tools/update_reports_index.py

echo ✅ All reports generated with fresh data

REM Step 4: Verify all report files exist
echo 🚀 Verifying all report files...
set REPORTS_DIR=%PROJECT_ROOT%\docs-site\docs\reports
set ALL_FILES_EXIST=1

if exist "%REPORTS_DIR%\test-results.md" (
    echo ✅ ✓ test-results.md generated
) else (
    echo ❌ ✗ test-results.md missing!
    set ALL_FILES_EXIST=0
)

if exist "%REPORTS_DIR%\coverage-report.md" (
    echo ✅ ✓ coverage-report.md generated
) else (
    echo ❌ ✗ coverage-report.md missing!
    set ALL_FILES_EXIST=0
)

if exist "%REPORTS_DIR%\performance-baselines.md" (
    echo ✅ ✓ performance-baselines.md generated
) else (
    echo ❌ ✗ performance-baselines.md missing!
    set ALL_FILES_EXIST=0
)

if exist "%REPORTS_DIR%\benchmark-results.md" (
    echo ✅ ✓ benchmark-results.md generated
) else (
    echo ❌ ✗ benchmark-results.md missing!
    set ALL_FILES_EXIST=0
)

if exist "%REPORTS_DIR%\index.md" (
    echo ✅ ✓ index.md generated
) else (
    echo ❌ ✗ index.md missing!
    set ALL_FILES_EXIST=0
)

if %ALL_FILES_EXIST%==0 (
    echo ❌ Some report files are missing - check the generation logs above
    exit /b 1
)

echo ✅ All required report files generated successfully

REM Step 5: Verify no "Coming Soon" text remains
echo 🚀 Verifying 'Coming Soon' text elimination...
findstr /C:"Coming Soon" "%REPORTS_DIR%\index.md" >nul
if errorlevel 1 (
    echo ✅ 'Coming Soon' text successfully eliminated
) else (
    echo ❌ 'Coming Soon' text still found in index.md!
    exit /b 1
)

REM Step 6: Display generation summary
echo 🚀 Site generation summary:
echo.
echo 📊 Generated Reports:
dir "%REPORTS_DIR%\*.md" /b 2>nul | findstr /v "^$"
if errorlevel 1 (
    echo   No markdown files found
) else (
    for %%f in ("%REPORTS_DIR%\*.md") do (
        echo   ✓ %%~nxf
    )
)

echo.
echo 📋 Test Summary:
if exist "%REPORTS_DIR%\test-results.md" (
    echo   Latest test results included in reports
)

echo ✅ Complete site generation finished!

REM Step 7: Optionally start the docs server
if /i "%1"=="serve" (
    echo 🚀 Starting mkdocs development server...
    cd docs-site
    
    echo.
    echo 🌐 Site will be available at: http://127.0.0.1:8005/hazelbean_dev/reports/
    echo 📋 Direct report links:
    echo   • Test Results: http://127.0.0.1:8005/hazelbean_dev/reports/test-results/
    echo   • Coverage Report: http://127.0.0.1:8005/hazelbean_dev/reports/coverage-report/
    echo   • Performance Baselines: http://127.0.0.1:8005/hazelbean_dev/reports/performance-baselines/
    echo   • Benchmark Results: http://127.0.0.1:8005/hazelbean_dev/reports/benchmark-results/
    echo.
    echo 🚀 Press Ctrl+C to stop the server
    echo.
    
    mkdocs serve --dev-addr 127.0.0.1:8005
) else (
    echo.
    echo 🌐 To view the generated site, run:
    echo   cd %PROJECT_ROOT%\docs-site
    echo   mkdocs serve --dev-addr 127.0.0.1:8005
    echo.
    echo 📋 Or use this complete command to generate and serve:
    echo   %PROJECT_ROOT%\tools\generate_complete_site.cmd serve
)
