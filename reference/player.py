"""Player snapshots, explicit login selection and deterministic daily rewards."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re
import struct
import uuid
from .common import PCGError, MAX_INT, MAX_PLAIN, canonical, digest

OFFSET_MS = 28_800_000
DAY_MS = 86_400_000


def validate_snapshot(value):
    """Stdlib structural/semantic gate matching the v1 schema; preserve unknown fields."""
    def fail():
        raise PCGError("SAVE_INVALID")
    def integer(x, minimum=0, maximum=MAX_INT):
        if type(x) is not int or not minimum <= x <= maximum:
            fail()
    def object_fields(x, keys):
        if not isinstance(x, dict) or not set(keys).issubset(x):
            fail()
    def uuid4(x):
        try:
            u = uuid.UUID(x)
            if u.version != 4 or str(u) != x:
                fail()
        except (TypeError, ValueError, AttributeError):
            fail()
    def ident(x):
        if not isinstance(x, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}", x):
            fail()
    def nickname(x):
        if not isinstance(x, str) or len(x) > 32 or len(x.encode("utf-8")) > 96:
            fail()
    def listing(x, maximum):
        if not isinstance(x, list) or len(x) > maximum:
            fail()
    if not isinstance(value, dict):
        fail()
    if type(value.get("save_schema_version")) is not int or value.get("save_schema_version") != 1:
        raise PCGError("SAVE_SCHEMA_UNSUPPORTED")
    # Validate before string encoding so surrogate errors remain explicit PCG errors.
    if len(canonical(value)) > MAX_PLAIN:
        raise PCGError("SAVE_TOO_LARGE")
    object_fields(value, ["save_schema_version", "snapshot_id", "parent_snapshot_id", "history_tail",
        "player_id", "writer_device_id", "save_seq", "modified_at_ms", "game_calendar_offset_min",
        "nickname", "collection", "decks", "wallet", "day_ledger", "clock", "extensions"])
    for key in ("snapshot_id", "player_id", "writer_device_id"):
        uuid4(value[key])
    if value["parent_snapshot_id"] is not None:
        uuid4(value["parent_snapshot_id"])
        if value["parent_snapshot_id"] == value["snapshot_id"]:
            fail()
    listing(value["history_tail"], 16)
    for x in value["history_tail"]:
        uuid4(x)
    if len(set(value["history_tail"])) != len(value["history_tail"]) or value["snapshot_id"] in value["history_tail"]:
        fail()
    integer(value["save_seq"]); integer(value["modified_at_ms"])
    if value["game_calendar_offset_min"] != 480:
        fail()
    nickname(value["nickname"])
    listing(value["collection"], 1024)
    template_ids = []
    for c in value["collection"]:
        object_fields(c, ["template_id", "obtained_at_ms", "draw_count", "mastery", "skin_id", "unlocked_skins", "nickname"])
        ident(c["template_id"]); ident(c["skin_id"]); nickname(c["nickname"])
        for k in ("obtained_at_ms", "mastery"):
            integer(c[k])
        integer(c["draw_count"], 1)
        listing(c["unlocked_skins"], 32)
        for skin in c["unlocked_skins"]:
            ident(skin)
        if "base" not in c["unlocked_skins"] or c["skin_id"] not in c["unlocked_skins"] or len(set(c["unlocked_skins"])) != len(c["unlocked_skins"]):
            fail()
        template_ids.append(c["template_id"])
    if template_ids != sorted(set(template_ids)):
        fail()
    listing(value["decks"], 16)
    deck_ids = []
    for d in value["decks"]:
        object_fields(d, ["deck_id", "name", "template_ids"])
        ident(d["deck_id"]); nickname(d["name"]); listing(d["template_ids"], 10)
        for t in d["template_ids"]:
            ident(t)
        if len(d["template_ids"]) != 10 or len(set(d["template_ids"])) != 10:
            fail()
        deck_ids.append(d["deck_id"])
    if len(set(deck_ids)) != len(deck_ids):
        fail()
    object_fields(value["wallet"], ["shards"]); integer(value["wallet"]["shards"])
    object_fields(value["day_ledger"], ["day_id", "claims"])
    integer(value["day_ledger"]["day_id"]); listing(value["day_ledger"]["claims"], 512)
    hero_ids = []
    hero_pattern = r"(?:uid:[0-9a-f]{64}|issued:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})"
    for c in value["day_ledger"]["claims"]:
        object_fields(c, ["hero_card_id", "template_id", "claim_id", "claimed_at_ms", "pool_id", "pool_hash"])
        if not isinstance(c["hero_card_id"], str) or not re.fullmatch(hero_pattern, c["hero_card_id"]):
            fail()
        for k in ("claim_id", "pool_hash"):
            if not isinstance(c[k], str) or not re.fullmatch(r"[0-9a-f]{64}", c[k]):
                fail()
        ident(c["template_id"]); ident(c["pool_id"]); integer(c["claimed_at_ms"])
        hero_ids.append(c["hero_card_id"])
    if hero_ids != sorted(set(hero_ids)):
        fail()
    object_fields(value["clock"], ["high_water_utc_ms", "high_water_day_id", "last_source"])
    integer(value["clock"]["high_water_utc_ms"]); integer(value["clock"]["high_water_day_id"])
    if value["clock"]["last_source"] not in ("unknown", "manual", "device", "network", "server"):
        fail()
    if not isinstance(value["extensions"], dict):
        fail()
    return value


def game_day(utc_ms):
    if type(utc_ms) is not int or utc_ms < 946684800000 or utc_ms > 4102444800000:
        raise PCGError("TIME_UNAVAILABLE", "an absolute UTC date between 2000 and 2100 is required")
    return (utc_ms + OFFSET_MS) // DAY_MS


def new_player(player_id, device_id, snapshot_id, utc_ms=0, nickname=""):
    for value in (player_id, device_id, snapshot_id):
        uuid.UUID(value)
    return {
        "save_schema_version": 1, "snapshot_id": snapshot_id, "parent_snapshot_id": None,
        "history_tail": [], "player_id": player_id, "writer_device_id": device_id,
        "save_seq": 0, "modified_at_ms": utc_ms, "game_calendar_offset_min": 480,
        "nickname": nickname, "collection": [], "decks": [], "wallet": {"shards": 0},
        "day_ledger": {"day_id": 0, "claims": []},
        "clock": {"high_water_utc_ms": 0, "high_water_day_id": 0, "last_source": "unknown"},
        "extensions": {},
    }


def bump_snapshot(original, changed, device_id, snapshot_id, utc_ms):
    if original.get("save_schema_version") != 1 or changed.get("save_schema_version") != 1:
        raise PCGError("SAVE_SCHEMA_UNSUPPORTED")
    if snapshot_id == original["snapshot_id"]:
        raise PCGError("SNAPSHOT_ID_REUSE")
    uuid.UUID(snapshot_id)
    uuid.UUID(device_id)
    out = deepcopy(changed)
    out["snapshot_id"] = snapshot_id
    out["parent_snapshot_id"] = original["snapshot_id"]
    out["history_tail"] = (original.get("history_tail", []) + [original["snapshot_id"]])[-16:]
    out["writer_device_id"] = device_id
    out["save_seq"] = original["save_seq"] + 1
    out["modified_at_ms"] = max(utc_ms, original["modified_at_ms"] + 1)
    if out["save_seq"] > MAX_INT or out["modified_at_ms"] > MAX_INT:
        raise PCGError("SAVE_COUNTER_EXHAUSTED")
    if len(canonical(out)) > MAX_PLAIN:
        raise PCGError("SAVE_TOO_LARGE")
    validate_snapshot(out)
    return out


def select_login_snapshot(local, card, local_ancestor_ids=()):
    """Selection never writes a card. Unknown/concurrent branches are not merged."""
    if card is None:
        return {"decision": "recovery_required", "reason": "card_invalid_or_missing", "write_card": False}
    if card.get("save_schema_version") != 1:
        return {"decision": "read_only", "reason": "future_save_schema", "write_card": False}
    if local is None:
        return {"decision": "card", "reason": "no_local_snapshot", "write_card": False}
    if local["player_id"] != card["player_id"]:
        raise PCGError("PLAYER_MISMATCH")
    if local.get("save_schema_version") != 1:
        return {"decision": "read_only", "reason": "future_local_schema", "write_card": False}
    if local["snapshot_id"] == card["snapshot_id"]:
        if digest(local) != digest(card):
            return {"decision": "conflict", "reason": "same_id_different_payload", "write_card": False}
        return {"decision": "local", "reason": "identical", "write_card": False}
    local_ancestors = set(local.get("history_tail", [])) | set(local_ancestor_ids)
    if local.get("parent_snapshot_id"):
        local_ancestors.add(local["parent_snapshot_id"])
    card_ancestors = set(card.get("history_tail", []))
    if card.get("parent_snapshot_id"):
        card_ancestors.add(card["parent_snapshot_id"])
    local_after = card["snapshot_id"] in local_ancestors
    card_after = local["snapshot_id"] in card_ancestors
    if local_after and not card_after and local["save_seq"] > card["save_seq"] and local["modified_at_ms"] > card["modified_at_ms"]:
        return {"decision": "local", "reason": "local_newer_known_lineage", "write_card": False}
    if card_after and not local_after and card["save_seq"] > local["save_seq"] and card["modified_at_ms"] > local["modified_at_ms"]:
        return {"decision": "card", "reason": "card_newer_known_lineage_backup_local_first", "write_card": False}
    return {"decision": "conflict", "reason": "concurrent_or_unproven_lineage", "write_card": False}


def claim_identifier(player_id, hero_card_id, day_id):
    return digest({"domain": "pcg.claim.v1", "player_id": player_id,
                   "hero_card_id": hero_card_id, "day_id": day_id})


def weighted_index(seed_object, weights):
    if not weights or any(type(w) is not int or w <= 0 for w in weights):
        raise PCGError("POOL_WEIGHTS")
    total = sum(weights)
    if total > 0x7FFFFFFF:
        raise PCGError("POOL_WEIGHT_SUM")
    limit = ((1 << 32) // total) * total
    encoded = canonical(seed_object)
    for counter in range(256):
        h = hashlib.sha256(encoded + struct.pack(">I", counter)).digest()
        value = int.from_bytes(h[:4], "big")
        if value < limit:
            chosen = value % total
            for i, weight in enumerate(weights):
                if chosen < weight:
                    return i
                chosen -= weight
    raise PCGError("DRAW_SAMPLER_EXHAUSTED")


def claim_hero(snapshot, hero, pack, observed_utc_ms, clock_source, device_id, new_snapshot_id):
    """Prepare one atomic local transaction; caller MUST persist before celebrating."""
    if snapshot.get("save_schema_version") != 1:
        raise PCGError("SAVE_SCHEMA_UNSUPPORTED")
    validate_snapshot(snapshot)
    if clock_source not in ("device", "manual", "network", "server"):
        raise PCGError("TIME_UNAVAILABLE")
    day_id = game_day(observed_utc_ms)
    if day_id < snapshot["clock"]["high_water_day_id"]:
        raise PCGError("CLOCK_ROLLBACK")
    hero_id = hero.get("hero_card_id", "")
    if not isinstance(hero_id, str) or not re.fullmatch(r"(?:uid:[0-9a-f]{64}|issued:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})", hero_id):
        raise PCGError("HERO_ID")
    old_ledger = snapshot["day_ledger"]
    if old_ledger["day_id"] > day_id:
        raise PCGError("CLOCK_ROLLBACK")
    if old_ledger["day_id"] == day_id and any(c["hero_card_id"] == hero_id for c in old_ledger["claims"]):
        raise PCGError("ALREADY_CLAIMED_TODAY")
    catalog = {c["template_id"]: c for c in pack["cards"]}
    mode = hero.get("mode")
    if mode == "fixed":
        template_id = hero.get("fixed_template_id")
        if template_id not in catalog or catalog[template_id]["kind"] != "unit":
            raise PCGError("FIXED_REWARD_UNSUPPORTED")
        pool_id = "fixed"
        pool_hash = digest({"mode": "fixed", "template_id": template_id, "content_hash": digest(pack)})
    elif mode == "blind_box":
        pool = next((p for p in pack["draw_pools"] if p["pool_id"] == hero.get("pool_id")), None)
        if pool is None:
            raise PCGError("POOL_UNSUPPORTED")
        if any(e["template_id"] not in catalog or catalog[e["template_id"]]["kind"] != "unit" for e in pool["entries"]):
            raise PCGError("POOL_CONTENT")
        pool_id, pool_hash = pool["pool_id"], digest(pool)
        seed = {"domain": "pcg.draw.v1", "player_id": snapshot["player_id"],
                "hero_card_id": hero_id, "day_id": day_id, "pool_id": pool_id, "pool_hash": pool_hash}
        index = weighted_index(seed, [e["weight"] for e in pool["entries"]])
        template_id = pool["entries"][index]["template_id"]
    else:
        raise PCGError("HERO_MODE")
    out = deepcopy(snapshot)
    if out["day_ledger"]["day_id"] != day_id:
        out["day_ledger"].update({"day_id": day_id, "claims": []})
    claim_id = claim_identifier(out["player_id"], hero_id, day_id)
    item = next((c for c in out["collection"] if c["template_id"] == template_id), None)
    duplicate = item is not None
    shards_delta = pack["duplicate_shards"] if duplicate else 0
    if item is None:
        out["collection"].append({"template_id": template_id, "obtained_at_ms": observed_utc_ms,
                                  "draw_count": 1, "mastery": 0, "skin_id": "base", "unlocked_skins": ["base"], "nickname": ""})
    else:
        item["draw_count"] += 1
    out["collection"].sort(key=lambda c: c["template_id"])
    out["wallet"]["shards"] += shards_delta
    out["day_ledger"]["claims"].append({"hero_card_id": hero_id, "template_id": template_id,
        "claim_id": claim_id, "claimed_at_ms": observed_utc_ms, "pool_id": pool_id, "pool_hash": pool_hash})
    out["day_ledger"]["claims"].sort(key=lambda c: c["hero_card_id"])
    out["clock"].update({"high_water_utc_ms": max(snapshot["clock"]["high_water_utc_ms"], observed_utc_ms),
                    "high_water_day_id": max(snapshot["clock"]["high_water_day_id"], day_id),
                    "last_source": clock_source})
    out = bump_snapshot(snapshot, out, device_id, new_snapshot_id, observed_utc_ms)
    return {"snapshot": out, "reward": {"template_id": template_id, "is_duplicate": duplicate,
            "shards_delta": shards_delta, "claim_id": claim_id, "day_id": day_id}}


def redeem_ink_skin(snapshot, template_id, pack, device_id, new_snapshot_id, utc_ms):
    if snapshot.get("save_schema_version") != 1:
        raise PCGError("SAVE_SCHEMA_UNSUPPORTED")
    out = deepcopy(snapshot)
    item = next((c for c in out["collection"] if c["template_id"] == template_id), None)
    if item is None:
        raise PCGError("CHARACTER_NOT_OWNED")
    if "ink" in item["unlocked_skins"]:
        raise PCGError("SKIN_ALREADY_OWNED")
    cost = pack["cosmetics"]["ink_unlock_shards"]
    if out["wallet"]["shards"] < cost:
        raise PCGError("INSUFFICIENT_SHARDS")
    out["wallet"]["shards"] -= cost
    item["unlocked_skins"].append("ink")
    item["unlocked_skins"].sort()
    item["skin_id"] = "ink"
    return bump_snapshot(snapshot, out, device_id, new_snapshot_id, utc_ms)
