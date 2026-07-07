# Bilibili Lead Finder

This workflow finds public Bilibili comments that may match JOTO's B2B work,
then generates local review files with reply drafts.

It does not publish replies, use cookies, bypass login, bypass captcha, or
pretend to be a human. Review every candidate before replying through an
authorized account and platform-approved flow.

## Business Signals

The default terms are based on:

- Pharaoh Command: AI NetOps, AI network operations, network automation,
  diagnostics, topology, alerting, SRE, and enterprise IT.
- JOTO cloud app: AI guardrails, private deployment, knowledge bases, RAG,
  agents, permissions, audit, and enterprise large-model safety.

## Usage

Use a curated seed file:

```powershell
python scripts\bilibili_lead_finder.py `
  --video-file comments\bilibili-business-seeds.txt `
  --max-videos 6 `
  --comments-per-video 20 `
  --min-score 2 `
  --out .commentops\leads\bilibili-joto-leads.json
```

Or try keyword discovery first:

```powershell
python scripts\bilibili_lead_finder.py `
  --keyword "AI网络运维" `
  --keyword "Dify 私有化部署" `
  --keyword "AI护栏" `
  --max-videos 5
```

The Bilibili search endpoint may return `412 Precondition Failed` in some
environments. In that case, use `--video` or `--video-file` with curated video
URLs. Comment reading for public videos is usually more stable than video
search.

## Output

The script writes:

- JSON data, defaulting to `.commentops/leads/bilibili-leads.json`
- A Markdown review sheet next to the JSON file

Each lead includes the video URL, comment URL, commenter name, comment text,
matched terms, demand signals, lead level, score, and a reply draft.

By default, topic-only comments are filtered out. A comment must have at least
one demand signal, such as deployment, enterprise/government context, quotation,
procurement, trial, demo, integration, or solution intent. Use
`--include-topic-only` only when you want broad market research instead of
lead discovery.

## Validation

```powershell
python -m pytest tests\test_bilibili_lead_finder.py
```
