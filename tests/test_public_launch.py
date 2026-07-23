from pathlib import Path
import re
import struct
import unittest


ROOT = Path(__file__).resolve().parents[1]
VIDEO_IDS = (
    "01-audit-overview",
    "02-safety-gates",
    "03-before-after",
    "04-empty-dir-red-green",
    "05-empty-dir-gate-two",
    "06-empty-dir-final",
    "07-github-ci-green",
    "08-public-demo-safety",
    "09-prompt-vs-skill",
    "10-transaction-recovery",
)


def png_dimensions(path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("not a PNG: %s" % path)
    return struct.unpack(">II", data[16:24])


class PublicLaunchPackageTests(unittest.TestCase):
    def test_readme_launch_navigation_and_safety(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for phrase in (
            "Quick links",
            "Risk is reduced, not zero",
            "docs/real-starter-experiment-report.zh-CN.md",
            "docs/video-director-script.zh-CN.md",
            "issues/new/choose",
            "214/214",
            "v0.1.2",
        ):
            self.assertIn(phrase, text)

    def test_final_report_separates_evidence_sources(self):
        text = (
            ROOT / "docs/real-starter-experiment-report.zh-CN.md"
        ).read_text(encoding="utf-8")
        for phrase in (
            "523 → 227",
            "1 → 0",
            "132 → 132",
            "214 / 214",
            "真实购买 Starter 验收",
            "公开合成实验",
            "Skill 回归与 GitHub CI",
            "没有一键恢复命令",
            "低风险不等于零风险",
        ):
            self.assertIn(phrase, text)

    def test_director_script_covers_required_story(self):
        text = (ROOT / "docs/video-director-script.zh-CN.md").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "为什么直接搜索替换不安全",
            "P0–P3",
            "两道人工审批门",
            "错误令牌与过期预览",
            "事务化备份、回滚和空目录清理",
            "214 项测试和真实 Starter 验收",
            "普通提示词和 Skill 的差别",
            "屏幕画面",
            "鼠标重点",
            "逐字口播",
            "不能说什么",
        ):
            self.assertIn(phrase, text)

    def test_feedback_form_requires_privacy_confirmation(self):
        text = (ROOT / ".github/ISSUE_TEMPLATE/feedback.yml").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "使用反馈",
            "项目类型",
            "使用阶段",
            "完全合成",
            "购买的 Starter 源码",
            "approval token",
            "required: true",
        ):
            self.assertIn(phrase, text)

    def test_all_video_assets_have_chinese_sources_and_exact_dimensions(self):
        forbidden_headings = (
            "READ-ONLY AUDIT",
            "Two gates. Zero blind writes.",
            "PROTECTED",
            "COMPATIBILITY",
            "USER DECIDES",
            "PRESENTATION",
            "REJECTED",
            "SCOPED APPLY",
        )
        for asset_id in VIDEO_IDS:
            source = (
                ROOT / "docs/assets/video/sources" / (asset_id + ".html")
            )
            image = ROOT / "docs/assets/video" / (asset_id + ".png")
            self.assertTrue(source.is_file(), source)
            self.assertTrue(image.is_file(), image)
            html = source.read_text(encoding="utf-8")
            self.assertRegex(html, r"[\u4e00-\u9fff]{4,}")
            for heading in forbidden_headings:
                self.assertNotIn(heading, html, "%s: %s" % (asset_id, heading))
            self.assertEqual(png_dimensions(image), (1600, 900))

    def test_social_preview_matches_github_requirements(self):
        source = ROOT / "docs/assets/github/social-preview.zh-CN.html"
        image = ROOT / "docs/assets/github/social-preview.zh-CN.png"
        self.assertTrue(source.is_file())
        self.assertTrue(image.is_file())
        html = source.read_text(encoding="utf-8")
        self.assertIn("安全去除 Starter 痕迹", html)
        self.assertIn("两道审批", html)
        self.assertEqual(png_dimensions(image), (1280, 640))
        self.assertLess(image.stat().st_size, 1_000_000)
        self.assertIsNone(re.search(r"\b[0-9a-f]{64}\b", html))


if __name__ == "__main__":
    unittest.main()
