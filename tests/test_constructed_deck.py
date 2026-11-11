"""30-card simulated decks stay inside the playtest limits."""
import json
import unittest
from collections import Counter
from pathlib import Path

from clash_walk import Game, load_cards
from constructed_deck import (
    DECK_SIZE,
    MAX_ATTACHMENTS,
    MIN_MAINS,
    SERVICE_IDS,
    build_simulated_deck,
    build_simulated_pair,
    copy_limit,
    deck_has_host,
    eligible_cards,
    is_chain_top,
    required_host_family,
)

ROOT = Path(__file__).resolve().parents[1]


def roster_cards():
    data = json.loads((ROOT / "content" / "clash_roster_96.json").read_text(encoding="utf-8"))
    return data["cards"]


class ConstructedDeckTests(unittest.TestCase):
    def test_pair_is_reproducible_and_independent(self):
        cards = roster_cards()
        first, second = build_simulated_pair(cards, 20261111)
        again = build_simulated_pair(cards, 20261111)
        self.assertEqual((first, second), again)
        self.assertNotEqual(first, second)
        self.assertEqual(len(first), DECK_SIZE)
        self.assertEqual(len(second), DECK_SIZE)

    def test_limits_curve_and_opening(self):
        cards = roster_cards()
        by_id = {card["template_id"]: card for card in eligible_cards(cards)}
        for seed in range(1, 21):
            for seat_seed in (seed, seed + 1):
                deck = build_simulated_deck(cards, seat_seed)
                counts = Counter(deck)
                for template_id, count in counts.items():
                    self.assertLessEqual(count, copy_limit(by_id[template_id]))
                    if is_chain_top(by_id[template_id]):
                        self.assertLessEqual(count, 1)
                mains = [by_id[template_id] for template_id in deck if by_id[template_id]["kind"] == "main"]
                attachments = [template_id for template_id in deck if by_id[template_id]["kind"] == "attachment"]
                for template_id in SERVICE_IDS:
                    self.assertGreaterEqual(counts[template_id], 1)
                self.assertGreaterEqual(len(mains), MIN_MAINS)
                self.assertLessEqual(len(attachments), MAX_ATTACHMENTS)
                self.assertGreater(len(mains), len(attachments))
                for template_id in attachments:
                    family = required_host_family(by_id[template_id])
                    self.assertIsNotNone(family)
                    self.assertTrue(deck_has_host(deck, by_id, family), template_id)
                self.assertGreaterEqual(sum(card["cost"] <= 2 for card in mains), 5)
                self.assertGreaterEqual(sum(3 <= by_id[template_id]["cost"] <= 5 for template_id in deck), 5)
                self.assertGreaterEqual(sum(by_id[template_id]["cost"] >= 6 for template_id in deck), 3)
                opening = deck[:4]
                self.assertGreaterEqual(sum(by_id[template_id]["cost"] <= 2 for template_id in opening), 2)

    def test_lesson_stays_short_and_constructed_hand_limit_is_10(self):
        spec = (ROOT / "docs" / "20_POINTER_AND_MODES.md").read_text(encoding="utf-8")
        self.assertIn("固定教学仍用 8 张写死牌库", spec)
        self.assertIn("备用电池", spec)
        play = json.loads((ROOT / "content" / "clash_playtest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(play["decks"]["first"]), 8)
        self.assertEqual(play["hand_limit"], 8)
        cards = load_cards(play)
        burned = Game.empty(cards)
        burned.hand_limit = 10
        burned.decks[0] = ["bu_ji"]
        burned.hands[0] = ["gan_rao"] * 10
        burned.draw(0)
        self.assertEqual(len(burned.hands[0]), 10)
        self.assertEqual(burned.graves[0], ["bu_ji"])
        tired = Game.empty(cards)
        tired.decks[0] = []
        tired.bases[0] = 20
        tired.draw(0)
        tired.draw(0)
        self.assertEqual(tired.bases[0], 17)


if __name__ == "__main__":
    unittest.main()
