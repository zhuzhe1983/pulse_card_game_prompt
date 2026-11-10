#!/usr/bin/env python3
"""Re-check the eight preview cards against same-color parameterized templates.

Renders each delivered card SVG with its character and title slots hidden,
renders the in-repo 01_S3 or 10_CORE template after substituting that card's
background token, and requires a pixel diff of 0. Also compares those renders
to the validation PNGs stored beside this script when they are present.

Does not regenerate characters, recolor the official 22-card files, or write
outside asset/preview/validation/fixed_layer_report.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "asset" / "concepts" / "cardputerzero-template" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chroma_and_compose as cc
from recolor_template import recolor_svg_text

PRODUCTS = ["StampFly", "StamPLC", "CoreMatrix", "CardputerZero"]
TEMPLATES = {
    "style-a": "asset/concepts/cardputerzero-template/templates/styleA_template_01_S3.svg",
    "style-b": "asset/concepts/cardputerzero-template/templates/styleB_template_10_CORE.svg",
}


def main() -> int:
    palette = json.loads((REPO / "asset" / "preview" / "palette.json").read_text(encoding="utf-8"))
    template_text = {key: (REPO / rel).read_text(encoding="utf-8") for key, rel in TEMPLATES.items()}
    out_dir = REPO / "asset" / "preview" / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    for product in PRODUCTS:
        for style_name, style in (("style-a", "A"), ("style-b", "B")):
            token = palette["products"][product][style_name.replace("-", "_")]
            recolored, report = recolor_svg_text(template_text[style_name], style, token["card_bg"], token.get("shadow"))
            svg_rel = f"asset/card/{style_name}/{product}.svg"
            hidden = cc.hide_slots(REPO / svg_rel)
            hidden_im = cc.render_svg_bytes(hidden, out_dir / f".{product}_{style_name}_hidden.png")
            template_im = cc.render_svg_bytes(recolored.encode("utf-8"), out_dir / f".{product}_{style_name}_template.png")
            diff = cc.pixel_diff(template_im, hidden_im)
            pack_hidden = out_dir / f"{product}_{style_name}_hidden_slots.png"
            pack_template = out_dir / f"{product}_{style_name}_template-only.png"
            hidden_vs_pack = cc.pixel_diff(hidden_im, Image.open(pack_hidden).convert("RGBA"))["diff_pixels"] if pack_hidden.is_file() else None
            template_vs_pack = cc.pixel_diff(template_im, Image.open(pack_template).convert("RGBA"))["diff_pixels"] if pack_template.is_file() else None
            cards.append({
                "product": product,
                "official_name": product,
                "style": style_name,
                "card_bg": report["card_bg"],
                "shadow": report["shadow"],
                "card_svg": svg_rel,
                "card_png": f"asset/card/{style_name}/{product}.png",
                "char_png": f"asset/char/{style_name}/{product}.png",
                "template": TEMPLATES[style_name],
                "diff_pixels": diff["diff_pixels"],
                "compared_pixels": diff["compared_pixels"],
                "identical": diff["identical"],
                "rerender_vs_stored_hidden_slots": hidden_vs_pack,
                "rerender_vs_stored_template_only": template_vs_pack,
            })
            print(product, style_name, "diff", diff["diff_pixels"])
    for path in out_dir.glob(".*_hidden.png"):
        path.unlink()
    for path in out_dir.glob(".*_template.png"):
        path.unlink()
    result = {
        "status": "preview_not_accepted",
        "rule": "same-color parameterized master; hidden slots versus template-only must differ by 0 pixels",
        "all_identical": all(item["identical"] for item in cards),
        "cards": cards,
    }
    report_path = out_dir / "fixed_layer_report.json"
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", report_path.relative_to(REPO))
    return 0 if result["all_identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
