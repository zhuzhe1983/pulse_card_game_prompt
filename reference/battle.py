"""Deterministic pcg.core.v1 reducer. No clocks, networking, UI or NFC calls."""
from __future__ import annotations

from copy import deepcopy
from .common import PCGError, digest, canonical

RULESET = "pcg.core.v1"
OPS = {"NONE", "BOOST", "DAMAGE", "SELF_BOOST_OTHER_ROW"}
TRAITS = {"shield_once", "stable"}
ROWS = {"front", "rear"}


def validate_pack(pack):
    if pack.get("ruleset_id") != RULESET:
        raise PCGError("RULESET_UNSUPPORTED")
    if set(pack.get("required_ops", [])) - OPS or set(pack.get("required_traits", [])) - TRAITS:
        raise PCGError("CONTENT_UNSUPPORTED")
    cards = pack.get("cards", [])
    ids = [c["template_id"] for c in cards]
    if len(ids) != len(set(ids)):
        raise PCGError("CONTENT_DUPLICATE_ID")
    for card in cards:
        if card["kind"] not in ("unit", "tactic") or card["effect"]["op"] not in OPS:
            raise PCGError("CONTENT_UNSUPPORTED")
        if set(card["traits"]) - TRAITS:
            raise PCGError("CONTENT_UNSUPPORTED")
        if card["kind"] == "unit":
            if not card["allowed_rows"] or set(card["allowed_rows"]) - ROWS:
                raise PCGError("CONTENT_ROW")
            if type(card["base_power"]) is not int or not 0 <= card["base_power"] <= 99:
                raise PCGError("CONTENT_POWER")
        elif card["base_power"] != 0 or card["allowed_rows"] or card["traits"]:
            raise PCGError("CONTENT_TACTIC")
        if card["effect"]["op"] in ("BOOST", "DAMAGE", "SELF_BOOST_OTHER_ROW"):
            if card["effect"].get("amount") != 2:
                raise PCGError("CONTENT_EFFECT_AMOUNT", "v1 effects have amount=2")
        elif card["effect"].get("amount") != 0:
            raise PCGError("CONTENT_EFFECT_AMOUNT")
        if card["kind"] == "tactic" and card["effect"]["op"] not in ("BOOST", "DAMAGE"):
            raise PCGError("CONTENT_TACTIC_EFFECT")
    return {c["template_id"]: c for c in cards}


def new_match(pack, match_id, player_ids, decks, seed_uint32):
    catalog = validate_pack(pack)
    if len(player_ids) != 2 or player_ids[0] == player_ids[1] or len(decks) != 2:
        raise PCGError("MATCH_PLAYERS")
    if type(seed_uint32) is not int or not 0 <= seed_uint32 <= 0xFFFFFFFF:
        raise PCGError("MATCH_SEED")
    players = []
    for seat, templates in enumerate(decks):
        if len(templates) != 10 or len(set(templates)) != 10:
            raise PCGError("DECK_SIZE_OR_DUPLICATE")
        if any(t not in catalog for t in templates):
            raise PCGError("DECK_UNKNOWN_CARD")
        if sum(catalog[t]["kind"] == "unit" for t in templates) < 6:
            raise PCGError("DECK_TOO_FEW_UNITS")
        players.append({
            "player_id": player_ids[seat],
            "hand": [{"instance_id": f"p{seat}:{i:02d}", "template_id": t}
                     for i, t in enumerate(templates)],
            "board": [], "discard": [], "played_count": 0,
            "passed": False, "match_points": 0,
        })
    return {
        "ruleset_id": RULESET, "content_hash": digest(pack), "match_id": match_id,
        "revision": 0, "round_index": 1, "phase": "playing",
        "round_starter": seed_uint32 & 1, "turn_player": seed_uint32 & 1,
        "players": players, "round_results": [], "winner": None,
        "result_reason": None,
    }


def board_scores(state):
    return [sum(u["power"] for u in p["board"]) for p in state["players"]]


def _target_candidates(state, actor, op):
    if op == "BOOST":
        return state["players"][actor]["board"]
    if op == "DAMAGE":
        return state["players"][1 - actor]["board"]
    return []


