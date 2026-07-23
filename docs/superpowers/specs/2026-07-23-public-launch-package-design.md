# De-starter GitHub 门面、最终实验报告与中文视频导演包设计

日期：2026-07-23

## 1. 目标

本轮工作把已经发布的 `de-starter v0.1.2` 整理成一个第一次进入 GitHub 仓库的人能够理解、能够安全反馈，也适合中文自媒体完整介绍的公开发布包。

交付范围只有三组：

1. GitHub 仓库门面：Topics、简介、Social Preview、README 导航、Issue 模板和反馈入口；
2. 最终公开实验报告：真实 Starter 前后结果、P0–P3、两道审批门、拒绝案例、事务恢复与隐私边界；
3. 中文视频导演包：逐字口播、分镜、屏幕重点、现有图片中文化和缺失证据图。

普通用户安装验收不在本轮范围内。已经完成的干净克隆、公开合成演示、214 项回归和 GitHub 多版本 CI 继续作为发布证据，不重复执行一轮面向新手的安装实验。

## 2. 受众与表达原则

### 2.1 GitHub 受众

仓库主 README 和仓库简介继续使用简洁英文，方便全球 Agent Skill 和开发工具用户检索。中文真实实验报告、自媒体包和导演稿通过 README 的 Public evidence 区域直接进入。

### 2.2 视频受众

视频面向中文初学者。所有画面中的标题、解释、状态、结论、提示和注释使用中文。

以下技术标识可以保留原文，但必须在第一次出现时用中文解释：

- `de-starter`；
- `P0`–`P3`；
- token；
- Preview、Apply、Verify；
- `restore.json`、`reverse.diff`、`apply-result.json` 等文件名；
- GitHub、Python、CI、README 等行业通用名称；
- 命令、路径和代码标识。

不得出现需要创作者朗读整段英文的画面。英文技术词只作为短标签或代码存在，旁边提供中文解释。

### 2.3 叙事方式

采用“故事 + 证据链”而不是功能说明书或全程命令录屏：

```text
一句话需求
  → 为什么全局搜索替换危险
  → P0–P3 如何分流
  → 两道审批门如何阻止盲写
  → 错误令牌与过期预览如何拒绝
  → 外部备份与回滚怎样保护原始对象
  → 真实 Starter 和 214 项测试证明了什么
  → Skill 相比一次性提示词多提供了什么
  → 风险边界与 GitHub 获取方式
```

视频目标时长为 14–16 分钟。出镜不是必需条件；稿件按“中文旁白 + 屏幕证据”即可独立成立。

## 3. GitHub 仓库门面

### 3.1 仓库简介

使用下列英文简介，避免绝对安全承诺：

> Safety-first Agent Skill for auditing and removing starter, boilerplate, template, and SaaS-kit residue with approval gates, external previews, backups, and rollback evidence.

### 3.2 Topics

设置为：

- `agent-skills`
- `code-audit`
- `starter-template`
- `boilerplate`
- `saas-starter`
- `template-cleanup`
- `safe-refactoring`
- `rollback`
- `python`
- `developer-tools`

Topics 不使用未经验证的具体 Agent 客户端名称，也不使用“best”“zero-risk”“one-click”等夸大词。

### 3.3 Social Preview

新增 `docs/assets/github/social-preview.zh-CN.png`，尺寸遵循 GitHub 当前官方建议，上传到仓库 Social Preview 设置。

画面全中文，保留产品名 `de-starter`，只表达三件事：

- 安全去除 Starter 痕迹；
- P0–P3 分级；
- 两道审批、项目外预览、可恢复证据。

Social Preview 不包含真实 Starter 数字、购买项目身份、源码、终端输出、审批 token 或本机路径，避免社交平台裁剪后产生隐私和误导。

### 3.4 README 首页结构

README 保留安装和使用命令，但顶部重排为：

1. 一句话说明它是 Agent Skill，不是独立 Agent；
2. 非零风险提示；
3. Quick links：安装、公开演示、真实实验报告、视频材料、反馈；
4. 核心工作流；
5. P0–P3 表格；
6. 证据与当前版本状态；
7. 安装、使用、限制、贡献和 License。

不得把 v0.1.2 描述成修改了生产清理引擎。准确说法是：v0.1.2 增加公开合成演示、拒绝证据、文档、图片和测试，生产 Skill 行为相对 v0.1.1 未改变。

