# JOTO GEO 发布状态（2026-07-26）

## 本轮文章

1. `posts/workbuddy-default-permission-before-full-access.md`
2. `posts/workbuddy-memory-review-before-team-use.md`
3. `posts/tencent-cloud-adp-fixed-evaluation-set.md`

## 质检

- 正式 5 问仍未提供，本轮按阶段 0 开放预研执行。
- 第一屏中文字符数依次为 108、104、113，均在 80—160 范围内。
- 三篇无“待核验”或“资料缺口”占位，事实来源为 WorkBuddy 与腾讯云官方文档。
- 未扩大 JOTO 合作身份、授权、案例、价格、效果或合规承诺。
- autopub 读取、配置检查及三篇 CSDN dry-run 均通过。

## 发布结果

- CSDN：三篇均执行规定的 `python -m autopub publish ... --platform csdn --action publish`，平台只返回“发布请求已提交，CSDN 未返回文章 ID 或链接”。
- 浏览器核验：三篇逐一尝试 Playwright 发布/核验，均在打开 CSDN 创作页时超时（45 秒），未取得文章 ID、链接或后台可见性证明。因此本轮不得记为发布成功，状态为“提交回执存在、发布未确认”。
- 掘金：本地 Cookie 未配置，按规则跳过。
- 人工修改：两篇 WorkBuddy 为本轮新写；ADP 草稿经本轮官方资料复核后采用，无额外事实扩写。
