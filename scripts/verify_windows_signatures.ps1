[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$BundlePath = "dist/FieldLab"
)

$ErrorActionPreference = "Stop"

$resolvedBundle = Resolve-Path -LiteralPath $BundlePath
$nativeExtensions = @(".exe", ".dll", ".pyd")
$nativeFiles = Get-ChildItem -LiteralPath $resolvedBundle -Recurse -File |
    Where-Object { $_.Extension.ToLowerInvariant() -in $nativeExtensions }

if (-not $nativeFiles) {
    throw "Aucun binaire Windows trouvé dans $resolvedBundle."
}

$invalidSignatures = @(foreach ($file in $nativeFiles) {
    $signature = Get-AuthenticodeSignature -LiteralPath $file.FullName
    if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
        [pscustomobject]@{
            Fichier = $file.FullName
            Statut = $signature.Status
            Message = $signature.StatusMessage
        }
    }
})

if ($invalidSignatures) {
    $displayLimit = 20
    $invalidSignatures |
        Select-Object -First $displayLimit |
        Format-Table -AutoSize |
        Out-String |
        Write-Host
    if ($invalidSignatures.Count -gt $displayLimit) {
        Write-Host "... et $($invalidSignatures.Count - $displayLimit) autre(s) fichier(s)."
    }
    throw "$($invalidSignatures.Count) binaire(s) Windows ne possèdent pas de signature Authenticode valide."
}

Write-Host "$($nativeFiles.Count) binaire(s) Windows possèdent une signature Authenticode valide."
