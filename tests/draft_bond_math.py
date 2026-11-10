"""Score the unenabled bond draft. Not used by reference.battle or pcg.core.v1."""

def tags_of(card):
    return set(card.get("tags") or [])


def has_tag(board, tag):
    return any(tag in tags_of(card) for card in board)


def count_tag(board, tag):
    return sum(1 for card in board if tag in tags_of(card))


def bond_granted(card, board, prior_bonds):
    """Return this card's bond bonus at the moment it is played.

    board includes this card. prior_bonds are already granted bonuses for earlier cards.
    Bonuses do not rewrite earlier cards.
    """
    rule = card.get("bond_rule") or "none"
    if rule == "none":
        return 0
    before = board[:-1]

    def earlier_bond(rule_name):
        return sum(amount for played, amount in prior_bonds if played.get("bond_rule") == rule_name and amount)

    if rule == "hat_on_stick":
        if has_tag(board, "stick_s3"):
            return 0
        if has_tag(board, "hat_host_thin"):
            return 1
        if has_tag(board, "hat_host_full"):
            return 2
        return 0
    if rule == "hat_i2s":
        return 2 if has_tag(board, "stick_plus") else 0
    if rule == "hat_power":
        return 1 if has_tag(board, "hat_host_full") else 0
    if rule == "s3_window":
        return 2 if has_tag(board, "stick_s3") else 0
    if rule == "bottom2":
        return 2 if has_tag(board, "core2") else 0
    if rule == "plain_base":
        return 1 if has_tag(board, "mbus_gen1") else 0
    if rule == "lamp":
        return 2 if has_tag(board, "mbus_gen1") else 0
    if rule == "faces_chassis":
        if not has_tag(board, "mbus"):
            return 0
        if count_tag(board, "addr08") >= 2:
            return 0
        return 2 if count_tag(board, "faces_panel") == 1 else 0
    if rule == "faces_08":
        if count_tag(board, "addr08") >= 2:
            return 0
        if has_tag(board, "faces_chassis") and has_tag(board, "mbus"):
            return 1
        return 0
    if rule == "faces_unknown":
        if has_tag(board, "faces_chassis") and has_tag(board, "mbus"):
            return 1
        return 0
    if rule == "atomic_seat":
        if not has_tag(board, "atom"):
            return 0
        return 0 if earlier_bond("atomic_seat") else 2
    if rule == "chain_node":
        master = has_tag(board, "chain_master") or (has_tag(board, "atom") and has_tag(before, "tochain"))
        if not master or earlier_bond("chain_node"):
            return 0
        return 1
    if rule in ("chain_lantern", "chain_return"):
        if not earlier_bond("chain_node"):
            return 0
        chain_so_far = sum(amount for played, amount in prior_bonds if played.get("bond_rule") in ("chain_node", "chain_lantern", "eight_chain", "chain_return"))
        return 1 if chain_so_far < 2 else 0
    if rule in ("unit_i2c", "unit_gpio", "unit_uart"):
        if has_tag(board, "one_grove") and any(amount and played.get("kind") == "gear" and "unit" in tags_of(played) for played, amount in prior_bonds):
            return 0
        if has_tag(board, "workshop") and "esp32_module" in tags_of(card):
            return 0
        need = {"unit_i2c": "grove_i2c", "unit_gpio": "grove_gpio", "unit_uart": "grove_uart"}[rule]
        if not has_tag(board, need):
            return 0
        if "env" in tags_of(card) and any("env" in tags_of(other) for other in before) and not has_tag(before, "split_case"):
            return 0
        if "tof" in tags_of(card) and any("tof" in tags_of(other) for other in before) and not has_tag(before, "split_case"):
            return 0
        if "sense" in tags_of(card) and has_tag(before, "magnet_haze"):
            return 0
        bonus = 1
        if "sense" in tags_of(card) and has_tag(board, "cores3") and not has_tag(before, "magnet_haze"):
            bonus = 2
        return bonus
    if rule == "star_module":
        if has_tag(board, "workshop"):
            return 0
        if not has_tag(board, "mbus"):
            return 0
        if has_tag(board, "fire") and has_tag(board, "locate_feather"):
            return 0
        return 2
    if rule == "thought_case":
        if has_tag(board, "workshop") or not has_tag(board, "mbus"):
            return 0
        return 1
    if rule == "nano_relay":
        return 2 if has_tag(board, "relay_feather") else 0
    if rule == "gray_sense":
        if has_tag(before, "magnet_haze"):
            return 0
        return 2 if any("sense" in tags_of(other) for other in board) else 0
    if rule == "heat_lens":
        if has_tag(board, "stick_t2"):
            return 0
        if not has_tag(board, "grove_i2c"):
            return 0
        return 1
    if rule == "eight_chain":
        master = has_tag(board, "chain_master") or (has_tag(board, "atom") and has_tag(before, "tochain"))
        return 1 if master else 0
    if rule == "tab_keys":
        return 2 if has_tag(board, "tab5") else 0
    if rule == "restore_star":
        if not has_tag(board, "mbus") or has_tag(board, "workshop"):
            return 0
        for played, amount in prior_bonds:
            if played.get("bond_rule") == "star_module" and amount == 0 and not (has_tag(board, "fire") and has_tag(board, "locate_feather")):
                return 2
        return 0
    raise ValueError("unknown bond_rule " + rule)


