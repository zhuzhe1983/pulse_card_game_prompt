# 可复用卡面预览流水线

这是后续「每产品一套 char/card」的方法说明。不要用它批量生成全部产品。后续批次须等官方操作面正视图核验齐全后另行指派。

每张产品卡是一张固定模板整卡，加上一张透明主体。不要把产品照片直接套进模板，不要用几何图形代替 AIGC 主体，缺合格官方正视参考时就停。

## 本仓库里可以重跑的部分

`verify_fixed_layer.py` 用仓库内的 `01_S3` / `10_CORE` 模板，按 `asset/preview/palette.json` 的 token 参数化，再与 `asset/card/style-a`、`asset/card/style-b` 里隐藏槽位后的 SVG 比较。八张卡的像素差都应为 0。

```
python3 asset/preview/scripts/verify_fixed_layer.py
```

依赖与模板合成相同：Pillow、numpy、lxml、CairoSVG、fontTools。脚本只改写 `asset/preview/validation/fixed_layer_report.json`。

`chroma_key.py`、`recolor_template.py`、`compose_card.py` 是抠图、底色 token 和合成模块。模板路径已指向 `asset/concepts/cardputerzero-template/`。设计机上的批量入口和错字修复脚本会改写设计机档案并重新打包，没有放进本仓库。错字修复的结果是当前 `asset/char/style-a/CardputerZero.png`，修复前的稿在 `archive/history/cardputerzero-style-a-before-lettering-fix/`。

## 步骤

1. 核实型号与干净操作面正视。只用已核验的官方操作面正视图。H050 CardputerZero 不使用 H031 Cardputer。缺合格参考就停。
2. 只重画 char 层。参考官方正视和对应风格母版 char。纯 lime 背景，封闭内洞不得留 lime。Style A 的产品名写在徽章内。Style B 的名称走标题槽。
3. 用 `chroma_key.py` 的 `key_file` 抠图。不要套用旧 CardputerZero 的局部涂字坐标。
4. 背景是可变 token。`recolor_template.py` 只改 Style A 卡身一处 `#009ee0`、Style B 卡身一处 `#0079b4` 和可见脚下椭圆一处 `#00679a`。`#005986` 放射残底、`#ffec00` 标语、商标、文字路径、clip 和坐标不动。
5. `compose_card.py` 把透明 char 嵌入官方 char 槽。Style B 标题用 Oswald 700 的同一路径描边加填充，只替换原 CORE 标题槽。
6. 差分比较同色参数化母版。隐藏 slot 后与同色 template-only 的 diff 必须为 0。不拿新底色整卡去和旧蓝色 template-only 比全身。
7. 新图进 `asset/char` 与 `asset/card` 的 style 目录。被替换的旧稿进 `archive/history/`。状态是 preview，尚未验收。

设计包原文保存在 `SOURCE_README.md`。
