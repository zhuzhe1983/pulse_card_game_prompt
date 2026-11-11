"""Playtest builder for 30-card simulated decks.

The fixed lesson does not use this. Card stats are not changed here.
"""
from __future__ import annotations

import random

KNOWN_EFFECTS = {None, "support", "knob", "play_draw", "play_damage"}
DECK_SIZE = 30
MAX_COPIES = 2
MIN_MAINS = 10
MIN_ATTACHMENTS = 5
MIN_LOW_MAINS = 5
MIN_MID_CARDS = 5
MIN_HIGH_CARDS = 3
OPENING_WINDOW = 4
MIN_LOW_IN_OPENING = 2


def is_chain_top(card):
    return bool(card.get("growth_kind") == "chain" and card.get("star") and not card.get("next_template_id"))


def copy_limit(card):
    return 1 if is_chain_top(card) else MAX_COPIES


def eligible_cards(cards):
    picked = []
    for card in cards:
        if card.get("kind") not in ("main", "attachment"):
            continue
        if card.get("effect") not in KNOWN_EFFECTS:
            continue
        if not card.get("template_id"):
            continue
        picked.append(card)
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


def build_simulated_deck(cards, seed):
    """Return 30 template ids. `seed` is an int. The caller builds each seat separately."""
    rng = random.Random(seed)
    pool = eligible_cards(cards)
    buckets = {
        "low_main": [card for card in pool if card["kind"] == "main" and card["cost"] <= 2],
        "mid": [card for card in pool if 3 <= card["cost"] <= 5],
        "high": [card for card in pool if card["cost"] >= 6],
        "attachment": [card for card in pool if card["kind"] == "attachment"],
        "main": [card for card in pool if card["kind"] == "main"],
    }
    used = {card["template_id"]: 0 for card in pool}
    deck = []
    deck += _take(rng, buckets, "low_main", MIN_LOW_MAINS, used)
    deck += _take(rng, buckets, "mid", MIN_MID_CARDS, used)
    deck += _take(rng, buckets, "high", MIN_HIGH_CARDS, used)
    deck += _take(rng, buckets, "attachment", MIN_ATTACHMENTS, used)
    mains = sum(1 for template_id in deck if any(
        card["template_id"] == template_id and card["kind"] == "main" for card in pool))
    if mains < MIN_MAINS:
        deck += _take(rng, buckets, "main", MIN_MAINS - mains, used)
    rest = []
    for card in pool:
        rest.extend([card] * (copy_limit(card) - used[card["template_id"]]))
    rng.shuffle(rest)
    for card in rest:
        if len(deck) >= DECK_SIZE:
            break
        if used[card["template_id"]] >= copy_limit(card):
            continue
        used[card["template_id"]] += 1
        deck.append(card["template_id"])
    if len(deck) != DECK_SIZE:
        raise ValueError("牌池不足")
    by_id = {card["template_id"]: card for card in pool}
    window = [template_id for template_id in deck[:OPENING_WINDOW] if by_id[template_id]["cost"] <= 2]
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
