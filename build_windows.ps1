$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

$Version = (Get-Content -Raw (Join-Path $ProjectDir "VERSION")).Trim()
if (-not $Version) {
    throw "VERSION file is empty."
}

$PythonExe = $null
$PythonArgs = @()

foreach ($Candidate in @("python", "py")) {
    $Command = Get-Command $Candidate -ErrorAction SilentlyContinue
    if (-not $Command) {
        continue
    }
    & $Command.Source -c "import sys; print(sys.executable)" *> $null
    if ($LASTEXITCODE -eq 0) {
        $PythonExe = $Command.Source
        break
    }
}

if (-not $PythonExe) {
    throw "A working Python 3.10+ installation was not found."
}

$FrontendDir = Join-Path $ProjectDir "frontend\grace-hymn-splitter-ui"
if (Test-Path -LiteralPath $FrontendDir) {
    $Npm = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $Npm) {
        throw "Node.js and npm are required to build the desktop interface."
    }

    Push-Location $FrontendDir
    try {
        Write-Host "Building desktop interface ..."
        & $Npm.Source ci
        if ($LASTEXITCODE -ne 0) {
            throw "npm ci failed with exit code $LASTEXITCODE."
        }
        & $Npm.Source run build
        if ($LASTEXITCODE -ne 0) {
            throw "npm run build failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host "Building Windows portable release v$Version ..."
& $PythonExe @PythonArgs (Join-Path $ProjectDir "tools\build_brand_assets.py")
if ($LASTEXITCODE -ne 0) {
    throw "Brand asset build failed with exit code $LASTEXITCODE."
}
& $PythonExe @PythonArgs -m PyInstaller --noconfirm --clean (Join-Path $ProjectDir "grace_hymn_splitter.spec")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$BuiltExe = Join-Path $ProjectDir "dist\GraceHymnSplitter.exe"
if (-not (Test-Path -LiteralPath $BuiltExe)) {
    throw "Build output was not found: $BuiltExe"
}

$ReleaseDir = Join-Path $ProjectDir "release"
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

$ReleaseName = "GraceHymnSplitter-v$Version-win64-portable.exe"
$ReleaseExe = Join-Path $ReleaseDir $ReleaseName
Copy-Item -LiteralPath $BuiltExe -Destination $ReleaseExe -Force

$Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $ReleaseExe).Hash.ToLowerInvariant()
$ChecksumFile = Join-Path $ReleaseDir "$ReleaseName.sha256"
"$Hash  $ReleaseName" | Set-Content -LiteralPath $ChecksumFile -Encoding ascii

Write-Host "Portable release built: $ReleaseExe"
Write-Host "Portable SHA256: $Hash"

$InnoCandidates = @()
$InnoCommand = Get-Command iscc -ErrorAction SilentlyContinue
if ($InnoCommand) {
    $InnoCandidates += $InnoCommand.Source
}
$ProgramFilesX86 = ${env:ProgramFiles(x86)}
if ($ProgramFilesX86) {
    $InnoCandidates += Join-Path $ProgramFilesX86 "Inno Setup 6\ISCC.exe"
    $InnoCandidates += Join-Path $ProgramFilesX86 "Inno Setup 5\ISCC.exe"
}
if ($env:ProgramFiles) {
    $InnoCandidates += Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"
}
if ($env:LOCALAPPDATA) {
    $InnoCandidates += Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
}
$Iscc = $InnoCandidates |
    Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
    Select-Object -First 1
if (-not $Iscc) {
    throw "Inno Setup 6 was not found. Install it before building the Windows installer."
}

$InstallerScript = Join-Path $ProjectDir "installer\grace_hymn_splitter.iss"
if (-not (Test-Path -LiteralPath $InstallerScript)) {
    throw "Installer script was not found: $InstallerScript"
}

Write-Host "Building Windows installer v$Version ..."
& $Iscc "/DMyAppVersion=$Version" $InstallerScript
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed with exit code $LASTEXITCODE."
}

$InstallerName = "GraceHymnSplitter-v$Version-setup-win64.exe"
$InstallerExe = Join-Path $ReleaseDir $InstallerName
if (-not (Test-Path -LiteralPath $InstallerExe)) {
    throw "Installer output was not found: $InstallerExe"
}

$InstallerHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $InstallerExe).Hash.ToLowerInvariant()
$InstallerChecksumFile = Join-Path $ReleaseDir "$InstallerName.sha256"
"$InstallerHash  $InstallerName" | Set-Content -LiteralPath $InstallerChecksumFile -Encoding ascii

Write-Host "Installer built: $InstallerExe"
Write-Host "Installer SHA256: $InstallerHash"
