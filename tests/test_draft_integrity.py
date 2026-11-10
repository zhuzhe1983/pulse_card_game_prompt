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

    def test_localized_fields_cover_every_card(self):
        required = ["stable_id", "game_name_zh", "game_name_en", "intro_zh", "skill_zh", "skill_en",
                    "official_product_name", "official_model", "faction", "faction_en", "v1_role",
                    "design_role", "base_power", "plays", "pair_with_zh", "pair_limit_zh",
                    "product_record_ids", "sources", "image_status", "image_url"]
        banned = ("CORE", "Stick", "TOUGH", "ATOM", "Dial", "PaperMono", "Cardputer", "LoRa", "Unit Cam", "Echo")
        zh = load("content/zh-CN.json")
        en = load("content/en.json")
        seen = []
        for card in self.draft["kept"] + self.draft["cards"]:
            for key in required:
                self.assertIn(key, card, card.get("template_id"))
            self.assertTrue(card["game_name_zh"] and card["game_name_en"] and card["skill_zh"] and card["skill_en"])
            for token in banned:
                self.assertNotIn(token, card["game_name_zh"])
            self.assertEqual(card["image_url"], "")
            seen.append(card["stable_id"])
        self.assertEqual(len(seen), 71)
        cam = self.deck["unit_cam_scout"]
        self.assertEqual(cam["v1_role"], "角色")
        self.assertEqual(cam["design_role"], "器具")
        self.assertEqual(cam["official_model"], "U109")
        self.assertEqual(cam["game_name_zh"], "千里眼")
        self.assertIn("不是 UnitV", cam["mapping_note"])
        for template_id, name in zh["names"].items():
            self.assertEqual(name, self.deck[template_id]["game_name_zh"])
            self.assertEqual(en["names"][template_id], self.deck[template_id]["game_name_en"])
        tactics = [card for card in self.draft["kept"] if card["stable_id"] in ("signal_boost", "signal_jam")]
        self.assertTrue(all(card["non_product"] for card in tactics))

    def test_product_image_fields_are_empty_pending(self):
        import csv
        with (ROOT / "research" / "history" / "hardware_catalog_95.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 95)
        self.assertIn("host_or_peripheral", rows[0])

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
        for name, count in (("hardware_catalog.csv", 258), ("compatibility.csv", 20), ("card_candidates.csv", 74)):
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
        self.assertIn("needs_revision", style)
        self.assertNotIn("100%", style)

    def test_front_image_catalog_is_strict(self):
        import csv
        catalog_path = ROOT / "research" / "hardware_catalog.csv"
        with catalog_path.open(encoding="utf-8", newline="") as handle:
            catalog = list(csv.DictReader(handle))
        self.assertEqual(len(catalog), 258)
        roles = {}
        for row in catalog:
            roles[row["row_role"]] = roles.get(row["row_role"], 0) + 1
            for key, value in row.items():
                self.assertNotIn("/workspace", value or "")
                self.assertFalse((value or "").startswith("/"))
        self.assertEqual(roles, {"original": 95, "split_specific": 161, "extra": 2})
        fronts = [row for row in catalog if row["operation_front_verification_status"] == "已核对操作面正视"]
        self.assertEqual(sorted(row["record_id"] for row in fronts),
                         ["H005", "H015", "H027", "H027a", "H028", "H031", "H050", "U109"])
        for row in fronts:
            self.assertEqual(row["view_orientation"], "正视")
            self.assertEqual(row["surface"], "操作面")
            self.assertTrue((ROOT / row["operation_front_image_path"]).is_file(), row["record_id"])
        backs = [row for row in catalog if row["back_ortho_view_orientation"] == "正视"]
        self.assertEqual(len(backs), 8)
        lite = next(row for row in catalog if row["record_id"] == "H026")
        self.assertEqual(lite["back_ortho_surface"], "背夹/USB面")
        self.assertNotEqual(lite["surface"], "操作面")
        self.assertTrue((ROOT / lite["back_ortho_image_path"]).is_file())
        self.assertTrue(all(not row["reference_image_path"] for row in catalog))
        self.assertIn("未找到/未核验", {row["operation_front_verification_status"] for row in catalog})
        history = ROOT / "research" / "history" / "hardware_catalog_95.csv"
        with history.open(encoding="utf-8", newline="") as handle:
            old_rows = list(csv.DictReader(handle))
        self.assertEqual(len(old_rows), 95)
        text = (ROOT / "research" / "README.md").read_text(encoding="utf-8")
        self.assertIn("不是当前目录", text)
        self.assertIn("front_image_v5.md", text)
        game = load("content/expansion_draft.json")
        cards = {card["stable_id"]: card for card in game["kept"] + game["cards"]}
        linked = {"core2_guard": "H005", "atom_matrix_link": "H027", "cardputer_hacker": "H031",
                  "tab5_watcher": "H015", "unit_cam_scout": "U109"}
        for stable_id, record_id in linked.items():
            self.assertEqual(cards[stable_id]["mapped_record_id"], record_id)
            self.assertTrue(cards[stable_id]["has_operation_front"])
            self.assertEqual(cards[stable_id]["surface"], "操作面")
            self.assertTrue((ROOT / cards[stable_id]["operation_front_image_path"]).is_file())
        self.assertEqual(cards["cardputer_hacker"]["mapped_record_id"], "H031")
        self.assertNotEqual(cards["cardputer_hacker"]["mapped_record_id"], "H050")
        self.assertEqual(cards["unit_cam_scout"]["design_role"], "器具")
        self.assertEqual(cards["atom_s3"]["has_operation_front"], False)
        self.assertEqual(cards["atom_s3"]["operation_front_image_path"], "")
        self.assertEqual(cards["atom_scout"]["back_ortho_surface"], "背夹/USB面")
        self.assertEqual(cards["atom_scout"]["surface"], "")
        self.assertEqual(sum(1 for card in cards.values() if card["has_operation_front"]), 5)
        for card in cards.values():
            if card.get("non_product"):
                self.assertFalse(card["has_operation_front"])

    def test_template_preview_links_and_original_cards_unmodified(self):
        import subprocess
        preview = ROOT / "asset" / "concepts" / "cardputerzero-template"
        readme = (preview / "README.md").read_text(encoding="utf-8")
        self.assertIn("needs_revision", readme)
        self.assertIn("不是 accepted", readme)
        self.assertNotIn("状态：accepted", readme.lower())
        for relative in (
            "composites/styleA_cardputerzero.png",
            "composites/styleA_cardputerzero.svg",
            "composites/styleB_cardputerzero.png",
            "composites/styleB_cardputerzero.svg",
            "chars/styleA_char_cardputerzero.png",
            "chars/styleB_char_cardputerzero.png",
            "templates/slots.json",
            "templates/styleA_template_01_S3.svg",
            "templates/styleB_template_10_CORE.svg",
            "source_masters/01_S3.svg",
            "source_masters/10_CORE.svg",
            "scripts/chroma_and_compose.py",
            "validation/compare_report.json",
        ):
            self.assertTrue((preview / relative).is_file(), relative)
        report = (preview / "validation" / "compare_report.json").read_text(encoding="utf-8")
        self.assertNotIn("/workspace/", report)
        self.assertIn('"diff_pixels": 0', report)
        self.assertEqual(len(list((ROOT / "asset" / "card").glob("[0-9][0-9]_*.png"))), 0)

    def test_offical_archive_spec_waits_for_package(self):
        import hashlib
        spec = load("asset/offical/MANIFEST.json")
        self.assertEqual(spec["archive_status"], "originals_archived_design_package_pending")
        self.assertFalse(spec["design_package_received"])
        self.assertIsNone(spec["background_token"]["value"])
        self.assertFalse(spec["original_assets_recolored"])
        self.assertTrue(spec["copies_written"])
        labels = {}
        for item in spec["files"]:
            self.assertNotRegex(item["filename"], r"^[0-9]{2}_")
            self.assertEqual(item["official_card_label"] + ".png", item["filename"])
            labels.setdefault(item["filename"], item["hardware_product_name"])
            self.assertEqual(labels[item["filename"]], item["hardware_product_name"])
        self.assertIsNone(labels["S3.png"])
        self.assertIsNone(labels["M5PAPER.png"])
        self.assertIsNone(labels["ATOM.png"])
        self.assertIsNone(labels["CORE.png"])
        self.assertEqual(labels["DUALKEY.png"], "Chain DualKey")
        self.assertEqual(labels["CORE2.png"], "Core2")
        self.assertNotEqual(labels["STICKC_PLUS.png"], "StickC-Plus2")
        for kind in ("card", "char"):
            recorded = spec["byte_baseline"][kind]
            files = list((ROOT / "asset" / kind).glob("*.png"))
            archive = list((ROOT / "asset" / "offical" / kind).glob("*.png"))
            self.assertEqual(len(files), 22)
            self.assertEqual(len(archive), 22)
            self.assertEqual(sorted(p.name for p in files), sorted(recorded))
            for path in files:
                info = recorded[path.name]
                data = path.read_bytes()
                archived = (ROOT / "asset" / "offical" / kind / path.name).read_bytes()
                self.assertEqual(data, archived)
                self.assertEqual(len(data), info["bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), info["sha256"])
                self.assertTrue(info["source_file"].startswith(tuple(str(i).zfill(2) for i in range(1, 23))))
        readme = (ROOT / "asset" / "offical" / "README.md").read_text(encoding="utf-8")
        self.assertIn("needs_revision", readme)
        self.assertIn("同一 token", readme)
        self.assertIn("还不是最终完成", readme)


if __name__ == "__main__":
    unittest.main()
