param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if ([string]::IsNullOrWhiteSpace($Version)) {
    $VersionSource = Get-Content (Join-Path $Root "gitcat\__init__.py") -Raw
    $VersionMatch = [regex]::Match($VersionSource, '(?m)^__version__\s*=\s*"([^"]+)"')
    if (-not $VersionMatch.Success) {
        throw "Unable to read __version__ from gitcat\__init__.py"
    }
    $Version = $VersionMatch.Groups[1].Value
}
if ($Version -notmatch '^[0-9A-Za-z][0-9A-Za-z._-]*$') {
    throw "Invalid release version: $Version"
}

$Release = Join-Path $Root "release"
$OneFile = Join-Path $Release "GitCat-Windows-x64-onefile-v$Version"

function Invoke-WithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$Description,
        [Parameter(Mandatory = $true)][scriptblock]$Action,
        [int]$Attempts = 6
    )
    for ($Attempt = 1; $Attempt -le $Attempts; $Attempt++) {
        try {
            & $Action
            return
        }
        catch {
            if ($Attempt -eq $Attempts) {
                throw "$Description failed after $Attempts attempts: $($_.Exception.Message)"
            }
            Write-Warning "$Description failed (attempt $Attempt/$Attempts); retrying in 2 seconds."
            Start-Sleep -Seconds 2
        }
    }
}

New-Item -ItemType Directory -Force $Release | Out-Null
if (Test-Path -LiteralPath $OneFile) {
    Invoke-WithRetry "Remove $OneFile" { Remove-Item -LiteralPath $OneFile -Recurse -Force -ErrorAction Stop }
}
New-Item -ItemType Directory -Force $OneFile | Out-Null

Invoke-WithRetry "Copy onefile executable" {
    Copy-Item (Join-Path $Root "dist\GitCat.exe") (Join-Path $OneFile "GitCat.exe") -Force -ErrorAction Stop
}

$Guide = @"
GitCat v$Version

1. Double-click GitCat.exe to start. Git for Windows must be installed and on PATH.
2. Drop a repository folder on the window, or use Open / Clone / New repository.
3. Ctrl+Shift+P opens the command palette; Help > Keyboard shortcuts lists every shortcut.
4. Help > Check for updates downloads and installs new releases from GitHub automatically.

Config: %APPDATA%\GitCat\config.json
"@
Set-Content -LiteralPath (Join-Path $OneFile "Quick-Start.txt") -Value $Guide -Encoding UTF8
Get-ChildItem -Path $Root -Filter "README*.md" | Copy-Item -Destination $OneFile
Copy-Item (Join-Path $Root "CHANGELOG.md") $OneFile
if (Test-Path (Join-Path $Root "LICENSE")) { Copy-Item (Join-Path $Root "LICENSE") $OneFile }
Copy-Item (Join-Path $Root "assets\gitcat.png") $OneFile

$OneFileZip = "$OneFile.zip"
if (Test-Path -LiteralPath $OneFileZip) {
    Invoke-WithRetry "Remove $OneFileZip" { Remove-Item -LiteralPath $OneFileZip -Force -ErrorAction Stop }
}
Invoke-WithRetry "Create onefile ZIP" {
    Compress-Archive -Path (Join-Path $OneFile "*") -DestinationPath $OneFileZip -CompressionLevel Optimal -ErrorAction Stop
}

Write-Output "Created: $OneFileZip"
