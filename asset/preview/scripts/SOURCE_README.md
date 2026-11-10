# 可复用卡面预览流水线（当前已验证方法）

这是给后续「全产品各一套 char/card」准备的方法说明与脚本。**当前不要用它批量生成全部产品。** 后续批次须等官方操作面正视图核验齐全后，由主助手另行指派。

每张产品卡 = 一张固定模板整卡（card）+ 一张对应的透明主体（char）。禁止：把产品照片直接套进模板、用几何图形代替 AIGC 主体、缺合格官方正视参考时硬画结构。

## 官方文件名与目录

- 文件名用官方英文产品名，无数字序号：`StampFly.png`、`StamPLC.png`、`CoreMatrix.png`、`CardputerZero.png`。
- 不要写成 Core Matrix、StampPLC、Cardputer Zero。
- 交付结构：`asset/char/{style-a,style-b}/官方名.png` 与 `asset/card/{style-a,style-b}/官方名.{png,svg}`。
- 用户拼写的 `asset/offical/` 备份由主助手/cloud 处理，本包不覆盖用户机器或仓库。

## 步骤

1. **核实型号与干净操作面正视**  
   只用已核验的官方操作面正视图（无硬币、称重、尺寸对照、斜视、包装、宣传拼图）。不要把相近型号混用（例如 H050 CardputerZero 不得用 H031 Cardputer）。缺合格参考就停，待补图。

2. **只重画 char 层**  
   用 GenerateImage，参考官方正视 + 对应风格母版 char（`01_S3` 科技模切贴纸 / `10_CORE` 简洁粗线吉祥物）。纯 lime 背景（约 `#B6F400`），封闭内洞不得留 lime。Style A 产品名写在徽章内；Style B 名称走标题槽，不要写在角色上。不要做成照片套卡，不要加卡背/自造二维码。

3. **抠图**  
   `python3 chroma_key.py` 中的 `key_file(src, dest)`：四角洪水填充去 lime，再清理封闭内洞。不要套用旧 CardputerZero 的局部涂字坐标。

4. **背景是可变 token，版式不是**  
   官方 22 张卡是「每张一色高饱和满版底」，不是两套蓝锁死。`recolor_template.py` 只改：
   - Style A 卡身 `fill: #009ee0`（1 处，不是渐变 defs 里的同色 stop）
   - Style B 卡身 `fill: #0079b4`（1 处）和可见脚下椭圆 `fill: #00679a`（1 处）
   - `#005986` 放射残底为 opacity 0，不改；`#ffec00` 标语、商标、文字路径、clip、坐标一律不动。  
   背景色优先取自该产品外壳/按键/标志色，再收成官方卡那样的纯色场；Style B 阴影用同色相约 0.82 加深。这是预览配色，不是官方成品色。记录取样路径与最终 token。

5. **合成**  
   `compose_card.py`：把透明 char 嵌入官方 char 槽（A：`xMidYMid meet`，B：`xMidYMax meet`）。Style B 标题用现成 Oswald 700 路径方案（同一路径黑描边+白填充），只在原 CORE 标题槽内替换，可两行。不要无休止找字体。

6. **差分**  
   不再拿「新底色整卡」去跟旧蓝色 template-only 比全身 0 差。正确规则：在**同色参数化母版**上，隐藏 slot 后 vs 同色 template-only，**diff = 0**。另外可用「除 token 字符串外 SVG 文本完全一致」确认版式未改。

7. **交付与历史**  
   新图进 `asset/`。被替换的旧纯蓝稿、旧试稿进 `history/`，不覆盖。状态标为 preview，不是用户验收成品。

## 脚本

- `chroma_key.py` — 抠图
- `recolor_template.py` — 参数化底色/阴影
- `compose_card.py` — 合成、渲染 638×1004、同色差分
- `build_four_product_previews.py` — 本轮四产品打包入口（CardputerZero 仅在新 char 已生成时合成）
- `../palette.json` — 本轮 token 与产品特征色依据

依赖与现有流程相同：Pillow、numpy、lxml、CairoSVG、fontTools，以及 `/workspace/pulse-card-design/template-rebuild/` 里的官方模板与 `chroma_and_compose` 标题工具。
