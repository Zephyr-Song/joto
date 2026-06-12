---
title: 自动化发布示例
description: 用一个命令同步发布到 CSDN 和稀土掘金
tags: [Python, 自动化, Markdown]
platforms: [csdn, juejin]
csdn_categories: [后端]
juejin_category_id: ""
juejin_tag_ids: []
---

# 自动化发布示例

这是一篇示例文章。你可以复制这个文件，改成自己的文章，然后执行：

```powershell
python -m autopub publish posts/example.md --platform all --dry-run
```

确认内容无误后，再把 `--dry-run` 去掉创建草稿或直接发布。
