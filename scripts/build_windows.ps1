[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..")
)
$distDirectory = Join-Path $projectRoot "dist\FieldLab"
$releaseDirectory = Join-Path $projectRoot "release"
$stagingDirectory = Join-Path $releaseDirectory "FieldLab"
$archive = Join-Path $projectRoot "FieldLab-Windows.zip"
$checksum = "$archive.sha256"

function Assert-PathInsideProject {
    param([Parameter(Mandatory)][string]$Path)

    $resolved = [System.IO.Path]::GetFullPath($Path)
    $prefix = $projectRoot.TrimEnd('\') + '\'
    if (-not $resolved.StartsWith(
            $prefix,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Chemin de travail hors du projet refusé : $resolved"
    }
}

Assert-PathInsideProject -Path $releaseDirectory
Assert-PathInsideProject -Path $stagingDirectory
Assert-PathInsideProject -Path $archive

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

        uv run pyinstaller --clean --noconfirm fieldlab.spec
        if ($LASTEXITCODE -ne 0) { throw "La construction PyInstaller a échoué." }
    }
    elseif (-not (Test-Path -LiteralPath (Join-Path $distDirectory "FieldLab.exe"))) {
        throw "dist\FieldLab\FieldLab.exe est absent. Relancez sans -SkipBuild."
    }

    New-Item -ItemType Directory -Path $releaseDirectory -Force | Out-Null
    if (Test-Path -LiteralPath $stagingDirectory) {
        Remove-Item -LiteralPath $stagingDirectory -Recurse -Force
    }
    Copy-Item -LiteralPath $distDirectory -Destination $releaseDirectory -Recurse

    $documents = @(
        "LISEZ-MOI.txt",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "CITATION.cff"
    )
    foreach ($document in $documents) {
        $source = Join-Path $projectRoot $document
        if (-not (Test-Path -LiteralPath $source)) {
            throw "Document de distribution manquant : $document"
        }
        Copy-Item -LiteralPath $source -Destination $stagingDirectory
    }
    Copy-Item -LiteralPath (Join-Path $projectRoot "docs\GUIDE_PROFESSEUR.md") `
        -Destination (Join-Path $stagingDirectory "GUIDE_PROFESSEUR.md")

    if (Test-Path -LiteralPath $archive) {
        Remove-Item -LiteralPath $archive -Force
    }
    if (Test-Path -LiteralPath $checksum) {
        Remove-Item -LiteralPath $checksum -Force
    }

    Compress-Archive -Path $stagingDirectory -DestinationPath $archive `
        -CompressionLevel Optimal

    $hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -LiteralPath $checksum -Value "$hash  FieldLab-Windows.zip" `
        -Encoding ascii

    $sizeMiB = [math]::Round((Get-Item -LiteralPath $archive).Length / 1MB, 1)
    Write-Host "Archive créée : $archive ($sizeMiB Mio)"
    Write-Host "Empreinte créée : $checksum"
}
finally {
    Pop-Location
}
