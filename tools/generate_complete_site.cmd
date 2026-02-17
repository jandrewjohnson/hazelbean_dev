@echo off
REM Complete Site Generation - Single Command Solution (Quarto) - Windows Version
REM Generates the entire Quarto documentation site with the most up-to-date data
REM
REM Usage: tools\generate_complete_site.cmd [--serve]
REM   --serve: Start the Quarto preview server after generation

setlocal enabledelayedexpansion

REM Colors for Windows (limited)
set "BLUE=[94m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "NC=[0m"

echo %BLUE%Starting complete site generation with fresh data...%NC%

REM Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%" || exit /b 1

echo %BLUE%Project root: %PROJECT_ROOT%%NC%

REM Check if conda is available
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo %RED%Error: conda not found in PATH%NC%
    exit /b 1
)

REM Activate conda environment
echo %BLUE%Activating hazelbean_env conda environment...%NC%
call conda activate hazelbean_env
if %errorlevel% neq 0 (
    echo %RED%Failed to activate hazelbean_env%NC%
    exit /b 1
)
echo %GREEN%hazelbean_env conda environment activated%NC%

REM Step 2: Generate fresh test results and coverage data
echo %BLUE%Running complete test suite with fresh coverage data...%NC%
cd hazelbean_tests || exit /b 1

REM Run tests with coverage and JSON reporting for Quarto
python -m pytest unit/ integration/ system/ ^
    --cov=hazelbean ^
    --cov-report=json:coverage.json ^
    --cov-report=term-missing ^
    --json-report ^
    --json-report-file=test-results.json ^
    --tb=short ^
    --quiet

if %errorlevel% neq 0 (
    echo %YELLOW%Some tests failed, but continuing with report generation...%NC%
)

echo %GREEN%Test execution completed, JSON reports generated for Quarto%NC%

REM Step 3: Generate all reports with fresh data
cd /d "%PROJECT_ROOT%"

echo %BLUE%Generating test results report from JSON data...%NC%
python tools\generate_test_results_report.py hazelbean_tests\test-results.json

echo %BLUE%Generating coverage report from JSON data...%NC%
python tools\generate_coverage_report.py

echo %BLUE%Generating performance baselines dashboard...%NC%
python tools\generate_baseline_report.py

echo %BLUE%Generating benchmark results summary...%NC%
python tools\generate_benchmark_summary.py

echo %GREEN%All Quarto reports generated with fresh data%NC%

REM Step 4: Verify all report files exist
echo %BLUE%Verifying all report files...%NC%
set "REPORTS_DIR=%PROJECT_ROOT%\docs-site\quarto-docs\reports"

set "ALL_FILES_EXIST=true"
for %%f in (test-results.qmd coverage-report.qmd performance-baselines.qmd benchmark-results.qmd index.qmd) do (
    if exist "%REPORTS_DIR%\%%f" (
        echo %GREEN%✓ %%f generated%NC%
    ) else (
        echo %RED%✗ %%f missing!%NC%
        set "ALL_FILES_EXIST=false"
    )
)

if "%ALL_FILES_EXIST%"=="false" (
    echo %RED%Some report files are missing - check the generation logs above%NC%
    exit /b 1
)

echo %GREEN%All required report files generated successfully%NC%

REM Step 5: Display generation summary
echo %BLUE%Site generation summary:%NC%
echo.
echo Generated Reports:
dir /b "%REPORTS_DIR%\*.qmd"

echo.
echo %GREEN%Complete site generation finished!%NC%

REM Step 6: Optionally start the docs server
if "%1"=="--serve" (
    echo %BLUE%Starting Quarto preview server...%NC%
    cd /d "%PROJECT_ROOT%\docs-site\quarto-docs" || exit /b 1
    
    echo.
    echo Quarto site will be available at: http://localhost:XXXX (Quarto assigns port)
    echo Direct report links will be shown by Quarto
    echo.
    echo Press Ctrl+C to stop the server
    echo.
    
    quarto preview
) else (
    echo.
    echo To view the generated site, run:
    echo   cd "%PROJECT_ROOT%\docs-site\quarto-docs" && quarto preview
    echo.
    echo Or use this complete command to generate and serve:
    echo   "%PROJECT_ROOT%\tools\generate_complete_site.cmd" --serve
    echo.
    echo You can also use the dedicated serve script:
    echo   "%PROJECT_ROOT%\tools\quarto_serve.cmd"
)

endlocal
