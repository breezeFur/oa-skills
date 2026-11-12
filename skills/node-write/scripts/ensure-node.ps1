#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$NodePath,
    [string]$InstallRoot,
    [version]$MinimumVersion = [version]'22.0.0',
    [switch]$Portable,
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$minimumNodeVersion = $MinimumVersion

function Get-AbsolutePath([string]$Value, [string]$Label) {
    if ($Value -notmatch '^(?:[A-Za-z]:[\\/]|\\\\[^\\/]+[\\/][^\\/]+[\\/])') {
        throw "$Label must be an absolute Windows path."
    }
    return [IO.Path]::GetFullPath($Value)
}

function Test-NodeRuntime([string]$Executable) {
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { return $null }
    if ($Executable -match '[\\/]Microsoft[\\/]WindowsApps[\\/]') { return $null }
    $probeCode = "console.log(JSON.stringify({execPath:process.execPath,version:process.versions.node,features:typeof Object.hasOwn==='function'&&typeof require('node:fs').readFileSync==='function'&&typeof require('node:util').TextDecoder==='function'&&typeof require('node:crypto').createHash==='function'}))"
    $probeInfo = New-Object Diagnostics.ProcessStartInfo
    $probeInfo.FileName = $Executable
    $probeInfo.Arguments = '-e "' + $probeCode + '"'
    $probeInfo.UseShellExecute = $false
    $probeInfo.CreateNoWindow = $true
    $probeInfo.RedirectStandardOutput = $true
    $probeInfo.RedirectStandardError = $true
    # Do not load unrelated preload modules or inherited Node options during discovery.
    $probeInfo.EnvironmentVariables.Remove('NODE_OPTIONS')
    $probeProcess = New-Object Diagnostics.Process
    $probeProcess.StartInfo = $probeInfo
    try {
        if (-not $probeProcess.Start()) { return $null }
        $probeOutput = $probeProcess.StandardOutput.ReadToEndAsync()
        $probeError = $probeProcess.StandardError.ReadToEndAsync()
        if (-not $probeProcess.WaitForExit(10000)) {
            $probeProcess.Kill()
            return $null
        }
        if ($probeProcess.ExitCode -ne 0) { return $null }
        $probeResult = $probeOutput.GetAwaiter().GetResult() | ConvertFrom-Json
        if (-not $probeResult.features -or [version]$probeResult.version -lt $minimumNodeVersion) { return $null }
        return [pscustomobject]@{
            nodePath = Get-AbsolutePath $probeResult.execPath 'Reported Node path'
            version = 'v' + $probeResult.version
        }
    } catch {
        return $null
    } finally {
        $probeProcess.Dispose()
    }
}

function Write-NodeResult($Runtime, [string]$Source, [bool]$Installed) {
    [ordered]@{
        ok = $true
        nodePath = $Runtime.nodePath
        version = $Runtime.version
        source = $Source
        installed = $Installed
        dgsVerificationRequired = $true
    } | ConvertTo-Json -Compress
}

function Assert-DownloadHash([string]$Archive, [string]$Checksums, [string]$FileName) {
    $checksumLines = @(Get-Content -LiteralPath $Checksums -Encoding UTF8 | Where-Object {
        $_ -match ('^[0-9a-fA-F]{64}\s+\*?' + [regex]::Escape($FileName) + '$')
    })
    if ($checksumLines.Count -ne 1) { throw 'Official checksums do not contain exactly one matching archive.' }
    $expectedHash = ($checksumLines[0] -split '\s+')[0]
    $actualHash = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash
    if ($actualHash -ne $expectedHash) { throw 'SHA-256 mismatch; refusing to extract or run the download.' }
}

function Assert-ChildPath([string]$Root, [string]$Child) {
    $rootPrefix = [IO.Path]::GetFullPath($Root).TrimEnd([char[]]'\/') + [IO.Path]::DirectorySeparatorChar
    $childFullPath = [IO.Path]::GetFullPath($Child)
    if (-not $childFullPath.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Installation path leaves the selected installation directory.'
    }
}

