# 四产品卡面预览

状态：**preview_not_accepted**。文件已入库。这批配色和主体都还没有验收。

## 当前文件

官方名无序号，style 由父目录区分：

`asset/char/{style-a,style-b}/StampFly.png`  
`asset/char/{style-a,style-b}/StamPLC.png`  
`asset/char/{style-a,style-b}/CoreMatrix.png`  
`asset/char/{style-a,style-b}/CardputerZero.png`

卡面 PNG 与 SVG 在对应的 `asset/card/{style-a,style-b}/`。合计 8 张透明角色图、8 张卡面 PNG、8 张卡面 SVG。八张卡面都是 638×1004 RGBA。

| 官方名 | 说明 |
| --- | --- |
| StampFly | 官方写作 StampFly。页面 https://docs.m5stack.com/en/app/StampFly |
| StamPLC | 官方写作 StamPLC，SKU K141 |
| CoreMatrix | 官方写作 CoreMatrix，SKU C158 |
| CardputerZero | 官方写作 CardputerZero，H050 / C154。H031 Cardputer 是另一款产品 |

原 22 张卡和角色图仍在 `asset/card/`、`asset/char/` 根目录，字节备份在 `asset/offical/`。这批预览没有改写那些文件。

## 配色

每张预览使用自己的高饱和满版底。Style B 的脚下椭圆是同色相约 0.82 加深。数值、取样依据和「这不是官方成品配色」写在 `palette.json`。附件原文在 `SOURCE_README.md` 与 `source_manifest.json`；里面的设计机路径只说明取样来源，不是本仓库的文件。

| 产品 | Style A | Style B 卡身 / 阴影 |
| --- | --- | --- |
| StampFly | `#f33e1a` | `#f33e1a` / `#c73215` |
| StamPLC | `#d23331` | `#0884cc` / `#066ca7` |
| CoreMatrix | `#b44343` | `#5c7cbc` / `#4b659a` |
| CardputerZero | `#c83711` | `#ab419d` / `#8c3580` |

## 固定层

八张卡都已用仓库内模板重渲：隐藏 slot 后对比同一 token 的 template-only，像素差为 0，比较像素 640552。报告在 `validation/fixed_layer_report.json`。重跑：

```
python3 asset/preview/scripts/verify_fixed_layer.py
```

## CardputerZero Style A 小字

当前角色图 SHA-256 是 `042f9e4ecf3735ac1dc2457b217e2f1476c2a536f20ae64c2d9cc3f8cba137be`。名牌为 ESC HOME，电源条为 LOCK。改字前的稿在 `archive/history/cardputerzero-style-a-before-lettering-fix/`，角色图 SHA-256 是 `7e38bd9c2f7fe3ef99cb03d09d4b5b8e43b54090009271bb87360b23b53b4189`。Style B 和其他三款产品没有跟着改字。

旧纯蓝稿和更早的失败试稿也在 `archive/history/`。`asset/concepts/cardputerzero/` 仍是 superseded，`asset/concepts/cardputerzero-template/` 仍是 needs_revision。它们都不是这批当前文件。
