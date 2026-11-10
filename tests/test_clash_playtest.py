"""Replay the pcg.clash.v0 tabletop examples.

The frozen pcg.core.v1 judge stays in reference/battle.py. These checks
cover the new single-game rules and do not retune the old golden vectors.
"""
import json
import unittest
from pathlib import Path

from clash_walk import ClashError, Game, load_cards

ROOT = Path(__file__).resolve().parents[1]


def payload():
    return json.loads((ROOT / "content" / "clash_playtest.json").read_text(encoding="utf-8"))


def new_game():
    data = payload()
    cards = load_cards(data)
    decks = data["decks"]
    return Game(cards, decks["first"], decks["second"]), cards


class ClashExampleTests(unittest.TestCase):
    def test_pack_shape_and_frozen_core_untouched(self):
        data = payload()
        self.assertEqual(data["ruleset_id"], "pcg.clash.v0")
        self.assertEqual(data["balance"], "playtest_unverified")
        self.assertIn("game_role", data["classification"])
        self.assertIn("hardware_controller", data["classification"])
        self.assertIn("art_type", data["classification"])
        by_id = {card["template_id"]: card for card in data["cards"]}
        self.assertEqual(by_id["xiao_yin"]["effect"], "support")
        self.assertIsNone(by_id["hou_ke"]["effect"])
        link = by_id["lian_jie"]
        self.assertEqual(link["game_role"], "attachment")
        self.assertEqual(link["hardware_controller"], "auxiliary_programmable_mcu")
        self.assertIsNone(link["art_type"])
        self.assertNotIn("无主控", link["hardware_note"].split("不是无主控")[0])
        self.assertEqual(len(data["cards"]), 12)
        names = [card["name"] for card in data["cards"]]
        self.assertEqual(len(names), len(set(names)))
        for card in data["cards"]:
            self.assertNotIn("Stamp", card["name"])
            self.assertNotIn("Core", card["name"])
            self.assertTrue(card["name"].isascii() is False or any("\u4e00" <= ch <= "\u9fff" for ch in card["name"]))
            if card["kind"] == "main":
                self.assertGreater(card["durability"], 0)
            if card["kind"] != "main":
                self.assertEqual(card["durability"], 0)
        mains = [card for card in data["cards"] if card["kind"] == "main"]
        self.assertGreaterEqual(len(mains), 4)
        import hashlib
        from reference.common import digest
        core_bytes = (ROOT / "content" / "core_pack.json").read_bytes()
        self.assertEqual(hashlib.sha256(core_bytes).hexdigest(),
                         "33b9c16549598bb20cdbbfdbc4ea8b1fff19409788e34b17ad94c74549e58311")
        self.assertEqual(digest(json.loads(core_bytes)),
                         "04fdd26a10af50aada7ade7f34ec97be2c24df67786be687a878b0299a46dbaf")

    def test_first_three_turns(self):
        game, _cards = new_game()
        self.assertEqual(game.hands[0], ["xi_tiao", "xiao_yin", "bu_ji"])
        self.assertEqual(game.hands[1][:4], ["xi_tiao", "hu_zhao", "xiao_yin", "gan_rao"])
        self.assertIn("jie_yi_ge_dian", game.hands[1])
        game.start_turn()
        game.play(0, "xi_tiao")
        game.end_turn(0)
        game.start_turn()
        self.assertEqual(game.hands[1][-2:], ["jie_yi_ge_dian", "dian_zhen"])
        game.play(1, "jie_yi_ge_dian")
        self.assertEqual(game.supply[1], 2)
        game.play(1, "xiao_yin")
        with self.assertRaises(ClashError):
            game.attack(1, "xiao_yin", "base")
        game.end_turn(1)
        game.start_turn()
        game.play(0, "xiao_yin")
        game.attack(0, "xi_tiao", "base")
        self.assertEqual(game.bases, [20, 19])
        with self.assertRaises(ClashError):
            game.attack(0, "xiao_yin", "base")
        game.end_turn(0)
        game.start_turn()
        game.play(1, "xi_tiao")
        game.attack(1, "xiao_yin", "xi_tiao")
        self.assertEqual(game.graves[0], ["xi_tiao"])
        self.assertEqual(game.bases, [20, 19])
        xiao = next(unit for unit in game.units(1) if unit["card_id"] == "xiao_yin")
        self.assertEqual(xiao["durability"], 1)
        game.end_turn(1)
        game.start_turn()
        game.play(0, "dian_zhen")
        game.attack(0, "xiao_yin", "xiao_yin")
        self.assertEqual(game.graves[0], ["xi_tiao", "xiao_yin"])
        self.assertEqual(game.graves[1], ["jie_yi_ge_dian", "xiao_yin"])
        self.assertEqual(game.bases, [20, 19])
        self.assertEqual([unit["card_id"] for unit in game.units(0)], ["dian_zhen"])
        self.assertEqual([unit["card_id"] for unit in game.units(1)], ["xi_tiao"])
        self.assertTrue(game.units(0)[0]["sick"])
        self.assertIsNone(game.winner)
        self.assertIn("同时结算", "\n".join(game.log))

    def test_support_already_on_board(self):
        cards = load_cards(payload())
        game = Game.empty(cards)
        game.supply = [6, 6]
        game.max_supply = [6, 6]
        game.bases = [16, 18]
        game.hands = [["bu_ji", "gan_rao"], []]
        game.graves = [["hou_ke"], []]
        game.spawn(0, "xiao_yin", 0, sick=False)
        game.spawn(1, "dian_zhen", 0)
        game.support(0)
        self.assertEqual(game.supply[0], 4)
        self.assertEqual(game.graves[0], [])
        self.assertEqual([unit["card_id"] for unit in game.units(0)], ["xiao_yin", "hou_ke"])
        shell = next(unit for unit in game.units(0) if unit["card_id"] == "hou_ke")
        stamp = next(unit for unit in game.units(0) if unit["card_id"] == "xiao_yin")
        self.assertEqual(shell["durability"], 6)
        self.assertTrue(shell["sick"])
        self.assertFalse(stamp["sick"])
        with self.assertRaises(ClashError):
            game.support(0)
        self.assertEqual(game.supply[0], 4)
        with self.assertRaises(ClashError):
            game.attack(0, "hou_ke", "dian_zhen")
        with self.assertRaises(ClashError):
            game.attack(0, "xiao_yin", "base")
        game.play(0, "bu_ji", "hou_ke", "heal")
        self.assertEqual(shell["durability"], 6)
        self.assertEqual(game.supply[0], 3)
        game.play(0, "gan_rao", "dian_zhen")
        self.assertEqual(game.units(1)[0]["durability"], 2)
        self.assertEqual(game.supply[0], 1)
        self.assertEqual([unit["card_id"] for unit in game.units(0)], ["xiao_yin", "hou_ke"])

    def test_support_after_later_deploy_and_after_shell_dies(self):
        cards = load_cards(payload())
        later = Game.empty(cards)
        later.supply = [6, 6]
        later.max_supply = [6, 6]
        later.hands = [["xiao_yin"], []]
        later.graves = [["hou_ke"], []]
        with self.assertRaises(ClashError):
            later.support(0)
        self.assertEqual(later.supply[0], 6)
        self.assertEqual(later.graves[0], ["hou_ke"])
        later.play(0, "xiao_yin")
        self.assertEqual(later.supply[0], 4)
        self.assertTrue(later.units(0)[0]["sick"])
        later.support(0)
        self.assertEqual(later.supply[0], 2)
        shell = next(unit for unit in later.units(0) if unit["card_id"] == "hou_ke")
        self.assertEqual(shell["durability"], 6)
        self.assertTrue(shell["sick"])
        with self.assertRaises(ClashError):
            later.attack(0, "hou_ke", "base")
        with self.assertRaises(ClashError):
            later.attack(0, "xiao_yin", "base")

        stayed = Game.empty(cards)
        stayed.supply = [4, 4]
        stayed.max_supply = [4, 4]
        stayed.hands = [[], ["gan_rao"]]
        stayed.spawn(0, "hou_ke", 0, durability=2)
        stayed.spawn(0, "xiao_yin", 1, sick=False)
        stayed.seat = 1
        stayed.phase = "main"
        stayed.play(1, "gan_rao", "hou_ke")
        self.assertEqual([unit["card_id"] for unit in stayed.units(0)], ["xiao_yin"])
        self.assertEqual(stayed.graves[0], ["hou_ke"])
        stayed.end_turn(1)
        stayed.seat = 0
        stayed.phase = "main"
        stayed.supply[0] = 4
        stayed.support(0)
        revived = next(unit for unit in stayed.units(0) if unit["card_id"] == "hou_ke")
        self.assertEqual([unit["card_id"] for unit in stayed.units(0)], ["hou_ke", "xiao_yin"])
        self.assertEqual(revived["slot"], 0)
        self.assertEqual(revived["durability"], 6)
        self.assertTrue(revived["sick"])
        self.assertEqual(stayed.supply[0], 2)

    def test_edges(self):
        cards = load_cards(payload())
        full = Game.empty(cards)
        full.supply = [5, 5]
        full.max_supply = [5, 5]
        for slot, card_id in enumerate(["xiao_yin", "dian_zhen", "xuan_niu", "qiao_jian", "xi_tiao"]):
            full.spawn(0, card_id, slot, sick=False)
        full.graves[0] = ["hou_ke"]
        with self.assertRaises(ClashError):
            full.support(0)
        self.assertEqual(full.supply[0], 5)
        self.assertEqual(full.graves[0], ["hou_ke"])

        guard = Game.empty(cards)
        guard.supply = [2, 2]
        guard.hands = [["hu_zhao", "qian_li"], []]
        guard.spawn(0, "dian_zhen", 0)
        with self.assertRaises(ClashError):
            guard.play(0, "hu_zhao", "dian_zhen")
        guard.play(0, "qian_li", "dian_zhen")
        guard.spawn(1, "hou_ke", 0)
        host = guard.units(0)[0]
        host["sick"] = False
        guard.attack(0, "dian_zhen", "base")
        self.assertEqual(guard.bases[1], 18)

        mend = Game.empty(cards)
        mend.supply = [1, 1]
        mend.hands = [["bu_ji"], []]
        unit = mend.spawn(0, "xiao_yin", 0, durability=1)
        mend.play(0, "bu_ji", "xiao_yin", "heal")
        self.assertEqual(unit["durability"], 2)
        mend.hands[0] = ["bu_ji"]
        mend.supply[0] = 1
        mend.play(0, "bu_ji", "xiao_yin", "temp")
        self.assertEqual(unit["temp_attack"], 1)
        mend.end_turn(0)
        self.assertEqual(unit["temp_attack"], 0)

        burn = Game.empty(cards)
        burn.decks[0] = ["xi_tiao"]
        burn.hands[0] = ["bu_ji"] * 8
        burn.draw(0)
        self.assertEqual(burn.graves[0], ["xi_tiao"])
        self.assertEqual(len(burn.hands[0]), 8)

        tired = Game.empty(cards)
        tired.bases[0] = 1
        tired.decks[0] = []
        tired.phase = "between"
        tired.seat = 0
        tired.turns_started = [1, 0]
        tired.start_turn()
        self.assertEqual(tired.winner, 1)
        self.assertEqual(tired.max_supply[0], 0)
        self.assertEqual(tired.bases[0], 0)

        link = Game.empty(cards)
        link.supply = [1, 1]
        link.hands = [["lian_jie"], []]
        host = link.spawn(0, "xiao_yin", 0, sick=False)
        link.play(0, "lian_jie", "xiao_yin")
        self.assertEqual(host["attachments"], ["lian_jie"])
        link.spawn(1, "qiao_jian", 0, sick=False)
        link.attack(0, "xiao_yin", "qiao_jian")
        self.assertEqual(link.graves[0], ["lian_jie", "xiao_yin"])
        self.assertEqual(link.units(0), [])


if __name__ == "__main__":
    unittest.main()
