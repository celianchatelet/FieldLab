[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$releaseDirectory = Join-Path $projectRoot "release"
$stagingDirectory = Join-Path $releaseDirectory "FieldLab"
$archive = Join-Path $projectRoot "FieldLab-Windows.zip"
$checksum = "$archive.sha256"
$portableBuilder = Join-Path $PSScriptRoot "build_windows_portable.ps1"
$downloadCache = Join-Path $projectRoot ".build-cache"

function Assert-PathInsideProject {
    param([Parameter(Mandatory)][string]$Path)

    $resolved = [IO.Path]::GetFullPath($Path)
    $prefix = $projectRoot.TrimEnd('\') + '\'
    if (-not $resolved.StartsWith(
            $prefix,
            [StringComparison]::OrdinalIgnoreCase)) {
        throw "Chemin de travail hors du projet refusé : $resolved"
    }
}

foreach ($path in @(
    $releaseDirectory, $stagingDirectory, $archive, $downloadCache
)) {
    Assert-PathInsideProject -Path $path
}

$env:UV_CACHE_DIR = Join-Path $projectRoot ".uv-cache"

Push-Location $projectRoot
try {
    if (-not $SkipBuild) {
        uv sync --extra dev --frozen
        if ($LASTEXITCODE -ne 0) { throw "uv sync a échoué." }

        if (-not $SkipTests) {
            uv run pytest -q
            if ($LASTEXITCODE -ne 0) { throw "Les tests ont échoué." }
        }

        if (Test-Path -LiteralPath $stagingDirectory) {
            Remove-Item -LiteralPath $stagingDirectory -Recurse -Force
        }
        & $portableBuilder -OutputDirectory $stagingDirectory `
            -DownloadCache $downloadCache
        if ($LASTEXITCODE -ne 0) {
            throw "La construction du paquet Windows portable a échoué."
        }
    }
    elseif (-not (Test-Path -LiteralPath (
            Join-Path $stagingDirectory "FieldLab.exe"))) {
        throw "release\FieldLab\FieldLab.exe est absent. Relancez sans -SkipBuild."
    }

    if (Test-Path -LiteralPath $archive) {
        Remove-Item -LiteralPath $archive -Force
    }
    if (Test-Path -LiteralPath $checksum) {
        Remove-Item -LiteralPath $checksum -Force
    }

    Compress-Archive -Path $stagingDirectory -DestinationPath $archive `
        -CompressionLevel Optimal

    $hash = (Get-FileHash -LiteralPath $archive `
        -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -LiteralPath $checksum `
        -Value "$hash  FieldLab-Windows.zip" -Encoding ascii

    $sizeMiB = [math]::Round((Get-Item -LiteralPath $archive).Length / 1MB, 1)
    Write-Host "Archive créée : $archive ($sizeMiB Mio)"
    Write-Host "Empreinte créée : $checksum"
}
finally {
    Pop-Location
}
