param(
    [string]$PackageName = "campus-ai-match-code-package-2026-05-30"
)

$ErrorActionPreference = "Stop"

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $scriptPath "..")
$releaseDir = Join-Path $root "release"
$packageDir = Join-Path $releaseDir $PackageName
$zipPath = Join-Path $releaseDir "$PackageName.zip"

function Assert-InsideRoot {
    param([string]$PathToCheck)
    $full = [System.IO.Path]::GetFullPath($PathToCheck)
    $rootFull = [System.IO.Path]::GetFullPath($root)
    if (-not $full.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to operate outside workspace: $full"
    }
}

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

Assert-InsideRoot $packageDir
Assert-InsideRoot $zipPath

if (Test-Path $packageDir) {
    Remove-Item -LiteralPath $packageDir -Recurse -Force
}
if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

$excludeDirs = @(
    ".git",
    ".claude",
    ".playwright-cli",
    ".superpowers",
    ".vscode",
    ".idea",
    "release",
    "docs",
    "scripts",
    "soybean-admin-main",
    "vue-pure-admin-main",
    "node_modules",
    "dist",
    ".vite",
    "__pycache__",
    "db_backups",
    "uploads",
    "tmp",
    "model_cache"
)

$excludeFiles = @(
    ".env",
    "*.env",
    "*.db",
    "*.db-wal",
    "*.db-shm",
    "*.log",
    "*.pyc",
    "~$*.docx",
    "Thumbs.db",
    ".DS_Store",
    "skill_graph.json",
    "人工智能学院首届校园黑客松挑战赛比赛秩序册.docx"
)

$robocopyArgs = @(
    $root,
    $packageDir,
    "/E",
    "/NFL",
    "/NDL",
    "/NJH",
    "/NJS",
    "/NP",
    "/XD"
) + $excludeDirs + @("/XF") + $excludeFiles

& robocopy @robocopyArgs | Out-Null
$exitCode = $LASTEXITCODE
if ($exitCode -gt 7) {
    throw "robocopy failed with exit code $exitCode"
}

# The submission code package should not include root-level Word source materials.
# Keep generated docs under docs/, but remove accidental root-level .docx files.
Get-ChildItem -LiteralPath $packageDir -File -Filter "*.docx" | Remove-Item -Force

Compress-Archive -LiteralPath $packageDir -DestinationPath $zipPath -CompressionLevel Optimal

$zip = Get-Item -LiteralPath $zipPath
Write-Host "Package directory: $packageDir"
Write-Host "Zip file: $zipPath"
Write-Host ("Zip size: {0:N2} MB" -f ($zip.Length / 1MB))