### 3.5 Issue 与反馈入口

保留现有：

- Bug report；
- Classification / false-positive report；
- private vulnerability reporting。

新增一个双语 `Feedback / 使用反馈` Issue Form，收集：

- 项目类型；
- 使用阶段；
- 哪一步难以理解；
- 期望改进；
- 是否愿意提供完全合成的最小示例；
- 强制隐私确认。

继续关闭 blank issue。暂不启用 GitHub Discussions，避免在没有维护流程时制造第二个重复反馈渠道。README、Issue config 和 CONTRIBUTING 均指向同一个公开反馈表；敏感内容继续进入 private vulnerability reporting。

## 4. 最终公开实验报告

更新 `docs/real-starter-experiment-report.zh-CN.md`，保留当前聚合数据，同时形成更清晰的公开证据结构。

### 4.1 首页结论卡

开头直接展示：

- 文件发现：523 → 227，减少 296，降幅 56.6%；
- 目录残留：1 → 0；
- P0：132 → 132；
- P1：52 → 35；
- P2：52 → 21；
- P3：287 → 39；
- 真实项目新增测试失败：0；
- Skill v0.1.2：214 / 214；
- GitHub CI：Python 3.9 / 3.11 / 3.13 通过。

### 4.2 两类证据必须分开

报告设置明确的证据来源列：

| 证据来源 | 能证明什么 | 不能声称什么 |
| --- | --- | --- |
| 真实购买 Starter 验收 | P0–P3 处理、审批范围、523→227、目录1→0、构建、测试与恢复材料 | 不公开源码、路径、token；不声称故意制造破坏 |
| 公开合成实验 | 错误令牌拒绝、过期 Preview 拒绝、无部分写入、精确获批 Apply | 不冒充真实购买项目的破坏性实验 |
| Skill 回归与 GitHub CI | 214 项回归、Python 三版本、Linux/macOS 差异 | 不等同于所有 Starter 和所有文件系统零风险 |

### 4.3 审批与事务证据

报告解释：

- 第一道审批批准允许操作的类别和精确范围；
- 第二道审批批准当前项目状态对应的 Preview 和 64 位 token；
- 错误 token、Preview 后状态变化、artifact 变化都会拒绝；
- 原始对象进入项目外 backup，不使用直接丢弃作为安全承诺；
- 恢复材料齐全，但 v0.1.2 没有一键恢复命令；
- 自动事务失败会尝试回滚，无法安全覆盖外来对象时保留 backup 并报告 incomplete rollback。

### 4.4 隐私边界

公开报告继续禁止：

- 购买项目身份和卖家身份；
- 私有绝对路径；
- 源码摘录和完整 diff；
- 审批 token；
- backup 路径映射；
- 凭据、真实域名、真实邮箱和 proprietary assets。

报告只使用聚合数字、中性操作名称、合成示例和公开 GitHub CI 链接。

## 5. 中文视频导演包

新增 `docs/video-director-script.zh-CN.md`。每个镜头使用固定字段：

- 时间码；
- 屏幕画面；
- 鼠标/高亮重点；
- 逐字口播；
- 这份证据证明什么；
- 观众应记住什么；
- 不能说什么；
- 转场方式。

### 5.1 七段核心证据

1. 搜索替换不安全：同一个来源词在 LICENSE、支付 key、Demo 和展示文案中需要四种不同处理；
2. P0–P3：保护、迁移、用户选择、中性化；
3. 两道审批门：先批准允许范围，再批准当前精确 Preview；
4. 两次拒绝：错误 token 和过期 Preview 均在写入前停止；
5. 事务保护：外部 Preview、backup、Apply、Verify、自动回滚与恢复证据；
6. 真实效果：523→227、目录1→0、P0 不变、新增测试失败0、构建通过；
7. Prompt vs Skill：一句提示词可以开始任务，Skill 固化完整安全流程并跨项目复用。

### 5.2 图片清单

所有视频图为 1600×900 PNG，并保留可编辑 HTML source。

现有图片全部复核并中文化：

