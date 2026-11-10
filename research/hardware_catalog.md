# M5Stack 硬件原始目录（脉冲对决研究用）

研究日期：2026-11-10（Asia/Shanghai）  
主表：`hardware_catalog.csv`（95 条已核实记录）  
说明：这不是官方产品线的穷尽清单。部分记录是**同一家族的代表型号或明确成对差异型号**（例如 Ultrasonic-I2C / Ultrasonic-IO、8Servos2-I2C / 8Servos2-Chain、CoreS3 / SE / Lite）。未查到的字段标为「未知」，未查到不得写成不兼容。

## 如何阅读

- **independent programmable host**：能独立烧录/运行自己的应用程序，适合作为游戏英雄或将军。
- **auxiliary MCU peripheral**：板上有 STM32、甚至 ESP32，但默认作为 I2C/UART 外设听命于宿主。不能因为「有芯片」就升格为英雄。
- **机械接口 ≠ 电气协议 ≠ 软件驱动**。HY2.0-4P 既出现在 Grove Unit 上，也出现在 Chain 总线上，协议完全不同。
- SKU 只在官方 I2C 索引、历史发布页或产品页明确写出时填写。

## 家族覆盖（本目录实际写到的）

### 带主控 / 可独立编程宿主

| 家族 | 代表记录 | 主控线索 | 扩展接口线索 |
| --- | --- | --- | --- |
| Core 初代 | Basic v2.7、Gray、Fire v2.7、M5GO IoT Kit v2.7 | ESP32-D0WDQ6 类 | M5-Bus + PORT.A/B/C |
| Core2 | Core2 / v1.1 / v1.3 / AWS | ESP32-D0WDQ6-V3 | M5-Bus；UART 脚位与初代不同；官方禁止与 Base 系列结构叠装 |
| CoreS3 | CoreS3 / SE / Lite / Thread BR | ESP32-S3（Thread BR 另有 ESP32-H2 伴随无线电） | M5-Bus 脚位第三次重排；带摄像头/九轴的 SKU 需注意磁干扰 |
| 坚壳 / 新射频 | Tough、ToughC5 | ESP32 / ESP32-C5 | ToughC5 为 Wi-Fi 6 双频 + 802.15.4，不是经典 ESP32 |
| Tab | Tab5 / Tab5 Kit | **ESP32-P4 + ESP32-C6** | 一块 Grove PORT.A + 背面 M5-Bus + Stamp 焊盘 |
| 其他 Core 形态 | CoreMatrix、PowerHub、CoreMP135、CM4Stack | C61 / S3+STM32辅控 / **STM32MP135 Linux** / **树莓派 CM4** | 并非都是 ESP32 |
| Stick | StickC、Plus、Plus2、Plus SE、StickS3、StickT2 | PICO-D4 / PICO-V3-02 / S3-PICO | 经典 HAT（G0/G26）与 StickS3 的 Hat2-Bus（16P）不是同一张图 |
| Atom | Lite、Matrix、AtomS3/Lite、AtomS3R 系列、Voice | PICO-D4 / S3 | Atomic 底座；经 Atomic ToChain 可做 Chain 主机 |
| Cardputer | Cardputer、v1.1、Adv / Mesh Kit | 内嵌 Stamp-S3 / S3A | 单路 Grove；无 M5-Bus |
| Stamp 躯壳产品 | Dial、Capsule、DinMeter、Air Quality、VAMeter、StamPLC | 多为 ESP32-S3 | 官方总览把它们放在 Stamp 主控谱系 |
| 裸 Stamp | S3/S3A、S3Bat、Pico/C3/C5/C6LoRa/P4 | 多代 SoC | 通常要嵌入载板才成为完整可用产品 |
| 墨面 | Paper v1.1、PaperS3、PaperColor/Mono/DIY、CoreInk | ESP32 或 ESP32-S3R8 | 不要默认能叠 Core 模块 |
| Station / Nano | Station-Bat/485、NanoC6、NanoH2 | ESP32 / C6 / H2 | H2 官方标签强调 802.15.4，未写 Wi-Fi |
| Chain 主机 | Chain DualKey | ESP32-S3FN8 | 双路 UART Chain 总线，不是 I2C Grove |

### 无独立主控 / 强绑定配件

| 家族 | 代表记录 | 依赖 |
| --- | --- | --- |
| HAT | DAC2、SPK2、经典喇叭、ToF、PIR、Mini JoyC、Mini EncoderC、18650C、JoyC、ENV III、Thermal/NCIR/Heart、舵机类、RS485/ADC/Yun、PowerC | 经典 Stick；StickS3 仅官方点名 3 个结构不兼容 SKU，其余经典 HAT 适配标未知 |
| M-Bus Module / 13.2 / Base | GPS v2（DIP）、通信模块组、13.2 家族、LLM 模块、M5GO Bottom、Bottom2、其他 Base | Core 主机；Core2 不可叠普通 Base，应改 Bottom2 |
| Faces | Bottom3、Keyboard3、Gamepad3、Calculator3 | Bottom 接 Core；面板是 STM32 I2C 外设 |
| Chain 节点 / 连接件 | 各类 Chain 节点、Bridge/Return、8Servos2-Chain | DualKey 或 Atom+ToChain；节点多为 STM32G031 |
| Atomic | ToChain、ToUnit 及其他 Atomic 底座 | Atom 底部只能坐一个底座 |
| Unit | I2C / GPIO / UART 三类，外加 PaHub、PbHub、Thermal2、CardKB2、相机/视觉、PoE-P4 等 | 口类型必须匹配；有 SoC 的 Unit 默认仍是外设 |

## MCU 分类原则（写进游戏前必读）

1. **独立可编程宿主**才优先做英雄：Core / Stick / Atom / Cardputer / Stamp 成品 / Paper / Tab5 / Chain DualKey / Station / Nano / 部分相机 Unit。
2. **辅助 MCU 外设**做随从或装备：Faces 面板、多数 HAT 舵机/摇杆、Chain 节点、8Servos、CardKB v1.1、PbHub。
3. **边界例子**必须单独标注，不能一刀切：
   - Unit Thermal2：有 ESP32-PICO-D4，对宿主走 I2C 0x33；官方写明也可独立使用。默认仍是 Unit 装备，只有设计明确启用「独立模式」时才可考虑稀有侦察英雄。
   - Unit CardKB2：有 ESP32-C61，默认为 I2C 键盘 Unit，兼 BLE HID。默认不升英雄。
   - Module LLM 的 AX630C、Gateway 上的 ESP32-H2、Tab5/CoreS3 Thread 的伴随无线电：都是伴随计算/无线，不是第二名英雄。
   - TimerCamera / UnitV2：更接近独立视觉宿主，但也不是 M-Bus 堆叠将军。
4. **不是所有宿主都是 ESP32**。Tab5 是 P4+C6，CoreMP135 是 STM32MP1 Linux，CM4Stack 是 BCM2711，UnitV2 是 SSD202D，ToughC5 是 ESP32-C5。

## 证据强度

- **high**：本轮完整抓取了对应产品页或教程页，并引用了其中的明确句子/脚位表。
- **medium**：来自官方产品总录 `docs.m5stack.com/en/products`、I2C 索引或 Release History，或只核对了差异表。
- 交互式 [Stack Compatibility](https://docs.m5stack.com/en/compatible) 存在，但本轮只抓到页面外壳，没有穷尽每一种堆叠组合。

完整字段见 `hardware_catalog.csv`。
