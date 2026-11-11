"""Chain formation, upper link, service spells, and seize."""
import json
import unittest
from pathlib import Path

from clash_walk import ClashError, Game, load_cards

ROOT = Path(__file__).resolve().parents[1]


def payload():
    return json.loads((ROOT / "content" / "clash_playtest.json").read_text(encoding="utf-8"))


def services():
    return json.loads((ROOT / "content" / "clash_services.json").read_text(encoding="utf-8"))


def roster_cards():
    data = json.loads((ROOT / "content" / "clash_roster_96.json").read_text(encoding="utf-8"))
    return {card["template_id"]: card for card in data["cards"]}


def table():
    cards = load_cards(payload())
    extra = services()
    for card in extra["cards"] + extra["design_hosts"]:
        cards[card["template_id"]] = card
    roster = roster_cards()
    for template_id in ("art_h050", "art_h018"):
        cards[template_id] = roster[template_id]
    chain = next(
        card for card in roster.values()
        if card.get("chain_piece") and card["kind"] == "attachment" and not card["grants_guard"]
    )
    cards[chain["template_id"]] = chain
    cards["art_h024"] = roster["art_h024"]
    cards["zero_atk"] = dict(cards["xiao_yin"], template_id="zero_atk", name="零攻", attack=0)
    return cards, chain["template_id"]


def arena():
    cards, chain_id = table()
    game = Game.empty(cards)
    game.phase = "main"
    game.seat = 0
    game.supply = [10, 10]
    game.max_supply = [8, 8]
    return game, chain_id


class FormationTests(unittest.TestCase):
    def test_leader_percent_and_low_attack_ceil(self):
        game, _chain = arena()
        game.spawn(0, "dian_zhen", sick=False)
        attack, parts = game.profile(0, game.units(0)[0])
        self.assertEqual(attack, 1)
        self.assertNotIn("最左主控", [item[0] for item in parts])
        game.attack(0, "dian_zhen", "base")
        self.assertEqual(game.bases[1], 19)

    def test_zero_attack_stays_zero(self):
        game, _chain = arena()
        game.spawn(0, "zero_atk", sick=False)
        game.attack(0, "zero_atk", "base")
        self.assertEqual(game.bases[1], 20)

    def test_chain_bonus_is_integer_and_a_break_cuts_the_tail(self):
        game, chain_id = arena()
        game.spawn(0, "qiao_jian", sick=False)
        game.hands[0] = [chain_id, chain_id, chain_id]
        game.play(0, chain_id, "qiao_jian")
        host = game.units(0)[0]
        self.assertFalse(host["attachment_meta"][0]["ready"])
        self.assertEqual(game.profile(0, host)[0], 5)
        host["attachment_meta"][0]["ready"] = True
        bonus = game.cards[chain_id]["attack_bonus"]
        self.assertEqual(game.profile(0, host)[0], 5 + bonus)
        with self.assertRaises(ClashError) as full:
            game.play(0, chain_id, "qiao_jian")
        self.assertEqual(full.exception.code, "chain_slot_full")
        game.spawn(1, "xiao_yin", sick=False)
        game.seat = 1
        game.attack(1, "xiao_yin", host["attachment_meta"][0]["iid"])
        self.assertEqual(host["attachments"], [])
        self.assertEqual(game.profile(0, host)[0], 5)
        self.assertIn(chain_id, game.graves[0])

    def test_three_links_and_counter_uses_defender_formation(self):
        game, chain_id = arena()
        game.spawn(0, "xiao_yin", sick=False)
        game.spawn(0, "qiao_jian", sick=False)
        game.spawn(0, "hou_ke", sick=False)
        game.hands[0] = [chain_id, chain_id, chain_id]
        game.play(0, chain_id, "xiao_yin")
        game.play(0, chain_id, "qiao_jian")
        game.play(0, chain_id, "hou_ke")
        self.assertNotIn("最左主控", [item["source"] for item in game.view()["boards"][0][0]["breakdown"]])
        game.spawn(1, "art_h024", sick=False)
        game.attack(0, "xiao_yin", "art_h024")
        self.assertEqual(game.units(1), [])
        self.assertNotIn("xiao_yin", [unit["card_id"] for unit in game.units(0)])

    def test_fixed_spell_ignores_percent(self):
        game, _chain = arena()
        game.spawn(0, "qiao_jian", sick=False)
        game.spawn(1, "hou_ke", sick=False)
        game.hands[0] = ["gan_rao"]
        game.play(0, "gan_rao", "hou_ke")
        self.assertEqual(game.units(1)[0]["durability"], 3)


