# 界面设计稿 / UI design reference

从登录门户到每一个功能组件，按 Claude Design System 的记号体系重绘的 100 屏。
GitHub 不渲染 HTML，请在本地打开 [`index.html`](index.html)。

100 screens, from the login portal to every functional component, redrawn on the
Claude Design System token vocabulary. GitHub does not render HTML — open
[`index.html`](index.html) locally.

```bash
open docs/design/index.html
```

## 这是什么，不是什么 / What this is and is not

**是**：设计稿。屏幕清单来自 `plugins/src/client/` 的实际组件，文案来自
`plugins/src/client/ui.ts` 的中英词条，状态词、依据等级、数字格式来自
[`docs/requirements/00-foundations.md`](../requirements/00-foundations.md) 第 5 节。

**不是**：实现。它不参与构建、不引入依赖，也不是第二个前端——前端仍然复用 dsh web
深度定制（Client 插件注册进插槽），不自建。修改这里不改变产品行为。

**Is** a design reference: the screen inventory comes from the real components under
`plugins/src/client/`, the copy from the zh/en pairs in `ui.ts`, and the status
vocabulary, evidence grades and number formats from §5 of the requirements foundations.

**Is not** an implementation: it is not built, ships no dependency, and is not a second
front end — the product still deeply customises dsh web through Client plugin slots.
Editing these files changes no product behaviour.

## 页面 / Pages

| 文件 / File | 内容 / Contents | 屏 / Screens |
| --- | --- | ---: |
| `index.html` | 总览与六条贯穿规则 / overview and the six rules | — |
| `00-foundations.html` | 记号、按钮、表单、状态词、依据等级、数字与图表规则 | 12 |
| `01-portal.html` | 飞书登录、应用入口、令牌过期、可见范围、失败关闭 | 10 |
| `02-shell.html` | 三栏笔记本、空白会话、笔记本列表、导览、窄屏 | 8 |
| `03-intake.html` | 导入、自检、飞书文件夹、单部门补传、模板预填 | 7 |
| `04-batch.html` | 主表、出处、清洗、隔离、总表核对、拒绝、导出 | 8 |
| `05-dictionary.html` | 字典、列画像、匹配、关系与别名、口径确认与版本 | 8 |
| `06-review.html` | 派活、四部门报告、证据、部分完成、校验拒绝、用量 | 8 |
| `07-conclusions.html` | 本月结论、跨期对比、指标图、依据链、报告导出 | 6 |
| `08-approvals.html` | 决定卡、工具变体、拒绝、员工许可、审计、护栏 | 7 |
| `09-workflow.html` | 模板、草稿、补问、看板、上下游、月度进度、收件箱 | 9 |
| `10-discovery.html` | 材料、候选、流转图、四象限、会议、决策 | 6 |
| `11-quotation.html` | 输入清单、抽取、草稿、方案比较、放行门 | 5 |
| `12-states.html` | 空态、加载、网络与服务失败、拒绝、图片、可访问性 | 6 |

共享样式与脚本在 `assets/`。右上角的中英与深浅开关是真的：语言切换会换掉每一条文案，
主题切换只换记号值，用来当场验证 NFR09（双语、深浅主题、760 px 窄屏、全键盘操作）。

Shared styles and script live in `assets/`. The zh/en and light/dark switches at the top
right are real — the language switch replaces every label and the theme switch swaps
token values only — so NFR09 can be checked rather than taken on trust.

## 每屏的实现状态 / Implementation status per screen

每屏标注底下实现的真实状态，取自各 epic 的 UC 索引：`IMPLEMENTED`、`PARTIAL`、
`DESIGNED`，以及 `NO CODE`（本设计稿提出、仓库尚无对应实现）。设计稿不改变这些状态。

Each screen carries the real status of the code beneath it, taken from the UC index in
each epic: `IMPLEMENTED`, `PARTIAL`, `DESIGNED`, and `NO CODE` for anything this
reference proposes that the repository does not yet have. The reference changes none of them.
