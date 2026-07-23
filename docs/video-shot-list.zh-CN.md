# De-starter 视频镜头清单

本清单只记录可公开的合成画面。私有审计截图、源码摘录、项目身份、绝对路径、批准令牌和真实凭据均不进入 Git。

| 镜头 ID | 来源 | 隐私级别 | 画面重点 | 旁白建议 | 文件名 |
| --- | --- | --- | --- | --- | --- |
| `audit-overview` | `docs/assets/video/sources/01-audit-overview.html` | 公开安全；仅含通用标签与汇总计数 | 350 个文件完成清点；523 条发现按 P0–P3 分类；新增、删除、变化均为 0；第一道审批门仍在等待明确确认 | “先做只读清点，再讨论要改什么。审计把受保护内容、高风险标识、用户选择项和展示残留分开；在第一道审批门通过前，源项目保持逐字节不变。” | `docs/assets/video/01-audit-overview.png` |
| `safety-gates` | `docs/assets/video/sources/02-safety-gates.html` | 公开安全；只展示脱敏后的流程与验证汇总，不展示令牌、路径和源码 | 第一道门确认允许修改的范围；第二道门绑定精确 Diff、验证结果和一次性令牌；预览已通过验证，但仍停在真正写入之前 | “第一道门确认修改范围；第二道门看精确 Diff 与令牌。即使预览已经通过 lint、没有新增测试失败并且能够构建，也必须再次得到明确批准，才会真正写入项目。” | `docs/assets/video/02-safety-gates.png` |
| `before-after` | `docs/assets/video/sources/03-before-after.html` | 公开安全；来自真实验收的聚合计数，不含项目身份、路径、源码、素材、令牌或凭据 | 总发现从 523 降至 227；P0 保持 132；P1/P2/P3 分别降至 35/21/39；底部展示精确应用、验证和回滚证据 | “真实效果不是把 Starter 这个单词清零，而是把 523 条发现逐类处理到 227 条可解释保留项。法律和敏感证据一条没动，兼容性标识只迁移批准范围，真正有用的 Demo 继续工作，卖家身份则被中性化。” | `docs/assets/video/03-before-after.png` |
| `empty-dir-red-green` | `docs/assets/video/sources/04-empty-dir-red-green.html` | 公开安全；仅含合成路径、测试汇总和审查级别，不含源码、私有路径或令牌 | 从目录能力缺失的 RED，到 126 项测试通过但审查未放行，再到 130 项测试与独立复审共同通过 | “这张图很能说明为什么它不是一段批量替换脚本：先用失败测试证明空目录对旧扫描器不可见；即使 126 项测试全绿，独立审查仍发现竞态和权限边界；补上确定性测试并加固后，130 项测试通过，复审也归零。” | `docs/assets/video/04-empty-dir-red-green.png` |
| `empty-dir-gate-two` | `docs/assets/video/sources/05-empty-dir-gate-two.html` | 公开安全；来自真实验收的聚合结果，但不含真实 token、私有路径、源码或购买项目身份 | 0 个文件变化、0 个普通删除、0 个重命名、1 个精确空目录清理；父级保留；预览已完成但仍等待 Gate 2 精确批准 | “这次真实验收只剩一个空目录：文件不改、文件不删、路径不改名，只清理这一个获批目录。操作很小，但 Skill 仍然停在第二道门；截图隐藏 token，真实值只在私有审批里展示。” | `docs/assets/video/05-empty-dir-gate-two.png` |
| `empty-dir-final` | `docs/assets/video/sources/06-empty-dir-final.html` | 公开安全；只含真实验收聚合数字与通用恢复证据 | 文件发现 523 → 227，目录残留 1 → 0；P0–P3 保留分布；外部备份、恢复材料、lint/build 与零新增测试失败 | “最终结果要看两套数字：文件发现从 523 到 227，剩余全部有保留理由；目录残留从 1 到 0。它没有靠删除目录美化文件数字，原目录还在外部备份，恢复材料齐全。” | `docs/assets/video/06-empty-dir-final.png` |
| `github-ci-green` | `docs/assets/video/sources/07-github-ci-green.html` | 公开安全；基于公开 GitHub CI 数据重绘，不是原始网页截图 | macOS 本地 195/195 → Linux 首次 1 failure → v0.1.1 标签 CI Python 3.9/3.11/3.13 全绿；Annotations 为空 | “真正发布后，Linux CI 揪出了一个 macOS 没暴露的 inode 复用测试假设。我没有重跑碰运气，而是读日志、修正跨平台断言，再发布不可变的 v0.1.1 补丁版；main 和标签 CI 都是三档全绿。” | `docs/assets/video/07-github-ci-green.png` |
| `public-demo-safety` | `docs/assets/video/sources/08-public-demo-safety.html` | 公开安全；只含公开合成演示聚合结果，令牌标为 `REDACTED`，无购买源码与本机路径 | 错误令牌和过期预览都被拒绝且无部分修改；当前精确批准只处理 P2/P3；P0/P1、普通空目录和恢复证据分别核对 | “这不是购买项目，而是任何人都能复现的公开合成演示。错误令牌不写，过期预览不写，只有人工检查过的当前范围才写。低风险不等于零风险；v0.1.2 有事务回滚和恢复证据，但没有一键恢复命令。” | `docs/assets/video/08-public-demo-safety.png` |

## 剪辑说明

- 画布：1600 × 900，16:9。
- 建议停留：6–8 秒；先强调左侧总量，再依次扫过右侧零差异证据和四级风险卡。
- `safety-gates` 建议停留 7–10 秒；从第一道门平移到第二道门，最后落在底部“尚未执行”状态。
- `before-after` 建议停留 9–12 秒；先展示 523 → 227，再从 P0 横向扫到 P3，最后落在底部“精确应用 / 无新增回归 / 可回滚”三项证据。
- `before-after` 推荐裁剪：完整保留顶部总量、四张风险卡和底部三项证据；不要单独截取“227”，避免被误解成未清理干净。
- `empty-dir-red-green` 建议停留 10–14 秒；按 RED → REVIEW → GREEN 从左向右推进，最后落在底部“独立复审通过”。
- `empty-dir-gate-two` 建议停留 8–12 秒；先扫过 0 / 0 / 0 / 1，再落到右侧 Gate 2 锁定区，完整保留底部“no project mutation before approval”。
- `empty-dir-final` 建议停留 10–14 秒；先看 523 → 227，再看 1 → 0，最后扫过右侧外部备份、恢复材料和验证结果。
- `github-ci-green` 建议停留 10–14 秒；从左到右依次展示“本地全绿 / Linux 暴露假设 / v0.1.1 三档全绿”，底部必须保留“基于已验证数据重绘”说明。
- `public-demo-safety` 建议停留 12–16 秒；先看两张拒绝卡，再看获批范围和底部保护项。必须保留 `REDACTED`、低风险不等于零风险、没有一键恢复命令三条边界。
- 隐私复核：画面与 HTML 不包含私有产品名、公司名、域名、邮箱、仓库、绝对路径、源码片段、素材拷贝、真实感 ID 或批准令牌。
