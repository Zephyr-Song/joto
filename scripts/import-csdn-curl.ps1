param(
    [string]$CurlText = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $CurlText) {
    $CurlText = Get-Clipboard -Raw
}

if (-not $CurlText -or $CurlText -notmatch "curl") {
    Write-Host "Clipboard does not look like a cURL command."
    Write-Host "In DevTools Network, right-click the CSDN saveArticle request and choose Copy > Copy as cURL."
    exit 1
}

if (-not (Test-Path "autopub.toml")) {
    Copy-Item "config.example.toml" "autopub.toml"
}

function Unquote-CurlValue([string]$value) {
    $value = $value.Trim()
    if (($value.StartsWith("'") -and $value.EndsWith("'")) -or ($value.StartsWith('"') -and $value.EndsWith('"'))) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    return $value -replace "\\'", "'" -replace '\\"', '"'
}

function Escape-Toml([string]$value) {
    return ($value -replace '\\', '\\' -replace '"', '\"')
}

$url = ""
$urlMatch = [regex]::Match($CurlText, "curl(?:\.exe)?\s+(?:--location\s+)?(?<url>'[^']+'|""[^""]+""|\S+)")
if ($urlMatch.Success) {
    $url = Unquote-CurlValue $urlMatch.Groups["url"].Value
}

$headers = [ordered]@{}
$headerMatches = [regex]::Matches($CurlText, "(?:-H|--header)\s+(?<header>'[^']+'|""[^""]+"")")
foreach ($match in $headerMatches) {
    $line = Unquote-CurlValue $match.Groups["header"].Value
    $parts = $line.Split(":", 2)
    if ($parts.Count -ne 2) {
        continue
    }
    $name = $parts[0].Trim()
    $value = $parts[1].Trim()
    if ($name) {
        $headers[$name] = $value
    }
}

if (-not $headers.Contains("Cookie") -and $CurlText -match "(?:-b|--cookie)\s+(?<cookie>'[^']+'|""[^""]+""|\S+)") {
    $headers["Cookie"] = Unquote-CurlValue $Matches["cookie"]
}

if (-not $headers.Contains("Cookie")) {
    Write-Host "No Cookie header found in the cURL command."
    exit 1
}

$configPath = "autopub.toml"
$text = [System.IO.File]::ReadAllText((Join-Path (Get-Location) $configPath), [System.Text.Encoding]::UTF8)
$cookie = Escape-Toml $headers["Cookie"]
$text = [regex]::Replace($text, '(?ms)(\[platforms\.csdn\].*?^cookie\s*=\s*)".*?"', '$1"' + $cookie + '"')

if ($headers.Contains("Referer")) {
    $referer = Escape-Toml $headers["Referer"]
    $text = [regex]::Replace($text, '(?ms)(\[platforms\.csdn\].*?^referer\s*=\s*)".*?"', '$1"' + $referer + '"')
}

if ($url -and $url -match "saveArticle") {
    $escapedUrl = Escape-Toml $url
    $text = [regex]::Replace($text, '(?ms)(\[platforms\.csdn\].*?^save_endpoint\s*=\s*)".*?"', '$1"' + $escapedUrl + '"')
    $text = [regex]::Replace($text, '(?ms)(\[platforms\.csdn\].*?^publish_endpoint\s*=\s*)".*?"', '$1"' + $escapedUrl + '"')
}

$text = [regex]::Replace($text, "(?ms)\n\[platforms\.csdn\.headers\].*?(?=\n\[|\z)", "")

$skip = @("cookie", "content-length", "host")
$headerLines = New-Object System.Collections.Generic.List[string]
foreach ($name in $headers.Keys) {
    if ($skip -contains $name.ToLowerInvariant()) {
        continue
    }
    $value = Escape-Toml $headers[$name]
    $headerLines.Add("$name = ""$value""")
}

$headersBlock = "`n[platforms.csdn.headers]`n" + (($headerLines | Sort-Object) -join "`n") + "`n"
if ($text -match "\n\[platforms\.juejin\]") {
    $text = $text -replace "\n\[platforms\.juejin\]", "$headersBlock`n[platforms.juejin]"
} else {
    $text += $headersBlock
}

[System.IO.File]::WriteAllText((Join-Path (Get-Location) $configPath), $text, [System.Text.UTF8Encoding]::new($false))

Write-Host "Imported CSDN Cookie and request headers into autopub.toml."
Write-Host "Now run: .\scripts\publish-csdn.ps1"