def _apply_effect(state, actor, definition, source, target_id, events):
    op = definition["effect"]["op"]
    amount = definition["effect"]["amount"]
    if op == "NONE":
        return
    if op == "SELF_BOOST_OTHER_ROW":
        if any(u["row"] != source["row"] for u in state["players"][actor]["board"]):
            if not source["stable"]:
                source["power"] += amount
                events.append({"kind": "power", "instance_id": source["instance_id"], "delta": amount})
        return
    if target_id is None:
        events.append({"kind": "effect_skipped", "source_instance_id": source["instance_id"]})
        return
    target = next(u for u in _target_candidates(state, actor, op) if u["instance_id"] == target_id)
    if target["stable"]:
        events.append({"kind": "immune", "instance_id": target_id})
    elif op == "DAMAGE" and target["shield"]:
        target["shield"] = False
        events.append({"kind": "shield_consumed", "instance_id": target_id})
    else:
        before = target["power"]
        target["power"] = max(0, before - amount) if op == "DAMAGE" else before + amount
        events.append({"kind": "power", "instance_id": target_id, "delta": target["power"] - before})


def _settle_round(state, events):
    scores = board_scores(state)
    winner = None if scores[0] == scores[1] else (0 if scores[0] > scores[1] else 1)
    awards = [1, 1] if winner is None else ([2, 0] if winner == 0 else [0, 2])
    result = {"round_index": state["round_index"], "scores": scores, "winner": winner, "awards": awards}
    state["round_results"].append(result)
    events.append({"kind": "round_ended", **deepcopy(result),
                   "final_boards": [deepcopy(p["board"]) for p in state["players"]],
                   "played_counts": [p["played_count"] for p in state["players"]],
                   "passed": [p["passed"] for p in state["players"]]})
    for seat, player in enumerate(state["players"]):
        player["match_points"] += awards[seat]
        player["discard"].extend({"instance_id": u["instance_id"], "template_id": u["template_id"]}
                                 for u in player["board"])
        player["board"] = []
    points = [p["match_points"] for p in state["players"]]
    if max(points) >= 4 or state["round_index"] == 3:
        state["phase"] = "finished"
        state["turn_player"] = None
        state["winner"] = None if points[0] == points[1] else (0 if points[0] > points[1] else 1)
        state["result_reason"] = "points"
        events.append({"kind": "match_ended", "winner": state["winner"], "match_points": points})
        return
    state["round_index"] += 1
    state["round_starter"] = 1 - state["round_starter"] if winner is None else winner
    state["turn_player"] = state["round_starter"]
    for player in state["players"]:
        player["passed"] = False
        player["played_count"] = 0


def _normalize(state, events):
    # At most three rounds can settle; no recursion or unbounded effect loop.
    while state["phase"] == "playing":
        for seat, player in enumerate(state["players"]):
            if not player["passed"] and (not player["hand"] or player["played_count"] >= 5):
                player["passed"] = True
                events.append({"kind": "auto_pass", "actor": seat})
        if all(p["passed"] for p in state["players"]):
            _settle_round(state, events)
            continue
        if state["players"][state["turn_player"]]["passed"]:
            state["turn_player"] = 1 - state["turn_player"]
        break


