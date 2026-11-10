# CardputerZero 模板预览（needs_revision）

状态：**needs_revision / 当前预览。** 不是 accepted，不是 final，也不是风格已经 100% 一致。不要把合成图当成印刷稿或客户端正式卡图。

这一轮只证明：固定模板被复用时，隐藏动态槽之后，以及整卡在角色/标题遮罩之外，CairoSVG 638×1004 的像素差是 0。这不代表主体画好了。

## 预览在哪

包里没有单独的 final 文件。当前预览就是下面两张合成图：

| 预览 | 文件 |
| --- | --- |
| 风格 A | `composites/styleA_cardputerzero.png` 与同名 `.svg` |
| 风格 B | `composites/styleB_cardputerzero.png` 与同名 `.svg` |

主体透明图在 `chars/styleA_char_cardputerzero.png`、`chars/styleB_char_cardputerzero.png`。它们是嵌进 SVG 的 PNG，不是纯矢量。`chars/raw/*_v3.jpg` 与被删掉的 selected 副本字节相同，所以只保留 v3。

## 已经看见的问题

- 风格 A 右上有一块明显的平色修补，是清掉乱码后留下的，不是原徽章。
- 风格 B 的新标题用 Oswald 700 转成路径，排成两行。它不是原卡 CORE 的同一套转曲字形。
- 固定层仍是母版上的 `Tap to Build`、`NTAG215 NFC Card`、`Powered by M5Stack` 和 `M5STACK`。这些是原模板文字，不是脉冲对决的原创标志。

## 母版

| 风格 | 母版 | 来源 |
| --- | --- | --- |
| A | `source_masters/01_S3.svg` | 本机 `card_export_v2_review` 的 01_S3。现行原卡文件名是 `asset/card/S3.png`，字节未改。 |
| B | `source_masters/10_CORE.svg` | 本机同一导出里的 10_CORE |

角色层：`source_masters/char_01_S3.svg`、`source_masters/char_10_CORE.svg`。槽位：`templates/slots.json`。合成脚本：`scripts/chroma_and_compose.py`。差分记录：`validation/compare_report.json`。

上一轮整卡生成仍在 `asset/concepts/cardputerzero/`，状态 superseded，不推荐。`asset/card/` 的 22 张原卡没有被这套预览覆盖。
