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
    def test_cost_counts_leave_room_in_the_middle(self):
        counts = Counter(card["cost"] for card in roster()["cards"])
        self.assertLessEqual(counts[1], 24)
        self.assertLessEqual(counts[2], 22)
        self.assertGreaterEqual(counts[3] + counts[4] + counts[5], 25)
        self.assertEqual(counts[1], 24)
        self.assertEqual(counts[2], 21)
        self.assertEqual(counts[3] + counts[4] + counts[5], 34)

    def test_stamp_modules_are_one_and_machines_are_not(self):
        by_rid = {card["rid"]: card for card in roster()["cards"]}
        modules = ["H038", "H038b", "H038c", "H039a", "H039b", "H039c", "H039e", "H039f"]
        for rid in modules:
            card = by_rid[rid]
            self.assertEqual(card["cost_band"], "series_core")
            self.assertEqual(card["cost_line"], "stamp_core")
            self.assertEqual(card["cost"], 1)
            if card.get("chip_tier") == "entry":
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
        self.assertEqual(by_rid["H016"]["cost"], 3)
        self.assertTrue(by_rid["H016"]["guard"])
        self.assertEqual(by_rid["H017"]["cost"], 5)
        self.assertTrue(by_rid["H017"]["guard"])
        self.assertGreaterEqual(by_rid["H017"]["durability"], 7)
        self.assertEqual(by_rid["H036"]["cost"], 2)
        self.assertEqual(by_rid["H036a"]["cost"], 3)
        self.assertEqual(by_rid["H037"]["cost"], 2)
        self.assertEqual(by_rid["H037a"]["cost"], 3)
        self.assertEqual(by_rid["H036"]["series_confidence"], "official")
        self.assertEqual(by_rid["H037"]["series_confidence"], "official")
        self.assertEqual(by_rid["H018"]["series_confidence"], "uncertain")
        for rid in ("H016", "H017", "H018", "H036", "H037"):
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
            diff = max(1, by_id[nxt]["cost"] - card["cost"])
            self.assertGreaterEqual(diff, 1, card["rid"])
            if card["kind"] == "main":
                self.assertEqual(diff, 1, card["rid"])
        self.assertEqual(by_id["art_c004d"]["cost"] - by_id["art_c004c"]["cost"], 2)
        base = {card["template_id"]: card for card in playtest()["cards"]}
        for card in cards:
            linked = card.get("baseline_template_id")
            if not linked:
                continue
            src = base[linked]
            for key in ("cost", "attack", "durability", "guard", "effect"):
                self.assertEqual(card[key], src[key], card["rid"] + key)
        self.assertNotIn("xi_tiao", base)
        roster_by = {card["template_id"]: card for card in roster()["cards"]}
        self.assertEqual(roster_by["art_h024"]["cost"], 3)
        self.assertEqual(roster_by["art_h024"]["attack"], 3)
        self.assertEqual(roster_by["art_h024"]["durability"], 2)
        self.assertIsNone(roster_by["art_h024"]["effect"])
        decks = playtest()["decks"]
        self.assertIn("art_h024", decks["first"])
        self.assertIn("art_h024", decks["second"])
        self.assertEqual(base["xiao_yin"]["amount"], 1)
        self.assertEqual(base["hou_ke"]["durability"], 5)

    def test_accessories_keep_a_one_cost_tier(self):
        parts = [card for card in roster()["cards"] if card["kind"] == "attachment"]
        self.assertGreaterEqual(sum(card["cost"] == 1 for card in parts), 8)
        for card in parts:
            self.assertEqual(card["cost_band"], "accessory")
            self.assertIn(card["cost"], (1, 2, 3, 4, 5))
        self.assertGreaterEqual(sum(card["cost"] >= 3 for card in parts), 12)


if __name__ == "__main__":
    unittest.main()
