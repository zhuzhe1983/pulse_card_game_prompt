# 16 · 原卡两种面貌，以及一轮已经放弃的试做

卡面用来认出设备和收藏。不要在卡面上加攻击、生命或未定稿的战力数字。战力若需要，以冻结卡包或草案正文为准，不画进宣传图。

## 原卡

`asset/card/` 的 22 张都是 638×1004、RGBA、圆角。测量见 `docs/visual/original_card_metrics.json`。它们是两组商品/宣传卡，不是已经填好数值的对战卡。

**01–09** 是居中的技术贴纸：顶上短句，中间厚白边的扁平插画，下面两行说明和一个白胶囊。几乎没有地面影子。04 画的是 Cardputer ADV，不能当作 CardputerZero。

**10–22** 是拟人海报：左上标志，角色加粗白边和椭圆影子，底部大标题，多数还有黑底黄字胶囊。10–17 更像产品变成生物，18–22 加上戏曲和节庆服饰，仍是同一套版式。

这是对原图的观察，不是「已经有一套生成流程可以百分百复刻」。两组内部也有底色和外形差别。

PULSE 文字和原立方图形的组合只是概念处理，不是已经定稿的原创标志，也不要写成官方新品牌。

## 试做状态

第一轮用生成图直接模仿整张卡，两种面貌各做了 v1 到 v4，共三轮修改。这些文件在 `asset/concepts/cardputerzero/`。

这一轮 **已经放弃，不推荐，也不是验收稿**。它没有使用固定的 SVG 模板和角色层，主体和版式都由生成模型一起画出，不能当成风格已经复刻。

另外，成稿是 864×1152 JPEG，比例和原卡 638×1004 不一致，没有透明圆角，没有出血，不能印刷，也不能替换 `asset/card/` 或客户端正式卡图。A 路仍然像产品渲染，平面机械贴纸不够。B 路的立体掌机和外伸 USB 还需要按实物核对。

固定模板加主体的预览已经放在 `asset/concepts/cardputerzero-template/`。状态是 **needs_revision**。它不是验收稿，也不是风格已经一致。

能说的只有：母版是 01_S3 和 10_CORE 的 SVG；隐藏动态槽后，以及角色/标题遮罩外面，CairoSVG 638×1004 的像素差是 0。主体是嵌进 SVG 的 PNG。A 的右上有平色修补，B 的标题是 Oswald 转曲的两行字，不是原 CORE 那套字形。模板上的 Tap to Build、NTAG215 和 M5STACK 仍是原卡文字，不是游戏的新标志。

## 四产品预览

StampFly、StamPLC、CoreMatrix、CardputerZero 的 style-a 与 style-b 在 `asset/char/` 和 `asset/card/` 的对应目录。合计 8 张透明角色 PNG、8 张卡面 PNG、8 张卡面 SVG，文件名是官方英文名，没有序号。CardputerZero 对应 H050。H031 Cardputer 仍是另一款产品。

状态是 preview_not_accepted。每张卡用自己的产品特征色做满版底，色值在 `asset/preview/palette.json`。这些是预览 token，不是官方成品卡配色。固定层只和同一 token 参数化后的 01_S3 或 10_CORE 模板比较；八张卡隐藏槽位后的像素差是 0。复核脚本是 `asset/preview/scripts/verify_fixed_layer.py`。

当前 CardputerZero Style A 角色图已把名牌写成 ESC HOME，电源条写成 LOCK。改字前的稿、旧蓝底预览和更早失败试稿在 `archive/history/`，不能当作当前文件。`asset/concepts/` 里的旧稿仍分别是 superseded 和 needs_revision。原 22 张卡的字节没有因为这批预览改动。
