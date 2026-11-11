"""The 96-card playtest roster stays complete and compatible with the baseline 12."""
import json
import unittest
from pathlib import Path

from clash_walk import ClashError, Game, load_cards

ROOT = Path(__file__).resolve().parents[1]


def roster():
    return json.loads((ROOT / "content" / "clash_roster_96.json").read_text(encoding="utf-8"))


def cards_by_id(data):
    out = {}
    for card in data["cards"]:
        out[card["template_id"]] = card
    return out


class RosterTests(unittest.TestCase):
    def test_ninety_six_are_designed(self):
        data = roster()
        self.assertEqual(data["ruleset_id"], "pcg.clash.v0")
        self.assertEqual(data["schema"], "pcg.clash.roster.v0")
        self.assertEqual(data["design_status"], "playtest_draft")
        self.assertEqual(len(data["cards"]), 96)
        self.assertEqual(len({c["rid"] for c in data["cards"]}), 96)
        self.assertEqual(len({c["template_id"] for c in data["cards"]}), 96)
        self.assertEqual(len({c["game_name_zh"] for c in data["cards"]}), 96)
        required = (
            "game_name_zh", "game_description", "balance_intent", "faction", "game_role",
            "kind", "cost", "attack", "durability", "hardware_controller", "art_type",
            "official_product_name_en", "growth_kind", "growth_basis", "design_status",
        )
        doc = (ROOT / "docs" / "18_ROSTER_AND_GROWTH.md").read_text(encoding="utf-8")
        for card in data["cards"]:
            for key in required:
                self.assertNotIn(card[key], (None, ""), card["rid"] + key)
            self.assertEqual(card["design_status"], "playtest_draft")
            self.assertEqual(card["game_role"], card["kind"])
            self.assertIn(card["art_type"], ("typeA", "typeB"))
            self.assertIn(card["hardware_controller"],
                          ("independent_host", "auxiliary_programmable_mcu", "no_main_chip_listed"))
            self.assertGreaterEqual(card["cost"], 1)
            self.assertLessEqual(card["cost"], 10)
            if card["kind"] == "main":
                self.assertGreaterEqual(card["durability"], 1)
                self.assertLessEqual(card["attack"], 5)
            else:
                self.assertEqual(card["durability"], 0)
                self.assertEqual(card["attack"], 0)
                self.assertGreaterEqual(card["attack_bonus"] + int(card["grants_guard"]) + int(card["bypass_guard"]), 1)
            if "待核验" in card["sku_status"]:
                self.assertIsNone(card["trusted_sku"], card["rid"])
            self.assertIn(card["rid"], doc)
            self.assertIn(card["game_name_zh"], doc)

    def test_growth_chains_are_real_revisions_only(self):
        data = roster()
        by_rid = {c["rid"]: c for c in data["cards"]}
        families = {}
        for card in data["cards"]:
            if card["growth_kind"] != "chain":
                self.assertIsNone(card["star"])
                self.assertIsNone(card["next_template_id"])
                continue
            families.setdefault(card["growth_family"], []).append(card)
        self.assertEqual(len(families), 9)
        for fam, rows in families.items():
            rows.sort(key=lambda c: c["star"])
            self.assertEqual([c["star"] for c in rows], list(range(1, len(rows) + 1)))
            self.assertLessEqual(len(rows), 2, fam)
            for i, card in enumerate(rows):
                if i + 1 < len(rows):
                    nxt = rows[i + 1]
                    self.assertEqual(card["next_template_id"], nxt["template_id"])
                    self.assertEqual(nxt["prev_template_id"], card["template_id"])
                else:
                    self.assertIsNone(card["next_template_id"])
        lateral = {"H038b", "H038c", "H039a", "H039f", "H033", "H050", "H010", "H029a", "C001a", "A012a"}
        for rid in lateral:
            self.assertEqual(by_rid[rid]["growth_kind"], "lateral")
        self.assertEqual(by_rid["H041"]["growth_kind"], "solo")
        self.assertEqual(by_rid["C001z"]["hardware_controller"], "auxiliary_programmable_mcu")
        self.assertEqual(by_rid["C001z"]["game_role"], "attachment")
        self.assertEqual(by_rid["H018"]["hardware_controller"], "independent_host")

    def test_baseline_twelve_are_not_forked(self):
        base = json.loads((ROOT / "content" / "clash_playtest.json").read_text(encoding="utf-8"))
        data = roster()
        by_template = cards_by_id(data)
        linked = []
        for card in data["cards"]:
            if not card["baseline_template_id"]:
                continue
            linked.append(card["baseline_template_id"])
            src = next(c for c in base["cards"] if c["template_id"] == card["baseline_template_id"])
            for key in ("cost", "attack", "durability", "guard", "effect"):
                self.assertEqual(card[key] if key != "effect" else card["effect"], src[key], card["rid"] + key)
        self.assertEqual(sorted(linked), ["dian_zhen", "hou_ke", "qiao_jian", "xiao_yin", "xuan_niu"])
        kept = {"xi_tiao", "lian_jie", "qian_li", "hu_zhao", "bu_ji", "gan_rao", "hui_chong"}
        self.assertTrue(kept.isdisjoint(by_template))

    def test_promote_keeps_slot_and_does_not_refresh_support(self):
        data = roster()
        base = load_cards(json.loads((ROOT / "content" / "clash_playtest.json").read_text(encoding="utf-8")))
        cards = dict(base)
        cards.update(cards_by_id(data))
        game = Game.empty(cards)
        game.supply = [5, 0]
        game.max_supply = [5, 0]
        game.hands = [["art_h038a"], []]
        game.spawn(0, "dian_zhen", sick=False)
        stamp = game.spawn(0, "xiao_yin", sick=False)
        stamp["attachments"] = ["lian_jie"]
        game.graves = [["hou_ke"], []]
        game.support(0)
        self.assertEqual(game.supply[0], 4)
        held = game.hands[0].pop(0)
        with self.assertRaises(ClashError) as missing:
            game.promote(0, "xiao_yin")
        self.assertEqual(missing.exception.code, "not_in_hand")
        self.assertEqual(game.supply[0], 4)
        game.hands[0].append(held)
        game.promote(0, "xiao_yin")
        self.assertEqual(game.supply[0], 3)
        self.assertEqual(game.graves[0][-2:], ["lian_jie", "xiao_yin"])
        revived = game.boards[0][2]
        self.assertEqual(game.boards[0][0]["card_id"], "hou_ke")
        self.assertEqual(game.boards[0][1]["card_id"], "dian_zhen")
        self.assertEqual(revived["card_id"], "art_h038a")
        self.assertEqual(revived["durability"], 2)
        self.assertTrue(revived["sick"])
        self.assertEqual(revived["attachments"], [])
        with self.assertRaises(ClashError) as again:
            game.support(0)
        self.assertEqual(again.exception.code, "already_used_ability")
        self.assertEqual(game.supply[0], 3)
        with self.assertRaises(ClashError) as lateral:
            game.promote(0, "art_h038b")
        self.assertEqual(lateral.exception.code, "no_growth")

        motion = Game.empty(cards)
        motion.supply = [3, 0]
        motion.hands = [["art_c004d"], []]
        host = motion.spawn(0, "dian_zhen", 0, sick=False)
        host["attachments"] = ["art_c004c"]
        motion.promote(0, "art_c004c")
        self.assertEqual(host["attachments"], ["art_c004d"])
        self.assertEqual(motion.supply[0], 1)
        self.assertFalse(host["sick"])
        self.assertEqual(motion.graves[0], ["art_c004c"])


if __name__ == "__main__":
    unittest.main()
