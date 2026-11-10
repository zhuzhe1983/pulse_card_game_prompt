#!/usr/bin/env python3
"""Compose a transparent char PNG onto a (optionally recolored) official template.

Renders 638x1004 with CairoSVG. Style B titles use the existing Oswald 700
identical-glyph-path scheme (stroke then fill) inside the original CORE title slot.
Validates: hide slots on the composite and diff against a same-color
parameterized template-only render; must be 0. Does not compare against
the original blue template-only PNG after a color change.

Does not paste product photos into the card and does not replace the
AIGC char with SVG geometry.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[3]
TPL_ROOT = REPO / 'asset' / 'concepts' / 'cardputerzero-template'
sys.path.insert(0, str(TPL_ROOT / 'scripts'))
import chroma_and_compose as cc

from recolor_template import recolor_template_file, TPL_A, TPL_B
OSWALD_VAR = Path('/usr/share/fonts/truetype/sand-box/google/Oswald/Oswald-VariableFont_wght.ttf')
SLOTS = json.loads((TPL_ROOT / 'templates' / 'slots.json').read_text())

TITLE_SLOT = [42.207, 190.863, 110.863, 215.346]


def title_spec_for(name_lines: list[str], product: str) -> dict:
    text = ' '.join(name_lines)
    layout = ' / '.join(name_lines) if len(name_lines) > 1 else name_lines[0]
    return {
        'text': text,
        'lines': name_lines,
        'slot_pt': TITLE_SLOT,
        'stroke_width': 1.95,
        'line_gap': 0.55,
        'font_path': str(OSWALD_VAR),
        'font_family': 'Oswald',
        'wght': 700,
        'font_note': (
            'Original CORE title is outlined path data; the source font is not embedded. '
            'This title is newly typeset from Oswald variable @ wght 700, converted to glyph '
            'paths, then drawn as the SAME path twice (black stroke, then white fill). '
            'Layout %s is fitted to the original CORE title slot %s. '
            'Oswald is a substitute face, not a glyph-accurate match to CORE.'
            % (layout, TITLE_SLOT)
        ),
    }


def compose(style: str, char_png: Path, dest_svg: Path, dest_png: Path,
            title_lines: list[str] | None = None,
            recolored_template: Path | None = None) -> dict:
    style = style.upper()
    cfg = SLOTS[style]
    tpl = recolored_template if recolored_template is not None else Path(cfg['template_svg'])
    spec = title_spec_for(title_lines, '') if (style == 'B' and title_lines) else None
    meet = 'xMidYMax meet' if style == 'B' else 'xMidYMid meet'
    dest_svg.parent.mkdir(parents=True, exist_ok=True)
    cc.embed_image_in_slot(tpl, char_png, cfg['char_union_pt'], dest_svg, spec, meet=meet)
    full_im = cc.render_svg_file(dest_svg, dest_png)
    return {
        'style': style,
        'template': str(tpl),
        'char': str(char_png),
        'svg': str(dest_svg),
        'png': str(dest_png),
        'size': list(full_im.size),
        'title_lines': title_lines if style == 'B' else None,
        'meet': meet,
    }


def validate_same_color(style: str, composite_svg: Path, recolored_template: Path,
                        out_dir: Path, stem: str) -> dict:
    """Hide slots on the composite and diff against template-only at the same tokens."""
    style = style.upper()
    hidden = cc.hide_slots(composite_svg)
    hidden_png = out_dir / f'{stem}_hidden_slots.png'
    hidden_im = cc.render_svg_bytes(hidden, hidden_png)

    # Render the recolored official template with empty slots (it already has empty slots)
    tpl_only_png = out_dir / f'{stem}_template-only.png'
    tpl_im = cc.render_svg_file(recolored_template, tpl_only_png)

    d = cc.pixel_diff(tpl_im.convert('RGBA'), hidden_im.convert('RGBA'))
    Image.fromarray(d['overlay'], 'RGB').save(out_dir / f'{stem}_template_diff_overlay.png')
    result = {
        'diff_pixels': d['diff_pixels'],
        'compared_pixels': d['compared_pixels'],
        'identical': d['identical'],
        'template_only': str(tpl_only_png),
        'hidden_slots': str(hidden_png),
        'rule': 'same-color parameterized master; slot-outside / hidden-slot render must be 0',
    }
    print('validate', stem, 'diff', d['diff_pixels'], 'identical', d['identical'])
    return result
