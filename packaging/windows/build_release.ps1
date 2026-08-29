param(
    [string]$Version = "2.9.0",
    [string]$Python = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$buildDirectory = Join-Path $projectRoot "build"
$distDirectory = Join-Path $projectRoot "dist"
$releaseDirectory = Join-Path $projectRoot "release"
$specFile = Join-Path $PSScriptRoot "MkvMuxingBatch.spec"
$installerScript = Join-Path $PSScriptRoot "Installer.iss"
$applicationDirectory = Join-Path $distDirectory "MKV Muxing Batch GUI"
$portableFile = Join-Path $releaseDirectory "MKV.Muxing.Batch.GUI.x64.v$Version.Qt6.Windows.Portable.zip"
$installerFile = Join-Path $releaseDirectory "MKV.Muxing.Batch.GUI.x64.v$Version.Qt6.Windows.Installer.exe"
$checksumsFile = Join-Path $releaseDirectory "SHA256SUMS.txt"
$dependencyCacheDirectory = Join-Path $projectRoot ".dependency-cache"
$mkvToolNixDirectory = Join-Path $buildDirectory "dependencies\mkvtoolnix-windows-x64"
$dependencyManifestFile = Join-Path $projectRoot "packaging\dependencies.json"
$dependencyFetcher = Join-Path $projectRoot "scripts\fetch_mkvtoolnix.py"
$sourceVersion = [regex]::Match(
    (Get-Content -LiteralPath (Join-Path $projectRoot "packages\Startup\Version.py") -Raw),
    'Version\s*=\s*"([^"]+)"'
).Groups[1].Value
if ($sourceVersion -ne $Version) {
    throw "Source version '$sourceVersion' does not match requested release '$Version'"
}

foreach ($target in @($buildDirectory, $distDirectory, $releaseDirectory)) {
    $fullTarget = [System.IO.Path]::GetFullPath($target)
    if (-not $fullTarget.StartsWith($projectRoot + [System.IO.Path]::DirectorySeparatorChar)) {
        throw "Refusing to clean a build path outside the project: $fullTarget"
    }
    if (Test-Path -LiteralPath $fullTarget) {
        Remove-Item -LiteralPath $fullTarget -Recurse -Force
    }
}
New-Item -ItemType Directory -Path $releaseDirectory | Out-Null

Push-Location $projectRoot
$previousMkvToolNixBundle = $env:MKVTOOLNIX_BUNDLE_DIR
try {
    & $Python $dependencyFetcher `
        --destination $mkvToolNixDirectory `
        --cache-dir $dependencyCacheDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "MKVToolNix download or verification failed with exit code $LASTEXITCODE"
    }

    $dependencyManifest = Get-Content -LiteralPath $dependencyManifestFile -Raw | ConvertFrom-Json
    $expectedMkvToolNixVersion = $dependencyManifest.mkvtoolnix_windows_x64.version
    foreach ($toolName in @("mkvmerge.exe", "mkvpropedit.exe")) {
        $toolPath = Join-Path $mkvToolNixDirectory $toolName
        $toolVersion = (& $toolPath -V | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or $toolVersion -notmatch [regex]::Escape("v$expectedMkvToolNixVersion")) {
            throw "$toolName did not report expected MKVToolNix version $expectedMkvToolNixVersion"
        }
    }

    $env:MKVTOOLNIX_BUNDLE_DIR = $mkvToolNixDirectory
    & $Python -m PyInstaller --noconfirm --clean --workpath $buildDirectory --distpath $distDirectory $specFile
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }

    $innoCompilerCandidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    $innoCompiler = $innoCompilerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $innoCompiler) {
        throw "Inno Setup 6 was not found"
    }
    & $innoCompiler "/DMyAppVersion=$Version" $installerScript
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed with exit code $LASTEXITCODE"
    }

    Compress-Archive -LiteralPath $applicationDirectory -DestinationPath $portableFile -CompressionLevel Optimal
    $checksumLines = foreach ($artifact in @($installerFile, $portableFile)) {
        $hash = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLowerInvariant()
        "$hash  $([System.IO.Path]::GetFileName($artifact))"
    }
    [System.IO.File]::WriteAllLines($checksumsFile, $checksumLines)
}
finally {
    if ($null -eq $previousMkvToolNixBundle) {
        Remove-Item Env:MKVTOOLNIX_BUNDLE_DIR -ErrorAction SilentlyContinue
    }
    else {
        $env:MKVTOOLNIX_BUNDLE_DIR = $previousMkvToolNixBundle
    }
    Pop-Location
}

Get-Item -LiteralPath $installerFile, $portableFile, $checksumsFile |
    Select-Object Name, Length, LastWriteTime
