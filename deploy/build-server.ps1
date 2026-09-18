param(
    [string]$PythonPath = "",
    [switch]$InstallBuildDependencies
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

if (-not $PythonPath) {
    $PythonPath = Join-Path $root ".venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Python environment not found: $PythonPath"
}

$ffmpegPath = Join-Path $root "vendor\ffmpeg\bin\ffmpeg.exe"
$ffprobePath = Join-Path $root "vendor\ffmpeg\bin\ffprobe.exe"
if (-not (Test-Path -LiteralPath $ffmpegPath)) {
    throw "Missing bundled executable: $ffmpegPath"
}
if (-not (Test-Path -LiteralPath $ffprobePath)) {
    throw "Missing bundled executable: $ffprobePath"
}

if ($InstallBuildDependencies) {
    & $PythonPath -m pip install -r (Join-Path $root "requirements-build.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to install build dependencies."
    }
}

& $PythonPath -c "import PyInstaller; print('PyInstaller', PyInstaller.__version__)"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is missing. Run this script with -InstallBuildDependencies."
}

& $PythonPath -m PyInstaller `
    --noconfirm `
    --clean `
    (Join-Path $root "deploy\DicteeCourriels.spec")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

$outputExe = Join-Path $root "dist\DicteeCourriels\DicteeCourriels.exe"
if (-not (Test-Path -LiteralPath $outputExe)) {
    throw "Build completed without the expected executable: $outputExe"
}

$outputSize = (Get-ChildItem (Split-Path -Parent $outputExe) -File -Recurse | Measure-Object Length -Sum).Sum
Write-Host "Standalone server created: $outputExe"
Write-Host ("Bundle size: {0:N1} MiB" -f ($outputSize / 1MB))
