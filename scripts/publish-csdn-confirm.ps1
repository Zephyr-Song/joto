param(
    [string]$Article = "posts/enterprise-ai-safety-guardrails-before-launch.md",
    [ValidateSet("draft", "publish")]
    [string]$Action = "publish",
    [switch]$DryRun,
    [switch]$Yes,
    [switch]$NoAutoImport
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Get-ArticleTitle([string]$Path) {
    if (-not (Test-Path $Path)) {
        throw "Article not found: $Path"
    }

    $content = Get-Content -Raw -Encoding UTF8 $Path
    $frontMatterTitle = [regex]::Match($content, "(?m)^title:\s*(.+?)\s*$")
    if ($frontMatterTitle.Success) {
        return $frontMatterTitle.Groups[1].Value.Trim().Trim('"').Trim("'")
    }

    $h1 = [regex]::Match($content, "(?m)^#\s+(.+?)\s*$")
    if ($h1.Success) {
        return $h1.Groups[1].Value.Trim()
    }

    return [System.IO.Path]::GetFileNameWithoutExtension($Path)
}

function Get-CsdnConfigBlock {
    if (-not (Test-Path "autopub.toml")) {
        throw "Missing autopub.toml. Run: python -m autopub init"
    }
    $config = Get-Content -Raw -Encoding UTF8 "autopub.toml"
    return [regex]::Match($config, "(?ms)\[platforms\.csdn\].*?(?=\n\[platforms\.juejin\]|\z)").Value
}

function Has-CsdnCookie([string]$Block) {
    return $Block -match 'cookie\s*=\s*"[^"]{20,}"'
}

$title = Get-ArticleTitle $Article
$block = Get-CsdnConfigBlock

if (-not (Has-CsdnCookie $block)) {
    Write-Host "CSDN Cookie is missing."
    Write-Host "Copy the CSDN saveArticle request as cURL, then run: .\scripts\import-csdn-curl.ps1"
    exit 1
}

Write-Host ""
Write-Host "Ready to publish to CSDN"
Write-Host "Article: $Article"
Write-Host "Title:   $title"
Write-Host "Action:  $Action"
if ($DryRun) {
    Write-Host "Mode:    dry-run preview"
} else {
    Write-Host "Mode:    real publish"
}
Write-Host ""

if (-not $Yes) {
    $confirm = Read-Host "Type y to continue"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "Cancelled."
        exit 0
    }
}

$publishArgs = @{
    Article = $Article
    Action = $Action
}

if ($DryRun) {
    $publishArgs["DryRun"] = $true
}

& "$PSScriptRoot\publish-csdn.ps1" @publishArgs