function Install-PortableNode([string]$Root) {
    $nodeArchitecture = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
    $archiveArchitecture = switch ($nodeArchitecture.ToUpperInvariant()) {
        'AMD64' { 'x64' }
        'ARM64' { 'arm64' }
        'X86' { 'x86' }
        default { throw "Unsupported Windows architecture: $nodeArchitecture" }
    }
    # Windows PowerShell 5.1 may otherwise negotiate an obsolete TLS default.
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $releaseIndex = Invoke-RestMethod -Uri 'https://nodejs.org/dist/index.json' -TimeoutSec 30
    $release = $releaseIndex | Where-Object {
        $_.lts -and $_.files -contains "win-$archiveArchitecture-zip" -and
        [version]($_.version.TrimStart('v')) -ge $minimumNodeVersion
    } | Sort-Object { [version]($_.version.TrimStart('v')) } -Descending | Select-Object -First 1
    if (-not $release -or $release.version -notmatch '^v\d+\.\d+\.\d+$') {
        throw 'No suitable official Windows LTS release is available.'
    }
    $releaseName = "node-$($release.version)-win-$archiveArchitecture"
    $archiveName = "$releaseName.zip"
    $releaseUrl = "https://nodejs.org/dist/$($release.version)"
    $null = New-Item -ItemType Directory -Path $Root -Force
    $resolvedRoot = (Resolve-Path -LiteralPath $Root).ProviderPath
    $stageDirectory = Join-Path $resolvedRoot ('.install-' + [guid]::NewGuid().ToString('N'))
    $destination = Join-Path $resolvedRoot $releaseName
    Assert-ChildPath $resolvedRoot $stageDirectory
    Assert-ChildPath $resolvedRoot $destination
    if (Test-Path -LiteralPath $destination) { throw 'Release directory already exists but has no usable Node; inspect it before retrying.' }
    $null = New-Item -ItemType Directory -Path $stageDirectory
    $archivePath = Join-Path $stageDirectory $archiveName
    $checksumsPath = Join-Path $stageDirectory 'SHASUMS256.txt'
    Invoke-WebRequest -UseBasicParsing -Uri "$releaseUrl/$archiveName" -OutFile $archivePath -TimeoutSec 120
    Invoke-WebRequest -UseBasicParsing -Uri "$releaseUrl/SHASUMS256.txt" -OutFile $checksumsPath -TimeoutSec 30
    Assert-DownloadHash $archivePath $checksumsPath $archiveName
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $unpackDirectory = Join-Path $stageDirectory 'unpacked'
    $zipFile = [IO.Compression.ZipFile]::OpenRead($archivePath)
    try {
        foreach ($zipEntry in $zipFile.Entries) {
            if (-not $zipEntry.FullName.StartsWith("$releaseName/", [StringComparison]::Ordinal)) {
                throw 'Unexpected archive layout; refusing extraction.'
            }
            Assert-ChildPath $unpackDirectory (Join-Path $unpackDirectory $zipEntry.FullName)
        }
    } finally {
        $zipFile.Dispose()
    }
    Expand-Archive -LiteralPath $archivePath -DestinationPath $unpackDirectory
    $unpackedRelease = (Resolve-Path -LiteralPath (Join-Path $unpackDirectory $releaseName)).ProviderPath
    Assert-ChildPath $resolvedRoot $unpackedRelease
    Assert-ChildPath $resolvedRoot $destination
    # Move only this verified release inside the explicitly selected root, without overwriting.
    [IO.Directory]::Move($unpackedRelease, $destination)
    $installedRuntime = Test-NodeRuntime (Join-Path $destination 'node.exe')
    if (-not $installedRuntime) { throw 'Downloaded Node failed its startup probe; DGS verification has not been performed.' }
    return $installedRuntime
}

function Ensure-Node {
    if ($env:OS -ne 'Windows_NT') { throw 'This bootstrap supports Windows only.' }
    if ($MinimumVersion -lt [version]'22.0.0') { throw 'MinimumVersion must be at least 22.0.0.' }
    if ($NodePath -and $Portable) { throw 'NodePath and Portable cannot be combined.' }
    if ($InstallRoot) { $script:InstallRoot = Get-AbsolutePath $InstallRoot 'InstallRoot' }
    else {
        if (-not $env:LOCALAPPDATA) { throw 'LOCALAPPDATA is unavailable; supply an absolute InstallRoot.' }
        $script:InstallRoot = Get-AbsolutePath (Join-Path $env:LOCALAPPDATA 'CodexTools\node-write\node') 'InstallRoot'
    }
    if ($NodePath) {
        $selectedRuntime = Test-NodeRuntime (Get-AbsolutePath $NodePath 'NodePath')
        if (-not $selectedRuntime) { throw 'Explicit NodePath is unusable or older than the required Node version; no fallback was attempted.' }
        Write-NodeResult $selectedRuntime 'explicit' $false
        return
    }
    $candidates = New-Object 'System.Collections.Generic.List[object]'
    if (-not $Portable) {
        foreach ($nodeCommand in @(Get-Command node.exe -CommandType Application -All -ErrorAction SilentlyContinue)) {
            $candidates.Add(@{ path = $nodeCommand.Source; source = 'path' })
        }
    }
    if (Test-Path -LiteralPath $InstallRoot -PathType Container) {
        $cachedReleases = Get-ChildItem -LiteralPath $InstallRoot -Directory | Where-Object {
            $_.Name -match '^node-v\d+\.\d+\.\d+-win-(x64|arm64|x86)$'
        } | Sort-Object { [version](($_.Name -split '-')[1].TrimStart('v')) } -Descending
        foreach ($cachedRelease in $cachedReleases) {
            $candidates.Add(@{ path = Join-Path $cachedRelease.FullName 'node.exe'; source = 'portable-cache' })
        }
    }
    if (-not $Portable) {
        foreach ($programRoot in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, (Join-Path $env:LOCALAPPDATA 'Programs'))) {
            if ($programRoot -and (Test-Path -LiteralPath $programRoot -PathType Container)) {
                foreach ($nodeDirectory in @(Get-ChildItem -LiteralPath $programRoot -Directory -Filter 'nodejs*')) {
                    $candidates.Add(@{ path = Join-Path $nodeDirectory.FullName 'node.exe'; source = 'installed' })
                }
            }
        }
        $codexConfigRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
        foreach ($runtimeRoot in @(
            (Join-Path $codexConfigRoot 'dependencies'),
            (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies')
        )) {
            $candidates.Add(@{ path = Join-Path $runtimeRoot 'node\bin\node.exe'; source = 'codex-runtime' })
        }
    }
    foreach ($candidate in $candidates) {
        $availableRuntime = Test-NodeRuntime $candidate.path
        if ($availableRuntime) {
            Write-NodeResult $availableRuntime $candidate.source $false
            return
        }
    }
    if ($CheckOnly) { throw 'No usable Node meeting MinimumVersion found; CheckOnly did not install anything.' }
    $newRuntime = Install-PortableNode $InstallRoot
    Write-NodeResult $newRuntime 'official-portable' $true
}

try {
    Ensure-Node
    exit 0
} catch {
    [ordered]@{ ok = $false; error = $_.Exception.Message; dgsVerificationRequired = $true } | ConvertTo-Json -Compress
    exit 1
}
