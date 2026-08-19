[CmdletBinding()]
param(
    [string]$OutputDirectory = "release/FieldLab",
    [string]$DownloadCache = ".build-cache"
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Resolve-ProjectPath([string]$Path) {
    if ([IO.Path]::IsPathRooted($Path)) {
        return [IO.Path]::GetFullPath($Path)
    }
    return [IO.Path]::GetFullPath((Join-Path $projectRoot $Path))
}

function Invoke-Checked([scriptblock]$Command, [string]$Description) {
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description a échoué avec le code $LASTEXITCODE."
    }
}

$outputPath = Resolve-ProjectPath $OutputDirectory
$cachePath = Resolve-ProjectPath $DownloadCache
$uvCachePath = Join-Path $cachePath "uv"
$pythonVersion = "3.12.10"
$pythonArchiveName = "python-$pythonVersion-embed-amd64.zip"
$pythonArchive = Join-Path $cachePath $pythonArchiveName
$pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/$pythonArchiveName"
$pythonSha256 = "4ACBED6DD1C744B0376E3B1CF57CE906F9DC9E95E68824584C8099A63025A3C3"

if (Test-Path -LiteralPath $outputPath) {
    throw "Le dossier de sortie existe déjà : $outputPath"
}

New-Item -ItemType Directory -Path $cachePath -Force | Out-Null
New-Item -ItemType Directory -Path $outputPath -Force | Out-Null

if (-not (Test-Path -LiteralPath $pythonArchive)) {
    Write-Host "Téléchargement du runtime Python officiel $pythonVersion..."
    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonArchive
}

$archiveHash = (Get-FileHash -LiteralPath $pythonArchive -Algorithm SHA256).Hash
if ($archiveHash -ne $pythonSha256) {
    throw "Empreinte SHA-256 invalide pour $pythonArchiveName."
}

Expand-Archive -LiteralPath $pythonArchive -DestinationPath $outputPath

# pythonw.exe est signé par la Python Software Foundation. Le renommer ne
# modifie aucun octet et conserve donc sa signature Authenticode.
Copy-Item -LiteralPath (Join-Path $outputPath "pythonw.exe") `
    -Destination (Join-Path $outputPath "FieldLab.exe")
Copy-Item -LiteralPath (
    Join-Path $projectRoot "packaging/windows_portable/python312._pth") `
    -Destination (Join-Path $outputPath "python312._pth") -Force

$sitePackages = Join-Path $outputPath "Lib/site-packages"
New-Item -ItemType Directory -Path $sitePackages -Force | Out-Null
Copy-Item -LiteralPath (
    Join-Path $projectRoot "packaging/windows_portable/sitecustomize.py") `
    -Destination (Join-Path $sitePackages "sitecustomize.py")

$buildPath = Join-Path $projectRoot "build/windows-portable"
New-Item -ItemType Directory -Path $buildPath -Force | Out-Null
$requirements = Join-Path $buildPath "requirements.txt"

Push-Location $projectRoot
try {
    Invoke-Checked {
        uv --quiet --cache-dir $uvCachePath export --frozen --no-dev --no-emit-project `
            --no-emit-package gmsh --no-emit-package pyvista `
            --no-emit-package pyvistaqt --no-emit-package vtk `
            --format requirements-txt --output-file $requirements
    } "L'export des dépendances"

    Invoke-Checked {
        uv --cache-dir $uvCachePath pip install --target $sitePackages `
            --python-version $pythonVersion `
            --python-platform x86_64-pc-windows-msvc `
            --requirements $requirements --require-hashes
    } "L'installation des dépendances"

}
finally {
    Pop-Location
}

# Copier les sources directement évite la création d'un environnement de build
# temporaire, dont l'exécutable Python peut être bloqué par Smart App Control.
$fieldlabSource = Join-Path $projectRoot "fieldlab"
$fieldlabDestination = Join-Path $sitePackages "fieldlab"
Get-ChildItem -LiteralPath $fieldlabSource -Recurse -File -Filter "*.py" |
    ForEach-Object {
        $relativePath = $_.FullName.Substring(
            $fieldlabSource.Length).TrimStart([char[]]"\/")
        $destination = Join-Path $fieldlabDestination $relativePath
        New-Item -ItemType Directory -Path (
            Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $destination
    }

Copy-Item -LiteralPath (Join-Path $projectRoot "assets") `
    -Destination (Join-Path $sitePackages "assets") -Recurse
Copy-Item -LiteralPath (
    Join-Path $projectRoot "docs/GUIDE_PROFESSEUR.md") `
    -Destination (Join-Path $outputPath "GUIDE_PROFESSEUR.md")
foreach ($document in @(
    "LISEZ-MOI.txt", "LICENSE", "THIRD_PARTY_NOTICES.md", "CITATION.cff"
)) {
    Copy-Item -LiteralPath (Join-Path $projectRoot $document) `
        -Destination $outputPath
}

$invalidRuntimeSignatures = @(Get-ChildItem -LiteralPath $outputPath -File |
    Where-Object { $_.Extension -in ".exe", ".dll", ".pyd" } |
    ForEach-Object {
        $signature = Get-AuthenticodeSignature -LiteralPath $_.FullName
        if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
            [pscustomobject]@{ Fichier = $_.Name; Statut = $signature.Status }
        }
    })

if ($invalidRuntimeSignatures) {
    $invalidRuntimeSignatures | Format-Table -AutoSize | Out-String | Write-Host
    throw "Le runtime Python officiel contient une signature invalide."
}

$launcherSignature = Get-AuthenticodeSignature `
    -LiteralPath (Join-Path $outputPath "FieldLab.exe")
Write-Host "Bundle portable créé : $outputPath"
Write-Host "Lanceur signé par : $($launcherSignature.SignerCertificate.Subject)"
