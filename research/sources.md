# 来源与研究边界

研究日期：2026-11-10（Asia/Shanghai）  
方法：优先阅读 M5Stack 官方文档 `docs.m5stack.com`、官方商店分类页和官方历史发布页。使用 WebSearch / WebFetch。非购物询价，未采集价格。未克隆、未读取、未修改任何代码仓库。

## 主要来源

| URL | 标题/性质 | 支持的结论 |
| --- | --- | --- |
| https://docs.m5stack.com/en/start | What is M5Stack / 产品与接口总览 | Core/Stick/Atom/Cardputer/Stamp/E-Paper 家族划分；Unit、Module/Base/Faces、Chain 三类扩展；HY2.0-4P 与 M5-Bus 的官方定义；Chain 为 UART 菊花链 |
| https://docs.m5stack.com/en/products | 官方产品总录 | 大量在产控制器、HAT、Module、Base、Faces、Chain、Unit 的名称与芯片标签；用于覆盖面，不代替单页脚位表 |
| https://docs.m5stack.com/en/history | Release History | SKU 与日期：如 CoreMatrix C158（2026-11-06）、ToughC5 K162（2026-10-09）、Faces3 面板（2026-09-04）、StickC-Plus SE K016-P-SE（2026-07-17）、Display 1.14 For StickS3 A183、Stamp-AddOn Cam、8Servos2 U222/U223、Bottom2 v1.3 A014-C-V13、Chain Switch/MIC 等 |
| https://docs.m5stack.com/en/product_i2c_addr | Product I2C Address Index | 部分控制器 SKU（K001-V27、K002、K006-V27、C123、C126、C139、C145/K145、C151、C153 等）及片上 I2C 地址 |
| https://docs.m5stack.com/en/guide/common/dip_switch | What is M5-Bus / DIP Switch | M5-Bus 编号固定、电源脚固定、其它 GPIO 随宿主变化；拨码用途 |
| https://docs.m5stack.com/en/guide/module_gps_v2/pins_change | Module GPS v2 pin change | CORE / CORE2 / CORES3 的 TXD/RXD/PPS 对照 |
| https://docs.m5stack.com/en/core/Basic_v2.7 | Basic v2.7 | 初代脚位、PORT.A/B/C、M5-Bus、IP5306、版本史、2018.2A 无 C2C/PD |
| https://docs.m5stack.com/en/core/Fire_v2.7 | Fire v2.7 | 完整脚位；**GPIO16/17 接 PSRAM** 的官方警告；M5GO 底灯光/麦脚位 |
| https://docs.m5stack.com/en/core/Core2 | Core2 | 触控一体机；PORT 与 M5-Bus；**禁止与任何 Base 系列功能底座叠装**；推荐 Bottom2 |
| https://docs.m5stack.com/en/core/CoreS3 | CoreS3 | 第三代脚位、HVIN、对比 SE/Lite、**BMM150 磁干扰**、microSD 16GB、I2C 地址表 |
| https://docs.m5stack.com/en/core/Tab5 | Tab5 | **ESP32-P4 + ESP32-C6**；单路 Grove；背面 M5-Bus 扩 Module；SKU C145/K145；屏幕驱动改版 |
| https://docs.m5stack.com/en/core/CoreMP135 | CoreMP135 | **STM32MP135 Linux**，非 ESP32；M5-Bus/PORT.A/C；总线 5V 默认关闭 |
| https://docs.m5stack.com/en/core/StickC-Plus2 | StickC-Plus2 | 与 Plus 的 SoC/电源/脚位差异表；HAT 与 Unit 兼容表述；麦克风占用 G0 |
| https://docs.m5stack.com/en/core/StickS3 | StickS3 | Hat2-Bus 16P；**结构不兼容 U156/U157/U080**；Grove G9/G10；EXT_5V 方向警告 |
| https://docs.m5stack.com/en/core/Cardputer | Cardputer | 内嵌 Stamp-S3；单 Grove G2/G1；键盘与电池结构 |
| https://docs.m5stack.com/en/chain/Chain_DualKey | Chain DualKey | 双 UART 口脚位；Bridge 方向；独立可编程宿主 |
| https://docs.m5stack.com/en/arduino/projects/chain/chain_bus | Chain Bus tutorial | Master/Node、STM32G031、ID 从 1 向外、心跳与枚举、类型码、推荐 Atom+ToChain |
| https://docs.m5stack.com/en/accessory/Atomic_ToChain_Base | Atomic ToChain Base | AtomS3/S3R 默认 G5/G6，经典 Atom G22/G19 |
| https://docs.m5stack.com/en/faces/Faces_Bottom3 | Faces Bottom3 | 兼容 Gen1/Gen3 面板与 Core1/Core2/CoreS3；面板总线；LED IO 开关 |
| https://docs.m5stack.com/en/faces/Faces_Keyboard3 | Faces Keyboard3 | STM32F030C8T6，I2C 0x08，A003-V3 |
| https://docs.m5stack.com/en/faces/Faces_Gamepad3 | Faces Gamepad3 | STM32F030F4P6，I2C 0x08，A004-V3 |
| https://docs.m5stack.com/en/hat/Hat_DAC2 | Hat DAC2 | StickC/PLUS/PLUS2；SDA G0 SCL G26；I2C 地址 |
| https://docs.m5stack.com/en/hat/Hat_SPK2 | Hat SPK2 | I2S，3V3 供电 |
| https://docs.m5stack.com/en/hat/Hat_PowerC | Hat PowerC | 面向 StickC；I2C 0x75；例程含 Plus |
| https://docs.m5stack.com/en/base/Base_M5GO_Bottom2_v1.3 | Bottom2 v1.3 | 专为 Core2；A014-C-V13；脚位 |
| https://docs.m5stack.com/en/unit/Unit_Thermal2 | Unit Thermal2 | ESP32-PICO-D4 + I2C 0x33；官方可配合宿主或独立使用 |
| https://docs.m5stack.com/en/unit/Unit_CardKB2 | Unit CardKB2 | ESP32-C61，默认 I2C 键盘（兼其它模式） |
| https://docs.m5stack.com/en/unit/Unit_PaHub_v2.1 | PaHub v2.1 | I2C 多路复用，地址 0x70–0x77 |
| https://docs.m5stack.com/en/compatible | Stack Compatibility | 存在交互式堆叠查看器；本轮未穷尽组合 |
| https://shop.m5stack.com/collections/for-stick | 官方店 For Stick | HAT 名称清单（未用价格） |
| https://shop.m5stack.com/collections/for-stack/faces | 官方店 Faces | Faces3 底盘与三块面板在售 |
| https://shop.m5stack.com/collections/for-chain | 官方店 For Chain | DualKey 与节点/连接件清单 |
| https://docs.m5stack.com/en/uiflow2/uiflow_web | UiFlow2 设备树 | 交叉核对控制器分组（含 Station、Paper、Cardputer、Chain DualKey） |

