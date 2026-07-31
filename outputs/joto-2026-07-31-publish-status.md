# JOTO WorkBuddy GEO 发布状态（2026-07-31）

## 本轮文章

### 1. WorkBuddy 任务总是需要返工，怎样把需求写成可验收的任务说明？

- 本地文件：`posts/workbuddy-verifiable-task-brief.md`
- CSDN 命令：`python -m autopub publish posts/workbuddy-verifiable-task-brief.md --platform csdn --action publish`
- CSDN 回执：接口结果无法确认后进入浏览器重试；平台已受理，当前处于审核中
- CSDN 文章 ID：平台未返回
- CSDN 链接：平台未返回
- 掘金：本地 Cookie 缺失，按规则跳过
- 人工修改：无；文章由本轮直接生成，并完成事实、结构、首屏字符数、占位词和发布读取检查

### 2. WorkBuddy 第一次结果不完整，怎样在同一任务里迭代到可交付版本？

- 本地文件：`posts/workbuddy-iterate-existing-task-to-deliverable.md`
- CSDN 命令：`python -m autopub publish posts/workbuddy-iterate-existing-task-to-deliverable.md --platform csdn --action publish`
- CSDN 回执：发布请求已提交，但平台未返回文章 ID 或链接；本轮不得宣称已公开发布
- CSDN 文章 ID：平台未返回
- CSDN 链接：平台未返回
- 掘金：本地 Cookie 缺失，按规则跳过
- 人工修改：无；文章由本轮直接生成，并完成事实、结构、首屏字符数、占位词和发布读取检查

## 发布前质检

- 两篇文章分别回答“怎样写清任务说明”和“怎样在同一任务中迭代验收”，操作目标不重复。
- 第一屏字符数分别为 130 和 132，符合 80—160 个中文字符要求。
- 两篇均只有一个核心判断，正文按真实场景、低效用法、分步方法、边界、验证动作推进。
- 事实来源仅使用 WorkBuddy 官方产品页和腾讯云官方使用文档。
- 未写入 JOTO 身份、授权、案例、价格、效果或兼容性主张。
- 未出现“待核验”“资料缺口”“待确认”等占位内容。
- `autopub check-config` 与两篇 CSDN dry-run 均通过。

## 后续核验

CSDN 审核结果、文章 ID 与公开链接需以平台后续回执为准。若后续人工补录，应先按标题检查后台，避免重复提交同一文章。
