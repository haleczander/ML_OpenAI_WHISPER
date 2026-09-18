param(
    [string]$StateRoot = "",
    [string[]]$AdditionalNames = @(),
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$scriptDir = $PSScriptRoot
if (Test-Path (Join-Path $scriptDir "server.py")) {
    $resourceRoot = $scriptDir
} elseif (Test-Path (Join-Path $scriptDir "..\server.py")) {
    $resourceRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
} else {
    $resourceRoot = $scriptDir
}

if (-not $StateRoot) {
    if ($env:APP_STATE_DIR) {
        $StateRoot = $env:APP_STATE_DIR
    } else {
        # Development and legacy portable archives keep state beside server.py.
        $StateRoot = $resourceRoot
    }
}
$StateRoot = [System.IO.Path]::GetFullPath($StateRoot)
$certDir = Join-Path $StateRoot "certs"
$certPath = Join-Path $certDir "local.pem"
$keyPath = Join-Path $certDir "local-key.pem"
$configPath = Join-Path $StateRoot "config.json"

if (((Test-Path $certPath) -or (Test-Path $keyPath)) -and -not $Force) {
    throw "A certificate or private key already exists in $certDir. Use -Force to regenerate both."
}

$mkcert = Get-Command mkcert -ErrorAction SilentlyContinue
if (-not $mkcert) {
    throw "mkcert is required. Install it with: winget install --id FiloSottile.mkcert -e"
}

$lanAddresses = @(
    Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -ne "127.0.0.1" -and
            -not $_.IPAddress.StartsWith("169.254.") -and
            $_.AddressState -eq "Preferred"
        } |
        Select-Object -ExpandProperty IPAddress -Unique
)
$certificateNames = @("localhost", "127.0.0.1") + $lanAddresses + $AdditionalNames
$certificateNames = @($certificateNames | Where-Object { $_ } | Select-Object -Unique)

New-Item -ItemType Directory -Force -Path $certDir | Out-Null
& $mkcert.Source -install
if ($LASTEXITCODE -ne 0) {
    throw "mkcert could not install its local certificate authority."
}
& $mkcert.Source -key-file $keyPath -cert-file $certPath @certificateNames
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $certPath) -or -not (Test-Path $keyPath)) {
    throw "mkcert could not generate the HTTPS certificate."
}

if (Test-Path $configPath) {
    $config = Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json
} else {
    $config = [PSCustomObject]@{
        host = "0.0.0.0"
        port = 8000
        https = $false
    }
}
if ($null -eq $config.PSObject.Properties["https"]) {
    $config | Add-Member -NotePropertyName "https" -NotePropertyValue $true
} else {
    $config.https = $true
}
$configJson = ($config | ConvertTo-Json) + [Environment]::NewLine
[System.IO.File]::WriteAllText(
    $configPath,
    $configJson,
    [System.Text.UTF8Encoding]::new($false)
)

$caRoot = & $mkcert.Source -CAROOT
Write-Host "HTTPS configured for: $($certificateNames -join ', ')"
Write-Host "Certificate: $certPath"
Write-Host "Client devices must trust the CA certificate: $(Join-Path $caRoot 'rootCA.pem')"