另参考但未当作单品穷尽依据的页面：产品选择器 <https://docs.m5stack.com/en/products_selector/m5atom_compare?select=K117>；Arduino 文档树中的设备列表（用于发现 Dial/Capsule/DinMeter/Paper 等确有文档条目）。

## 研究范围

已覆盖的主控家族：Core 初代（Basic/Gray/Fire/M5GO）、Core2 及修订/AWS、CoreS3 及 SE/Lite/Thread BR、Tough/ToughC5、Tab5、CoreMatrix、PowerHub、CoreMP135、CM4Stack、Stick 各代（含 Plus SE、StickS3、StickT2）、Atom 主要 SKU、Cardputer 系、Dial/Capsule/DinMeter/Air Quality/VAMeter、Stamp 多代与 StamPLC/S3Bat、Paper 系与 CoreInk、Station、NanoC6/H2、Chain DualKey。

已覆盖的配件层：经典 HAT 与 Hat2 差异、M-Bus 模块与 13.2、Base 与 Core2 特供 Bottom2、Faces3 生态、Chain 节点与连接件、Atomic 桥、Grove Unit 的 I2C/GPIO/UART 分流及若干带 SoC 的边界 Unit。

## 未覆盖与诚实的缺口

- 官方 Unit / Module 还有大量单品未逐页打开（电机、工业采集、老款 COMX、部分摄像头套件等）。目录用「家族代表 + 成对差异型号」而不是假装扫完 SKU 全集。
- 交互式 Stack Compatibility 与 Stack Screw Length 未逐条导出。
- Faces 第一代面板的旧地址/旧固件、Calculator3 的精确 I2C 地址未复核。
- StickS3 对其它经典 HAT（除点名的三件）的物理能否插入：未知。
- Tough、Station、多数 Stamp 成品、Paper 是否具备完整 M5-Bus：本轮未全部抓取脚位表。
- Unit Thermal2 独立使用时的具体固件能力未展开。
- 未做实验室插拔验证。所有「支持 / 需拨码 / 冲突」均来自文档陈述，不是实测。
- 未读取用户仓库中现有 12 英雄 + 2 战术的正式卡名，集成时需要人工对名去重。

## 歧义

- 官方文案常说 Unit「可轻松连接各种主控」，同时各主控脚位表又把 Grove 口分成 I2C / GPIO / UART。本文件以脚位表和「I2C 版 vs IO 版」这种成对 SKU 为准，不把营销句写成万能兼容。
- 「有 MCU」在 M5 生态里经常只是外设上的 STM32/ESP32。分类必须看它是不是独立可编程宿主。
- Core2 的 Base 禁令写得很死；该禁令是否延伸到 CoreS3/Tab5/Tough **没有**被本轮文档支持，故保持未知。
- Plus2 麦克风与 HAT SDA 共用 G0：有引脚表依据，但没有官方「禁止使用 HAT」的句子。

不声称穷尽产品线，不把未查到写成不兼容，不捏造验证。
