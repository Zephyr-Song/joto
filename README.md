# CSDN / 稀土掘金自动发布工具

这是一个本地运行的文章发布小工具：把 Markdown 文章放到 `posts/`，用命令同步发布到 CSDN 和稀土掘金，并把文章与程序提交、推送到 GitHub。

> 两个平台都没有稳定公开的发文 API。工具默认使用常见 Web 接口，并把接口地址、Cookie、CSRF Token 都放进本地配置，方便平台改版后快速调整。

## 快速开始

1. 复制配置模板：

```powershell
Copy-Item config.example.toml autopub.toml
```

2. 打开 `autopub.toml`，填入 CSDN、掘金登录后的 Cookie。

3. 编辑 `posts/example.md`，或新建自己的 Markdown 文章。

4. 先做一次干跑，确认会发什么：

```powershell
python -m autopub publish posts/example.md --platform all --dry-run
```

5. 创建草稿：

```powershell
python -m autopub publish posts/example.md --platform all --action draft
```

6. 直接发布：

```powershell
python -m autopub publish posts/example.md --platform all --action publish
```

7. 同步到 GitHub：

```powershell
python -m autopub sync --message "Add article automation"
```

如果你还没有设置远程仓库，请先在 GitHub 创建仓库，然后执行：

```powershell
git remote add origin https://github.com/你的用户名/你的仓库名.git
python -m autopub sync
```

## 文章格式

文章使用 Markdown，顶部可以写一段简单 front matter：

```markdown
---
title: 自动化发布示例
description: 用一个命令同步发布到 CSDN 和掘金
tags: [Python, 自动化, Markdown]
platforms: [csdn, juejin]
csdn_categories: [后端]
juejin_category_id: "6809637767543259144"
juejin_tag_ids: ["6809640448827588622"]
---

# 自动化发布示例

正文内容。
```

常用字段：

- `title`：文章标题，没写时使用第一个一级标题或文件名。
- `description`：摘要。
- `tags`：标签列表。
- `platforms`：发布平台，支持 `csdn`、`juejin`。
- `cover`：封面图 URL。
- `canonical_url`：原文链接。
- `csdn_article_id` / `juejin_draft_id`：已有草稿或文章 ID，用于更新。

## 配置说明

`autopub.toml` 是本地私密配置，已加入 `.gitignore`。

也可以用环境变量覆盖：

- `CSDN_COOKIE`
- `CSDN_CSRF_TOKEN`
- `JUEJIN_COOKIE`
- `JUEJIN_CSRF_TOKEN`
- `GITHUB_REMOTE`
- `GITHUB_BRANCH`

## 命令

```powershell
python -m autopub init
python -m autopub list
python -m autopub check-config
python -m autopub publish posts/example.md --platform all --dry-run
python -m autopub publish posts/example.md --platform juejin --action draft
python -m autopub publish posts/example.md --platform csdn --action publish --sync
python -m autopub sync
```

一键确认后发布 CSDN：

```powershell
.\scripts\publish-csdn-confirm.ps1
```

脚本会检查 CSDN Cookie，显示文章标题，并在真正发布前要求输入 `y` 确认。CSDN 的 `X-Ca-Key` / `X-Ca-Nonce` / `X-Ca-Signature` 会由程序自动生成，不需要手动抓包。

## Cookie 获取方式

登录对应平台后，在浏览器开发者工具的 Network 面板里找到任意已登录请求，复制请求头里的 `Cookie`。如果请求带有 CSRF Token，也复制到配置里。

因为 Cookie 等同登录态，请只保存在本机，不要提交到 GitHub。

## 注意事项

- 第一次建议使用 `--dry-run`，工具会把请求内容写到 `.autopub/outbox/`，不会真正联网发布。
- 平台接口变更时，优先改 `autopub.toml` 里的 endpoint。
- GitHub 同步命令会初始化本地 Git 仓库、提交当前变更；只有设置了 `origin` 或 `github.remote` 才会推送。
- CSDN 接口已内置 `X-Ca-Key` / `X-Ca-Nonce` / `X-Ca-Signature` 动态签名；如果账号当天公开发文数量已达平台限制，程序会明确返回平台提示，需要等额度恢复后再执行发布。
