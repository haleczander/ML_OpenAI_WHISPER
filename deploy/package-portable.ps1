param(
    [string]$OutputZip = "ML_OpenAI_WHISPER_portable.zip",
    [string]$FfmpegSource = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$zipPath = Join-Path $root $OutputZip
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

$staging = Join-Path $root ".portable-staging"
if (Test-Path $staging) {
    Remove-Item -Recurse -Force $staging
}
New-Item -ItemType Directory -Force -Path $staging | Out-Null

$vendorBin = Join-Path $root "vendor\ffmpeg\bin"
New-Item -ItemType Directory -Force -Path $vendorBin | Out-Null
if ($FfmpegSource) {
    $resolvedSource = Resolve-Path -LiteralPath $FfmpegSource -ErrorAction Stop
    $sourcePath = $resolvedSource.Path

    if (Test-Path (Join-Path $sourcePath "bin\ffmpeg.exe")) {
        $sourceBin = Join-Path $sourcePath "bin"
    } elseif (Test-Path (Join-Path $sourcePath "ffmpeg.exe")) {
        $sourceBin = $sourcePath
    } elseif ((Test-Path $sourcePath) -and ((Get-Item $sourcePath).PSIsContainer -eq $false) -and ((Get-Item $sourcePath).Name -ieq "ffmpeg.exe")) {
        $sourceBin = Split-Path -Parent $sourcePath
    } else {
        throw "FfmpegSource must point to a folder containing ffmpeg.exe (or bin\\ffmpeg.exe), or directly to ffmpeg.exe."
    }

    Copy-Item -Path (Join-Path $sourceBin "*") -Destination $vendorBin -Recurse -Force
} else {
    $ffmpegCmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($null -ne $ffmpegCmd -and (Test-Path $ffmpegCmd.Source)) {
        $sourceBin = Split-Path -Parent $ffmpegCmd.Source
        Copy-Item -Path (Join-Path $sourceBin "*") -Destination $vendorBin -Recurse -Force
        Write-Host "Bundled ffmpeg from PATH: $($ffmpegCmd.Source)"
    }
}

$bundledFfmpeg = Join-Path $vendorBin "ffmpeg.exe"
$bundledFfprobe = Join-Path $vendorBin "ffprobe.exe"
if (-not (Test-Path $bundledFfmpeg)) {
    throw "Missing bundled ffmpeg at vendor\\ffmpeg\\bin\\ffmpeg.exe. Provide -FfmpegSource."
}
if (-not (Test-Path $bundledFfprobe)) {
    throw "Missing bundled ffprobe at vendor\\ffmpeg\\bin\\ffprobe.exe. Provide -FfmpegSource with a full ffmpeg distro."
}

$items = @(
    "server.py",
    "requirements.txt",
    "install.bat",
    "run.bat",
    "src",
    "static",
    "deploy\install.ps1",
    "deploy\run.ps1",
    "deploy\setup-https.ps1",
    "vendor\ffmpeg\bin"
)

$existing = $items | Where-Object { Test-Path $_ }
if (-not $existing -or $existing.Count -eq 0) {
    throw "No files found to package."
}

foreach ($item in $existing) {
    $destination = Join-Path $staging $item
    $destinationParent = Split-Path -Parent $destination
    if ($destinationParent) {
        New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null
    }
    Copy-Item -Path $item -Destination $destination -Recurse -Force
}

Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zipPath -CompressionLevel Optimal
Remove-Item -Recurse -Force $staging
Write-Host "Portable package created: $zipPath"
