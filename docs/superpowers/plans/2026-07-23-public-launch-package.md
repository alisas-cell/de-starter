# De-starter Public Launch Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 GitHub 仓库门面、最终脱敏实验报告和可以直接照着录制的全中文视频导演包。

**Architecture:** 真实 Starter 聚合结果、公开合成拒绝实验和 GitHub CI 是三类独立证据。Markdown 负责信息架构与口播，HTML 是图片 source，PNG 是展示资产，Python 回归锁定数字、链接、中文叙事、尺寸和隐私边界；GitHub 外部设置只在本地材料验证并推送后更新。

**Tech Stack:** Markdown、GitHub Issue Forms YAML、HTML/CSS、PNG、Python 3.9+ `unittest`、GitHub Actions、GitHub repository settings。

## Global Constraints

- 不重新做普通用户安装验收，不再次修改真实购买 Starter。
- 不修改生产清理行为，不移动 v0.1.0、v0.1.1 或 v0.1.2 标签。
- 视频图片的叙事文字全部中文；技术标识可保留，但第一次出现必须配中文解释。
- 真实项目、合成实验和 CI 不能混为同一种证据。
- 不公开购买项目身份、源码、完整 diff、私有路径、审批 token、backup 映射、凭据、真实域名、邮箱或 proprietary assets。
- 不使用“零风险”“绝不会破坏”“一键恢复”“全网第一”“唯一”“市场最强”。
- 10 张视频 PNG 为 1600×900；Social Preview 为 1280×640、PNG、纯色背景、小于 1 MB，符合 [GitHub 官方建议](https://docs.github.com/zh/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview)。
- v0.1.2 只描述为公开演示、拒绝证据、文档、图片和测试更新；生产 Skill 行为相对 v0.1.1 未改变。

---

### Task 1: Add the public-launch regression contract

**Files:**
- Create: `tests/test_public_launch.py`

**Interfaces:**
- Consumes: repository Markdown, Issue Forms, HTML sources and PNG assets.
- Produces: six `unittest` cases used as the acceptance contract for Tasks 2–6.

- [ ] **Step 1: Write the failing tests**

Create `ROOT`, IDs `01-audit-overview` through `10-transaction-recovery`, and a PNG signature/dimension helper. Add these exact tests:

```python
def test_readme_launch_navigation_and_safety(self):
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for phrase in ("Quick links", "Risk is reduced, not zero",
                   "docs/real-starter-experiment-report.zh-CN.md",
                   "docs/video-director-script.zh-CN.md",
                   "issues/new/choose", "214/214", "v0.1.2"):
        self.assertIn(phrase, text)

def test_final_report_separates_evidence_sources(self):
    text = (ROOT / "docs/real-starter-experiment-report.zh-CN.md").read_text(encoding="utf-8")
    for phrase in ("523 → 227", "1 → 0", "132 → 132", "214 / 214",
                   "真实购买 Starter 验收", "公开合成实验",
                   "Skill 回归与 GitHub CI", "没有一键恢复命令",
                   "低风险不等于零风险"):
        self.assertIn(phrase, text)

def test_director_script_covers_required_story(self):
    text = (ROOT / "docs/video-director-script.zh-CN.md").read_text(encoding="utf-8")
    for phrase in ("为什么直接搜索替换不安全", "P0–P3", "两道人工审批门",
                   "错误令牌与过期预览", "事务化备份、回滚和空目录清理",
                   "214 项测试和真实 Starter 验收", "普通提示词和 Skill 的差别",
                   "屏幕画面", "鼠标重点", "逐字口播", "不能说什么"):
        self.assertIn(phrase, text)

def test_feedback_form_requires_privacy_confirmation(self):
    text = (ROOT / ".github/ISSUE_TEMPLATE/feedback.yml").read_text(encoding="utf-8")
    for phrase in ("使用反馈", "项目类型", "使用阶段", "完全合成",
                   "购买的 Starter 源码", "approval token", "required: true"):
        self.assertIn(phrase, text)
```

Add `test_all_video_assets_have_chinese_sources_and_exact_dimensions`: all 10 IDs need source HTML and PNG; HTML must contain four consecutive CJK characters, omit the old English headings, and PNG dimensions equal `(1600, 900)`.

Add `test_social_preview_matches_github_requirements`: require HTML/PNG, phrases `安全去除 Starter 痕迹` and `两道审批`, dimensions `(1280, 640)`, size under 1,000,000 bytes, and no 64-hex token.

- [ ] **Step 2: Prove the contract is red**

```bash
python3 -m unittest tests.test_public_launch -v
```

Expected: six tests run; missing director script, feedback form, IDs 09/10, Social Preview, README navigation and report-source assertions fail.

- [ ] **Step 3: Commit the red contract**

```bash
git add tests/test_public_launch.py
git commit -m "test: define public launch package"
```

---

### Task 2: Build the tracked GitHub facade

**Files:**
- Modify: `README.md`
- Create: `.github/ISSUE_TEMPLATE/feedback.yml`
- Modify: `.github/ISSUE_TEMPLATE/config.yml`
- Modify: `CONTRIBUTING.md`

**Interfaces:**
- Consumes: public demo, report, director-script path and security route.
- Produces: one fast repository entry point and one privacy-safe feedback route.

- [ ] **Step 1: Add README Quick links**

Add Install, public demo, Chinese report, Chinese director script, `/issues/new/choose`, and Latest v0.1.2 links. Put the non-zero-risk warning immediately below. Add the exact version statement: `v0.1.2 adds the synthetic public lab, refusal evidence, documentation, media, and tests. Production Skill behavior is unchanged from v0.1.1.`

- [ ] **Step 2: Add the feedback Issue Form**

Create a bilingual `使用反馈 / Feedback` form with required project-type and stage dropdowns, required difficulty and improvement textareas, optional fully synthetic example, and a required checkbox confirming no purchased source, identity, private path, credential, diff, backup map or approval token. Label it `feedback`.

- [ ] **Step 3: Align entry points**

Keep blank issues disabled. Add Feedback to `config.yml` and a `Feedback without a code change` section to CONTRIBUTING; both point to `/issues/new/choose`. Keep sensitive reports on private vulnerability reporting.

- [ ] **Step 4: Verify and commit**

```bash
python3 -m unittest tests.test_public_launch.PublicLaunchPackageTests.test_readme_launch_navigation_and_safety tests.test_public_launch.PublicLaunchPackageTests.test_feedback_form_requires_privacy_confirmation -v
git add README.md CONTRIBUTING.md .github/ISSUE_TEMPLATE
git commit -m "docs: improve repository entry points"
```

Expected: both tests pass.

---

### Task 3: Finalize the sanitized experiment report

**Files:**
- Modify: `docs/real-starter-experiment-report.zh-CN.md`
- Modify: `examples/sanitized-real-run-summary.md`

**Interfaces:**
- Consumes: verified aggregates, public-demo refusals and v0.1.2 CI.
- Produces: canonical Chinese evidence report plus aligned English summary.

- [ ] **Step 1: Add the one-page result table**

Rows: `523 → 227（减少 296，降幅 56.6%）`, directory `1 → 0`, P0 `132 → 132`, P1 `52 → 35`, P2 `52 → 21`, P3 `287 → 39`, real-project new failures `0`, Skill `214 / 214`, CI `Python 3.9 / 3.11 / 3.13 全部通过`.

- [ ] **Step 2: Add evidence-source boundaries**

Create rows `真实购买 Starter 验收`, `公开合成实验`, `Skill 回归与 GitHub CI`, each with “能证明什么 / 不能声称什么”. State that synthetic refusals are not destructive tests on the purchased project.

- [ ] **Step 3: Add refusal and recovery boundaries**

State that wrong/stale tokens refuse before project writes, backup and apply-result, with no partial operations; v0.1.2 has transaction rollback and recovery evidence but no one-command restore; low risk is not zero risk. Update only the Skill row to 214/214; real project remains 63/65 with the same two inherited failures and zero new failures.

- [ ] **Step 4: Align the English summary, verify and commit**

Append `Public refusal evidence and current release` with the same claims.

```bash
python3 -m unittest tests.test_public_launch.PublicLaunchPackageTests.test_final_report_separates_evidence_sources -v
git add docs/real-starter-experiment-report.zh-CN.md examples/sanitized-real-run-summary.md
git commit -m "docs: finalize sanitized experiment evidence"
```

Expected: test passes; no private material enters either report.

---

### Task 4: Write the recording-ready Chinese director script

**Files:**
- Create: `docs/video-director-script.zh-CN.md`
- Modify: `docs/video-shot-list.zh-CN.md`
- Modify: `docs/self-media-package.zh-CN.md`
- Modify: `docs/video-production-log.zh-CN.md`

**Interfaces:**
- Consumes: image IDs 01–10 and verified public claims.
- Produces: a 14–16 minute word-for-word script and synchronized shot ledger.

- [ ] **Step 1: Use the fixed scene fields**

Every scene contains `时间码`, `屏幕画面`, `鼠标重点`, `逐字口播`, `证据证明什么`, `观众应记住`, `不能说什么`, `转场`.

- [ ] **Step 2: Write the exact sequence**

```text
00:00–00:45 开场：一句话为什么变成一个 Skill（03 → 01）
00:45–02:35 为什么直接搜索替换不安全（01）
02:35–04:30 P0–P3：四种处理方式（01 → 03）
04:30–06:30 两道人工审批门（02 → 05）
06:30–08:15 错误令牌与过期预览（08）
08:15–10:25 事务化备份、回滚和空目录清理（10 → 05 → 06）
10:25–12:35 214 项测试和真实 Starter 验收（03 → 06 → 07）
12:35–14:20 普通提示词和 Skill 的差别（09）
14:20–15:20 限制和 GitHub 获取方式（Social Preview → README）
```

Explain technical words in Chinese. Explicitly separate real/synthetic/CI evidence, 227 classified retention, 214 Skill tests, and real-project 63/65.

- [ ] **Step 3: Synchronize media documents**

Link the director script from all three documents; register 09, 10 and Social Preview with source, privacy, duration, focus, narration and filename; update current status from 195/v0.1.1 to 214/v0.1.2 without rewriting historical events.

- [ ] **Step 4: Verify and commit**

```bash
python3 -m unittest tests.test_public_launch.PublicLaunchPackageTests.test_director_script_covers_required_story -v
git add docs/video-director-script.zh-CN.md docs/video-shot-list.zh-CN.md docs/self-media-package.zh-CN.md docs/video-production-log.zh-CN.md
git commit -m "docs: add Chinese recording director script"
```

---

### Task 5: Translate and refresh images 01–08

**Files:**
- Modify: `docs/assets/video/sources/01-audit-overview.html` through `08-public-demo-safety.html`
- Regenerate: matching PNG files.

**Interfaces:**
- Consumes: existing layouts, verified data and current CI.
- Produces: eight Chinese 1600×900 evidence cards.

- [ ] **Step 1: Apply the Chinese title map**

Titles: `先看清残留，再保护产品`, `两道审批门，拒绝盲目写入`, `不是清零，而是安全地留下该留下的`, `测试全绿，不等于已经足够安全`, `只清理 1 个空目录，也要停在第二道门`, `文件残留可解释，目录残留归零`, `本地全绿，还要经过公开 Linux CI`, `两次拒绝，一次精确批准`. Translate every narrative label; keep only short technical identifiers beside Chinese explanations.

- [ ] **Step 2: Refresh image 07**

Use local 214/214, v0.1.2, Python 3.9/3.11/3.13 and commit `65b99eb`. Preserve the inode-reuse lesson and label it `基于公开 GitHub 数据重绘`.

- [ ] **Step 3: Render and inspect**

Use Chrome headless `--window-size=1600,900` with matching source and target paths. Never write absolute paths into tracked HTML. Inspect each PNG at original detail for Chinese copy, crop, overflow, readability and privacy.

- [ ] **Step 4: Test and commit**

Run the visual test; expected remaining failures mention only missing 09/10. Then:

```bash
git add docs/assets/video/sources/0[1-8]-*.html docs/assets/video/0[1-8]-*.png
git commit -m "docs: translate public evidence cards"
```

---

### Task 6: Add images 09, 10 and Social Preview

**Files:**
- Create: `docs/assets/video/sources/09-prompt-vs-skill.html`, matching PNG
- Create: `docs/assets/video/sources/10-transaction-recovery.html`, matching PNG
- Create: `docs/assets/github/social-preview.zh-CN.html`, matching PNG

**Interfaces:**
- Consumes: existing visual system.
- Produces: two final video cards and one upload-ready preview.

- [ ] **Step 1: Build 09 Prompt vs Skill**

Compare current-conversation dependency, ad-hoc reminders and repeated explanation against fixed P0–P3, two gates, external Preview/backup, wrong/stale refusal and post-Apply verification. Title: `一句提示词可以开始，Skill 负责把安全流程走完`. Footer: `提示词是起点，Skill 是可复用的执行边界`.

- [ ] **Step 2: Build 10 transaction recovery**

Flow: `真实项目（只读） → 第一道审批 → 项目外 Preview → 第二道审批：当前精确 token → 外部 backup → 限定 Apply 与 Verify`. Show success evidence and failure rollback branches. Footer: `像先搬进保险柜，不是直接扔进垃圾桶｜恢复证据齐全，但没有一键恢复命令`.

- [ ] **Step 3: Build the 1280×640 Social Preview**

Use only `de-starter`, `安全去除 Starter 痕迹`, `P0–P3 分级｜两道审批｜项目外预览｜恢复证据`, `低风险不等于零风险`; solid background, text within centered 1120×480 safe area.

- [ ] **Step 4: Render, inspect, test and commit**

Render 09/10 at 1600×900 and Social Preview at 1280×640. Inspect all three and run both visual tests. Then:

```bash
git add docs/assets/video/sources/09-prompt-vs-skill.html docs/assets/video/09-prompt-vs-skill.png docs/assets/video/sources/10-transaction-recovery.html docs/assets/video/10-transaction-recovery.png docs/assets/github
git commit -m "docs: add Chinese launch visuals"
```

---

### Task 7: Verify, publish and apply GitHub settings

**Files:**
- Modify if needed: README, report and media documents
- Upload: `docs/assets/github/social-preview.zh-CN.png`

**Interfaces:**
- Consumes: Tasks 1–6.
- Produces: clean main, green CI, public metadata, Social Preview and feedback entry.

- [ ] **Step 1: Cross-link final assets**

README links report/director script; director script embeds images 01–10; shot list contains exactly IDs 01–10 plus Social Preview with source, PNG, privacy, focus, duration and narration.

- [ ] **Step 2: Run final verification**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest discover -s tests -v
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/de-starter
PYTHONPYCACHEPREFIX=/tmp/de-starter-launch-pyc python3 -m compileall -q skills/de-starter/scripts examples/public-demo tests
git diff --check
```

Expected: 220 tests if exactly six were added; Skill, compile and diff checks pass.

- [ ] **Step 3: Check links, YAML, images and privacy**

Use `git ls-files`; strip fenced code before local Markdown link checks; validate Issue Form keys/privacy; validate 10 video PNGs plus Social Preview; reject machine paths, private-key headers, GitHub/OpenAI token shapes, historical approval tokens and known purchased identity patterns. Expected: zero missing links and privacy matches.

- [ ] **Step 4: Push and wait for CI**

Commit only real corrections, push `HEAD:main`, and wait for Python 3.9/3.11/3.13 success. Do not create or move a release tag.

- [ ] **Step 5: Apply GitHub facade settings**

Description: `Safety-first Agent Skill for auditing and removing starter, boilerplate, template, and SaaS-kit residue with approval gates, external previews, backups, and rollback evidence.`

Topics: `agent-skills`, `code-audit`, `starter-template`, `boilerplate`, `saas-starter`, `template-cleanup`, `safe-refactoring`, `rollback`, `python`, `developer-tools`. Ensure `bug`, `classification`, `feedback` labels exist. Do not enable Discussions.

- [ ] **Step 6: Upload and verify Social Preview**

Upload only the generated public PNG in Settings → Social preview. Verify description, 10 topics, preview, README links, Issue chooser, private security route, Latest v0.1.2 and three-of-three CI.

- [ ] **Step 7: Record final public evidence**

Append public URLs, main SHA, CI URL, Social Preview and Issue chooser confirmation to the production log without cookies, session data, local paths or private screenshots. Commit/push and wait for final CI if the log changes.

---

## Final Review Gate

1. inspect all Markdown/YAML/HTML for accuracy and privacy;
2. visually inspect all 11 PNGs;
3. rerun tests, compile, links, dimensions and privacy checks;
4. confirm clean status and `HEAD == origin/main`;
5. confirm GitHub description, topics, Social Preview, Issue chooser, Latest Release and CI;
6. report that risk is reduced, not zero, and v0.1.2 has recovery evidence but no one-command restore.
