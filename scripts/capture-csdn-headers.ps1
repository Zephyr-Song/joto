param(
    [int]$Port = 9222,
    [int]$TimeoutSeconds = 240,
    [string]$Article = "posts/enterprise-ai-safety-guardrails-before-launch.md"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Find-Edge {
    $candidates = @(
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
        "msedge.exe"
    )

    foreach ($candidate in $candidates) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) {
            return $cmd.Source
        }
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "Microsoft Edge was not found."
}

function Send-Cdp($Socket, [string]$Method, $Params = @{}) {
    $script:NextCdpId += 1
    $payload = @{
        id = $script:NextCdpId
        method = $Method
        params = $Params
    } | ConvertTo-Json -Depth 20 -Compress

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
    $segment = [ArraySegment[byte]]::new($bytes)
    $Socket.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).Wait()
}

function Receive-Cdp($Socket) {
    $buffer = New-Object byte[] 65536
    $stream = [System.IO.MemoryStream]::new()
    do {
        $segment = [ArraySegment[byte]]::new($buffer)
        $result = $Socket.ReceiveAsync($segment, [Threading.CancellationToken]::None).Result
        if ($result.Count -gt 0) {
            $stream.Write($buffer, 0, $result.Count)
        }
    } until ($result.EndOfMessage)

    if ($stream.Length -eq 0) {
        return $null
    }

    $text = [System.Text.Encoding]::UTF8.GetString($stream.ToArray())
    return $text | ConvertFrom-Json
}

function Escape-Toml([string]$value) {
    return ($value -replace '\\', '\\' -replace '"', '\"')
}

function Update-CsdnConfig([hashtable]$Headers, [string]$Url) {
    if (-not (Test-Path "autopub.toml")) {
        Copy-Item "config.example.toml" "autopub.toml"
    }

    $text = [System.IO.File]::ReadAllText((Join-Path (Get-Location) "autopub.toml"), [System.Text.Encoding]::UTF8)

    if ($Headers.ContainsKey("Cookie")) {
        $cookie = Escape-Toml $Headers["Cookie"]
        $text = [regex]::Replace($text, '(?ms)(\[platforms\.csdn\].*?^cookie\s*=\s*)".*?"', '$1"' + $cookie + '"')
    }

    if ($Headers.ContainsKey("Referer")) {
        $referer = Escape-Toml $Headers["Referer"]
        $text = [regex]::Replace($text, '(?ms)(\[platforms\.csdn\].*?^referer\s*=\s*)".*?"', '$1"' + $referer + '"')
    }

    if ($Url -and $Url -match "saveArticle") {
        $escapedUrl = Escape-Toml $Url
        $text = [regex]::Replace($text, '(?ms)(\[platforms\.csdn\].*?^save_endpoint\s*=\s*)".*?"', '$1"' + $escapedUrl + '"')
        $text = [regex]::Replace($text, '(?ms)(\[platforms\.csdn\].*?^publish_endpoint\s*=\s*)".*?"', '$1"' + $escapedUrl + '"')
    }

    $text = [regex]::Replace($text, "(?ms)\n\[platforms\.csdn\.headers\].*?(?=\n\[|\z)", "")

    $skip = @("cookie", "content-length", "host")
    $headerLines = New-Object System.Collections.Generic.List[string]
    foreach ($name in $Headers.Keys) {
        if ($skip -contains $name.ToLowerInvariant()) {
            continue
        }
        $value = Escape-Toml $Headers[$name]
        $headerLines.Add("$name = ""$value""")
    }

    $headersBlock = "`n[platforms.csdn.headers]`n" + (($headerLines | Sort-Object) -join "`n") + "`n"
    if ($text -match "\n\[platforms\.juejin\]") {
        $text = $text -replace "\n\[platforms\.juejin\]", "$headersBlock`n[platforms.juejin]"
    } else {
        $text += $headersBlock
    }

    [System.IO.File]::WriteAllText((Join-Path (Get-Location) "autopub.toml"), $text, [System.Text.UTF8Encoding]::new($false))
}

$edge = Find-Edge
$profile = Join-Path $env:TEMP "joto-csdn-edge-profile"
$url = "https://mp.csdn.net/mp_blog/creation/editor"

Write-Host "Opening Edge for CSDN header capture..."
Write-Host "In the browser, log in if needed, then create/edit any article so CSDN triggers saveArticle."
Write-Host "This script will capture the request headers automatically."

Start-Process -FilePath $edge -ArgumentList @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$profile",
    "--new-window",
    $url
) -WindowStyle Normal

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$tabs = $null
do {
    Start-Sleep -Milliseconds 700
    try {
        $tabs = Invoke-RestMethod "http://127.0.0.1:$Port/json"
    } catch {
        $tabs = $null
    }
} until ($tabs -or (Get-Date) -gt $deadline)

if (-not $tabs) {
    throw "Could not connect to Edge remote debugging port $Port."
}

$page = @($tabs | Where-Object { $_.type -eq "page" } | Select-Object -First 1)[0]
if (-not $page.webSocketDebuggerUrl) {
    throw "No debuggable Edge page found."
}

$socket = [System.Net.WebSockets.ClientWebSocket]::new()
$socket.ConnectAsync([Uri]$page.webSocketDebuggerUrl, [Threading.CancellationToken]::None).Wait()

$script:NextCdpId = 0
Send-Cdp $socket "Network.enable"
Send-Cdp $socket "Page.enable"

$requestUrls = @{}
$captured = $null

while ((Get-Date) -lt $deadline -and -not $captured) {
    $event = Receive-Cdp $socket
    if (-not $event -or -not $event.method) {
        continue
    }

    if ($event.method -eq "Network.requestWillBeSent") {
        $requestId = [string]$event.params.requestId
        $requestUrl = [string]$event.params.request.url
        $requestUrls[$requestId] = $requestUrl

        if ($requestUrl -match "saveArticle|blog-console-api|mdeditor") {
            $headers = @{}
            foreach ($prop in $event.params.request.headers.PSObject.Properties) {
                $headers[$prop.Name] = [string]$prop.Value
            }
            if ($headers.ContainsKey("X-Ca-Key") -or $headers.ContainsKey("x-ca-key")) {
                $captured = @{
                    url = $requestUrl
                    headers = $headers
                }
            }
        }
    }

    if ($event.method -eq "Network.requestWillBeSentExtraInfo") {
        $requestId = [string]$event.params.requestId
        $requestUrl = [string]$requestUrls[$requestId]
        if ($requestUrl -match "saveArticle|blog-console-api|mdeditor") {
            $headers = @{}
            foreach ($prop in $event.params.headers.PSObject.Properties) {
                $headers[$prop.Name] = [string]$prop.Value
            }
            if ($headers.ContainsKey("X-Ca-Key") -or $headers.ContainsKey("x-ca-key")) {
                $captured = @{
                    url = $requestUrl
                    headers = $headers
                }
            }
        }
    }
}

$socket.Dispose()

if (-not $captured) {
    Write-Host "Did not capture a saveArticle request with X-Ca-Key."
    Write-Host "Keep the browser open, edit the article title/body, or click publish preview, then run this script again."
    exit 1
}

Update-CsdnConfig -Headers $captured.headers -Url $captured.url
Write-Host "Captured CSDN request headers and updated autopub.toml."
Write-Host "Now running confirmed publish..."
& "$PSScriptRoot\publish-csdn-confirm.ps1" -Article $Article
