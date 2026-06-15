param(
    [string]$Article = "posts/enterprise-ai-safety-guardrails-before-launch.md",
    [int]$Port = 9222
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

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

function Invoke-Cdp($Socket, [ref]$NextId, [string]$Method, $Params = @{}) {
    $NextId.Value += 1
    $id = $NextId.Value
    Send-Cdp $Socket $id $Method $Params
    while ($true) {
        $event = Receive-Cdp $Socket
        if ($event -and $event.id -eq $id) {
            if ($event.error) {
                throw ($event.error | ConvertTo-Json -Depth 10)
            }
            return $event.result
        }
    }
}

function Parse-Article([string]$Raw) {
    $meta = @{}
    $body = $Raw
    $match = [regex]::Match($Raw, "(?s)^---\s*\n(.*?)\n---\s*\n?(.*)$")
    if ($match.Success) {
        $body = $match.Groups[2].Value.Trim()
        foreach ($line in ($match.Groups[1].Value -split "`n")) {
            if ($line -match "^\s*([^:#]+):\s*(.*?)\s*$") {
                $meta[$Matches[1].Trim()] = $Matches[2].Trim().Trim('"').Trim("'")
            }
        }
    }
    return @{ meta = $meta; body = $body }
}

if (-not (Test-Path $Article)) {
    throw "Article not found: $Article"
}

$parsed = Parse-Article (Get-Content -Raw -Encoding UTF8 $Article)
$title = if ($parsed.meta.ContainsKey("title")) { $parsed.meta["title"] } else { [System.IO.Path]::GetFileNameWithoutExtension($Article) }
$description = if ($parsed.meta.ContainsKey("description")) { $parsed.meta["description"] } else { "" }
$body = $parsed.body

$targets = Invoke-RestMethod "http://127.0.0.1:$Port/json"
$page = @($targets | Where-Object { $_.type -eq "page" -and $_.url -like "*mp_blog/creation/editor*" } | Select-Object -First 1)[0]
if (-not $page.webSocketDebuggerUrl) {
    throw "No CSDN editor page found."
}

$socket = [System.Net.WebSockets.ClientWebSocket]::new()
$socket.ConnectAsync([Uri]$page.webSocketDebuggerUrl, [Threading.CancellationToken]::None).Wait()
$nextId = 0
$nextRef = [ref]$nextId

Invoke-Cdp $socket $nextRef "Runtime.evaluate" @{
    expression = @"
(() => {
  const setValue = (selector, value) => {
    const el = document.querySelector(selector);
    if (!el) return false;
    el.focus();
    el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  };
  setValue('#txtTitle', $(ConvertTo-Json $title -Compress));
  setValue('#txtSammary', $(ConvertTo-Json $description -Compress));
  return true;
})()
"@
    awaitPromise = $true
    returnByValue = $true
} | Out-Null

$rectResult = Invoke-Cdp $socket $nextRef "Runtime.evaluate" @{
    expression = "JSON.stringify((()=>{const e=document.querySelector('iframe.cke_wysiwyg_frame')||document.querySelector('#cke_1_contents')||document.querySelector('#editor'); if(!e)return null; const r=e.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height};})())"
    awaitPromise = $true
    returnByValue = $true
}

$rect = $rectResult.result.value | ConvertFrom-Json
if (-not $rect) {
    throw "Could not locate CSDN editor area."
}

$x = [double]($rect.x + [Math]::Max(20, $rect.w / 2))
$y = [double]($rect.y + [Math]::Min(80, [Math]::Max(20, $rect.h / 4)))

Invoke-Cdp $socket $nextRef "Input.dispatchMouseEvent" @{ type = "mousePressed"; x = $x; y = $y; button = "left"; clickCount = 1 } | Out-Null
Invoke-Cdp $socket $nextRef "Input.dispatchMouseEvent" @{ type = "mouseReleased"; x = $x; y = $y; button = "left"; clickCount = 1 } | Out-Null
Start-Sleep -Milliseconds 300

Invoke-Cdp $socket $nextRef "Input.dispatchKeyEvent" @{ type = "rawKeyDown"; key = "a"; code = "KeyA"; windowsVirtualKeyCode = 65; nativeVirtualKeyCode = 65; modifiers = 2 } | Out-Null
Invoke-Cdp $socket $nextRef "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "a"; code = "KeyA"; windowsVirtualKeyCode = 65; nativeVirtualKeyCode = 65; modifiers = 2 } | Out-Null
Start-Sleep -Milliseconds 100
Invoke-Cdp $socket $nextRef "Input.dispatchKeyEvent" @{ type = "keyDown"; key = "Backspace"; code = "Backspace"; windowsVirtualKeyCode = 8; nativeVirtualKeyCode = 8 } | Out-Null
Invoke-Cdp $socket $nextRef "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "Backspace"; code = "Backspace"; windowsVirtualKeyCode = 8; nativeVirtualKeyCode = 8 } | Out-Null
Start-Sleep -Milliseconds 100

Invoke-Cdp $socket $nextRef "Input.insertText" @{ text = $body } | Out-Null
Start-Sleep -Milliseconds 500

$check = Invoke-Cdp $socket $nextRef "Runtime.evaluate" @{
    expression = "JSON.stringify({title:document.querySelector('#txtTitle')?.value||'', bodyText:Array.from(document.querySelectorAll('iframe.cke_wysiwyg_frame')).map(f=>{try{return f.contentDocument?.body?.innerText||''}catch(e){return ''}}).join('').slice(0,200), ckText:window.editorxx?.editable?.()?.getText?.()?.slice(0,200)||'', ckDataLen:window.editorxx?.getData?.()?.length||0})"
    awaitPromise = $true
    returnByValue = $true
}

$socket.Dispose()
Write-Output $check.result.value
