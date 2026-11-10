#!/usr/bin/env python3
"""Lime-screen chroma key for AIGC character rasters.

Corner flood-fill removes the backdrop. Enclosed lime (holes between
LEDs, badge cutouts, etc.) is recolored from local non-lime neighbors
so it cannot pollute the card face. This is cleanup, not a redraw.

Do not import the CardputerZero-specific label-wipe helpers here.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


def chroma_key_lime(im: Image.Image) -> tuple[Image.Image, dict]:
    rgba = np.array(im.convert('RGBA'))
    rgb = rgba[:, :, :3].astype(np.int16)
    h, w = rgb.shape[:2]
    corners = [tuple(int(x) for x in rgba[y, x, :3]) for y, x in
               [(2, 2), (2, w - 3), (h - 3, 2), (h - 3, w - 3)]]
    key = np.median(np.array(corners), axis=0).astype(np.float32)
    dist = np.sqrt(((rgb.astype(np.float32) - key) ** 2).sum(axis=2))
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    greendominant = (g > r + 20) & (g > b + 20) & (g > 120)
    screenish = (dist < 55) | greendominant
    visited = np.zeros((h, w), dtype=bool)
    q = deque()
    for y, x in [(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1),
                 (0, w // 2), (h - 1, w // 2), (h // 2, 0), (h // 2, w - 1)]:
        q.append((y, x))
        visited[y, x] = True
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
    dil[1:] |= bg[:-1]
    dil[:-1] |= bg[1:]
    dil[:, 1:] |= bg[:, :-1]
    dil[:, :-1] |= bg[:, 1:]
    edge = dil & (~bg)
    extra = np.clip(g - np.maximum(r, b), 0, 255)
    g2 = g.copy()
    fix = edge & (extra > 6)
    g2[fix] = np.maximum(r[fix], b[fix])
    rgb2 = rgb.copy()
    rgb2[:, :, 1] = g2
    rgba2 = np.dstack([np.clip(rgb2, 0, 255).astype(np.uint8), alpha])
    out = Image.fromarray(rgba2, 'RGBA')
    bbox = out.getbbox()
    if bbox is None:
        raise RuntimeError('chroma key emptied the image')
    x0, y0, x1, y1 = bbox
    pad = 4
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(out.width, x1 + pad), min(out.height, y1 + pad)
    out = out.crop((x0, y0, x1, y1))
    arr = np.array(out)
    arr[arr[:, :, 3] == 0, :3] = 0
    out = Image.fromarray(arr, 'RGBA')
    opaque = int((arr[:, :, 3] > 8).sum())
    fringe = int(((arr[:, :, 3] > 8) & (arr[:, :, 3] < 250)).sum())
    corners_a = [int(out.getpixel((0, 0))[3]), int(out.getpixel((out.width - 1, 0))[3]),
                 int(out.getpixel((0, out.height - 1))[3]),
                 int(out.getpixel((out.width - 1, out.height - 1))[3])]
    info = {
        'size': list(out.size),
        'source_corners_rgb': [list(c) for c in corners],
        'opaque_pixels': opaque,
        'partial_alpha_pixels': fringe,
        'corners_alpha': corners_a,
        'method': 'Corner flood-fill of screen-similar pixels (RGB dist<55 OR green-dominant). Edge despill only.',
    }
    return out, info


def clean_enclosed_lime(im: Image.Image) -> tuple[Image.Image, dict]:
    """Recolor leftover opaque lime so it cannot show through on the card."""
    arr = np.array(im.convert('RGBA')).copy()
    rgb = arr[:, :, :3].astype(np.int16)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    a = arr[:, :, 3]
    # Only treat leftover pixels that still look like the chroma screen
    # (near the typical lime key), not product greens such as a Python logo
    # or a Stamp-S3 color block.
    dist_lime = np.sqrt((r.astype(np.float32) - 180) ** 2 + (g.astype(np.float32) - 230) ** 2 + (b.astype(np.float32) - 40) ** 2)
    lime = (a > 8) & (g > r + 20) & (g > b + 20) & (g > 120) & (dist_lime < 90)
    n = int(lime.sum())
    if n == 0:
        return im, {'enclosed_lime_pixels': 0, 'recolored': 0}
    yy, xx = np.where(lime)
    h, w = a.shape
    recolored = 0
    for y, x in zip(yy, xx):
        y0, y1 = max(0, y - 3), min(h, y + 4)
        x0, x1 = max(0, x - 3), min(w, x + 4)
        patch = arr[y0:y1, x0:x1]
        pr, pg, pb, pa = patch[:, :, 0], patch[:, :, 1], patch[:, :, 2], patch[:, :, 3]
        good = (pa > 8) & ~((pg > pr + 20) & (pg > pb + 20) & (pg > 120))
        if int(good.sum()) >= 3:
            arr[y, x] = np.median(patch[good], axis=0)
        else:
            arr[y, x, :3] = (20, 20, 20)
            arr[y, x, 3] = 255
        recolored += 1
    arr[arr[:, :, 3] == 0, :3] = 0
    return Image.fromarray(arr, 'RGBA'), {'enclosed_lime_pixels': n, 'recolored': recolored}


def key_file(src: Path, dest: Path) -> dict:
    raw = Image.open(src)
    keyed, info = chroma_key_lime(raw)
    cleaned, cinfo = clean_enclosed_lime(keyed)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cleaned.save(dest)
    info['enclosed_lime'] = cinfo
    info['source'] = str(src)
    info['output'] = str(dest)
    return info