class UpperLinkTests(unittest.TestCase):
    def test_connect_aura_does_not_stack_or_reprint(self):
        game, _chain = arena()
        upper = game.spawn(0, "art_h050", sick=False)
        esp = game.spawn(0, "qiao_jian", sick=False)
        other = game.spawn(0, "xiao_yin", sick=False)
        game.spawn(0, "cm4_stack", sick=False)
        game.upper_link(0, "art_h050", "qiao_jian")
        self.assertEqual(game.supply[0], 9)
        self.assertEqual(len(game.upper_links[0]), 1)
        game.supply[0] = 10
        game.upper_link(0, "cm4_stack", "xiao_yin")
        self.assertEqual(game.supply[0], 9)
        game.attack(0, "qiao_jian", "base")
        self.assertEqual(game.bases[1], 14)
        before = game.view()
        with self.assertRaises(ClashError) as again:
            game.upper_link(0, "art_h050", "xiao_yin")
        self.assertEqual(again.exception.code, "already_used_ability")
        self.assertEqual(game.view(), before)
        other["durability"] = 0
        game.check_deaths()
        self.assertEqual(len(game.upper_links[0]), 1)
        upper["durability"] = 0
        game.check_deaths()
        self.assertEqual(game.upper_links[0], [])
        self.assertEqual(game.supply[0], 8)

    def test_illegal_types_are_atomic(self):
        game, chain_id = arena()
        game.spawn(0, "art_h018", sick=False)
        game.spawn(0, "art_h050", sick=False)
        game.spawn(0, "qiao_jian", sick=False)
        game.spawn(1, "xiao_yin", sick=False)
        game.hands[0] = [chain_id]
        game.play(0, chain_id, "qiao_jian")
        accessory = game.units(0)[2]["attachment_meta"][0]["iid"]
        before = game.view()
        for source, target in (
            ("art_h018", "qiao_jian"),
            ("art_h050", "art_h018"),
            ("art_h050", "xiao_yin"),
            ("art_h050", "art_h050"),
            ("art_h050", accessory),
        ):
            with self.assertRaises(ClashError) as bad:
                game.upper_link(0, source, target)
            self.assertEqual(bad.exception.code, "bad_target")
            self.assertEqual(game.view(), before)
        game.supply[0] = 0
        before = game.view()
        with self.assertRaises(ClashError) as poor:
            game.upper_link(0, "art_h050", "qiao_jian")
        self.assertEqual(poor.exception.code, "not_enough_supply")
        self.assertEqual(game.view(), before)

    def test_reconnect_same_turn_does_not_grant_supply_again(self):
        game, _chain = arena()
        game.max_supply = [4, 4]
        game.supply = [4, 4]
        upper = game.spawn(0, "cm4_stack", sick=False)
        target = game.spawn(0, "art_h024", sick=False)
        game.upper_link(0, upper["iid"], target["iid"])
        self.assertEqual(game.supply[0], 4)
        target["durability"] = 0
        game.check_deaths()
        self.assertEqual(game.supply[0], 4)
        game.supply[0] = 4
        game.spawn(0, "qiao_jian", sick=False)
        game.upper_link(0, "cm4_stack", "qiao_jian")
        self.assertEqual(game.supply[0], 3)
        self.assertEqual(game.upper_links[0][0]["source"], upper["iid"])


class ServiceTests(unittest.TestCase):
    def test_three_services_and_combo_order(self):
        game, _chain = arena()
        game.decks[0] = ["hou_ke"]
        game.hands[0] = ["uiflow_blocks", "ezdata_note", "aiflow_say", "gan_rao"]
        game.play(0, "uiflow_blocks")
        self.assertEqual(game.hands[0][-1], "hou_ke")
        self.assertIn("uiflow_blocks", game.graves[0])
        game.play(0, "ezdata_note")
        self.assertIn("uiflow_blocks", game.hands[0])
        self.assertNotIn("uiflow_blocks", game.graves[0])
        game.graves[0] = []
        game.hands[0] = ["ezdata_note"]
        game.supply[0] = 2
        game.play(0, "ezdata_note")
        self.assertEqual(game.graves[0], ["ezdata_note"])
        game.hands[0] = ["aiflow_say", "aiflow_say"]
        game.supply[0] = 8
        game.spawn(0, "xiao_yin", sick=False)
        game.play(0, "aiflow_say")
        before = game.view()
        with self.assertRaises(ClashError) as armed:
            game.play(0, "aiflow_say")
        self.assertEqual(armed.exception.code, "already_used_ability")
        self.assertEqual(game.view(), before)
        game.attack(0, "xiao_yin", "base")
        self.assertEqual(game.bases[1], 16)
        self.assertFalse(game.aiflow_armed[0])
        game.hands[0] = ["aiflow_say", "gan_rao"]
        game.supply[0] = 8
        game.spawn(1, "hou_ke", sick=False)
        game.play(0, "aiflow_say")
        game.play(0, "gan_rao", "hou_ke")
        self.assertEqual(game.units(1)[0]["durability"], 3)
        self.assertTrue(game.aiflow_armed[0])
        game.end_turn(0)
        self.assertFalse(game.aiflow_armed[0])


