param(
    [string]$Article = "posts/enterprise-ai-safety-guardrails-before-launch.md"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path $Article)) {
    throw "Article not found: $Article"
}

function Parse-FrontMatter([string]$Raw) {
    $meta = @{}
    $body = $Raw
    $match = [regex]::Match($Raw, "(?s)^---\s*\n(.*?)\n---\s*\n?(.*)$")
    if ($match.Success) {
        $body = $match.Groups[2].Value
        foreach ($line in ($match.Groups[1].Value -split "`n")) {
            if ($line -match "^\s*([^:#]+):\s*(.*?)\s*$") {
                $meta[$Matches[1].Trim()] = $Matches[2].Trim().Trim('"').Trim("'")
            }
        }
    }
    return @{ meta = $meta; body = $body }
}

function Html([string]$Text) {
    return [System.Net.WebUtility]::HtmlEncode($Text)
}

function Convert-MarkdownToHtml([string]$Markdown) {
    $lines = $Markdown -split "`r?`n"
    $blocks = New-Object System.Collections.Generic.List[string]
    $paragraph = New-Object System.Collections.Generic.List[string]
    $inCode = $false
    $code = New-Object System.Collections.Generic.List[string]
    $list = New-Object System.Collections.Generic.List[string]

    function Flush-Paragraph {
        if ($paragraph.Count -gt 0) {
            $blocks.Add("<p>" + (Html (($paragraph -join " ").Trim())) + "</p>")
            $paragraph.Clear()
        }
    }

    function Flush-List {
        if ($list.Count -gt 0) {
            $blocks.Add("<ul>" + (($list | ForEach-Object { "<li>" + (Html $_) + "</li>" }) -join "") + "</ul>")
            $list.Clear()
        }
    }

    foreach ($line in $lines) {
        if ($line.Trim().StartsWith('```')) {
            if (-not $inCode) {
                Flush-Paragraph
                Flush-List
                $inCode = $true
                $code.Clear()
            } else {
                $blocks.Add("<pre><code>" + (Html ($code -join "`n")) + "</code></pre>")
                $inCode = $false
            }
            continue
        }

        if ($inCode) {
            $code.Add($line)
            continue
        }

        if ($line -match "^#\s+(.+)$") {
            Flush-Paragraph
            Flush-List
            $blocks.Add("<h1>" + (Html $Matches[1].Trim()) + "</h1>")
            continue
        }

        if ($line -match "^##\s+(.+)$") {
            Flush-Paragraph
            Flush-List
            $blocks.Add("<h2>" + (Html $Matches[1].Trim()) + "</h2>")
            continue
        }

        if ($line -match "^###\s+(.+)$") {
            Flush-Paragraph
            Flush-List
            $blocks.Add("<h3>" + (Html $Matches[1].Trim()) + "</h3>")
            continue
        }

        if ($line -match "^\s*[-*]\s+(.+)$") {
            Flush-Paragraph
            $list.Add($Matches[1].Trim())
            continue
        }

        if ([string]::IsNullOrWhiteSpace($line)) {
            Flush-Paragraph
            Flush-List
            continue
        }

        $paragraph.Add($line.Trim())
    }

    Flush-Paragraph
    Flush-List

    return ($blocks -join "`n")
}

$raw = Get-Content -Raw -Encoding UTF8 $Article
$parsed = Parse-FrontMatter $raw
$meta = $parsed.meta
$body = $parsed.body.Trim()
$title = if ($meta.ContainsKey("title")) { $meta["title"] } else { [System.IO.Path]::GetFileNameWithoutExtension($Article) }
$plainBody = ($body -replace '#+|\*|`|>', '' -replace '\s+', ' ').Trim()
$description = if ($meta.ContainsKey("description")) { $meta["description"] } else { $plainBody.Substring(0, [Math]::Min(180, $plainBody.Length)) }
$html = Convert-MarkdownToHtml $body
$tags = @()
if ($meta.ContainsKey("tags")) {
    $tags = ($meta["tags"].Trim("[]") -split ",") | ForEach-Object { $_.Trim().Trim('"').Trim("'") } | Where-Object { $_ }
}

$payload = @{
    title = $title
    description = $description
    html = $html
    tags = $tags
} | ConvertTo-Json -Depth 10 -Compress

$payloadLiteral = $payload | ConvertTo-Json -Compress
$js = @"
(async () => {
  const payload = JSON.parse($payloadLiteral);
  const setValue = (el, value) => {
    if (!el) return false;
    el.focus();
    el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  };

  const titleOk = setValue(document.querySelector('#txtTitle'), payload.title);
  const summaryOk = setValue(document.querySelector('#txtSammary'), payload.description)
    || setValue(Array.from(document.querySelectorAll('textarea')).find(e => (e.placeholder || '').includes('摘要')), payload.description);

  let editorOk = false;
  if (window.CKEDITOR && window.CKEDITOR.instances && window.CKEDITOR.instances.editor) {
    window.CKEDITOR.instances.editor.setData(payload.html);
    window.CKEDITOR.instances.editor.fire('change');
    editorOk = true;
  }

  const tagInput = Array.from(document.querySelectorAll('input')).find(e => (e.placeholder || '').includes('Enter键入'));
  if (tagInput && payload.tags) {
    for (const tag of payload.tags.slice(0, 5)) {
      tagInput.focus();
      tagInput.value = tag;
      tagInput.dispatchEvent(new Event('input', { bubbles: true }));
      tagInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
      tagInput.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
      await new Promise(resolve => setTimeout(resolve, 120));
    }
  }

  return JSON.stringify({
    titleOk,
    summaryOk,
    editorOk,
    title: payload.title,
    tags: payload.tags,
    htmlLength: payload.html.length
  });
})()
"@

& "$PSScriptRoot\cdp-eval.ps1" -Expression $js

$framePayload = @{
    html = $html
    text = $body
} | ConvertTo-Json -Depth 5 -Compress
$framePayloadLiteral = $framePayload | ConvertTo-Json -Compress
$frameJs = @"
(() => {
  const payload = JSON.parse($framePayloadLiteral);
  document.body.innerHTML = payload.html;
  document.body.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: payload.text.slice(0, 100) }));
  document.body.dispatchEvent(new Event('change', { bubbles: true }));
  return JSON.stringify({ bodyText: document.body.innerText.slice(0, 120), htmlLength: document.body.innerHTML.length });
})()
"@

& "$PSScriptRoot\cdp-eval.ps1" -FrameUrlContains "mp_blog/creation/editor" -Expression $frameJs
