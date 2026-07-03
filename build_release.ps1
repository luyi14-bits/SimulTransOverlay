# Build Release Script for SimulTransOverlay
# Builds a onedir distribution using SimulTransOverlay.spec
# Models are NOT bundled — they download on first run via ModelManager.

$ErrorActionPreference = "Stop"

# Configuration
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$OutputDir = Join-Path $ProjectRoot "dist"
$AppName = "SimulTransOverlay"

Write-Host "=== SimulTransOverlay Build Script (onedir) ===" -ForegroundColor Cyan
Write-Host ""

# Stage 0: Environment check
Write-Host "[Stage 0] Environment check..." -ForegroundColor Yellow
$PythonVersion = python --version 2>&1
Write-Host "  $PythonVersion"

try {
    python -m PyInstaller --version 2>&1 | Out-Null
    Write-Host "  PyInstaller: OK" -ForegroundColor Green
} catch {
    Write-Host "  Installing PyInstaller..." -ForegroundColor Yellow
    python -m pip install pyinstaller --quiet
}

# Stage 1: Clean old builds
Write-Host "[Stage 1] Cleaning old builds..." -ForegroundColor Yellow
if (Test-Path $OutputDir) {
    Remove-Item -Path $OutputDir -Recurse -Force
    Write-Host "  Removed old dist/" -ForegroundColor Green
}
$BuildDir = Join-Path $ProjectRoot "build"
if (Test-Path $BuildDir) {
    Remove-Item -Path $BuildDir -Recurse -Force
    Write-Host "  Removed old build/" -ForegroundColor Green
}

# Stage 2: Build using spec file (onedir + precise control)
Write-Host "[Stage 2] Building with spec file..." -ForegroundColor Yellow
Set-Location $ProjectRoot

python -m PyInstaller SimulTransOverlay.spec 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "  Build: OK" -ForegroundColor Green

# Stage 3: Verify output
Write-Host "[Stage 3] Verifying output..." -ForegroundColor Yellow
$ExePath = Join-Path $OutputDir "$AppName" "$AppName.exe"
if (Test-Path $ExePath) {
    $dirSize = (Get-ChildItem -Path (Join-Path $OutputDir $AppName) -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host "  $AppName.exe created" -ForegroundColor Green
    Write-Host "  Total directory size: $([math]::Round($dirSize, 1)) MB" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Executable not found at $ExePath!" -ForegroundColor Red
    exit 1
}

# Stage 4: Security check
Write-Host "[Stage 4] Security check..." -ForegroundColor Yellow
$sensitivePatterns = @("*.pdb", "*.env", "*.db", "*.sqlite", "*.instance")
$issues = 0
foreach ($pattern in $sensitivePatterns) {
    $found = Get-ChildItem -Path $OutputDir -Recurse -Filter $pattern -ErrorAction SilentlyContinue
    if ($found) {
        Write-Host "  [WARN] Found sensitive file: $($found.FullName)" -ForegroundColor Red
        $issues++
    }
}

if ($issues -gt 0) {
    Write-Host "[WARN] $issues sensitive file(s) found in output" -ForegroundColor Yellow
} else {
    Write-Host "  No sensitive files: OK" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Build Complete ===" -ForegroundColor Cyan
Write-Host "  Output: $ExePath"
Write-Host "  Size: $([math]::Round($dirSize, 1)) MB"
Write-Host "  Note: Models NOT bundled. First run auto-downloads from HuggingFace."
