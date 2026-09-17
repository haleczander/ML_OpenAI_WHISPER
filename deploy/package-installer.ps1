param(
    [string]$Version = "",
    [string]$OutputDirectory = "Releases"
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

if (-not $Version) {
    $Version = (Get-Content -Raw -LiteralPath (Join-Path $root "VERSION")).Trim()
}
if ($Version -notmatch '^\d+\.\d+\.\d+([\-+][0-9A-Za-z.-]+)?$') {
    throw "Version must be valid SemVer, for example 1.2.3: $Version"
}

$packDirectory = Join-Path $root "dist\DicteeCourriels"
$mainExe = Join-Path $packDirectory "DicteeCourriels.exe"
if (-not (Test-Path -LiteralPath $mainExe)) {
    throw "Standalone build not found. Run .\deploy\build-server.ps1 first."
}

$vpk = Get-Command vpk -ErrorAction SilentlyContinue
if ($vpk) {
    $vpkPath = $vpk.Source
} else {
    $globalToolPath = Join-Path $env:USERPROFILE ".dotnet\tools\vpk.exe"
    if (Test-Path -LiteralPath $globalToolPath) {
        $vpkPath = $globalToolPath
    } else {
        throw "Velopack CLI vpk 1.2.0 is required. Install it with: dotnet tool install --global vpk --version 1.2.0"
    }
}
$installedVersion = (& $vpkPath -H 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0 -or $installedVersion -notmatch '1\.2\.0') {
    throw "Velopack CLI 1.2.0 is required; detected: $($installedVersion.Trim())"
}

$resolvedOutputDirectory = [System.IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
New-Item -ItemType Directory -Force -Path $resolvedOutputDirectory | Out-Null

& $vpkPath --yes pack `
    --packId "DicteeCourriels" `
    --packVersion $Version `
    --packDir $packDirectory `
    --mainExe "DicteeCourriels.exe" `
    --packTitle "Dictee Courriels" `
    --packAuthors "haleczander" `
    --channel "win" `
    --outputDir $resolvedOutputDirectory
if ($LASTEXITCODE -ne 0) {
    throw "Velopack packaging failed."
}

$setup = Get-ChildItem -LiteralPath $resolvedOutputDirectory -Filter "*-Setup.exe" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $setup) {
    throw "Velopack completed without creating Setup.exe."
}

Write-Host "Installer created: $($setup.FullName)"
Get-ChildItem -LiteralPath $resolvedOutputDirectory -File |
    Sort-Object Name |
    Select-Object Name, Length
