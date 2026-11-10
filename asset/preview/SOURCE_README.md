# PULSE NFC 卡面预览档案（四产品）

状态：**preview，不是用户验收成品。** 重做授权不等于接受新稿。未改仓库，未改用户机器文件。

## 官方文件名（无序号）

| 官方名 | 说明 |
| --- | --- |
| StampFly | 官方写作 StampFly |
| StamPLC | 官方写作 StamPLC（SKU K141） |
| CoreMatrix | 官方写作 CoreMatrix，不要写成 Core Matrix（SKU C158） |
| CardputerZero | 官方写作 CardputerZero（H050 / C154）。不要写成 Cardputer Zero，不要与 H031 Cardputer 混用 |

目录：`asset/char/{style-a,style-b}/官方名.png` 与 `asset/card/{style-a,style-b}/官方名.{png,svg}`。

用户提到的 `asset/offical/`（保留该拼写）用于把更早的 asset/char 与 asset/card 备份进去，由主助手/cloud 在入库时复制；本包按新结构交付。

## 配色（不是官方成品色）

官方 22 张卡是「每张一色高饱和满版底」，不是两套蓝锁死。本轮按各产品外壳/按键/标志色选取背景，Style B 脚下椭圆用同色相约 0.82 加深。版式、字体、标志位置不变。详见 `palette.json` 与 `manifest.json`。

| 产品 | Style A 卡身 | Style B 卡身 / 阴影 | 依据 |
| --- | --- | --- | --- |
| StampFly | `#f33e1a` | `#f33e1a` / `#c73215` | 官方俯拍电机轴套橙色 (243,62,26) |
| StamPLC | `#d23331` | `#0884cc` / `#066ca7` | 官方正视 PWR-CAN 红 / PWR-485 蓝 |
| CoreMatrix | `#b44343` | `#5c7cbc` / `#4b659a` | 电池口红色；LED 光晕提饱和。主体未重画 |
| CardputerZero | `#c83711` | `#ab419d` / `#8c3580` | 电源拨杆橙；Shift 键紫（H050 正视） |

旧纯蓝整卡在 `history/all-blue-previews/`。CardputerZero 旧试稿在 `history/cardputerzero-needs_revision/`。

## 模板验证

全部 8 张：在同色参数化母版上，隐藏 slot 后 vs 同色 template-only，**diff = 0**。SVG 除 1–2 处底色/阴影 token 外与官方模板一致。

## 后续全产品批次

方法与脚本在 `scripts/README.md`。每产品仍须：合格官方操作面正视、AIGC 重画 char（禁止照片套模板或几何代替）、抠图、参数化底色、同色差分。缺参考就待补。当前不要扩张到全目录批量生成。

## 预览图

- `validation/compare_all_cards_colorized.png`
- `validation/compare_all_chars.png`

## 本轮勘误（CardputerZero Style A 小字）

在不改四产品风格、不改固定模板文字/商标、不改配色 token 的前提下，对 CardputerZero Style A 主体图做了局部像素修复：

- 名牌黑条误植 **ESC HAME** 改为正确的 **ESC HOME**（只替换其中的 A 为与相邻字母笔画粗细匹配的 O）。
- 电源区 **LOCK** 中用挂锁图形代替 O 的乱码，改为正常 O，读作 LOCK TAB。
- 方式：已抠好的透明 char 局部编辑，不重跑 AIGC；再用同一张 `#c83711` 参数化官方母版重拼 Style A 整卡。Style B 与其余三产品未改。
- 错字版原图保留在 `history/cardputerzero-style-a-before-lettering-fix/`，供审计。更早的旧试稿与纯蓝预览仍在原 history 目录/历史包中。

