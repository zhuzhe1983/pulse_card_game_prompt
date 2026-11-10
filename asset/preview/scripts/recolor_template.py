#!/usr/bin/env python3
"""Parameterize official NFC card template background / shadow tokens.

Only two visible fills are variable:
  Style A card body:  style="fill-rule: evenodd; fill: #009ee0; "
  Style B card body:  style="fill-rule: evenodd; fill: #0079b4; "
  Style B ground oval: style="fill-rule: evenodd; fill: #00679a; "

The shared gradient defs, invisible #005986 sunburst remnants
(fill-opacity 0), typography, logos, clip path, slogan #ffec00,
and all coordinates stay untouched. Replacing any other fill is
out of scope.

Official 22-card language: one saturated solid field per card.
Style B pairs the field with a darker same-hue ground oval.
"""
from __future__ import annotations

from pathlib import Path

BODY_A = 'style="fill-rule: evenodd; fill: #009ee0; "'
BODY_B = 'style="fill-rule: evenodd; fill: #0079b4; "'
SHADOW_B = 'style="fill-rule: evenodd; fill: #00679a; "'

DEFAULT_A_BG = '#009ee0'
DEFAULT_B_BG = '#0079b4'
DEFAULT_B_SHADOW = '#00679a'

REPO = Path(__file__).resolve().parents[3]
TPL_A = REPO / 'asset/concepts/cardputerzero-template/templates/styleA_template_01_S3.svg'
TPL_B = REPO / 'asset/concepts/cardputerzero-template/templates/styleB_template_10_CORE.svg'


def darken_hex(hx: str, factor: float = 0.82) -> str:
    hx = hx.lstrip('#')
    r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
    return '#{:02x}{:02x}{:02x}'.format(int(r * factor), int(g * factor), int(b * factor))


def normalize_hex(hx: str) -> str:
    hx = hx.strip().lower()
    if not hx.startswith('#'):
        hx = '#' + hx
    if len(hx) != 7:
        raise ValueError('expected #rrggbb, got %r' % hx)
    return hx


def recolor_svg_text(text: str, style: str, card_bg: str, shadow: str | None = None) -> tuple[str, dict]:
    style = style.upper()
    card_bg = normalize_hex(card_bg)
    report = {'style': style, 'card_bg': card_bg, 'shadow': None,
              'replacements': [], 'untouched_note':
              'gradient defs, #005986 opacity-0 remnants, logos, type, clip, #ffec00 slogan were not edited'}
    if style == 'A':
        n = text.count(BODY_A)
        if n != 1:
            raise RuntimeError('Style A body token count is %s, expected 1' % n)
        if text.count('#009ee0') < 1:
            raise RuntimeError('missing default Style A body color')
        new = text.replace(BODY_A, 'style="fill-rule: evenodd; fill: %s; "' % card_bg, 1)
        report['replacements'].append({'token': 'card_bg', 'old': DEFAULT_A_BG, 'new': card_bg, 'count': 1})
    elif style == 'B':
        n = text.count(BODY_B)
        if n != 1:
            raise RuntimeError('Style B body token count is %s, expected 1' % n)
        sh = normalize_hex(shadow) if shadow else darken_hex(card_bg, 0.82)
        ns = text.count(SHADOW_B)
        if ns != 1:
            raise RuntimeError('Style B shadow token count is %s, expected 1' % ns)
        new = text.replace(BODY_B, 'style="fill-rule: evenodd; fill: %s; "' % card_bg, 1)
        new = new.replace(SHADOW_B, 'style="fill-rule: evenodd; fill: %s; "' % sh, 1)
        report['shadow'] = sh
        report['replacements'].append({'token': 'card_bg', 'old': DEFAULT_B_BG, 'new': card_bg, 'count': 1})
        report['replacements'].append({'token': 'shadow', 'old': DEFAULT_B_SHADOW, 'new': sh, 'count': 1})
    else:
        raise ValueError('style must be A or B')
    return new, report


def only_token_changes(original: str, recolored: str, style: str, card_bg: str, shadow: str | None) -> bool:
    expected, _ = recolor_svg_text(original, style, card_bg, shadow)
    return expected == recolored


def recolor_template_file(style: str, card_bg: str, dest: Path, shadow: str | None = None) -> dict:
    src = TPL_A if style.upper() == 'A' else TPL_B
    text = src.read_text(encoding='utf-8')
    new, report = recolor_svg_text(text, style, card_bg, shadow)
    if not only_token_changes(text, new, style, card_bg, report.get('shadow')):
        raise RuntimeError('recolor produced unexpected edits beyond the color tokens')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(new, encoding='utf-8')
    report['source_template'] = str(src)
    report['dest'] = str(dest)
    report['byte_identical_except_tokens'] = True
    return report
