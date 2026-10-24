$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

$Version = (Get-Content -Raw (Join-Path $ProjectDir "VERSION")).Trim()
if (-not $Version) {
    throw "VERSION file is empty."
}

Write-Host "Building Windows portable release v$Version ..."
py -m PyInstaller --noconfirm --clean (Join-Path $ProjectDir "grace_hymn_splitter.spec")

$BuiltExe = Join-Path $ProjectDir "dist\GraceHymnSplitter.exe"
if (-not (Test-Path -LiteralPath $BuiltExe)) {
    throw "Build output was not found: $BuiltExe"
}

$ReleaseDir = Join-Path $ProjectDir "release"
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

$ReleaseName = "GraceHymnSplitter-v$Version-win64.exe"
$ReleaseExe = Join-Path $ReleaseDir $ReleaseName
Copy-Item -LiteralPath $BuiltExe -Destination $ReleaseExe -Force

$Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $ReleaseExe).Hash.ToLowerInvariant()
$ChecksumFile = Join-Path $ReleaseDir "$ReleaseName.sha256"
"$Hash  $ReleaseName" | Set-Content -LiteralPath $ChecksumFile -Encoding ascii

Write-Host "Release built: $ReleaseExe"
Write-Host "SHA256: $Hash"