class SeizeTests(unittest.TestCase):
    def test_seize_moves_control_and_keeps_state(self):
        game, chain_id = arena()
        game.hands[0] = ["burner_seize"]
        foe = game.spawn(1, "qiao_jian", sick=False)
        foe["durability"] = 2
        game.hands[1] = [chain_id]
        game.spawn(1, "art_h050", sick=False)
        game.seat = 1
        game.play(1, chain_id, "qiao_jian")
        game.upper_link(1, "art_h050", "qiao_jian")
        game.seat = 0
        before_dur = foe["durability"]
        game.play(0, "burner_seize", "qiao_jian")
        self.assertEqual(game.supply[0], 3)
        self.assertEqual([unit["card_id"] for unit in game.units(0)], ["qiao_jian"])
        moved = game.units(0)[0]
        self.assertEqual(moved["durability"], before_dur)
        self.assertEqual(moved["attachments"], [chain_id])
        self.assertTrue(moved["sick"])
        self.assertTrue(moved["ability_lock"])
        self.assertFalse(game.boards[0][-1].get("link"))
        self.assertNotIn("最左主控", [item["source"] for item in game.view()["boards"][0][0]["breakdown"]])
        self.assertEqual(game.upper_links[1], [])
        with self.assertRaises(ClashError) as sick:
            game.attack(0, "qiao_jian", "base")
        self.assertEqual(sick.exception.code, "summoning_sickness")
        self.assertIn("burner_seize", game.graves[0])
        moved["durability"] = 0
        game.check_deaths()
        self.assertEqual(game.graves[0][-2:], [chain_id, "qiao_jian"])
        self.assertNotIn("qiao_jian", game.graves[1])

    def test_illegal_seize_is_atomic_and_leader_can_be_taken(self):
        game, chain_id = arena()
        game.hands[0] = ["burner_seize", "burner_seize", "burner_seize"]
        game.spawn(0, "xiao_yin", sick=False)
        leader = game.spawn(1, "art_h050", sick=False)
        game.hands[1] = [chain_id]
        game.seat = 1
        game.play(1, chain_id, "art_h050")
        game.seat = 0
        accessory = game.units(1)[0]["attachment_meta"][0]["iid"]
        before = game.view()
        with self.assertRaises(ClashError):
            game.play(0, "burner_seize", "base")
        with self.assertRaises(ClashError):
            game.play(0, "burner_seize", accessory)
        with self.assertRaises(ClashError):
            game.play(0, "burner_seize", "xiao_yin")
        self.assertEqual(game.view(), before)
        game.play(0, "burner_seize", leader["iid"])
        self.assertEqual(game.units(0)[-1]["card_id"], "art_h050")
        self.assertEqual(game.units(1), [])
        self.assertEqual(game.supply[0], 3)

    def test_seized_shell_returns_to_current_controller(self):
        game, _chain = arena()
        game.hands[0] = ["burner_seize"]
        game.spawn(0, "xiao_yin", sick=False)
        game.spawn(1, "xiao_yin", sick=False)
        game.spawn(1, "hou_ke", sick=False)
        game.play(0, "burner_seize", "hou_ke")
        seized = next(unit for unit in game.units(0) if unit["card_id"] == "hou_ke")
        seized["durability"] = 0
        seized["sick"] = False
        game.check_deaths()
        game.ability_used[0]["support"] = 1
        before = game.supply[0]
        with self.assertRaises(ClashError) as used:
            game.support(0)
        self.assertEqual(used.exception.code, "already_used_ability")
        self.assertEqual(game.supply[0], before)
        game.ability_used[0] = {}
        game.support(0)
        self.assertEqual(game.units(0)[0]["card_id"], "hou_ke")
        self.assertEqual(game.units(0)[0]["durability"], 5)
        game.seat = 1
        with self.assertRaises(ClashError) as missing:
            game.support(1)
        self.assertEqual(missing.exception.code, "no_shell_in_grave")


class ServiceRosterSplitTests(unittest.TestCase):
    def test_services_are_not_hardware_cards(self):
        data = services()
        roster = roster_cards()
        self.assertEqual(len(roster), 96)
        self.assertTrue({"uiflow_blocks", "ezdata_note", "aiflow_say", "burner_seize"}.isdisjoint(roster))
        for card in data["cards"] + data["design_hosts"]:
            self.assertIsNone(card["trusted_sku"])
            self.assertIsNone(card["artwork"])
        zero = roster["art_h050"]
        self.assertEqual((zero["cost"], zero["attack"], zero["durability"]), (10, 4, 7))
        self.assertTrue(zero["upper_host"])
        core = roster["art_h018"]
        self.assertNotIn("upper_host", core)
        play = payload()
        by_id = {card["template_id"]: card for card in play["cards"]}
        self.assertEqual(by_id["lian_jie"]["attack_bonus"], 1)
        self.assertEqual(by_id["xiao_yin"]["cost"], 1)
        self.assertEqual(by_id["hou_ke"]["cost"], 6)
        self.assertTrue(by_id["lian_jie"]["chain_piece"])


if __name__ == "__main__":
    unittest.main()
