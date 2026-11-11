"""Host slots for Hat, Chain, Module, Base and Unit."""
import json
import unittest
from pathlib import Path

from clash_walk import ClashError, Game, choose_trial_action

ROOT = Path(__file__).resolve().parents[1]


def cards():
    data = json.loads((ROOT / "content" / "clash_roster_96.json").read_text(encoding="utf-8"))
    return {card["template_id"]: card for card in data["cards"]}


def board(supply, hand, hosts):
    game = Game.empty(cards())
    game.supply = [supply, 0]
    game.hands = [list(hand), []]
    for template_id in hosts:
        game.spawn(0, template_id, sick=False)
    return game


class MountRuleTests(unittest.TestCase):
    def test_family_slots_and_atom_buses(self):
        hat = board(2, ["art_a001", "art_a002"], ["art_h024"])
        hat.play(0, "art_a001", "art_h024")
        before = hat.view()
        with self.assertRaises(ClashError) as full:
            hat.play(0, "art_a002", "art_h024")
        self.assertEqual(full.exception.code, "hat_slot_full")
        self.assertEqual(hat.view(), before)
        wrong = board(1, ["art_a001"], ["xiao_yin"])
        before = wrong.view()
        with self.assertRaises(ClashError) as host:
            wrong.play(0, "art_a001", "xiao_yin")
        self.assertEqual(host.exception.code, "wrong_host")
        self.assertIn("Hat", str(host.exception))
        self.assertEqual(wrong.view(), before)

        module = board(4, ["art_s001a"], ["art_h003"])
        module.play(0, "art_s001a", "art_h003")
        self.assertEqual(module.units(0)[0]["attachments"], ["art_s001a"])
        stuck = board(4, ["art_s001a"], ["art_h024"])
        with self.assertRaises(ClashError) as mod:
            stuck.play(0, "art_s001a", "art_h024")
        self.assertEqual(mod.exception.code, "wrong_host")

        base = board(2, ["art_c004c", "art_c004h"], ["dian_zhen"])
        base.play(0, "art_c004c", "dian_zhen")
        before = base.view()
        with self.assertRaises(ClashError) as second_base:
            base.play(0, "art_c004h", "dian_zhen")
        self.assertEqual(second_base.exception.code, "base_slot_full")
        self.assertEqual(base.view(), before)

        unit = board(8, ["art_u002a", "art_u002a"], ["dian_zhen"])
        unit.play(0, "art_u002a", "dian_zhen")
        before = unit.view()
        with self.assertRaises(ClashError) as second_unit:
            unit.play(0, "art_u002a", "dian_zhen")
        self.assertEqual(second_unit.exception.code, "unit_slot_full")
        self.assertEqual(unit.view(), before)

        widened = board(13, ["art_c004a", "art_u002a", "art_u002a", "art_u002a"], ["dian_zhen"])
        widened.play(0, "art_c004a", "dian_zhen")
        widened.play(0, "art_u002a", "dian_zhen")
        widened.play(0, "art_u002a", "dian_zhen")
        self.assertEqual(widened.units(0)[0]["attachments"].count("art_u002a"), 2)
        before = widened.view()
        with self.assertRaises(ClashError) as third:
            widened.play(0, "art_u002a", "dian_zhen")
        self.assertEqual(third.exception.code, "unit_slot_full")
        self.assertEqual(widened.view(), before)

    def test_chain_bus_is_capped_and_atom_needs_to_chain(self):
        bare = board(1, ["art_c002c"], ["dian_zhen"])
        before = bare.view()
        with self.assertRaises(ClashError) as need:
            bare.play(0, "art_c002c", "dian_zhen")
        self.assertEqual(need.exception.code, "need_to_chain")
        self.assertEqual(bare.view(), before)

        stamp = board(2, ["art_c002c", "art_c002c"], ["xiao_yin"])
        stamp.play(0, "art_c002c", "xiao_yin")
        before = stamp.view()
        with self.assertRaises(ClashError) as occupied:
            stamp.play(0, "art_c002c", "xiao_yin")
        self.assertEqual(occupied.exception.code, "chain_slot_full")
        self.assertEqual(stamp.view(), before)

        bus = board(7, ["art_c003"] + ["art_c002c"] * 6, ["dian_zhen"])
        bus.play(0, "art_c003", "dian_zhen")
        for _ in range(6):
            bus.play(0, "art_c002c", "dian_zhen")
        host = bus.units(0)[0]
        self.assertEqual(host["attachments"].count("art_c002c"), 6)
        self.assertEqual(bus.profile(0, host)[0], 2)
        for meta in host["attachment_meta"]:
            meta["ready"] = True
        self.assertEqual(bus.profile(0, host)[0], 14)
        bus.spawn(1, "xiao_yin", sick=False)
        bus.seat = 1
        bus.attack(1, "xiao_yin", host["attachment_meta"][3]["iid"])
        self.assertTrue(host["attachment_meta"][3]["severed"])
        self.assertEqual(bus.profile(0, host)[0], 6)

    def test_same_series_neighbors_stack_and_drop_when_split(self):
        game = board(0, [], [])
        left = game.spawn(0, "art_h024", sick=False)
        right = game.spawn(0, "art_h022", sick=False)
        self.assertEqual(left["durability"], game.cards["art_h024"]["durability"] + 1)
        self.assertEqual(right["durability"], game.cards["art_h022"]["durability"] + 1)
        attack, parts = game.profile(0, left)
        self.assertEqual(attack, game.cards["art_h024"]["attack"] + 2)
        self.assertIn(("右邻同系", 1, 1), parts)
        _attack, right_parts = game.profile(0, right)
        self.assertIn(("左邻同系", 1, 1), right_parts)
        third = game.spawn(0, "art_h023", sick=False)
        self.assertEqual(right["series_durability"], 2)
        self.assertEqual(right["durability"], game.cards["art_h022"]["durability"] + 2)
        _attack, mid_parts = game.profile(0, right)
        self.assertIn(("左邻同系", 1, 1), mid_parts)
        self.assertIn(("右邻同系", 1, 1), mid_parts)
        for unit in (left, right, third):
            unit["durability"] = 0
        game.check_deaths()
        self.assertEqual(game.units(0), [])

    def test_trial_opponent_plays_a_main_before_an_attachment(self):
        game = board(4, ["art_a001", "xiao_yin"], ["art_h024"])
        game.hands[1] = ["art_h015"]
        choice = choose_trial_action(game, 0)
        self.assertEqual(choice, {"do": "play", "card": "xiao_yin"})
        game.hands[0] = ["art_a001"]
        attached = choose_trial_action(game, 0)
        self.assertEqual(attached["do"], "play")
        self.assertEqual(attached["card"], "art_a001")
        self.assertNotIn("art_h015", str(attached))


if __name__ == "__main__":
    unittest.main()
