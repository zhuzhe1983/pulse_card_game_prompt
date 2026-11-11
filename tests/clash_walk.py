"""Tabletop walker for the pcg.clash.v0 playtest.

This is not the frozen pcg.core.v1 judge and not a networked client.
It only exists so the written examples can be replayed in order.
"""
from __future__ import annotations

from copy import deepcopy


class ClashError(Exception):
    def __init__(self, message, code="rejected"):
        super().__init__(message)
        self.code = code


def attack_of(card, unit):
    bonus = sum(card[item]["attack_bonus"] for item in unit["attachments"])
    return card[unit["card_id"]]["attack"] + bonus + unit["temp_attack"]


def has_guard(card, unit):
    if card[unit["card_id"]]["guard"]:
        return True
    return any(card[item]["grants_guard"] for item in unit["attachments"])


def bypass_guard(card, unit):
    return any(card[item]["bypass_guard"] for item in unit["attachments"])


def support_cost(card):
    amount = card.get("effect_amount")
    if not amount:
        amount = card.get("amount") or 1
    return amount


class Game:
    @classmethod
    def empty(cls, cards):
        game = cls.__new__(cls)
        game.cards = cards
        game.bases = [20, 20]
        game.max_supply = [0, 0]
        game.supply = [0, 0]
        game.fatigue = [0, 0]
        game.decks = [[], []]
        game.hands = [[], []]
        game.boards = [[], []]
        game.graves = [[], []]
        game.ability_used = [{}, {}]
        game.promote_ban = [set(), set()]
        game.upper_links = [[], []]
        game.upper_pulsed = [False, False]
        game.aiflow_armed = [False, False]
        game.seat = 0
        game.turns_started = [1, 0]
        game.phase = "main"
        game.winner = None
        game.log = []
        game._next_id = 1
        return game

    def _reindex(self, seat):
        for index, unit in enumerate(self.boards[seat]):
            unit["slot"] = index

    def spawn(self, seat, card_id, index=None, durability=None, sick=False):
        card = self.cards[card_id]
        unit = {
            "iid": f"u{self._next_id}",
            "card_id": card_id,
            "seat": seat,
            "slot": 0,
            "durability": card["durability"] if durability is None else durability,
            "sick": sick,
            "attacked": False,
            "temp_attack": 0,
            "attachments": [],
            "ability_lock": False,
        }
        self._next_id += 1
        if index is None:
            self.boards[seat].append(unit)
        elif 0 <= index <= len(self.boards[seat]):
            self.boards[seat].insert(index, unit)
        else:
            raise ClashError("插入位置不存在", "bad_index")
        self._reindex(seat)
        return unit
    def __init__(self, cards, deck0, deck1):
        self.cards = cards
        self.bases = [20, 20]
        self.max_supply = [0, 0]
        self.supply = [0, 0]
        self.fatigue = [0, 0]
        self.decks = [list(deck0), list(deck1)]
        self.hands = [[], []]
        self.boards = [[], []]
        self.graves = [[], []]
        self.ability_used = [{}, {}]
        self.promote_ban = [set(), set()]
        self.upper_links = [[], []]
        self.upper_pulsed = [False, False]
        self.aiflow_armed = [False, False]
        self.seat = 0
        self.turns_started = [0, 0]
        self.phase = "opening"
        self.winner = None
        self.log = []
        self._next_id = 1
        for _ in range(3):
            self._opening_draw(0)
        for _ in range(4):
            self._opening_draw(1)
        self.hands[1].append("jie_yi_ge_dian")
        self.log.append("起手：先手3张，后手4张，后手获得借一格电")

    def _opening_draw(self, seat):
        if not self.decks[seat]:
            raise ClashError("起手时牌库不够")
        self.hands[seat].append(self.decks[seat].pop(0))

    def event(self, text):
        self.log.append(text)

    def units(self, seat):
        return [unit for unit in self.boards[seat] if not unit.get("link")]

    def _is_chain(self, card_id):
        card = self.cards[card_id]
        return bool(card.get("chain_piece"))

    def _is_esp32_main(self, card_id):
        card = self.cards[card_id]
        if card.get("upper_host") or card.get("kind") != "main":
            return False
        if card.get("esp32_main"):
            return True
        text = " ".join(card.get("official_main_chips") or [])
        return card.get("hardware_controller") == "independent_host" and "ESP32" in text

    def _is_upper_host(self, card_id):
        return bool(self.cards[card_id].get("upper_host"))

    def formation_state(self, seat):
        line = self.boards[seat]
        if not line or line[0].get("link") or self.cards[line[0]["card_id"]].get("kind") != "main":
            return {"leader": False, "chain_run": 0, "percent": 0}
        run = 0
        for entry in line[1:]:
            if entry.get("link") and self._is_chain(entry["card_id"]):
                run += 1
            else:
                break
        return {"leader": True, "chain_run": run, "percent": 10 + 5 * run}

    def strike_damage(self, seat, attack_value):
        if attack_value <= 0:
            return 0
        boosted = attack_value
        if self.upper_links[seat]:
            boosted += 1
        if self.aiflow_armed[seat]:
            boosted += 2
            self.aiflow_armed[seat] = False
        percent = self.formation_state(seat)["percent"]
        return (boosted * (100 + percent) + 99) // 100

    def _effective_max(self, seat):
        bonus = 1 if self.upper_links[seat] else 0
        return min(10, self.max_supply[seat] + bonus)

    def _drop_upper_links(self, iid):
        for seat in (0, 1):
            kept = [link for link in self.upper_links[seat]
                    if link["source"] != iid and link["target"] != iid]
            if len(kept) != len(self.upper_links[seat]):
                self.upper_links[seat] = kept
                if not kept:
                    self.supply[seat] = min(self.supply[seat], self.max_supply[seat])

    def _place_link(self, seat, card_id, host_iid, index=None):
        link = {
            "iid": f"u{self._next_id}",
            "card_id": card_id,
            "seat": seat,
            "slot": 0,
            "durability": 1,
            "sick": False,
            "attacked": False,
            "temp_attack": 0,
            "attachments": [],
            "ability_lock": False,
            "link": True,
            "host_iid": host_iid,
        }
        self._next_id += 1
        if index is None:
            self.boards[seat].append(link)
        else:
            self.boards[seat].insert(index, link)
        self._reindex(seat)
        self.event(f"链节标记放到座位{seat}位置{link['slot']}")
        return link

    def _remove_links(self, seat, host_iid):
        self.boards[seat] = [
            unit for unit in self.boards[seat]
            if not (unit.get("link") and unit.get("host_iid") == host_iid)
        ]
        self._reindex(seat)

    def _seize_unit(self, seat, foe):
        old = foe["seat"]
        links = [entry for entry in self.boards[old] if entry.get("link") and entry.get("host_iid") == foe["iid"]]
        for entry in links:
            self.boards[old].remove(entry)
        self.boards[old].remove(foe)
        self._reindex(old)
        foe["seat"] = seat
        foe["sick"] = True
        foe["ability_lock"] = True
        self.boards[seat].append(foe)
        for entry in links:
            entry["seat"] = seat
            self.boards[seat].append(entry)
        self._reindex(seat)
        self._drop_upper_links(foe["iid"])
        self.event(f"夺舍，{self.cards[foe['card_id']]['name']}改由座位{seat}控制，排到最右，本回合不能攻击")

    def upper_link(self, seat, source_id, target_id):
        self.require_main(seat)
        source_iid = self.resolve_iid(seat, source_id)
        target_iid = self.resolve_iid(seat, target_id)
        source_seat, _slot, source = self.find(source_iid)
        target_seat, _slot, target = self.find(target_iid)
        if source_seat != seat or source.get("link") or not self._is_upper_host(source["card_id"]):
            raise ClashError("来自上位的爱只能由己方上位机发动", "bad_target")
        if source.get("ability_lock"):
            raise ClashError("这台单位本回合不能发动技能", "seized_this_turn")
        if target_seat != seat or target.get("link") or not self._is_esp32_main(target["card_id"]):
            raise ClashError("只能连到己方的 ESP32 主控", "bad_target")
        if source_iid == target_iid:
            raise ClashError("不能连自己", "bad_target")
        if any(item["source"] == source_iid for item in self.upper_links[seat]):
            raise ClashError("这台上位机已经连着", "already_used_ability")
        if any(item["target"] == target_iid for item in self.upper_links[seat]):
            raise ClashError("这台主控已经连着上位机", "already_used_ability")
        if self.supply[seat] < 1:
            raise ClashError("供电不足", "not_enough_supply")
        self.pay(seat, 1)
        was_empty = not self.upper_links[seat]
        self.upper_links[seat].append({"source": source_iid, "target": target_iid})
        if was_empty and not self.upper_pulsed[seat]:
            self.supply[seat] = min(10, self.supply[seat] + 1)
            self.upper_pulsed[seat] = True
        self.supply[seat] = min(self.supply[seat], self._effective_max(seat))
        self.event("来自上位的爱接上")

    def alive_count(self, seat):
        return len(self.units(seat))

    def find(self, iid):
        for seat in (0, 1):
            for slot, unit in enumerate(self.boards[seat]):
                if unit is not None and unit["iid"] == iid:
                    return seat, slot, unit
        raise ClashError("场上没有这张单位")

    def require_main(self, seat):
        if self.winner is not None:
            raise ClashError("对局已经结束", "game_over")
        if self.phase != "main" or self.seat != seat:
            raise ClashError("还没轮到这一方的主阶段", "not_your_turn")

    def start_turn(self):
        if self.winner is not None:
            raise ClashError("对局已经结束", "game_over")
        if self.phase not in ("opening", "between"):
            raise ClashError("回合开始只能接在开局或上一回合结束之后", "bad_phase")
        seat = self.seat
        self.phase = "start"
        self.turns_started[seat] += 1
        self.ability_used[seat] = {}
        self.promote_ban[seat] = set()
        self.upper_pulsed[seat] = False
        for unit in self.units(seat):
            unit["ability_lock"] = False
        first_opening = seat == 0 and self.turns_started[seat] == 1
        if first_opening:
            self.event(f"座位{seat}回合开始：先手第1回合不抽牌")
        else:
            self.event(f"座位{seat}回合开始：抽牌")
            self.draw(seat)
            if self.winner is not None:
                return
        for unit in self.units(seat):
            unit["sick"] = False
            unit["attacked"] = False
        self.event(f"座位{seat}场上原有单位解除新入场限制")
        self.max_supply[seat] = min(10, self.max_supply[seat] + 1)
        self.supply[seat] = self._effective_max(seat)
        self.phase = "main"
        self.event(f"座位{seat}供电上限{self.max_supply[seat]}，当前供电回满")

    def draw(self, seat):
        if self.decks[seat]:
            card_id = self.decks[seat].pop(0)
            if len(self.hands[seat]) >= 8:
                self.graves[seat].append(card_id)
                self.event(f"座位{seat}手牌已满，{self.cards[card_id]['name']}展示后进入墓地")
            else:
                self.hands[seat].append(card_id)
                self.event(f"座位{seat}抽到{self.cards[card_id]['name']}")
            return
        self.fatigue[seat] += 1
        self.bases[seat] = max(0, self.bases[seat] - self.fatigue[seat])
        self.event(f"座位{seat}疲劳{self.fatigue[seat]}，基地变为{self.bases[seat]}")
        self.check_bases()

    def pay(self, seat, amount):
        if self.supply[seat] < amount:
            raise ClashError("供电不足", "not_enough_supply")
        self.supply[seat] -= amount

    def take_hand(self, seat, card_id):
        try:
            self.hands[seat].remove(card_id)
        except ValueError as exc:
            raise ClashError("手牌里没有这张牌", "not_in_hand") from exc

    def place_new(self, seat, card_id, index=None, sick=True):
        if index is not None and not (0 <= index <= len(self.boards[seat])):
            raise ClashError("插入位置不存在", "bad_index")
        unit = {
            "iid": f"u{self._next_id}",
            "card_id": card_id,
            "seat": seat,
            "slot": 0,
            "durability": self.cards[card_id]["durability"],
            "sick": sick,
            "attacked": False,
            "temp_attack": 0,
            "attachments": [],
            "ability_lock": False,
        }
        self._next_id += 1
        if index is None:
            self.boards[seat].append(unit)
        else:
            self.boards[seat].insert(index, unit)
        self._reindex(seat)
        note = "本回合不能攻击" if sick else "本回合可以攻击"
        self.event(f"座位{seat}{self.cards[card_id]['name']}进入位置{unit['slot']}，{note}")
        return unit

    def resolve_iid(self, seat, ref):
        if isinstance(ref, str) and ref.startswith("u") and ref[1:].isdigit():
            self.find(ref)
            return ref
        found = [unit["iid"] for unit in self.units(seat) if unit["card_id"] == ref]
        if len(found) != 1:
            raise ClashError("无法唯一确定单位", "bad_target")
        return found[0]

    def play(self, seat, card_id, target=None, mode=None, index=None):
        self.require_main(seat)
        card = self.cards[card_id]
        if card_id not in self.hands[seat]:
            raise ClashError("手牌里没有这张牌", "not_in_hand")
        if self.supply[seat] < card["cost"]:
            raise ClashError("供电不足", "not_enough_supply")
        kind = card["kind"]
        host = None
        if kind == "main":
            if index is not None and not (0 <= index <= len(self.boards[seat])):
                raise ClashError("插入位置不存在", "bad_index")
            if card.get("effect") == "play_damage" and target is not None:
                self.find(self.resolve_iid(1 - seat, target))
        elif kind == "attachment":
            if card.get("chain_piece") and index is not None and not (0 <= index <= len(self.boards[seat])):
                raise ClashError("插入位置不存在", "bad_index")
            if target is None:
                raise ClashError("配件必须指定己方主控", "bad_target")
            host_seat, _slot, host = self.find(self.resolve_iid(seat, target))
            if host_seat != seat:
                raise ClashError("配件只能装在己方主控上", "bad_target")
            if len(host["attachments"]) >= 1:
                raise ClashError("这台主控已经有配件", "already_has_attachment")
            if card["grants_guard"] and has_guard(self.cards, host):
                raise ClashError("这台主控已经有护卫", "already_has_guard")
        elif kind == "spell":
            self.prepare_spell(seat, card, target, mode)
        else:
            raise ClashError("未知卡种")
        self.pay(seat, card["cost"])
        self.take_hand(seat, card_id)
        if kind == "main":
            unit = self.place_new(seat, card_id, index=index, sick=not card.get("rush"))
            if card.get("effect") == "play_draw":
                self.draw(seat)
            elif card.get("effect") == "play_damage" and target is not None:
                foe = self.find(self.resolve_iid(1 - seat, target))[2]
                amount = card.get("effect_amount") or card.get("amount") or 1
                foe["durability"] = max(0, foe["durability"] - amount)
                self.event(f"入场打击，{self.cards[foe['card_id']]['name']}耐久变为{foe['durability']}")
        elif kind == "attachment":
            host["attachments"].append(card_id)
            self.event(f"{card['name']}装到{self.cards[host['card_id']]['name']}上")
            if card.get("chain_piece"):
                self._place_link(seat, card_id, host["iid"], index=index)
        else:
            self.cast_spell(seat, card, target, mode)
            self.graves[seat].append(card_id)
            self.event(f"{card['name']}进入墓地")
        self.check_deaths()
        self.check_bases()

    def prepare_spell(self, seat, card, target, mode):
        effect = card["effect"]
        if effect in ("supply", "heal_base", "draw_one", "retrieve_grave"):
            return
        if effect == "arm_aiflow":
            if self.aiflow_armed[seat]:
                raise ClashError("说人话还没用掉", "already_used_ability")
            return
        if effect == "seize":
            if target is None or target == "base":
                raise ClashError("夺舍只能指定敌方场上的主控", "bad_target")
            foe_seat, _slot, foe = self.find(self.resolve_iid(1 - seat, target))
            if foe_seat == seat or foe.get("link") or self.cards[foe["card_id"]].get("kind") != "main":
                raise ClashError("夺舍只能指定敌方场上的主控", "bad_target")
            return
        if effect == "damage":
            if target is None:
                raise ClashError("干扰必须指定敌方单位", "bad_target")
            host_seat, _slot, _host = self.find(self.resolve_iid(1 - seat, target))
            if host_seat == seat:
                raise ClashError("干扰只能指定敌方单位", "bad_target")
        elif effect == "mend":
            if target is None:
                raise ClashError("补给必须指定己方单位", "bad_target")
            self.find(self.resolve_iid(seat, target))
            if mode not in ("heal", "temp"):
                raise ClashError("补给要选择修复或临时强化", "bad_target")
        else:
            raise ClashError("未知战术")

    def cast_spell(self, seat, card, target, mode):
        effect = card["effect"]
        if effect == "supply":
            self.supply[seat] += card["amount"]
            self.event(f"当前供电变为{self.supply[seat]}")
        elif effect == "heal_base":
            before = self.bases[seat]
            self.bases[seat] = min(20, self.bases[seat] + card["amount"])
            self.event(f"座位{seat}基地从{before}变为{self.bases[seat]}")
        elif effect == "damage":
            _host_seat, _slot, host = self.find(self.resolve_iid(1 - seat, target))
            host["durability"] = max(0, host["durability"] - card["amount"])
            self.event(f"{self.cards[host['card_id']]['name']}耐久变为{host['durability']}")
        elif effect == "mend":
            host_seat, _slot, host = self.find(self.resolve_iid(seat, target))
            if host_seat != seat:
                raise ClashError("补给只能指定己方单位")
            if mode == "heal":
                cap = self.cards[host["card_id"]]["durability"]
                host["durability"] = min(cap, host["durability"] + card["amount"])
                self.event(f"{self.cards[host['card_id']]['name']}耐久变为{host['durability']}")
            elif mode == "temp":
                host["temp_attack"] += 1
                self.event(f"{self.cards[host['card_id']]['name']}本回合攻击变为{attack_of(self.cards, host)}")
            else:
                raise ClashError("补给要选择修复或临时强化")
        elif effect == "draw_one":
            self.draw(seat)
        elif effect == "retrieve_grave":
            if not self.graves[seat]:
                self.event("墓地是空的，记一笔没有取回")
            else:
                recovered = self.graves[seat].pop()
                if len(self.hands[seat]) >= 8:
                    self.graves[seat].append(recovered)
                    self.event("手牌已满，记一笔没有取回")
                else:
                    self.hands[seat].append(recovered)
                    self.event(f"记一笔取回{self.cards[recovered]['name']}")
        elif effect == "arm_aiflow":
            self.aiflow_armed[seat] = True
            self.event("说人话：本回合下一次打击在百分比之前攻击+2")
        elif effect == "seize":
            foe = self.find(self.resolve_iid(1 - seat, target))[2]
            self._seize_unit(seat, foe)
        else:
            raise ClashError("未知战术")

    def support(self, seat):
        """小印支援：把墓地里的厚壳工控复活到空位。小印自己留在场上。"""
        self.require_main(seat)
        all_sources = [unit for unit in self.units(seat) if self.cards[unit["card_id"]].get("effect") == "support"]
        sources = [unit for unit in all_sources if not unit.get("ability_lock")]
        if not sources:
            if all_sources:
                raise ClashError("这台小印本回合不能支援", "seized_this_turn")
            raise ClashError("场上要有一台小印才能支援", "no_stamp_on_board")
        if self.ability_used[seat].get("support"):
            raise ClashError("本回合已经支援过", "already_used_ability")
        if "hou_ke" not in self.graves[seat] or "hou_ke" in self.promote_ban[seat]:
            raise ClashError("墓地里没有可支援的厚壳工控", "no_shell_in_grave")
        if self.supply[seat] < support_cost(self.cards[sources[0]["card_id"]]):
            raise ClashError("供电不足", "not_enough_supply")
        self.pay(seat, support_cost(self.cards[sources[0]["card_id"]]))
        self.ability_used[seat]["support"] = 1
        self.graves[seat].remove("hou_ke")
        self.event("小印支援，厚壳工控离开墓地")
        revived = self.place_new(seat, "hou_ke", index=0, sick=True)
        return revived

    def promote_cost(self, current_id, next_id):
        current = self.cards[current_id]
        nxt = self.cards[next_id]
        return max(1, nxt["cost"] - current["cost"])

    def promote(self, seat, current_id):
        """把场上的这一星换成手牌里的下一星。没有降星。"""
        self.require_main(seat)
        current = self.cards.get(current_id)
        if current is None or not current.get("next_template_id"):
            raise ClashError("这张牌没有下一星", "no_growth")
        next_id = current["next_template_id"]
        nxt = self.cards[next_id]
        if current.get("growth_kind") != "chain" or nxt.get("growth_family") != current.get("growth_family"):
            raise ClashError("这张牌没有下一星", "no_growth")
        if nxt.get("star") != current.get("star") + 1:
            raise ClashError("星级没有接上", "no_growth")
        if next_id not in self.hands[seat]:
            raise ClashError("手牌里没有下一星", "not_in_hand")
        found = None
        for unit in self.units(seat):
            if unit["card_id"] == current_id:
                found = ("main", unit)
                break
            if current_id in unit["attachments"]:
                found = ("attachment", unit)
                break
        if found is None:
            raise ClashError("场上没有这一星", "bad_target")
        kind, unit = found
        if kind == "attachment" and nxt.get("grants_guard") and self.cards[unit["card_id"]].get("guard"):
            raise ClashError("这台主控已经有护卫", "already_has_guard")
        cost = self.promote_cost(current_id, next_id)
        if self.supply[seat] < cost:
            raise ClashError("供电不足", "not_enough_supply")
        self.pay(seat, cost)
        self.take_hand(seat, next_id)
        if kind == "main":
            self._drop_upper_links(unit["iid"])
            self._remove_links(seat, unit["iid"])
            slot = unit["slot"]
            for attachment in list(unit["attachments"]):
                self.graves[seat].append(attachment)
                self.event(f"{self.cards[attachment]['name']}随升星进入墓地")
            self.boards[seat].pop(slot)
            self.graves[seat].append(current_id)
            self.promote_ban[seat].add(current_id)
            self.event(f"{current['name']}升星退役，进入墓地")
            self.place_new(seat, next_id, index=slot, sick=True)
        else:
            unit["attachments"].remove(current_id)
            self.graves[seat].append(current_id)
            self.promote_ban[seat].add(current_id)
            unit["attachments"].append(next_id)
            for entry in self.boards[seat]:
                if entry.get("link") and entry.get("host_iid") == unit["iid"] and entry["card_id"] == current_id:
                    entry["card_id"] = next_id
            self.event(f"{current['name']}升成{nxt['name']}，仍装在原宿主上")
        self.check_deaths()
        self.check_bases()

    def knob(self, seat, host_id, target):
        self.require_main(seat)
        host_id = self.resolve_iid(seat, host_id)
        target = self.resolve_iid(seat, target)
        host_seat, _slot, host = self.find(host_id)
        if host_seat != seat or self.cards[host["card_id"]].get("effect") != "knob":
            raise ClashError("只有己方旋钮台能调这一下", "bad_target")
        if host.get("ability_lock"):
            raise ClashError("这台单位本回合不能发动技能", "seized_this_turn")
        if self.ability_used[seat].get("knob"):
            raise ClashError("本回合旋钮已经用过", "already_used_ability")
        ally_seat, _slot, ally = self.find(target)
        if ally_seat != seat:
            raise ClashError("旋钮只能强化己方单位", "bad_target")
        if self.supply[seat] < 1:
            raise ClashError("供电不足", "not_enough_supply")
        self.pay(seat, 1)
        self.ability_used[seat]["knob"] = 1
        ally["temp_attack"] += 1
        self.event(f"旋钮台让{self.cards[ally['card_id']]['name']}本回合攻击变为{attack_of(self.cards, ally)}")

    def attack(self, seat, attacker_id, target):
        self.require_main(seat)
        attacker_id = self.resolve_iid(seat, attacker_id)
        atk_seat, _slot, attacker = self.find(attacker_id)
        if atk_seat != seat:
            raise ClashError("不能操作对方的单位", "bad_target")
        if attacker.get("link"):
            raise ClashError("链节标记不能攻击", "bad_target")
        if attacker["sick"]:
            raise ClashError("新入场的单位本回合不能攻击", "summoning_sickness")
        if attacker["attacked"]:
            raise ClashError("这台单位本回合已经攻击过", "already_attacked")
        guards = [unit for unit in self.units(1 - seat) if has_guard(self.cards, unit)]
        if target == "base":
            if guards and not bypass_guard(self.cards, attacker):
                raise ClashError("对方有护卫时只能攻击护卫", "guard_blocks")
            attacker["attacked"] = True
            damage = self.strike_damage(seat, attack_of(self.cards, attacker))
            self.bases[1 - seat] = max(0, self.bases[1 - seat] - damage)
            self.event(f"{self.cards[attacker['card_id']]['name']}攻击基地，对方基地变为{self.bases[1 - seat]}")
            self.check_bases()
            return
        def_seat, _slot, defender = self.find(self.resolve_iid(1 - seat, target))
        if def_seat == seat:
            raise ClashError("不能攻击己方单位", "bad_target")
        if defender.get("link"):
            raise ClashError("不能攻击链节标记", "bad_target")
        if guards and defender not in guards and not bypass_guard(self.cards, attacker):
            raise ClashError("对方有护卫时只能攻击护卫", "guard_blocks")
        attacker["attacked"] = True
        atk_damage = self.strike_damage(seat, attack_of(self.cards, attacker))
        def_damage = self.strike_damage(1 - seat, attack_of(self.cards, defender))
        attacker["durability"] = max(0, attacker["durability"] - def_damage)
        defender["durability"] = max(0, defender["durability"] - atk_damage)
        self.event(
            f"{self.cards[attacker['card_id']]['name']}与{self.cards[defender['card_id']]['name']}同时结算，"
            f"耐久变为{attacker['durability']}和{defender['durability']}"
        )
        self.check_deaths()

    def check_deaths(self):
        dead = []
        for seat in (0, 1):
            for unit in self.boards[seat]:
                if not unit.get("link") and unit["durability"] <= 0:
                    dead.append(unit)
        for unit in dead:
            seat = unit["seat"]
            if unit not in self.boards[seat]:
                continue
            self._drop_upper_links(unit["iid"])
            self._remove_links(seat, unit["iid"])
            for attachment in unit["attachments"]:
                self.graves[seat].append(attachment)
                self.event(f"{self.cards[attachment]['name']}随宿主进入墓地")
            self.graves[seat].append(unit["card_id"])
            self.boards[seat].remove(unit)
            self._reindex(seat)
            self.event(f"{self.cards[unit['card_id']]['name']}进入座位{seat}墓地")

    def check_bases(self):
        fallen = [seat for seat, life in enumerate(self.bases) if life <= 0]
        if len(fallen) == 2:
            self.winner = "draw"
            self.phase = "over"
            self.event("双方基地同时倒下，平局")
        elif len(fallen) == 1:
            self.winner = 1 - fallen[0]
            self.phase = "over"
            self.event(f"座位{fallen[0]}基地倒下，座位{self.winner}获胜")

    def end_turn(self, seat):
        self.require_main(seat)
        for unit in self.units(seat):
            unit["temp_attack"] = 0
            unit["attacked"] = False
        self.supply[seat] = 0
        self.aiflow_armed[seat] = False
        self.event(f"座位{seat}回合结束，临时攻击加成清除，没用完的供电清零")
        self.seat = 1 - seat
        self.phase = "between"

    def view(self):
        def show_unit(unit):
            if unit is None:
                return None
            return {
                "iid": unit["iid"],
                "card_id": unit["card_id"],
                "durability": unit["durability"],
                "attack": attack_of(self.cards, unit),
                "sick": unit["sick"],
                "guard": has_guard(self.cards, unit),
                "attachments": list(unit["attachments"]),
            }
            if unit.get("link"):
                shown["link"] = True
                shown["host_iid"] = unit["host_iid"]
        return {
            "bases": list(self.bases),
            "supply": list(self.supply),
            "max_supply": list(self.max_supply),
            "hands": [list(hand) for hand in self.hands],
            "decks": [len(deck) for deck in self.decks],
            "boards": [[show_unit(unit) for unit in row] for row in self.boards],
            "graves": [list(grave) for grave in self.graves],
            "winner": self.winner,
            "seat": self.seat,
            "phase": self.phase,
            "formation": [self.formation_state(0), self.formation_state(1)],
            "upper_links": [list(row) for row in self.upper_links],
            "aiflow_armed": list(self.aiflow_armed),
        }


def replay(cards, deck0, deck1, steps):
    game = Game(cards, deck0, deck1)
    for step in steps:
        kind = step["do"]
        seat = step.get("seat", game.seat)
        if kind == "start":
            game.start_turn()
        elif kind == "play":
            game.play(seat, step["card"], step.get("target"), step.get("mode"), step.get("index"))
        elif kind == "support":
            game.support(seat)
        elif kind == "knob":
            game.knob(seat, step["host"], step["target"])
        elif kind == "attack":
            game.attack(seat, step["attacker"], step["target"])
        elif kind == "upper_link":
            game.upper_link(seat, step["source"], step["target"])
        elif kind == "end":
            game.end_turn(seat)
        else:
            raise ClashError(kind)
        if "expect" in step:
            actual = game.view()
            for key, value in step["expect"].items():
                if actual[key] != value:
                    raise AssertionError(f"{step['do']} {key}: {actual[key]} != {value}")
    return game


def load_cards(payload):
    cards = {}
    for card in payload["cards"]:
        cards[card["template_id"]] = card
    cards[payload["second_player_token"]["template_id"]] = payload["second_player_token"]
    return cards
