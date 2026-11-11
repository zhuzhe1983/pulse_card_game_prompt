"""The web tap-to-play note stays a playtest design, separate from hardware facts."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = (ROOT / "docs" / "21_NFC_TAP_TO_PLAY.md").read_text(encoding="utf-8")
HANDOFF = (ROOT / "WEB_IMPLEMENTATION_HANDOFF.md").read_text(encoding="utf-8")


class NfcTapSpecTests(unittest.TestCase):
    def test_platform_and_sources(self):
        self.assertIn("待试玩方案", SPEC)
        self.assertIn("https://developer.chrome.com/docs/capabilities/nfc", SPEC)
        self.assertIn("https://w3c-cg.github.io/web-nfc/", SPEC)
        self.assertIn("serialNumber", SPEC)
        self.assertIn("Android", SPEC)
        self.assertIn("iOS", SPEC)
        self.assertIn("HTTPS", SPEC)
        self.assertIn("开始刷卡", SPEC)
        self.assertIn("拖拽或点选", SPEC)

    def test_record_and_classification(self):
        self.assertIn("application/vnd.pulse.card+json", SPEC)
        self.assertIn('"cardId":"H024"', SPEC)
        self.assertIn("空白卡", SPEC)
        self.assertIn("陌生内容", SPEC)
        self.assertIn("没读到卡，请再贴一次", SPEC)
        self.assertIn("没有刷卡权限", SPEC)
        self.assertIn("仍然覆写", SPEC)
        self.assertIn("绝不静默覆盖", SPEC)
        self.assertIn("写入后校验失败", SPEC)

    def test_play_matches_drag_rules(self):
        self.assertIn("等于从手牌打出", SPEC)
        self.assertIn("手里没有这张牌", SPEC)
        self.assertIn("现在不能替这一方操作", SPEC)
        self.assertIn("红色圆圈加 ×", SPEC)
        self.assertIn("不扣电", SPEC)
        self.assertIn("1.5 秒", SPEC)
        self.assertIn("复活厚壳", SPEC)
        self.assertIn("docs/21_NFC_TAP_TO_PLAY.md", HANDOFF)


if __name__ == "__main__":
    unittest.main()