def settle_faces(board, granted):
    """Faces look at the whole round once. Two known 0x08 panels cancel the face."""
    settled = []
    for card, amount in granted:
        if card.get("bond_rule") in ("faces_chassis", "faces_08", "faces_unknown"):
            amount = 0
        settled.append([card, amount])
    if not has_tag(board, "mbus"):
        return [(card, amount) for card, amount in settled]
    if count_tag(board, "addr08") >= 2:
        return [(card, amount) for card, amount in settled]
    panels = count_tag(board, "faces_panel")
    if panels == 1:
        for item in settled:
            if item[0].get("bond_rule") == "faces_chassis":
                item[1] = 2
            elif item[0].get("bond_rule") in ("faces_08", "faces_unknown"):
                item[1] = 1
    elif panels > 1:
        for item in settled:
            if item[0].get("bond_rule") in ("faces_08", "faces_unknown"):
                item[1] = 1
    return [(card, amount) for card, amount in settled]


def resolve_round(deck, plays, bond_cap=3):
    board = []
    granted = []
    for template_id in plays:
        card = deck[template_id]
        board.append(card)
        granted.append((card, bond_granted(card, board, granted)))
    granted = settle_faces(board, granted)
    # Capsule keeps only the first accessory bond.
    if any("capsule" in tags_of(card) for card, _amount in granted):
        seen = False
        trimmed = []
        for card, amount in granted:
            if amount and card.get("kind") in ("retainer", "gear", "tactic") and card.get("bond_rule") not in ("none", "restore_star"):
                if seen:
                    amount = 0
                else:
                    seen = True
            trimmed.append((card, amount))
        granted = trimmed
    # One chain link stays at +2, earliest first.
    chain_left = 2
    capped_chain = []
    for card, amount in granted:
        if amount and card.get("bond_rule") in ("chain_node", "chain_lantern", "eight_chain", "chain_return"):
            allowed = min(amount, chain_left)
            chain_left -= allowed
            amount = allowed
        capped_chain.append((card, amount))
    bond_left = bond_cap
    bond_sum = 0
    for _card, amount in capped_chain:
        allowed = min(amount, bond_left)
        bond_left -= allowed
        bond_sum += allowed
    skills = 0
    kinds = {card.get("kind") for card, _amount in granted}
    if bond_sum == 0 and any("lonely" in tags_of(card) for card, _amount in granted):
        skills += 1
    if any("coreink" in tags_of(card) for card, _amount in granted) and not ({"retainer", "gear"} & kinds):
        skills += 2
    if any("din" in tags_of(card) for card, _amount in granted) and not any("hat" in tags_of(card) or "module" in tags_of(card) for card, _amount in granted):
        skills += 2
    if any("matrix_keeper" in tags_of(card) for card, _amount in granted) and not any("screen" in tags_of(card) for card, _amount in granted):
        skills += 2
    if any("stick_t2" in tags_of(card) for card, _amount in granted):
        skills += 1
    quiet = 0
    base = sum(deck[template_id]["base_power"] for template_id in plays)
    return {"base": base, "bonds": bond_sum, "skills": skills, "quiet": quiet, "total_before_quiet": base + bond_sum + skills}


def quiet_bonus(own_total_plays, other_total_plays, own_ids, deck):
    if any(deck[template_id].get("bond_rule") == "quiet" or "quiet" in deck[template_id].get("tags", []) for template_id in own_ids):
        if own_total_plays < other_total_plays:
            return 2
    return 0
