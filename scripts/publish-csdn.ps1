param(
    [string]$Article = "posts/enterprise-ai-safety-guardrails-before-launch.md",
    [ValidateSet("draft", "publish")]
    [string]$Action = "publish",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path "autopub.toml")) {
    Write-Host "Missing autopub.toml. Run: python -m autopub init"
    exit 1
}

$config = Get-Content -Raw -Encoding UTF8 "autopub.toml"
$csdnBlock = [regex]::Match($config, "(?ms)\[platforms\.csdn\].*?(?=\n\[|\z)").Value
if ($csdnBlock -notmatch 'cookie\s*=\s*"[^"]{20,}"') {
    Write-Host "CSDN Cookie is empty. Fill platforms.csdn.cookie in autopub.toml first."
    exit 1
}

$argsList = @(
    "-m", "autopub",
    "publish", $Article,
    "--platform", "csdn",
    "--action", $Action
)

if ($DryRun) {
    $argsList += "--dry-run"
}

python @argsList
