param(
    [string]$UrlContains = "mp_blog/creation/editor",
    [int]$Port = 9222
)

$ErrorActionPreference = "Stop"

function Send-Cdp($Socket, [int]$Id, [string]$Method, $Params = @{}) {
    $payload = @{
        id = $Id
        method = $Method
        params = $Params
    } | ConvertTo-Json -Depth 20 -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
    $Socket.SendAsync([ArraySegment[byte]]::new($bytes), [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).Wait()
}

function Receive-Cdp($Socket) {
    $buffer = New-Object byte[] 65536
    $stream = [System.IO.MemoryStream]::new()
    do {
        $result = $Socket.ReceiveAsync([ArraySegment[byte]]::new($buffer), [Threading.CancellationToken]::None).Result
        if ($result.Count -gt 0) { $stream.Write($buffer, 0, $result.Count) }
    } until ($result.EndOfMessage)
    if ($stream.Length -eq 0) { return $null }
    return ([System.Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json)
}

function Flatten-Frames($Node, [int]$Depth = 0) {
    $item = [ordered]@{
        depth = $Depth
        id = $Node.frame.id
        parentId = $Node.frame.parentId
        name = $Node.frame.name
        url = $Node.frame.url
    }
    Write-Output ([pscustomobject]$item)
    if ($Node.childFrames) {
        foreach ($child in $Node.childFrames) {
            Flatten-Frames $child ($Depth + 1)
        }
    }
}

$targets = Invoke-RestMethod "http://127.0.0.1:$Port/json"
$page = @($targets | Where-Object { $_.type -eq "page" -and $_.url -like "*$UrlContains*" } | Select-Object -First 1)[0]
if (-not $page.webSocketDebuggerUrl) {
    throw "No matching Edge page found."
}

$socket = [System.Net.WebSockets.ClientWebSocket]::new()
$socket.ConnectAsync([Uri]$page.webSocketDebuggerUrl, [Threading.CancellationToken]::None).Wait()
Send-Cdp $socket 1 "Page.getFrameTree"
$response = $null
while ($true) {
    $event = Receive-Cdp $socket
    if ($event -and $event.id -eq 1) {
        $response = $event
        break
    }
}
$socket.Dispose()

Flatten-Frames $response.result.frameTree | ConvertTo-Json -Depth 10
