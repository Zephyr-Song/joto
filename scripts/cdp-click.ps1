param(
    [Parameter(Mandatory=$true)]
    [double]$X,
    [Parameter(Mandatory=$true)]
    [double]$Y,
    [string]$UrlContains = "mp_blog/creation/editor",
    [int]$Port = 9222,
    [int]$TimeoutSeconds = 10
)

$ErrorActionPreference = "Stop"

function Send-Cdp($Socket, [int]$Id, [string]$Method, $Params = @{}) {
    $payload = @{
        id = $Id
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

$targets = Invoke-RestMethod "http://127.0.0.1:$Port/json"
$page = @($targets | Where-Object { $_.type -eq "page" -and $_.url -like "*$UrlContains*" } | Select-Object -First 1)[0]
if (-not $page.webSocketDebuggerUrl) {
    throw "No matching Edge page found for $UrlContains"
}

$socket = [System.Net.WebSockets.ClientWebSocket]::new()
$socket.ConnectAsync([Uri]$page.webSocketDebuggerUrl, [Threading.CancellationToken]::None).Wait()

Send-Cdp $socket 1 "Input.dispatchMouseEvent" @{
    type = "mouseMoved"
    x = $X
    y = $Y
    button = "none"
}
Send-Cdp $socket 2 "Input.dispatchMouseEvent" @{
    type = "mousePressed"
    x = $X
    y = $Y
    button = "left"
    clickCount = 1
}
Send-Cdp $socket 3 "Input.dispatchMouseEvent" @{
    type = "mouseReleased"
    x = $X
    y = $Y
    button = "left"
    clickCount = 1
}

$seen = @()
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $deadline -and $seen.Count -lt 3) {
    $event = Receive-Cdp $socket
    if ($event -and $event.id -in @(1, 2, 3)) {
        $seen += $event.id
    }
}

$socket.Dispose()

@{
    ok = $true
    x = $X
    y = $Y
    responses = $seen
} | ConvertTo-Json -Compress
