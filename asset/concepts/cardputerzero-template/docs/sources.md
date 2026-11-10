# 来源

## 官方卡片矢量

用户本机 `card_export_v2_review/`。仓库只收了 01_S3 与 10_CORE 这两张母版及其角色层，没有收进整个导出目录。

- `README_v2_修复说明.md`、`manifest.json`、`validation.json`
- `char_extract/README_角色提取.md`、`char_extract/char_manifest.json`、`char_extract/extract_chars.py`
- 逐卡 SVG 实际路径：`card_export_v2_review/svg/*.svg`
- 提取角色：`card_export_v2_review/char_extract/char_svg/*.svg`

选择逻辑以 `extract_chars.select_subject()` 与 `char_manifest.json` 的 notes/selected/union_local_bbox 为准。

## CardputerZero

沿用上一轮官方文档与主图：https://docs.m5stack.com/en/CardputerZero  
`C154-CardputerZero-main-pictures_06` 等 docs OSS 照片，仅作主体结构参考。

## 字体

- 固定层原字：全部为转曲 path，本轮未改。
- 新 B 标题：本机 `/usr/share/fonts/truetype/sand-box/google/Oswald/Oswald-VariableFont_wght.ttf`，CSS 名 Oswald，weight 700。不是原稿 CORE 字体。18–22 曾用 Carlito 替代 Calibri，与本张 10_CORE 无关。

## 生成工具路径

见 `chars/raw/` 与下方工具原件：

- A v3：`chars/raw/styleA_char_v3.jpg`
- B v3：`chars/raw/styleB_char_v3.jpg`
