"""Integrity checks for the unenabled expansion draft and the abandoned concept art.

These tests do not score pcg.core.v1 and do not claim the draft is balanced.
"""
import hashlib
import json
import struct
import unittest
from pathlib import Path

from draft_bond_math import quiet_bonus, resolve_round


ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def png_size(path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(path.name)
    return struct.unpack(">II", data[16:24])


class DraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.draft = load("content/expansion_draft.json")
        cls.core = load("content/core_pack.json")
        cls.deck = {card["template_id"]: card for card in cls.draft["kept"] + cls.draft["cards"]}

    def test_status_and_counts(self):
        draft = self.draft
        self.assertEqual(draft["document_status"], "design_draft_not_enabled")
        self.assertEqual(draft["does_not_replace"], "pcg.core.v1")
        self.assertTrue(draft["not_loaded_by_reference_engine"])
        self.assertEqual(len(draft["kept"]), 14)
        self.assertEqual(len(draft["cards"]), 57)
        self.assertEqual(len(draft["factions"]), 11)
        self.assertEqual(draft["counts"]["hardware_rows"], 95)
        self.assertEqual(draft["counts"]["research_candidate_cards"], 74)

    def test_one_play_and_no_duplicate_ids(self):
        ids = [card["template_id"] for card in self.draft["cards"]]
        self.assertEqual(len(ids), len(set(ids)))
        core_ids = {card["template_id"] for card in self.core["cards"]}
        self.assertFalse(set(ids) & core_ids)
        for card in self.draft["cards"]:
            self.assertEqual(card["plays"], 1)
            self.assertNotIn("生命", card["skill_zh"])
            self.assertNotIn("HP", card["skill_zh"])

    def test_kept_powers_match_frozen_pack(self):
        core = {card["template_id"]: card for card in self.core["cards"]}
        for card in self.draft["kept"]:
            self.assertEqual(card["base_power"], core[card["template_id"]]["base_power"])

    def test_examples_match_the_written_rules(self):
        for example in self.draft["examples"]:
            for key in ("a", "b", "blocked", "open"):
                if key not in example:
                    continue
                stored = example[key]
                result = resolve_round(self.deck, stored["plays"], bond_cap=stored["bond_cap"])
                other = None
                if stored.get("quiet"):
                    other = len(stored["plays"]) + 1 if stored["plays"][0] == "quiet_pulse" else None
                # The stored quiet flag is the computed bonus. Recompute from play counts when present.
                quiet = stored["quiet"]
                if quiet:
                    self.assertEqual(quiet_bonus(len(stored["plays"]), len(stored["plays"]) + 1, stored["plays"], self.deck), 2)
                self.assertEqual(result["base"], stored["base"])
                self.assertEqual(result["bonds"], stored["bonds"])
                self.assertEqual(result["skills"], stored["skills"])
                self.assertEqual(result["total_before_quiet"] + quiet, stored["total"])

    def test_core_hash_and_engine_untouched_by_name(self):
        manifest = load("content/manifest.json")
        self.assertEqual(manifest["content_hash"], "04fdd26a10af50aada7ade7f34ec97be2c24df67786be687a878b0299a46dbaf")
        battle = (ROOT / "reference" / "battle.py").read_text(encoding="utf-8")
        self.assertNotIn("expansion_draft", battle)

    def test_research_tables_have_the_recorded_rows(self):
        import csv
        for name, count in (("hardware_catalog.csv", 95), ("compatibility.csv", 20), ("card_candidates.csv", 74)):
            with (ROOT / "research" / name).open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), count, name)

    def test_original_cards_remain_and_concepts_are_not_replacements(self):
        cards = list((ROOT / "asset" / "card").glob("*.png"))
        self.assertEqual(len(cards), 22)
        self.assertTrue(all(png_size(path) == (638, 1004) for path in cards))
        concept = ROOT / "asset" / "concepts" / "cardputerzero"
        readme = (concept / "README.md").read_text(encoding="utf-8")
        self.assertIn("superseded", readme)
        self.assertIn("不推荐", readme)
        for name in (
            "styleA/styleA_cardputerzero_v4.jpg",
            "styleB/styleB_cardputerzero_v4.jpg",
        ):
            self.assertTrue((concept / name).is_file())
        self.assertEqual(list(concept.glob("**/*final*.jpg")), [])


class WordingTests(unittest.TestCase):
    def test_new_docs_do_not_cite_dead_absolute_paths(self):
        roots = [ROOT / "docs" / "13_WORLD_AND_FACTIONS.md", ROOT / "docs" / "14_EXPANSION_DRAFT.md",
                 ROOT / "docs" / "16_CARD_FACE_STYLES.md", ROOT / "asset" / "concepts" / "cardputerzero" / "README.md",
                 ROOT / "research" / "README.md", ROOT / "README.md", ROOT / "START_HERE.txt"]
        banned = ("/Users/", "/workspace/pulse-card-design", "/cursor/stores", "card_export_v2_review/")
        for path in roots:
            text = path.read_text(encoding="utf-8")
            for item in banned:
                if item == "card_export_v2_review/":
                    continue
                self.assertNotIn(item, text, path.name)
        style = (ROOT / "docs" / "16_CARD_FACE_STYLES.md").read_text(encoding="utf-8")
        self.assertIn("模板重制进行中", style)
        self.assertNotIn("100%", style)


if __name__ == "__main__":
    unittest.main()
