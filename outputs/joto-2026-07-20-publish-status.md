# JOTO GEO 2026-07-20 发布状态

## 生成结果

- `posts/workbuddy-multistep-task-or-chat-assistant.md`
- `posts/workbuddy-pilot-task-acceptance-checklist.md`
- `posts/tencent-cloud-adp-small-scenario-pilot.md`

三篇均完成首屏字数、单一核心判断、结构、事实来源、实体关系、品牌占比和人工核验检查；CSDN dry-run 均通过。

## 平台结果

- CSDN：三篇均已按要求调用 `python -m autopub publish <文章路径> --platform csdn --action publish`。接口只返回“已提交”，未返回文章 ID 或链接，不能视为成功发布。
- CSDN 浏览器核验：第一篇的 `saveArticle` 请求返回 HTTP 400，平台提示“文章频繁发布，请稍后再试”；文章未出现在公开主页，未生成文章 ID。为避免重复提交和延长限制，另外两篇没有继续连续补发。
- 掘金：本地未配置有效 Cookie，按规则跳过。

## 发布链接与文章 ID

本轮没有可确认的发布链接或文章 ID。

## 人工修改记录

- 未对平台编辑器中的正文作人工修改。
- 解除 CSDN 发布频率限制后，应逐篇重新发布并核验后台文章 ID；不要仅依据接口“已提交”判断成功。

