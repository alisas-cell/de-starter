# De-starter 自媒体发布完整包

## 内容定位

这期内容的重点不是教观众从零编写 Skill，而是回答五个问题：

1. `de-starter` 是什么；
2. 为什么买来的 Starter 需要这种 Skill；
3. 它具体能做什么；
4. 为什么它比一句临时提示词更稳定；
5. 真实项目上的效果、限制和 GitHub 获取方式。

推荐人物视角：

> 我也是第一次做可以公开分享的 Agent Skill。我一开始只对 AI 说了一句“帮我去掉这个 Starter 的痕迹”，后来才发现，真正难的不是搜索替换，而是判断哪些能删、哪些不能动，以及怎么证明改错了还能恢复。

## 一句话介绍

`de-starter` 是给现有编码 Agent 使用的通用 Agent Skill：它会审计 Starter 身份残留，把风险分级，先生成项目外预览并等待两次明确批准，再事务化执行和复核。

它不是独立 Agent。Agent 是实际执行任务的人，Skill 更像一份可加载的专业 SOP，加上可重复运行的扫描、Preview、Apply 和 Verify 工具。

## 推荐标题

### 长视频标题

1. 我把“去 Starter 痕迹”做成了一个可回滚的 Agent Skill
2. 买了 SaaS Starter 之后，别急着全局替换：我做了个安全清理 Skill
3. 523 条 Starter 痕迹怎么处理？我的真实项目实验结果
4. 一句话也能让 AI 清理 Starter，为什么我还做了一个 Skill？
5. 从 523 到 227：不是没删干净，而是我拒绝让 AI 乱删
6. 我第一次开源 Agent Skill：两道审批门、事务备份、真实验收
7. 删除一个空目录，为什么还要审批 token？
8. AI 改代码最怕误删，我给“去 Starter”加了保险柜

### 短视频标题

1. AI 去 Starter 痕迹，最危险的不是漏删
2. 为什么我不让 AI 直接全局替换 Starter
3. 523 → 227，剩下的为什么不能删？
4. 一个空目录，也值得两次审批吗？
5. Skill 和一句提示词，到底差在哪里？

### 封面文字

- 主标题：`Starter 痕迹，不能一键乱删`
- 副标题：`523 → 227｜目录 1 → 0｜可审批｜可回滚`
- 角标：`真实项目验收`

## 推荐视频结构（12–15 分钟）

### 00:00–00:35 开场钩子

口播：

> 我刚买了一个 AI SaaS Starter，第一句话只是让 AI 帮我去掉 Starter 痕迹。AI 当然可以直接搜关键词，但这里面有 LICENSE、支付计划 key、数据库字段、Demo、评价、卖家链接，还有一个空目录。删少了会留下卖家身份，删多了可能把计费和认证一起搞坏。所以我最后没有做一个“批量替换脚本”，而是做了一个带两道审批门、项目外预览和事务回滚的 Agent Skill。

屏幕：先快速闪过 `audit-overview`，再落到 `before-after`。

### 00:35–01:40 普通用户为什么会需要

口播：

> 普通用户最大的问题不是不会输入“帮我清理”，我当时也只输入了这一句。问题是后面的判断很长：版权能不能删？支付 ID 能不能改？Demo 是卖家垃圾还是产品能力？没有自己的品牌名怎么办？AI 改完以后怎么确认没有偷偷扩大范围？下一次换一个项目，难道还要重新提醒一遍吗？
>
> Skill 的意义，就是把这些后续问题变成固定流程。用户仍然可以只说一句话，但 Agent 每次都会得到同一套安全边界，而不是依赖这次对话里有没有刚好想到。

屏幕：`safety-gates`。

### 01:40–02:40 Skill、Agent 和普通提示词

口播：

> Agent 是执行者，它能读代码、运行命令、改文件。Skill 不是另一个机器人，它是一套执行者按需加载的专业方法和工具。普通提示词是一次性说明；Skill 可以放进 GitHub，安装给不同 Agent 和不同用户重复使用。官方 Agent Skills 规范本身也支持把 `SKILL.md`、references 和 scripts 放在一个自包含目录里，按需加载。

