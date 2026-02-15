param(
    [switch]$Https
)

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

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Virtual environment not found. Run .\deploy\install.ps1 first."
}

$bundledFfmpeg = Join-Path $root "vendor\ffmpeg\bin\ffmpeg.exe"
if (-not (Test-Path $bundledFfmpeg)) {
    throw "Missing bundled ffmpeg at vendor\\ffmpeg\\bin\\ffmpeg.exe"
}
Write-Host "Using bundled ffmpeg: $bundledFfmpeg"

if ($Https) {
    $env:APP_SSL = "1"
    $deployCert = Join-Path $root "deploy\certs\local.pem"
    $deployKey = Join-Path $root "deploy\certs\local-key.pem"
    $runtimeCert = Join-Path $root "certs\local.pem"
    $runtimeKey = Join-Path $root "certs\local-key.pem"

    if ((-not (Test-Path $runtimeCert) -or -not (Test-Path $runtimeKey)) -and ((Test-Path $deployCert) -and (Test-Path $deployKey))) {
        New-Item -ItemType Directory -Force -Path (Join-Path $root "certs") | Out-Null
        Copy-Item -Force $deployCert $runtimeCert
        Copy-Item -Force $deployKey $runtimeKey
        Write-Host "Copied bundled certs from deploy/certs to certs/"
    }

    if (-not (Test-Path "$root\certs\local.pem") -or -not (Test-Path "$root\certs\local-key.pem")) {
        throw "Missing certs/local.pem or certs/local-key.pem for HTTPS mode."
    }
    Write-Host "Starting HTTPS server on https://localhost:8000"
} else {
    $env:APP_SSL = "0"
    Write-Host "Starting HTTP server on http://localhost:8000"
}

& $venvPython server.py
