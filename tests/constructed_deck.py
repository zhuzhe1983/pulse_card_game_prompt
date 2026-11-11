"""Playtest builder for 30-card simulated decks.

The fixed lesson does not use this. Card stats are not changed here.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

KNOWN_EFFECTS = {None, "support", "knob", "play_draw", "play_damage"}
DECK_SIZE = 30
MAX_COPIES = 2
MIN_MAINS = 21
MAX_ATTACHMENTS = 6
ATTACHMENT_TARGET = 4
SERVICE_IDS = ("uiflow_blocks", "ezdata_note", "aiflow_say")
ROOT = Path(__file__).resolve().parents[1]
MIN_LOW_MAINS = 5
MIN_MID_MAINS = 5
MIN_HIGH_MAINS = 3
OPENING_WINDOW = 4
MIN_LOW_IN_OPENING = 2


def is_chain_top(card):
    return bool(card.get("growth_kind") == "chain" and card.get("star") and not card.get("next_template_id"))


def copy_limit(card):
    return 1 if is_chain_top(card) else MAX_COPIES


def service_cards():
    data = json.loads((ROOT / "content" / "clash_services.json").read_text(encoding="utf-8"))
    by_id = {card["template_id"]: card for card in data["cards"]}
    return [by_id[template_id] for template_id in SERVICE_IDS]


def eligible_cards(cards):
    picked = []
    seen = set()
    for card in list(cards) + service_cards():
        template_id = card.get("template_id")
        if not template_id or template_id in seen:
            continue
        if template_id in SERVICE_IDS:
            picked.append(card)
            seen.add(template_id)
            continue
        if card.get("kind") not in ("main", "attachment"):
            continue
        if card.get("effect") not in KNOWN_EFFECTS:
            continue
        picked.append(card)
        seen.add(template_id)
    return picked


def _take(rng, buckets, key, count, used):
    chosen = []
    pool = [card for card in buckets[key] if used[card["template_id"]] < copy_limit(card)]
    rng.shuffle(pool)
    for card in pool:
        if len(chosen) >= count:
            break
        used[card["template_id"]] += 1
        chosen.append(card["template_id"])
    return chosen


def required_host_family(card):
    mount = card.get("mount_class")
    if mount == "hat":
        return "stick"
    if mount == "module":
        return "core"
    if mount in ("base", "unit"):
        return "atom"
    if mount == "chain":
        return "any"
    return None


def deck_has_host(deck, by_id, family):
    mains = [by_id[item] for item in deck if by_id[item]["kind"] == "main"]
    if family == "any":
        return bool(mains)
    return any(card.get("host_family") == family for card in mains)


def _take_hosted(rng, cards, count, used, deck, by_id):
    chosen = []
    pool = [card for card in cards if used[card["template_id"]] < copy_limit(card)]
    rng.shuffle(pool)
    for card in pool:
        if len(chosen) >= count:
            break
        family = required_host_family(card)
        if family is None or not deck_has_host(deck + chosen, by_id, family):
            continue
        used[card["template_id"]] += 1
        chosen.append(card["template_id"])
    return chosen


def build_simulated_deck(cards, seed):
    """Return 30 template ids. `seed` is an int. The caller builds each seat separately."""
    rng = random.Random(seed)
    pool = eligible_cards(cards)
    by_id = {card["template_id"]: card for card in pool}
    buckets = {
        "low_main": [card for card in pool if card["kind"] == "main" and card["cost"] <= 2],
        "mid_main": [card for card in pool if card["kind"] == "main" and 3 <= card["cost"] <= 5],
        "high_main": [card for card in pool if card["kind"] == "main" and card["cost"] >= 6],
        "attachment": [card for card in pool if card["kind"] == "attachment"],
        "main": [card for card in pool if card["kind"] == "main"],
    }
    used = {card["template_id"]: 0 for card in pool}
    deck = []
    deck += _take(rng, buckets, "low_main", MIN_LOW_MAINS, used)
    deck += _take(rng, buckets, "mid_main", MIN_MID_MAINS, used)
    deck += _take(rng, buckets, "high_main", MIN_HIGH_MAINS, used)
    mains = sum(by_id[item]["kind"] == "main" for item in deck)
    if mains < MIN_MAINS:
        deck += _take(rng, buckets, "main", MIN_MAINS - mains, used)
    for template_id in SERVICE_IDS:
        if used[template_id] < 1:
            used[template_id] += 1
            deck.append(template_id)
    deck += _take_hosted(rng, buckets["attachment"], ATTACHMENT_TARGET, used, deck, by_id)
    while len(deck) < DECK_SIZE:
        added = _take(rng, buckets, "main", 1, used)
        if not added and sum(by_id[item]["kind"] == "attachment" for item in deck) < MAX_ATTACHMENTS:
            added = _take_hosted(rng, buckets["attachment"], 1, used, deck, by_id)
        if not added:
            break
        deck += added
    if len(deck) != DECK_SIZE:
        raise ValueError("牌池不足")
    window = [item for item in deck[:OPENING_WINDOW] if by_id[item]["cost"] <= 2]
    if len(window) < MIN_LOW_IN_OPENING:
        later = [index for index in range(OPENING_WINDOW, len(deck)) if by_id[deck[index]]["cost"] <= 2]
        early = [index for index in range(OPENING_WINDOW) if by_id[deck[index]]["cost"] > 2]
        for late, slot in zip(later, early):
            if len([item for item in deck[:OPENING_WINDOW] if by_id[item]["cost"] <= 2]) >= MIN_LOW_IN_OPENING:
                break
            deck[slot], deck[late] = deck[late], deck[slot]
    return deck


def build_simulated_pair(cards, seed):
    """Two decks from the same pool. Neither builder receives the other deck."""
    return build_simulated_deck(cards, seed), build_simulated_deck(cards, seed + 1)