屏幕：简单三栏字幕：`Prompt = 一次说明`、`Skill = 可复用 SOP + 工具`、`Agent = 实际执行者`。

资料链接：

- [Agent Skills：为 Agent 增加 Skills 支持](https://agentskills.io/client-implementation/adding-skills-support)
- [Anthropic 公共 Skills 仓库](https://github.com/anthropics/skills)

### 02:40–04:40 具体功能

口播：

> 第一，它不只搜单词，而是先识别 Starter 的来源身份，包括名称、域名、仓库、作者和目录名。
>
> 第二，它把发现分成 P0 到 P3。P0 是 LICENSE、版权、疑似密钥和生产数据，默认只报告不修改；P1 是支付、认证、数据库、API 和持久化标识，没有迁移和回滚计划就保留；P2 是 Demo、样例、评价、测试数据和资产，必须让用户选；P3 才是适合中性化的展示文案、SEO、邮件签名和仓库链接。
>
> 第三，缺少真实品牌资料时，它不会替用户编公司名。用户可以暂停补充，也可以选择固定的中性占位符，后面再统一替换。
>
> 第四，它支持受保护的行级语义编辑。不是看到 Starter 就整行替换，而是绑定文件哈希、开始行、结束行和修改目的；如果范围碰到 P1，还必须带迁移和回滚计划。
>
> 第五，它把文件发现和 source-named 目录残留分开。空目录不会出现在普通文件扫描里，但也不能用全局清空目录或随手 `rmdir` 处理。

屏幕：`audit-overview` → `empty-dir-red-green`。

### 04:40–06:25 两道审批门

口播：

> 第一道门批准的是“允许做什么”：哪些 Demo 删除、哪些路径重命名、哪些语义编辑、哪些高风险迁移、哪一个空目录允许清理。
>
> 第二道门批准的是“这一次具体会发生什么”。Skill 在项目外生成 Preview、完整 diff、二进制操作清单、占位符清单和语义编辑摘要，再用当前源码、Preview、目录身份和这些 artifact 的哈希生成一次 token。哪怕只多批准一个空目录，也必须重新生成 Preview 和 token。
>
> 所以用户说“你帮我决定”“赶紧删掉”或者“全部替换”，都不能被当成第二道门批准。

屏幕：`safety-gates` → `empty-dir-gate-two`。

### 06:25–07:35 为什么删除目录会这么复杂

口播：

> 因为我们承诺的不是“正常情况下删得掉”，而是“异常发生在任何一步都不会覆盖别人刚写进去的内容”。
>
> 真正执行时，目录不是直接 `rmdir`，而是原子移动到项目外备份。原子动作一成功，系统先记录 committed，再做可能失败的验证。回滚时先恢复父目录，再恢复子项；如果目标位置被外来文件占用，系统宁愿保留备份并报告恢复不完整，也不会覆盖外来数据。
>
> 这就是为什么一个空目录最终牵涉 token、device/inode、no-clobber、事务账本和恢复清单。复杂的是安全承诺，不是“删除”这个动作。

屏幕：`empty-dir-red-green`，可加字幕“搬进保险柜，不是扔进垃圾桶”。

### 07:35–09:25 真实实验结果

口播：

> 真实 Starter 的文件发现从 523 降到 227，减少了 296 条。P0 仍然是 132，一条没动；P1 从 52 降到 35；P2 从 52 降到 21；P3 从 287 降到 39。
>
> 这 227 条不是“Skill 没清干净”，而是已经解释过的保留项。比如法律证据、兼容性 key、用户选择保留的 Demo，以及明确要求保留的通用业务词。
>
> 目录是另一套指标：`Directory residue: 1 → 0`。最后一次 Apply 没有改文件、没有普通删除、没有重命名，只事务化移动了一个获批空目录，并保留了普通父目录。
>
> 项目 lint 通过；65 条测试中 63 条通过，剩下两条是清理前后相同的 docs 链接断言，新增失败为 0；Webpack production build 成功，生成 71 个静态页面。

屏幕：`before-after` → `empty-dir-final`。

### 09:25–10:25 测试不是跑一次最好看的

口播：

> 我还专门测试了 Skill 本身。旧版本面对空目录压力场景，五次 fresh context 全部没有完整通过，也就是 baseline 0/5。修改以后，再跑五个互不共享答案的新上下文，五次全部 9/9，scenario pass 5/5，方差为 0。
>
> 通用运行时最终是 195/195，CLI 13/13；独立总审还发现了普通 child move 的事务漏洞和未绑定的 preview 摘要。四条回归先真实失败，再修复，最后复审 Critical、Important、Minor 全部为 0。

屏幕：`empty-dir-red-green`，字幕 `baseline 0/5 → final 5/5`。

### 10:25–12:20 与公开市场现有做法比较

建议口播：

> 我没有找到一个可以负责任地称为“全网第一”的证据。我的说法是：在这次对 skills.sh、GitHub 和公开 Agent Skill 目录的检索范围内，没有发现一个直接同类项目同时覆盖下面整条链路。
>
> 市面上有通用代码清理 Skill，它们擅长 Clean Code、SOLID、去重复和重构；也有文件整理或安全修复 Skill，提供 dry-run、备份和确认。这些能力都很有价值，但问题不同。
>
> `de-starter` 的区别，是把 source identity、P0–P3、缺品牌暂停/中性占位符、受保护语义编辑、文件与目录双审计、两道 token 审批、目录身份绑定、外部事务备份、篡改失效、真实项目验收和 fresh-context 压力实验放进同一个专门流程。

公开比较参考：

- [通用 Codebase Cleanup / Refactor Skill](https://www.skills.sh/sickn33/antigravity-awesome-skills/codebase-cleanup-refactor-clean)：重点是 Clean Code 和重构。
- [Hazelnut 文件整理 Skill](https://gist.github.com/hkay-dev/b35d9f7ae9f51d86a15884d595dd6773)：提供 dry-run、确认和文件移动/删除规则。
- [Anthropic Skill Creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)：明确倡导 baseline/with-skill 对照和重复评估。

不要说：`这是全网最强、市场第一、唯一一个。`

推荐说：

> 本次公开检索范围内，我暂时没有发现覆盖同等完整链路的直接同类项目。如果你知道类似仓库，欢迎在评论区告诉我，我会补充公平对比。

### 12:20–13:10 适合与不适合

口播：

> 它适合买来的 SaaS Starter、模板、boilerplate、克隆项目和课程代码，尤其是已经包含认证、支付、数据库和 Demo 的项目。
>
> 如果只是一个三文件静态页面，而且你完全确定没有 LICENSE、持久化 key 和真实功能依赖，直接对话可能已经够用。
>
> v0.1 目前只支持 macOS/Linux 的 POSIX 安全能力，项目与外部运行目录还必须在同一文件系统。它也不能替代法律审查、真实支付迁移或生产密钥管理。

### 13:10–结尾 GitHub 分享与 CTA

口播：

> 这个 Skill 我会放到 GitHub，仓库名是 `de-starter`。你可以把它装进支持 Agent Skills 的编码 Agent，然后只说一句“帮我审计并去掉这个项目的 Starter 痕迹，修改前先给我看报告和 diff”。
>
> 这是我第一次从自己的真实问题出发，做一个能给别人复用的 Skill。它肯定还会继续迭代。如果你愿意测试，欢迎把项目类型、误报和你觉得不够安全的地方提到 Issue 里。

仓库地址占位：`https://github.com/YOUR_ACCOUNT/de-starter`

## 60 秒短视频口播

> 我买了一个 AI SaaS Starter，只对 AI 说了一句：帮我去掉 Starter 痕迹。
>
> 后来我发现，真正危险的不是漏掉几个单词，而是把 LICENSE、支付 key、数据库字段和工作中的 Demo 一起删掉。
>
> 所以我做了一个通用 Agent Skill，叫 `de-starter`。它先识别来源身份，再把发现分成 P0 到 P3；法律和敏感证据不动，高风险标识必须有迁移和回滚计划，Demo 让用户选择，展示文案才进入替换。
>
> 它还有两道审批门：先批准范围，再批准项目外 Preview 和精确 token。真正执行时，原始内容先进入外部备份，空目录也不是直接 `rmdir`。
>
> 真实结果：文件发现 523 到 227，剩余全部可解释；目录残留 1 到 0；没有新增测试失败，构建通过，恢复材料齐全。
>
> 我会把它开源到 GitHub。它不是“一键全删”，而是让 AI 的每一次删除都有证据、有边界、能恢复。

画面顺序：`audit-overview` 4 秒 → `safety-gates` 8 秒 → `before-after` 12 秒 → `empty-dir-gate-two` 8 秒 → `empty-dir-final` 15 秒 → GitHub CTA。

## 3 分钟版本提纲

1. 20 秒：一句话需求为什么演变成 Skill。
2. 35 秒：P0–P3 和不能全局替换的原因。
3. 35 秒：两道审批门与中性占位符。
4. 30 秒：行级语义编辑、目录双审计和事务备份。
5. 35 秒：523 → 227、1 → 0、测试与构建。
6. 15 秒：baseline 0/5 → final 5/5。
7. 10 秒：适用范围、限制、GitHub CTA。

## 所有可验证优势清单

口播中可按时长挑选，但长稿建议全部覆盖：

1. 不只搜关键词，先识别来源身份；
2. P0–P3 上下文风险分级；
3. LICENSE、版权、疑似凭据和生产数据不可进入修改范围；
4. P1 必须有真实迁移与回滚计划；
5. Demo、样例、评价、测试数据和资产逐类决策；
6. 缺品牌信息时暂停，或使用固定中性占位符，不编造品牌；
7. 文件哈希与行范围绑定的语义编辑；
8. 文件发现与 source-named 目录残留双审计；
9. `cleanup_empty_dirs` 是独立权限，不从子操作推断；
10. 项目外 Preview，不先污染真实工作区；
11. 两道审批门和精确 64 位 token；
12. 当前源码、Preview、操作、artifact hash、device/inode 和目录状态共同绑定；
13. 篡改、过期 token、路径替换、软链接和竞态均失败关闭；
14. 普通文件、目录和空目录统一 no-clobber 原子备份；
15. 先记录 committed phase，再做可能失败的验证；
16. 外部 backup、`restore.json`、`reverse.diff` 和 `apply-result.json`；
17. Git 可选，非 Git 项目仍具备恢复证据；
18. verify 不隐藏剩余发现，退出码 3 如实报告；
19. baseline/final 各五次 fresh-context 压力实验；
20. 独立安全审查与故障注入；
21. 真实 Starter 前后验收；
22. 公开仓库全树隐私扫描，不发布购买源码或真实 token。

## 演示录屏流程

录屏只展示公开安全的合成项目，真实项目使用聚合截图：

1. 展示 GitHub README 和安装目录结构；
2. 输入：`$de-starter Audit this repository and show the report and proposed diff before making changes.`；
3. 展示发现 source candidates，但不要用真实购买项目身份；
4. 展示缺品牌时的两个选择：补齐真实 profile，或固定中性占位符；
5. 展示 P0–P3 表格；
6. 展示 `Directory residue: 1` 和未批准时的停止响应；
7. 展示 Gate 1 决策，不展示真实源码；
8. 展示 Preview artifacts 文件名和脱敏 diff；
9. 展示 Gate 2 等待状态，token 用模糊遮罩；
10. 在合成 fixture 上批准并 Apply；
11. 展示 backup、restore、reverse diff 和 verify 汇总；
12. 插入真实实验截图 `empty-dir-final`；
13. 回到 GitHub README，展示限制和 Issue 入口。

## 截图插入表

| 时间点 | 镜头 | 作用 |
| --- | --- | --- |
| 开场 | `01-audit-overview.png` | 说明不是直接修改 |
| 两道门 | `02-safety-gates.png` | 解释 Gate 1 / Gate 2 |
| 第一轮真实效果 | `03-before-after.png` | 展示 523 → 227 |
| 开发与审查 | `04-empty-dir-red-green.png` | 解释测试全绿仍需复审 |
| 真实 Gate 2 | `05-empty-dir-gate-two.png` | 展示 0 / 0 / 0 / 1 且未 Apply |
| 最终效果 | `06-empty-dir-final.png` | 展示 523 → 227 与 1 → 0 |

## 视频简介

> 我把真实购买 Starter 的“去痕迹”过程做成了一个可复用的 Agent Skill：`de-starter`。
>
> 它不是简单全局替换，而是包含来源身份识别、P0–P3 风险分级、缺品牌暂停/中性占位符、受保护语义编辑、文件与目录双审计、两道审批门、项目外 Preview、精确 token、事务备份、回滚与 Verify。
>
> 真实验收：文件发现 523 → 227，目录残留 1 → 0；P0 与 LICENSE 保持，没有新增测试失败，production build 通过。
>
> GitHub：`https://github.com/YOUR_ACCOUNT/de-starter`
>
> 欢迎提交 Issue，尤其欢迎提供不同技术栈、误报和安全边界反馈。

## 置顶评论

> 仓库地址：`https://github.com/YOUR_ACCOUNT/de-starter`
>
> 提醒：它不会承诺关键词清零。剩余 P0/P1/P2/P3 可能是法律证据、兼容性标识或用户主动保留的功能。v0.1 自动 Apply 暂只支持 macOS/Linux，并要求项目与外部运行目录位于同一文件系统。
>
> 如果你知道已经存在、并且覆盖同等完整审计/审批/事务链路的项目，欢迎留言。我会补充公平对比，而不是宣传“全网第一”。

## FAQ

### 我直接在对话框里说“帮我去 Starter”不就行了吗？

可以，这也是本项目的起点。Skill 的价值是把后续风险判断、审批门、artifact、回滚和验证变成每次都能复用和测试的行为，而不是要求用户写更长的提示词。

### 它是不是一个 Agent？

不是。Agent 是执行者；Skill 是 Agent 按需加载的专业 SOP、约束和工具包。安装 Skill 不会额外启动一个独立机器人。

### 为什么还剩 227 条？

因为安全目标不是关键词清零。剩余包括 P0 法律/敏感证据、P1 兼容性标识、用户保留的 P2 功能和明确保留的 P3 业务词。

### 删除一个空目录为什么这么复杂？

因为 Skill 承诺不覆盖并发出现的外来数据，并且要可恢复。它需要身份绑定、原子 no-clobber 移动、事务阶段记录、外部备份和恢复验证。

### 能在 Windows 使用吗？

v0.1 的自动 Apply 暂不支持。Audit 思路可参考，但不能把 POSIX 安全语义直接假装成 Windows 等价实现。

### 会上传我的代码吗？

Skill 本身在本地运行。是否把任何内容发送给模型取决于使用它的 Agent 平台；公开仓库明确禁止提交购买源码、私有 diff、凭据与真实 token。

### 如果没有自己的品牌名怎么办？

暂停补齐真实品牌 profile，或者选择固定中性占位符。Skill 不替用户编造公司、域名和邮箱。

### 它能保证不出错吗？

不能承诺绝对无错误。它通过失败关闭、两次审批、状态绑定、外部备份、回归测试和独立复审显著降低风险，并保留可诊断恢复证据。

## 发布前检查清单

- [ ] 替换全部 `YOUR_ACCOUNT` GitHub 占位符；
- [ ] GitHub 仓库公开可访问；
- [ ] README 安装命令在一个干净目录验证；
- [ ] Release tag 与 CHANGELOG 一致；
- [ ] 所有截图 1600×900，未裁掉状态说明；
- [ ] 视频中真实 token 全程遮挡；
- [ ] 不展示购买源码、私有路径、项目身份、邮箱、密钥或备份映射；
- [ ] “市场比较”使用检索范围限定，不说“全网第一”；
- [ ] 简介、置顶评论和片尾仓库地址一致；
- [ ] 发布后创建 Issue 模板，邀请误报与跨技术栈反馈。
