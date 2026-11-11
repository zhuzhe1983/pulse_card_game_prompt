"""Series cost curve: bare modules stay cheap, complete machines do not."""
import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def roster():
    return json.loads((ROOT / "content" / "clash_roster_96.json").read_text(encoding="utf-8"))


def playtest():
    return json.loads((ROOT / "content" / "clash_playtest.json").read_text(encoding="utf-8"))


class CostCurveTests(unittest.TestCase):
    def test_every_cost_from_one_to_ten_has_a_card(self):
        counts = Counter(card["cost"] for card in roster()["cards"])
        for cost in range(1, 11):
            self.assertGreaterEqual(counts[cost], 2, cost)
        self.assertNotIn(0, counts)

    def test_stamp_modules_are_one_and_machines_are_not(self):
        by_rid = {card["rid"]: card for card in roster()["cards"]}
        modules = ["H038", "H038b", "H038c", "H039a", "H039b", "H039c", "H039e", "H039f"]
        for rid in modules:
            card = by_rid[rid]
            self.assertEqual(card["cost_band"], "series_core")
            self.assertEqual(card["cost_line"], "stamp_core")
            self.assertEqual(card["cost"], 1)
            self.assertLessEqual(card["attack"], 1)
        self.assertEqual(by_rid["H038a"]["cost"], 2)
        machine = by_rid["H041"]
        self.assertEqual(machine["official_product_name_en"], "StamPLC")
        self.assertEqual(machine["cost_band"], "series_machine")
        self.assertGreaterEqual(machine["cost"], 6)
        self.assertNotIn("StampFly", {card["official_product_name_en"] for card in by_rid.values()})

    def test_atom_and_stick_cores_stay_on_their_tier(self):
        for card in roster()["cards"]:
            if card["cost_line"] == "atom_core" and card.get("star") != 2:
                self.assertEqual(card["cost"], 2, card["rid"])
            if card["cost_line"] == "stick_core":
                self.assertEqual(card["cost"], 3, card["rid"])
                self.assertEqual(card["cost_band"], "series_core")

    def test_named_ladder_and_uncertain_machines(self):
        by_rid = {card["rid"]: card for card in roster()["cards"]}
        self.assertEqual(by_rid["H003"]["cost"], 4)
        self.assertEqual(by_rid["H005"]["cost"], 5)
        self.assertEqual(by_rid["H010"]["cost"], 6)
        self.assertEqual(by_rid["H013"]["cost"], 7)
        self.assertEqual(by_rid["H034"]["cost"], 8)
        self.assertEqual(by_rid["H031"]["cost"], 9)
        self.assertEqual(by_rid["H015"]["cost"], 10)
        self.assertEqual(by_rid["H050"]["cost"], 10)
        self.assertTrue(by_rid["H050"]["upper_host"])
        self.assertNotIn("upper_host", by_rid["H018"])
        for rid in ("H016", "H017", "H018", "H036", "H037"):
            self.assertEqual(by_rid[rid]["series_confidence"], "uncertain")
            self.assertEqual(by_rid[rid]["cost_band"], "series_machine")
        self.assertEqual(by_rid["H004"]["cost_line"], "core_kit")
        self.assertEqual(by_rid["H004"]["cost"], 5)
        self.assertEqual(by_rid["H033a"]["cost"], 10)

    def test_promote_diff_is_one_and_baseline_matches(self):
        cards = roster()["cards"]
        by_id = {card["template_id"]: card for card in cards}
        for card in cards:
            nxt = card.get("next_template_id")
            if not nxt:
                continue
            self.assertEqual(max(1, by_id[nxt]["cost"] - card["cost"]), 1, card["rid"])
        base = {card["template_id"]: card for card in playtest()["cards"]}
        for card in cards:
            linked = card.get("baseline_template_id")
            if not linked:
                continue
            src = base[linked]
            for key in ("cost", "attack", "durability", "guard", "effect"):
                self.assertEqual(card[key], src[key], card["rid"] + key)
        self.assertEqual(base["xi_tiao"]["cost"], 3)
        self.assertEqual(base["xiao_yin"]["amount"], 1)
        self.assertEqual(base["hou_ke"]["durability"], 7)

    def test_accessories_keep_a_one_cost_tier(self):
        parts = [card for card in roster()["cards"] if card["kind"] == "attachment"]
        self.assertGreaterEqual(sum(card["cost"] == 1 for card in parts), 8)
        for card in parts:
            self.assertEqual(card["cost_band"], "accessory")
            self.assertIn(card["cost"], (1, 2))


if __name__ == "__main__":
    unittest.main()
