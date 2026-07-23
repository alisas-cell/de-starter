# De-starter 视频镜头清单

本清单只记录可公开的合成画面。私有审计截图、源码摘录、项目身份、绝对路径、批准令牌和真实凭据均不进入 Git。

[完整逐字口播、鼠标重点和禁用表述](video-director-script.zh-CN.md)

| 镜头 ID | 来源 | 隐私级别 | 画面重点 | 建议停留 | 旁白建议 | 文件名 |
| --- | --- | --- | --- | --- | --- | --- |
| `audit-overview` | `docs/assets/video/sources/01-audit-overview.html` | 公开安全；通用标签与汇总计数 | 只读清点；523 条按 P0–P3 分类；源项目变化为 0 | 12–16 秒 | “关键词命中只是线索，不是删除授权。” | `docs/assets/video/01-audit-overview.png` |
| `safety-gates` | `docs/assets/video/sources/02-safety-gates.html` | 公开安全；不展示令牌、路径和源码 | 第一道门批准范围；第二道门绑定当前精确预览；应用前停止 | 12–16 秒 | “第一道门决定能做什么，第二道门决定这一版会改什么。” | `docs/assets/video/02-safety-gates.png` |
| `before-after` | `docs/assets/video/sources/03-before-after.html` | 真实验收聚合数据；无身份、路径、源码、素材或 token | 523 → 227；P0 132 不变；P1/P2/P3 分类保留 | 12–18 秒 | “不是清零，而是让留下和修改都有理由。” | `docs/assets/video/03-before-after.png` |
| `empty-dir-red-green` | `docs/assets/video/sources/04-empty-dir-red-green.html` | 合成测试与审查汇总 | 能力缺失 → 测试复核 → 安全加固 → 独立复审通过 | 10–14 秒 | “测试全绿是复审输入，不是自动放行。” | `docs/assets/video/04-empty-dir-red-green.png` |
| `empty-dir-gate-two` | `docs/assets/video/sources/05-empty-dir-gate-two.html` | 真实验收聚合；token 遮罩 | 0 文件变化、0 删除、0 重命名、1 个精确目录；仍停在第二道门 | 10–14 秒 | “操作再小，也不能绕过第二道门。” | `docs/assets/video/05-empty-dir-gate-two.png` |
| `empty-dir-final` | `docs/assets/video/sources/06-empty-dir-final.html` | 真实验收聚合与通用恢复证据 | 文件 523 → 227；目录 1 → 0；恢复材料和新增失败 0 | 12–18 秒 | “文件发现和目录残留是两套指标。” | `docs/assets/video/06-empty-dir-final.png` |
| `github-ci-green` | `docs/assets/video/sources/07-github-ci-green.html` | 公开 GitHub 数据重绘，不是网页原始截图 | 本地 214/214；Linux 暴露测试假设；v0.1.2 Python 三档全绿 | 12–18 秒 | “本地全绿是发布前提，公开 CI 是另一种环境测试。” | `docs/assets/video/07-github-ci-green.png` |
| `public-demo-safety` | `docs/assets/video/sources/08-public-demo-safety.html` | 公开合成演示；令牌遮罩 | 错误令牌拒绝、过期预览拒绝、当前精确批准限定执行 | 14–20 秒 | “错误令牌不写，旧预览不写，当前精确批准才写。” | `docs/assets/video/08-public-demo-safety.png` |
| `prompt-vs-skill` | `docs/assets/video/sources/09-prompt-vs-skill.html` | 公开概念比较；无私有证据 | 一次性提示词依赖当前对话；Skill 固化分级、审批、备份、拒绝和验证 | 14–20 秒 | “提示词是起点，Skill 是可复用的执行边界。” | `docs/assets/video/09-prompt-vs-skill.png` |
| `transaction-recovery` | `docs/assets/video/sources/10-transaction-recovery.html` | 公开事务流程；无真实路径与 backup 映射 | 只读 → 两道门 → backup → Apply/Verify → 成功证据或失败回滚 | 16–22 秒 | “像先搬进保险柜，不是直接扔进垃圾桶。” | `docs/assets/video/10-transaction-recovery.png` |
| `social-preview` | `docs/assets/github/social-preview.zh-CN.html` | 公开品牌图；无真实实验明细 | 产品名、中文用途、四项安全能力、非零风险边界 | 6–10 秒 | “它不是一键全删，而是让每次修改都有边界。” | `docs/assets/github/social-preview.zh-CN.png` |

## 剪辑说明

- 画布：1600 × 900，16:9。
- 建议停留：6–8 秒；先强调左侧总量，再依次扫过右侧零差异证据和四级风险卡。
- `safety-gates` 建议停留 7–10 秒；从第一道门平移到第二道门，最后落在底部“尚未执行”状态。
- `before-after` 建议停留 9–12 秒；先展示 523 → 227，再从 P0 横向扫到 P3，最后落在底部“精确应用 / 无新增回归 / 可回滚”三项证据。
- `before-after` 推荐裁剪：完整保留顶部总量、四张风险卡和底部三项证据；不要单独截取“227”，避免被误解成未清理干净。
- `empty-dir-red-green` 建议停留 10–14 秒；按 RED → REVIEW → GREEN 从左向右推进，最后落在底部“独立复审通过”。
- `empty-dir-gate-two` 建议停留 8–12 秒；先扫过 0 / 0 / 0 / 1，再落到右侧 Gate 2 锁定区，完整保留底部“no project mutation before approval”。
- `empty-dir-final` 建议停留 10–14 秒；先看 523 → 227，再看 1 → 0，最后扫过右侧外部备份、恢复材料和验证结果。
- `github-ci-green` 建议停留 12–18 秒；从左到右依次展示“本地 214/214 / Linux 暴露假设 / v0.1.2 三档全绿”，底部必须保留“基于公开 GitHub 数据重绘”说明。
- `public-demo-safety` 建议停留 12–16 秒；先看两张拒绝卡，再看获批范围和底部保护项。必须保留 `REDACTED`、低风险不等于零风险、没有一键恢复命令三条边界。
- `prompt-vs-skill` 从左向右逐项对应，不要把普通提示词描述成必然不安全。
- `transaction-recovery` 沿箭头移动，在 backup 节点停留，再分别进入成功与失败分支。
- `social-preview` 只用于开头、结尾和仓库分享，不承担真实实验数字证明。
- 隐私复核：画面与 HTML 不包含私有产品名、公司名、域名、邮箱、仓库、绝对路径、源码片段、素材拷贝、真实感 ID 或批准令牌。
