$ErrorActionPreference = "Stop"

$scriptDir = $PSScriptRoot
if (Test-Path (Join-Path $scriptDir "server.py")) {
    $root = $scriptDir
} elseif (Test-Path (Join-Path $scriptDir "..\server.py")) {
    $root = (Resolve-Path (Join-Path $scriptDir "..")).Path
} else {
    $root = $scriptDir
}
Set-Location $root

Write-Host "Installing app in $root"

$hasPython = $null -ne (Get-Command python -ErrorAction SilentlyContinue)

if (-not $hasPython) {
    throw "Python not found. Install Python 3.10+ first."
}

if (-not (Test-Path ".venv")) {
    $venvCreated = $false
    if ($hasPython) {
        & python -m venv .venv
        if ($LASTEXITCODE -eq 0) {
            $venvCreated = $true
        }
    }
    if (-not $venvCreated) {
        throw "Unable to create .venv with py/python. Install Python 3.10+ and retry."
    }
}

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Virtual environment is missing: $venvPython"
}

$env:PIP_NO_CACHE_DIR = "1"
& $venvPython -m pip install --upgrade pip --no-cache-dir
& $venvPython -m pip install -r requirements.txt --no-cache-dir

New-Item -ItemType Directory -Force -Path "$root\certs" | Out-Null

$bundledFfmpeg = Join-Path $root "vendor\ffmpeg\bin\ffmpeg.exe"
if (Test-Path $bundledFfmpeg) {
    Write-Host "Bundled ffmpeg found: $bundledFfmpeg"
} elseif ($null -eq (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Warning "No ffmpeg found (PATH or vendor\\ffmpeg\\bin\\ffmpeg.exe)."
    Write-Host "Install with winget: winget install --id Gyan.FFmpeg -e"
}

$bundledCert = Join-Path $root "deploy\certs\local.pem"
$bundledKey = Join-Path $root "deploy\certs\local-key.pem"
if ((Test-Path $bundledCert) -and (Test-Path $bundledKey)) {
    Copy-Item -Force $bundledCert "$root\certs\local.pem"
    Copy-Item -Force $bundledKey "$root\certs\local-key.pem"
    Write-Host "Bundled HTTPS certs copied to certs/"
}

if (-not (Test-Path "$root\certs\local.pem") -or -not (Test-Path "$root\certs\local-key.pem")) {
    Write-Warning "HTTPS cert files are missing. You can still run in HTTP mode."
    Write-Host "To bundle certs, add deploy/certs/local.pem and deploy/certs/local-key.pem"
}

Write-Host "Install complete."
Write-Host "Run HTTP mode:   .\deploy\run.ps1"
Write-Host "Run HTTPS mode:  .\deploy\run.ps1 -Https"