def apply_action(pack, current, actor, command):
    """Returns a new state and public animation events; input is never mutated."""
    catalog = validate_pack(pack)
    if digest(pack) != current["content_hash"]:
        raise PCGError("CONTENT_MISMATCH")
    required = {"match_id", "action_id", "expected_revision", "kind", "card_instance_id", "row", "target_instance_id"}
    if set(command) != required:
        raise PCGError("COMMAND_FIELDS")
    if command["match_id"] != current["match_id"]:
        raise PCGError("MATCH_MISMATCH")
    if type(command["expected_revision"]) is not int or command["expected_revision"] != current["revision"]:
        raise PCGError("STALE_REVISION")
    if current["phase"] != "playing":
        raise PCGError("MATCH_FINISHED")
    if type(actor) is not int or actor not in (0, 1) or actor != current["turn_player"]:
        raise PCGError("NOT_YOUR_TURN")
    if current["players"][actor]["passed"]:
        raise PCGError("ALREADY_PASSED")
    state = deepcopy(current)
    player = state["players"][actor]
    events = []
    if command["kind"] == "pass":
        if any(command[k] is not None for k in ("card_instance_id", "row", "target_instance_id")):
            raise PCGError("PASS_ARGUMENTS")
        player["passed"] = True
        events.append({"kind": "pass", "actor": actor})
    elif command["kind"] == "play":
        hand_card = next((c for c in player["hand"] if c["instance_id"] == command["card_instance_id"]), None)
        if hand_card is None:
            raise PCGError("CARD_NOT_IN_HAND")
        definition = catalog[hand_card["template_id"]]
        if definition["kind"] == "unit":
            if command["row"] not in definition["allowed_rows"]:
                raise PCGError("ILLEGAL_ROW")
        elif command["row"] is not None:
            raise PCGError("TACTIC_ROW")
        op = definition["effect"]["op"]
        candidates = _target_candidates(state, actor, op)
        target_id = command["target_instance_id"]
        if op in ("BOOST", "DAMAGE"):
            if candidates:
                if target_id not in {u["instance_id"] for u in candidates}:
                    raise PCGError("TARGET_REQUIRED_OR_INVALID")
            elif definition["kind"] == "tactic":
                raise PCGError("NO_TACTIC_TARGET")
            elif target_id is not None:
                raise PCGError("TARGET_INVALID")
        elif target_id is not None:
            raise PCGError("TARGET_NOT_ALLOWED")
        player["hand"].remove(hand_card)
        player["played_count"] += 1
        if definition["kind"] == "unit":
            source = {**hand_card, "row": command["row"], "base_power": definition["base_power"],
                      "power": definition["base_power"], "shield": "shield_once" in definition["traits"],
                      "stable": "stable" in definition["traits"], "deploy_order": player["played_count"]}
            player["board"].append(source)
        else:
            source = hand_card
            player["discard"].append(deepcopy(hand_card))
        events.append({"kind": "played", "actor": actor, "card": deepcopy(hand_card), "row": command["row"]})
        _apply_effect(state, actor, definition, source, target_id, events)
    else:
        raise PCGError("COMMAND_KIND")
    state["revision"] += 1
    state["turn_player"] = 1 - actor
    _normalize(state, events)
    return {"state": state, "events": events}


def project_view(state, viewer):
    if viewer is not None and (type(viewer) is not int or viewer not in (0, 1)):
        raise PCGError("VIEWER")
    view = deepcopy(state)
    view["viewer_seat"] = viewer
    for seat, player in enumerate(view["players"]):
        player["hand_count"] = len(player["hand"])
        if seat != viewer:
            del player["hand"]
    view["scores"] = board_scores(state)
    return view


def legal_commands(pack, state, actor, action_id):
    """Caller supplies an intent ID; generate a fresh ID when choosing a new action."""
    if state["phase"] != "playing" or actor != state["turn_player"]:
        return []
    base = {"match_id": state["match_id"], "action_id": action_id, "expected_revision": state["revision"],
            "kind": "pass", "card_instance_id": None, "row": None, "target_instance_id": None}
    out = [base]
    catalog = validate_pack(pack)
    for card in state["players"][actor]["hand"]:
        definition = catalog[card["template_id"]]
        candidates = _target_candidates(state, actor, definition["effect"]["op"])
        if definition["kind"] == "tactic" and not candidates:
            continue
        targets = [u["instance_id"] for u in candidates] or [None]
        for row in definition["allowed_rows"] if definition["kind"] == "unit" else [None]:
            for target in targets:
                out.append({**base, "kind": "play", "card_instance_id": card["instance_id"], "row": row,
                            "target_instance_id": target})
    return out


class Authority:
    """Reference idempotence boundary; production must persist this ledger."""
    def __init__(self, pack, state):
        self.pack, self.state, self.results = deepcopy(pack), deepcopy(state), {}

    def submit(self, actor, command):
        key = (actor, command.get("action_id"))
        fingerprint = canonical(command)
        if key in self.results:
            old_fingerprint, result = self.results[key]
            if fingerprint != old_fingerprint:
                raise PCGError("ACTION_ID_CONFLICT")
            return deepcopy(result)
        try:
            applied = apply_action(self.pack, self.state, actor, command)
            self.state = applied["state"]
            result = {"match_id": self.state["match_id"], "action_id": command["action_id"],
                      "status": "accepted", "revision": self.state["revision"],
                      "error_code": None, "events": applied["events"], "snapshot_required": True}
        except PCGError as exc:
            result = {"match_id": self.state["match_id"], "action_id": command.get("action_id"),
                      "status": "rejected", "revision": self.state["revision"],
                      "error_code": exc.code, "events": [], "snapshot_required": True}
        self.results[key] = (fingerprint, deepcopy(result))
        return deepcopy(result)
