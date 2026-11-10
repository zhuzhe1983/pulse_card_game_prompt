# 角色主体提取（透明 PNG）

输出到游戏素材目录：`asset/char/*.png`（22 张）。
本目录仅保留可重跑脚本、manifest、主体 SVG 审阅件与联系预览，不打包 zip，不提交 CDR/整页设计稿。

## 规则摘要
- 去掉卡底色、放射底、顶标、标题、标语、底部 logo 胶囊、脚下色底椭圆。
- 18–22 优先去掉烟花/星点等场景装饰；保留角色、帽子与手持道具。
- 长边 1024px，按主体宽高比缩放，约 6pt 安全留白；RGBA，角透明。
- 01/04/05/06 文件名仍为待核实中性名，未假装确认产品名。

## 重跑
依赖与 V2 卡片导出相同（CairoSVG 等）。在已有逐卡 SVG 上：

```sh
python3 extract_chars.py \
  --cards-svg-dir ../svg \
  --manifest ../manifest.json \
  --out-png /ABS/path/to/pulse_card_game_prompt/asset/char \
  --out-review ./out_review \
  --long-edge 1024
```

不要把 CDR、整页 SVG、本审阅目录默认提交到公开 git；用户自行决定哪些 PNG 可上传。
