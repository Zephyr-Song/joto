param(
    [Parameter(Mandatory=$true)]
    [string]$Expression,
    [string]$UrlContains = "mp_blog/creation/editor",
    [string]$FrameUrlContains = "",
    [int]$Port = 9222,
    [int]$TimeoutSeconds = 30
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

$contextId = $null
if ($FrameUrlContains) {
    Send-Cdp $socket 100 "Page.getFrameTree"
    $frameResponse = $null
    while ($true) {
        $event = Receive-Cdp $socket
        if ($event -and $event.id -eq 100) {
            $frameResponse = $event
            break
        }
    }

    function Find-Frame($Node, [string]$Needle) {
        if ($Node.childFrames) {
            foreach ($child in $Node.childFrames) {
                $found = Find-Frame $child $Needle
                if ($found) {
                    return $found
                }
            }
        }
        if ($Node.frame.url -like "*$Needle*") {
            return $Node.frame.id
        }
        return $null
    }

    $frameId = Find-Frame $frameResponse.result.frameTree $FrameUrlContains
    if (-not $frameId) {
        throw "No frame found for $FrameUrlContains"
    }

    Send-Cdp $socket 101 "Page.createIsolatedWorld" @{
        frameId = $frameId
        worldName = "joto"
        grantUniveralAccess = $true
    }
    while ($true) {
        $event = Receive-Cdp $socket
        if ($event -and $event.id -eq 101) {
            $contextId = $event.result.executionContextId
            break
        }
    }
}

$params = @{
    expression = $Expression
    awaitPromise = $true
    returnByValue = $true
    includeCommandLineAPI = $true
}
if ($contextId) {
    $params.contextId = $contextId
}

Send-Cdp $socket 1 "Runtime.evaluate" $params
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$response = $null
while ((Get-Date) -lt $deadline) {
    $event = Receive-Cdp $socket
    if ($event -and $event.id -eq 1) {
        $response = $event
        break
    }
}

$socket.Dispose()

if (-not $response) {
    throw "No CDP response received."
}

if ($response.error) {
    throw ($response.error | ConvertTo-Json -Depth 10)
}

if ($response.result.exceptionDetails) {
    throw ($response.result.exceptionDetails | ConvertTo-Json -Depth 10)
}

$value = $response.result.result.value
if ($null -eq $value) {
    $response.result.result | ConvertTo-Json -Depth 20
} elseif ($value -is [string]) {
    Write-Output $value
} else {
    $value | ConvertTo-Json -Depth 20
}
