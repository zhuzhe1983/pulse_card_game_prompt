#!/usr/bin/env python3
"""Chroma-key CardputerZero character rasters and composite them onto official SVG templates.

This is a design-asset pipeline, not game-engine code. It:
  * keys lime backgrounds from GenerateImage JPEGs
  * locally paints out generated garbage labels on the Style A character
  * embeds the resulting PNG into copies of the official card SVG templates
  * typesets the Style B dynamic title as identical glyph paths (black stroke + white fill)
  * renders 638x1004 RGBA PNGs with CairoSVG
  * pixel-compares template-only outputs (must match) and masked full-card diffs

It does not edit the user's git repository.
"""
from __future__ import annotations

import json
from pathlib import Path
import io
import numpy as np
from PIL import Image, ImageDraw
from lxml import etree as E
import cairosvg
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
NS = 'http://www.w3.org/2000/svg'
XLINK = 'http://www.w3.org/1999/xlink'
OSWALD_VAR = Path('/usr/share/fonts/truetype/sand-box/google/Oswald/Oswald-VariableFont_wght.ttf')


def q(n: str) -> str:
    return '{%s}%s' % (NS, n)


def chroma_key_lime(im: Image.Image, out_path: Path) -> dict:
    """Remove the lime screen by flood-filling from the four corners.

    Interior lime (for example the word ZERO on the device screen) stays,
    because it is not connected to the canvas background. JPEG green fringe
    on the outer silhouette is despilled after the fill.
    """
    from collections import deque
    rgba = np.array(im.convert('RGBA'))
    rgb = rgba[:, :, :3].astype(np.int16)
    h, w = rgb.shape[:2]
    corners = [tuple(int(x) for x in rgba[y, x, :3]) for y, x in [(2, 2), (2, w - 3), (h - 3, 2), (h - 3, w - 3)]]
    key = np.median(np.array(corners), axis=0).astype(np.float32)
    dist = np.sqrt(((rgb.astype(np.float32) - key) ** 2).sum(axis=2))
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    greendominant = (g > r + 20) & (g > b + 20) & (g > 120)
    screenish = (dist < 55) | greendominant
    visited = np.zeros((h, w), dtype=bool)
    q = deque()
    for y, x in [(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1),
                 (0, w // 2), (h - 1, w // 2), (h // 2, 0), (h // 2, w - 1)]:
        q.append((y, x)); visited[y, x] = True
    bg = np.zeros((h, w), dtype=bool)
    while q:
        y, x = q.popleft()
        if not screenish[y, x]:
            continue
        bg[y, x] = True
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    dil = bg.copy()
    dil[1:] |= bg[:-1]; dil[:-1] |= bg[1:]; dil[:, 1:] |= bg[:, :-1]; dil[:, :-1] |= bg[:, 1:]
    edge = dil & (~bg)
    extra = np.clip(g - np.maximum(r, b), 0, 255)
    g2 = g.copy()
    fix = edge & (extra > 6)
    g2[fix] = np.maximum(r[fix], b[fix])
    rgb2 = rgb.copy(); rgb2[:, :, 1] = g2
    rgba2 = np.dstack([np.clip(rgb2, 0, 255).astype(np.uint8), alpha])
    out = Image.fromarray(rgba2, 'RGBA')
    bbox = out.getbbox()
    if bbox is None:
        raise RuntimeError('chroma key emptied the image')
    x0, y0, x1, y1 = bbox
    pad = 4
    x0 = max(0, x0 - pad); y0 = max(0, y0 - pad)
    x1 = min(out.width, x1 + pad); y1 = min(out.height, y1 + pad)
    out = out.crop((x0, y0, x1, y1))
    arr = np.array(out)
    arr[arr[:, :, 3] == 0, :3] = 0
    out = Image.fromarray(arr, 'RGBA')
    out.save(out_path)
    opaque = int((arr[:, :, 3] > 8).sum())
    fringe = int(((arr[:, :, 3] > 8) & (arr[:, :, 3] < 250)).sum())
    corners_a = [int(out.getpixel((0, 0))[3]), int(out.getpixel((out.width - 1, 0))[3]),
                 int(out.getpixel((0, out.height - 1))[3]), int(out.getpixel((out.width - 1, out.height - 1))[3])]
    return {
        'file': str(out_path), 'size': list(out.size), 'source_corners_rgb': [list(c) for c in corners],
        'opaque_pixels': opaque, 'partial_alpha_pixels': fringe, 'corners_alpha': corners_a,
        'method': 'Corner flood-fill of screen-similar pixels (RGB dist<55 OR green-dominant). Interior lime (e.g. ZERO text) is kept if not connected to the canvas. Edge despill only. JPEG source is not lossless.'
    }


def clean_style_a_garbled_labels(im: Image.Image) -> dict:
    """Paint out generated garbage labels on the Style A character.

    This is local text cleanup, not a redraw of the device. Kept: gray shell,
    black keys, cyan mechanical badge, orange rocker (including its ON mark),
    screw, USB graphic, and real product names (CARDPUTER ZERO / ZERO /
    Python / STORE / CLI / M5STACK). Removed: LACK TAB and nearby power-cluster
    soup (POWER SWITCH, USB C2, 5V ONLY CHG). LACK TAB is replaced with two
    unlabeled dark key marks in the original pill slot.
    """
    arr = np.array(im.convert('RGBA')).copy()
    h, w = arr.shape[:2]
    if (w, h) != (906, 642):
        # Coordinates were measured on the v3 chroma crop (906x642).
        return {'applied': False, 'reason': f'unexpected char size {(w, h)}; skip cleanup rather than mis-paint'}
    rgb = arr[:, :, :3].astype(np.int16)
    r, g, bch = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    protect = np.zeros((h, w), dtype=bool)
    # Rocker: protect only warm orange/red button pixels, not the neutral-black
    # POWER letterforms that sit just below the button in the same coarse box.
    yy, xx = np.ogrid[:h, :w]
    lum = rgb.mean(axis=2)
    rocker_roi = np.zeros((h, w), dtype=bool)
    rocker_roi[68:110, 668:730] = True
    warm = (r > g + 20) & (r > bch + 20) & (r > 70)
    protect |= rocker_roi & warm
    protect |= (xx - 697) ** 2 + (yy - 172) ** 2 <= 10 ** 2  # screw
    protect[154:186, 776:808] = True  # stacked USB graphic
    protect[184:208, 798:826] = True  # orange arrow
    protect |= (r > 195) & (g > 90) & (g < 155) & (bch < 90) & (r > g + 45)
    protect[:, :640] = True  # screen / CLI / product name lockup
    protect[255:, :] = True  # keyboard and badge title

    def wipe_box(box, thresh):
        x0, y0, x1, y1 = box
        patch = arr[y0:y1, x0:x1].copy()
        prot = protect[y0:y1, x0:x1]
        pl = patch[:, :, :3].astype(np.float32)
        lu = pl.mean(2)
        ch = pl.max(2) - pl.min(2)
        panel = (~prot) & (lu > 185) & (ch < 25)
        if int(panel.sum()) < 6:
            return {'box': box, 'skipped': True}
        bg = np.median(patch[panel], axis=0)
        dist = np.sqrt(((pl - bg[:3]) ** 2).sum(2))
        marks = (~prot) & (dist > thresh)
        n = int(marks.sum())
        patch[marks] = bg
        arr[y0:y1, x0:x1] = patch
        return {'box': list(box), 'marks': n, 'thresh': thresh}

    wipes = []
    for box, thr in [
        ((684, 92, 786, 136), 18),   # POWER including glyph tops below the rocker
        ((724, 90, 788, 112), 22),    # POWER caps to the right of the rocker
        ((696, 128, 774, 154), 22),   # SWITCH
        ((718, 146, 764, 168), 24),   # USB
        ((748, 158, 778, 184), 24),   # C2
        ((686, 166, 732, 198), 22),   # 5V
        ((714, 178, 762, 206), 22),   # ONLY
        ((748, 176, 800, 206), 22),   # CHG
    ]:
        wipes.append(wipe_box(box, thr))
    # Final plate fill for POWER/SWITCH so leftover AA cannot still read as letters.
    # Only unprotected pixels; rocker/screw stay.
    x0, y0, x1, y1 = 684, 92, 786, 152
    patch = arr[y0:y1, x0:x1]
    prot = protect[y0:y1, x0:x1]
    pl = patch[:, :, :3].astype(np.float32)
    lu = pl.mean(2)
    ch = pl.max(2) - pl.min(2)
    panel = (~prot) & (lu > 200) & (ch < 20)
    if int(panel.sum()) >= 6:
        bg = np.median(patch[panel], axis=0)
        n = int((~prot).sum())
        patch[~prot] = bg
        arr[y0:y1, x0:x1] = patch
        wipes.append({'box': [x0, y0, x1, y1], 'plate_fill': n})

    ly0, ly1, lx0, lx1 = 198, 226, 662, 792
    pill = arr[ly0:ly1, lx0:lx1]
    plum = pill[:, :, :3].astype(np.float32).mean(axis=2)
    dark = plum < 85
    dlt = dark.copy()
    for _ in range(2):
        n = dlt.copy()
        n[1:] |= dlt[:-1]; n[:-1] |= dlt[1:]
        n[:, 1:] |= dlt[:, :-1]; n[:, :-1] |= dlt[:, 1:]
        dlt = n
    letters = (plum > 115) & dlt
    inkc = np.median(pill[dark], axis=0) if dark.any() else np.array([20, 20, 18, 255], np.uint8)
    arr[ly0:ly1, lx0:lx1][letters] = inkc
    out = Image.fromarray(arr, 'RGBA')
    dr = ImageDraw.Draw(out)
    dr.rounded_rectangle([664, 200, 724, 223], radius=6, fill=(22, 22, 20, 255))
    dr.rounded_rectangle([728, 200, 788, 223], radius=6, fill=(22, 22, 20, 255))
    return {
        'applied': True,
        'wipes': wipes,
        'lack_tab_letters_painted': int(letters.sum()),
        'replacement': 'two unlabeled rounded dark key marks in the original LACK TAB pill',
        'kept': ['CARDPUTER ZERO', 'ZERO', 'Python', 'STORE', 'CLI', 'M5STACK', 'orange rocker + ON', 'screw', 'USB graphic', 'cyan badge', 'gray shell', 'black keys'],
        'removed': ['LACK TAB', 'POWER SWITCH', 'USB C2', '5V ONLY CHG'],
    }, out


def glyph_path_for_text(text: str, font_path: Path, wght: float | None):
    font = TTFont(str(font_path))
    if wght is not None and 'fvar' in font:
        font = instantiateVariableFont(font, {'wght': float(wght)})
    glyphset = font.getGlyphSet()
    cmap = font.getBestCmap()
    x = 0.0
    cmds = []
    bp = BoundsPen(glyphset)
    for ch in text:
        name = cmap.get(ord(ch))
        if name is None:
            continue
        g = glyphset[name]
        g.draw(TransformPen(bp, Transform().translate(x, 0)))
        sp = SVGPathPen(glyphset)
        g.draw(TransformPen(sp, Transform().translate(x, 0)))
        d = sp.getCommands()
        if d:
            cmds.append(d)
        x += g.width
    if bp.bounds is None:
        raise RuntimeError('no glyph bounds for %r' % text)
    return ' '.join(cmds), bp.bounds


def add_outlined_line(parent, d, bounds, cx, cy, max_w, max_h, stroke,
                      fill='#ffffff', stroke_color='#1b1918'):
    """Same path twice: black stroke, then white fill. No offset, no second point size."""
    xmin, ymin, xmax, ymax = bounds
    bw, bh = xmax - xmin, ymax - ymin
    if bw <= 0 or bh <= 0:
        return
    scale = min(max_w / bw, max_h / bh)
    fcx, fcy = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
    g = E.SubElement(parent, q('g'))
    g.set('transform', 'translate(%s %s) scale(%s %s) translate(%s %s)' % (
        cx, cy, scale, -scale, -fcx, -fcy))
    p1 = E.SubElement(g, q('path'))
    p1.set('d', d)
    p1.set('fill', 'none')
    p1.set('stroke', stroke_color)
    p1.set('stroke-width', '%.6f' % (stroke / scale))
    p1.set('stroke-linejoin', 'round')
    p1.set('stroke-linecap', 'round')
    p2 = E.SubElement(g, q('path'))
    p2.set('d', d)
    p2.set('fill', fill)
    p2.set('stroke', 'none')


def embed_outlined_title(slot_name, title_spec):
    slot = title_spec['slot_pt']
    stroke = float(title_spec.get('stroke_width', 1.95))
    font_path = Path(title_spec['font_path'])
    wght = title_spec.get('wght', 700)
    lines = title_spec.get('lines') or [title_spec['text']]
    x0, y0, x1, y1 = slot
    avail_w = (x1 - x0) - stroke
    avail_h = (y1 - y0) - stroke
    cx = (x0 + x1) / 2.0
    gap = float(title_spec.get('line_gap', 0.55))
    if len(lines) == 1:
        d, bounds = glyph_path_for_text(lines[0], font_path, wght)
        add_outlined_line(slot_name, d, bounds, cx, (y0 + y1) / 2.0, avail_w, avail_h, stroke)
    else:
        line_h = (avail_h - gap * (len(lines) - 1)) / len(lines)
        for i, line in enumerate(lines):
            d, bounds = glyph_path_for_text(line, font_path, wght)
            cy = y0 + stroke / 2.0 + i * (line_h + gap) + line_h / 2.0
            add_outlined_line(slot_name, d, bounds, cx, cy, avail_w, line_h, stroke)
    slot_name.set('data-font-note', title_spec['font_note'])
    slot_name.set('data-title-method', 'identical-glyph-paths-stroke-then-fill')


def embed_image_in_slot(svg_path: Path, png_path: Path, bbox_pt: list[float], dest_svg: Path, title_spec=None, meet='xMidYMid meet') -> Path:
    tree = E.parse(str(svg_path))
    root = tree.getroot()
    slot_char = root.xpath('.//*[@id="slot-char"]')[0]
    slot_name = root.xpath('.//*[@id="slot-dynamic-name"]')[0]
    for slot in (slot_char, slot_name):
        for ch in list(slot):
            slot.remove(ch)
    x0, y0, x1, y1 = bbox_pt
    img = E.SubElement(slot_char, q('image'))
    img.set('x', str(x0))
    img.set('y', str(y0))
    img.set('width', str(x1 - x0))
    img.set('height', str(y1 - y0))
    img.set('preserveAspectRatio', meet)
    import base64
    b64 = base64.b64encode(png_path.read_bytes()).decode('ascii')
    href = 'data:image/png;base64,' + b64
    img.set('href', href)
    img.set('data-note', 'raster character embed (PNG data URI); not a native vector redraw of the subject')

    if title_spec:
        embed_outlined_title(slot_name, title_spec)
    dest_svg.write_bytes(E.tostring(root, xml_declaration=True, encoding='utf-8'))
    return dest_svg


def hide_slots(svg_path: Path) -> bytes:
    root = E.parse(str(svg_path)).getroot()
    for sid in ('slot-char', 'slot-dynamic-name'):
        nodes = root.xpath(f'.//*[@id="{sid}"]')
        for n in nodes:
            n.set('display', 'none')
    return E.tostring(root, xml_declaration=True, encoding='utf-8')


def render_svg_bytes(data: bytes, dest: Path, w=638, h=1004) -> Image.Image:
    png = cairosvg.svg2png(bytestring=data, output_width=w, output_height=h, unsafe=True)
    im = Image.open(io.BytesIO(png)).convert('RGBA')
    im.save(dest)
    return im


def render_svg_file(path: Path, dest: Path, w=638, h=1004) -> Image.Image:
    return render_svg_bytes(path.read_bytes(), dest, w, h)


def pixel_diff(a: Image.Image, b: Image.Image, mask: np.ndarray | None = None) -> dict:
    aa = np.array(a.convert('RGBA'))
    bb = np.array(b.convert('RGBA'))
    if aa.shape != bb.shape:
        return {'error': f'shape {aa.shape} vs {bb.shape}'}
    diff = np.any(aa != bb, axis=2)
    if mask is not None:
        considered = ~mask
        n = int(diff[considered].sum())
        total = int(considered.sum())
    else:
        n = int(diff.sum()); total = diff.size
    overlay = np.zeros((*diff.shape, 3), dtype=np.uint8)
    overlay[:, :] = (30, 30, 30)
    overlay[diff] = (255, 60, 60)
    if mask is not None:
        overlay[mask] = (40, 90, 200)
    return {'diff_pixels': n, 'compared_pixels': total, 'identical': n == 0, 'overlay': overlay, 'diff_map': diff}


def rect_mask(shape, boxes_px, pad=0):
    m = np.zeros(shape[:2], dtype=bool)
    h, w = m.shape
    for x0, y0, x1, y1 in boxes_px:
        xa, xb = max(0, int(np.floor(x0) - pad)), min(w, int(np.ceil(x1) + pad))
        ya, yb = max(0, int(np.floor(y0) - pad)), min(h, int(np.ceil(y1) + pad))
        m[ya:yb, xa:xb] = True
    return m


def make_triple_sheet(orig, tmpl, comp, title, captions, dest: Path):
    """original | template-only | composite contact sheet."""
    from PIL import ImageDraw, ImageFont
    card_h = 440
    aspect = orig.width / orig.height
    card_w = int(card_h * aspect)
    gap = 18
    pad_x, pad_top, pad_bot = 24, 48, 36
    W = pad_x * 2 + card_w * 3 + gap * 2
    H = pad_top + card_h + pad_bot
    canvas = Image.new('RGB', (W, H), (247, 244, 236))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
        font_s = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    except Exception:
        font = font_s = ImageFont.load_default()
    draw.text((pad_x, 16), title, fill=(40, 40, 40), font=font)

    def fit(im):
        rgb = im.convert('RGBA')
        bg = Image.new('RGBA', rgb.size, (247, 244, 236, 255))
        bg = Image.alpha_composite(bg, rgb).convert('RGB')
        return bg.resize((card_w, card_h), Image.Resampling.LANCZOS)

    imgs = [fit(orig), fit(tmpl), fit(comp)]
    for i, im in enumerate(imgs):
        x = pad_x + i * (card_w + gap)
        canvas.paste(im, (x, pad_top))
        draw.text((x, pad_top + card_h + 8), captions[i], fill=(70, 70, 70), font=font_s)
    canvas.save(dest)
    return dest


def main():
    slots = json.loads((ROOT / 'templates' / 'slots.json').read_text())
    report = {'chroma': {}, 'cleanup': {}, 'title': {}, 'template_compare': {}, 'fullcard_masked_compare': {}, 'chosen': {}}

    for style, raw_name, out_name in [
        ('A', 'styleA_char_v3.jpg', 'styleA_char_cardputerzero.png'),
        ('B', 'styleB_char_v3.jpg', 'styleB_char_cardputerzero.png'),
    ]:
        raw = Image.open(ROOT / 'chars' / 'raw' / raw_name)
        info = chroma_key_lime(raw, ROOT / 'chars' / out_name)
        if style == 'A':
            keyed = Image.open(ROOT / 'chars' / out_name)
            cinfo, cleaned = clean_style_a_garbled_labels(keyed)
            cleaned.save(ROOT / 'chars' / out_name)
            report['cleanup'][style] = cinfo
            info['post_cleanup'] = True
        report['chroma'][style] = info
        print('chroma', style, info['size'], 'opaque', info['opaque_pixels'], 'corners', info['corners_alpha'])
        if style == 'A':
            print('cleanup A', cinfo.get('applied'), 'lack_letters', cinfo.get('lack_tab_letters_painted'))

    title_slot = [42.207, 190.863, 110.863, 215.346]
    title_spec = {
        'text': 'CARDPUTER ZERO',
        'lines': ['CARDPUTER', 'ZERO'],
        'slot_pt': title_slot,
        'stroke_width': 1.95,
        'line_gap': 0.55,
        'font_path': str(OSWALD_VAR),
        'font_family': 'Oswald',
        'wght': 700,
        'font_note': (
            'Original CORE title is outlined path data from the CDR conversion; the source font is not embedded. '
            'This title is newly typeset from locally installed Oswald variable font instantiated at weight 700, '
            'converted to glyph paths with fontTools, then drawn as the SAME path twice (black stroke with round '
            'joins, then white fill). It is stacked as CARDPUTER / ZERO so the long product name stays inside the '
            'original CORE title slot [42.207, 190.863, 110.863, 215.346] without covering the yellow slogan capsule '
            'or the character. Visible outline thickness is half the stroke (stroke is centered; fill covers the inner half). '
            'This is NOT a 100% match to the original CORE outlined glyphs: Oswald is a substitute face, the original '
            'four-letter CORE lockup cannot be reproduced glyph-for-glyph for a 14-letter name, and the stacked layout '
            'is a fitting choice rather than a source trace.'
        ),
    }
    report['title'] = {
        'method': 'identical-glyph-paths-stroke-then-fill',
        'font': 'Oswald variable @ wght 700 (max axis value)',
        'layout': 'two lines CARDPUTER / ZERO fitted to original CORE title slot',
        'slot_pt': title_slot,
        'stroke_width_pt': 1.95,
        'not_original_outlined_glyphs': True,
        'previous_bug': 'two <text> nodes (black larger+offset, white on top) caused a wide black ghost',
    }

    composites = {}
    for style in ('A', 'B'):
        cfg = slots[style]
        tpl = Path(cfg['template_svg'])
        char_png = ROOT / 'chars' / f'style{style}_char_cardputerzero.png'
        dest_svg = ROOT / 'composites' / f'style{style}_cardputerzero.svg'
        spec = title_spec if style == 'B' else None
        meet = 'xMidYMax meet' if style == 'B' else 'xMidYMid meet'
        embed_image_in_slot(tpl, char_png, cfg['char_union_pt'], dest_svg, spec, meet=meet)
        composites[style] = dest_svg
        print('wrote svg', dest_svg)

        full_png = ROOT / 'composites' / f'style{style}_cardputerzero.png'
        full_im = render_svg_file(dest_svg, full_png)
        print('render full', full_png, full_im.size)

        hidden = hide_slots(dest_svg)
        new_tpl_png = ROOT / 'validation' / f'style{style}_new_template-only.png'
        new_tpl_im = render_svg_bytes(hidden, new_tpl_png)

        old_tpl_png = ROOT / 'templates' / f'style{style}_template-only.png'
        old_tpl_im = Image.open(old_tpl_png).convert('RGBA')
        d = pixel_diff(old_tpl_im, new_tpl_im)
        overlay = Image.fromarray(d['overlay'], 'RGB')
        overlay.save(ROOT / 'validation' / f'style{style}_template_diff_overlay.png')
        report['template_compare'][style] = {
            'diff_pixels': d['diff_pixels'],
            'compared_pixels': d['compared_pixels'],
            'identical': d['identical'],
            'old': str(old_tpl_png),
            'new': str(new_tpl_png),
        }
        print('template compare', style, 'diff', d['diff_pixels'], 'identical', d['identical'])

        orig = Image.open(ROOT / 'source_renders' / f"{cfg['master_stem']}_original.png").convert('RGBA')
        sx = 638 / 153.0708661417323
        sy = 1004 / 240.9448818897638
        boxes = [cfg['char_union_pt']]
        if cfg.get('title_union_pt'):
            boxes.append(cfg['title_union_pt'])
        boxes_px = [[b[0] * sx, b[1] * sy, b[2] * sx, b[3] * sy] for b in boxes]
        mask = rect_mask(np.array(orig).shape, boxes_px, pad=1)
        md = pixel_diff(orig, full_im, mask=mask)
        Image.fromarray(md['overlay'], 'RGB').save(ROOT / 'validation' / f'style{style}_fullcard_masked_diff.png')
        report['fullcard_masked_compare'][style] = {
            'diff_pixels_outside_masks': md['diff_pixels'],
            'compared_pixels': md['compared_pixels'],
            'identical_outside_masks': md['identical'],
            'masks_pt': boxes,
            'masks_px': [[round(v, 2) for v in b] for b in boxes_px],
            'mask_note': 'Union of official char bbox and (Style B) original title bbox only. Title no longer uses an expanded rectangle.',
        }
        print('fullcard masked', style, 'outside diffs', md['diff_pixels'])

        report['chosen'][style] = {
            'composite_png': str(full_png),
            'composite_svg': str(dest_svg),
            'char_png': str(char_png),
            'template_svg': str(tpl),
            'template_only_png': str(old_tpl_png),
            'master': cfg['master_stem'],
            'raster_embed': True,
            'subject_is_not_pure_vector': True,
        }

        tmpl_only = Image.open(old_tpl_png)
        sheet_title = {
            'A': 'Style A master 01_S3 | fixed template | CardputerZero composite',
            'B': 'Style B master 10_CORE | fixed template | CardputerZero composite',
        }[style]
        caps = {
            'A': ['01_S3 original', 'A template-only', 'A composite'],
            'B': ['10_CORE original', 'B template-only', 'B composite'],
        }[style]
        make_triple_sheet(
            orig, tmpl_only, full_im, sheet_title, caps,
            ROOT / 'validation' / f'compare_style{style}_original_template_composite.png',
        )

    (ROOT / 'validation' / 'compare_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('report written')


if __name__ == '__main__':
    main()
