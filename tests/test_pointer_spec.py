"""The pointer and mode spec stays aligned with the current rules."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = (ROOT / "docs" / "20_POINTER_AND_MODES.md").read_text(encoding="utf-8")
HANDOFF = (ROOT / "WEB_IMPLEMENTATION_HANDOFF.md").read_text(encoding="utf-8")


class PointerSpecTests(unittest.TestCase):
    def test_sources_stay_separate_from_the_design(self):
        self.assertIn("https://hearthstone.blizzard.com/en-us/news/23765275", SPEC)
        self.assertIn("https://hearthstone.blizzard.com/en-us/news/23156373", SPEC)
        self.assertIn("https://hearthstone.wiki.gg/wiki/Target", SPEC)
        self.assertIn("不借用炉石的七个场位", SPEC)
        self.assertIn("没有张数上限", SPEC)

    def test_drag_deploy_and_attack_do_not_reorder(self):
        self.assertIn("松手在一条合法的缝上", SPEC)
        self.assertIn("双击或双点手牌", SPEC)
        self.assertIn("厚壳永远插到己方最左", SPEC)
        self.assertIn("费用仍是 1", SPEC)
        self.assertIn("不改变顺序", SPEC)
        self.assertIn("点自己的单位再点目标", SPEC)

    def test_cancel_and_reasons_stay_distinct(self):
        for label in ("拖回手牌", "pointercancel", "第二根手指", "Esc"):
            self.assertIn(label, SPEC)
        self.assertIn("不扣电、不弃牌", SPEC)
        self.assertIn("打出两遍", SPEC)
        for code in (
            "summoning_sickness",
            "already_attacked",
            "not_enough_supply",
            "guard_blocks",
            "bad_target",
            "already_used_ability",
        ):
            self.assertIn(code, SPEC)
        self.assertIn("不能把这些都写成「本回合用过」", SPEC)

    def test_modes_and_toolbar(self):
        self.assertIn("默认入口是人机", SPEC)
        self.assertIn("不能看玩家手牌的内容", SPEC)
        self.assertIn("不是强人工智能", SPEC)
        self.assertIn("两人轮流，共用这一块屏幕", SPEC)
        self.assertIn("请交给对方", SPEC)
        self.assertIn("复活厚壳 · 1电", SPEC)
        self.assertIn("攻击+1 · 1电", SPEC)
        self.assertIn("不出现攻击 +1", SPEC)
        self.assertIn("不是上面资料里核实过的炉石事实", SPEC)
        self.assertIn("绿色圈或绿色描边，再加上靶标形状", SPEC)
        self.assertIn("红色圆圈和居中的 ×", SPEC)
        self.assertIn("不能只把圈涂成红色", SPEC)
        self.assertIn("不符合夺舍", SPEC)
        self.assertIn("不消耗攻击次数", SPEC)
        self.assertIn("不要为了显示红 × 去伪造一个目标", SPEC)
        self.assertIn("手指不能把红色圆圈、× 和那句短原因完全挡住", SPEC)
        self.assertIn("固定教学", SPEC)
        self.assertIn("每副正好 30 张", SPEC)
        self.assertIn("备用电池", SPEC)
        self.assertIn("手牌上限 10", SPEC)
        self.assertIn("不承诺 96 张每一张都会进某一局", SPEC)
        self.assertIn("rotateX", SPEC)
        self.assertIn("perspective", SPEC)
        self.assertIn("不得只把卡的高度压扁", SPEC)
        self.assertIn("不得让 char 独立浮在卡片上方", SPEC)
        self.assertIn("没有「最左主控」这一条", SPEC)
        self.assertIn("不看玩家即将拿到的手牌", SPEC)
        self.assertIn("重开模拟战就换新种子", SPEC)
        self.assertIn("390×844", SPEC)
        self.assertIn("1280×800", SPEC)
        self.assertIn("docs/20_POINTER_AND_MODES.md", HANDOFF)
        self.assertIn("默认是人机", HANDOFF)


if __name__ == "__main__":
    unittest.main()
