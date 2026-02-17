@echo off
REM Quarto Site Preview Server - Windows Version
REM Serves the Quarto documentation site with live reload
REM
REM Usage: tools\quarto_serve.cmd [--render]
REM   --render: Render the site before serving

setlocal enabledelayedexpansion

REM Colors for Windows (limited)
set "BLUE=[94m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "NC=[0m"

echo %BLUE%Quarto Documentation Server%NC%
echo.

REM Check if we should render first
set "RENDER_FIRST=false"
if "%1"=="--render" set "RENDER_FIRST=true"

REM Get script directory and navigate to quarto-docs
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "QUARTO_DIR=%PROJECT_ROOT%\docs-site\quarto-docs"

if not exist "%QUARTO_DIR%" (
    echo %RED%Error: Quarto directory not found at: %QUARTO_DIR%%NC%
    exit /b 1
)

cd /d "%QUARTO_DIR%" || exit /b 1

REM Check conda
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo %RED%Error: conda not found in PATH%NC%
    exit /b 1
)

REM Activate conda environment
echo %BLUE%Activating hazelbean_env...%NC%
call conda activate hazelbean_env
if %errorlevel% neq 0 (
    echo %RED%Failed to activate hazelbean_env%NC%
    exit /b 1
)
echo %GREEN%hazelbean_env conda environment active%NC%
echo.

REM Optionally render first
if "%RENDER_FIRST%"=="true" (
    echo %BLUE%Rendering site before serving...%NC%
    quarto render
    if %errorlevel% neq 0 (
        echo %RED%Rendering failed!%NC%
        exit /b 1
    )
    echo %GREEN%Site rendered successfully%NC%
    echo.
)

REM Start the preview server
echo Starting Quarto preview server...
echo.
echo The site will be available at a local address (Quarto will display it below)
echo Live reload is enabled - changes will update automatically
echo.
echo %BLUE%Press Ctrl+C to stop the server%NC%
echo.

quarto preview

endlocal