1. `01-audit-overview.png`：将英文标题、卡片和状态改为中文；
2. `02-safety-gates.png`：将 Gate、scope、preview、hash 等叙事文字改成中文解释；
3. `03-before-after.png`：将 PROTECTED、COMPATIBILITY、USER DECIDES、PRESENTATION 等改成中文；
4. `04-empty-dir-red-green.png`：将 RED、REVIEW、GREEN、ImportError 等画面说明改成中文；代码错误名可保留并配中文；
5. `05-empty-dir-gate-two.png`：将 Gate 2、approval token 等解释改为中文；token 值继续遮罩；
6. `06-empty-dir-final.png`：将 FILE FINDINGS、DIRECTORY RESIDUE、PASS 等解释改成中文；
7. `07-github-ci-green.png`：更新为 214/214、v0.1.2 和当前 Python 3.9/3.11/3.13 证据；删除已过时的 v0.1.1 主结论；
8. `08-public-demo-safety.png`：将 REJECTED、SCOPED APPLY、Inventory 等叙事文字改成中文；token 继续遮罩；
9. 新增 `09-prompt-vs-skill.png`：一次性提示词与可复用 Skill 的证据链对比；
10. 新增 `10-transaction-recovery.png`：真实项目 → 项目外 Preview → backup → 获批 Apply → Verify / rollback。

图片不得用英文大标题作为主要视觉。`P0`–`P3`、token、Preview、Apply、Verify 等保留词旁必须有中文解释。

### 5.3 准确性红线

- 不说“零风险”“绝不会破坏项目”“一键恢复”；
- 不说“剩余 227 条是没清干净”；
- 不把合成拒绝实验说成真实购买 Starter 的故意破坏实验；
- 不把 214 项 Skill 测试和真实项目 63/65 测试混为一组；
- 不把 v0.1.2 说成生产引擎升级；
- 不把公开证据重绘图称为 GitHub 原始截图；
- 不宣称全网第一、唯一或市场最强。

## 6. 数据流与来源

公开数字只从已经验证并已提交的脱敏证据中取值：

```text
真实私有验收 artifacts
  → 只提取聚合数字
  → sanitized real-run summary
  → 中文最终实验报告
  → 中文图片 source
  → PNG 与导演稿
```

公开合成拒绝案例只从 `examples/public-demo` 和 `tests/test_public_demo.py` 取值。GitHub CI 数字只从公开 Actions run 取值。任何来源冲突都以最新可复验证据为准，不能为了视频叙事选择更好看的旧数字。

## 7. 验收标准

### 7.1 内容

- README 首屏能在 60 秒内回答“是什么、如何使用、为什么安全但非零风险、哪里反馈”；
- 最终实验报告包含真实/合成/CI 三类证据边界；
- 导演稿覆盖用户要求的七个重点，并为每段提供屏幕与口播指令；
- 所有公开数字与 v0.1.2 当前证据一致；
- 不含占位符、TODO 或含糊的“以后补充”。

### 7.2 图片

- 10 张视频 PNG 均为 1600×900；
- Social Preview 使用 GitHub 官方建议尺寸；
- 所有叙事文字为中文；
- token、私有路径、购买身份、源码和 proprietary assets 不出现；
- 图片逐张人工视觉检查，无裁切、溢出、乱码和过小文字。

### 7.3 仓库与 GitHub

- Topics、简介和 Social Preview 与本规格一致；
- Issue Forms 可解析，反馈入口和 private security 入口均可达；
- README、报告、导演稿、镜头表和图片互相链接；
- 仓库 Latest Release 仍为 v0.1.2；本轮门面工作使用后续文档版本提交，不移动既有标签。

### 7.4 验证

- `quick_validate.py` 通过；
- 214 项全量回归通过，若新增文档/媒体测试则总数相应增加并全部通过；
- Python compile、JSON、YAML、Markdown 本地链接、PNG 尺寸和 `git diff --check` 通过；
- tracked-tree 隐私扫描对机器路径、私钥头、GitHub/OpenAI token 形态、真实审批 token 和已知购买项目身份零命中；
- 从 GitHub 公共页面复核 Topics、简介、Social Preview、Issue 入口和反馈链接。

## 8. 非目标

- 不重新进行普通用户安装验收；
- 不再次修改真实购买 Starter；
- 不公开私有完整审计、diff 或 backup；
- 不修改 `de-starter` 生产 Apply 行为；
- 不新增 Windows 支持或一键恢复命令；
- 不启用 GitHub Discussions；
- 不移动 v0.1.0、v0.1.1 或 v0.1.2 标签。
