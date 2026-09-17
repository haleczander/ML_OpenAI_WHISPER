param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not $Version) {
    $Version = (Get-Content -Raw -LiteralPath (Join-Path $root "VERSION")).Trim()
}

& (Join-Path $PSScriptRoot "build-server.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "Standalone server build failed."
}

& (Join-Path $PSScriptRoot "package-installer.ps1") -Version $Version
if ($LASTEXITCODE -ne 0) {
    throw "Installer packaging failed."
}

Write-Host "Release $Version is ready in $(Join-Path $root 'Releases')"
