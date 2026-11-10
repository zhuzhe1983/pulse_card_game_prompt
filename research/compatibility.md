# 兼容规则（按事实组合，不是全对全矩阵）

研究日期：2026-11-10（Asia/Shanghai）  
机读表：`compatibility.csv`（20 条规则）  
原则：只记录官方写明的组合、脚位差异和冲突。没查到的组合标「未知」，不要写成不兼容。硬件接不上的关系，游戏里不得用加成伪装成「其实兼容」。

## 1. 四层兼容，不要混为一谈

| 层 | 问的是什么 | 例子 |
| --- | --- | --- |
| 物理插接 | 插头/壳体/高度会不会卡住或顶坏 | Core2 震动马达与 Base 系列结构干涉；StickS3 与 Mini JoyC / Mini EncoderC / 18650C 结构不兼容 |
| 电气 | 脚位、电平、电源方向、总线类型是否对得上 | M5-Bus 电源脚固定、GPIO 随宿主变化；Grove 红线多为 5V，GPIO 为 3.3V 级别 |
| 软件 | 驱动是否按该宿主的脚位号初始化 | GPS v2 必须按 CORE / CORE2 / CORES3 拨码 |
| 并发 / 地址 / 电源 / 引脚占用 | 同时插两样时会不会抢同一脚、同一地址或同一路供电 | Fire 的 PSRAM 占用 GPIO16/17；Faces Keyboard3 与 Gamepad3 都是 I2C 0x08 |

官方总览把扩展分成三类物理语言：

- **HY2.0-4P Grove**：快插传感器/执行器接口，有防反插。
- **M5-Bus**：Core 与 Module / Module13.2 / Base / Faces 使用的可堆叠 2x15P@2.54mm 总线。
- **Chain**：横向 daisy-chain，双 HY2.0-4P，**UART** 通信，不是 I2C Unit。

来源：<https://docs.m5stack.com/en/start>

## 2. M5-Bus / 堆叠族

官方 DIP 教程写得很清楚：M5-Bus 从左上 GND 起编号 1–30，这个顺序在各宿主上一致；红框内的电源/GND 等是固定功能，其余脚「因主控型号而异」。

来源：<https://docs.m5stack.com/en/guide/common/dip_switch>

### 已核对的脚位代差（不要靠家族名脑补）

| 功能 | Basic/Fire 初代 | Core2 | CoreS3 | Tab5 |
| --- | --- | --- | --- | --- |
| PORT.A | G21/G22 I2C | G32/G33 I2C | G2/G1 I2C | 仅板载 1 路 Grove：G53/G54 |
| PORT.B | G26/G36 | G26/G36 DAC/ADC | G9/G8 | 出现在 M5-Bus 的 PB_IN/PB_OUT（G17/G52），不是第二路板载 Grove |
| PORT.C / UART2 | G17/G16 | G14/G13 | G17/G18 | M5-Bus PC_RX/TX G7/G6 |
| SPI MOSI | G23 | G23 | G37 | G18 |
| 内部 I2C | G21/G22 | G21/G22 | G12/G11 | G31/G32 |
| M5-Bus 25/27/29 | HPWR（初代） | NC | HVIN（Base DIN） | HVIN |

来源：Basic v2.7、Fire v2.7、Core2、CoreS3、Tab5 产品页脚位表。

### 明确组合

- **模块 + 拨码**：Module GPS v2 用拨码把 TXD/RXD/PPS 切到当前宿主。CORE / CORE2 / CORES3 都有官方对照表。拨错不是「这个模块不能用于 CoreS3」，而是电气冲突风险。来源：<https://docs.m5stack.com/en/guide/module_gps_v2/pins_change>
- **Fire + 占用 G16/G17 的模块或 PORT.C**：Fire v2.7 写明 GPIO16/17 默认接 PSRAM，堆叠时要避开。来源：<https://docs.m5stack.com/en/core/Fire_v2.7>
- **Core2 + 任意 Base 系列功能底座：结构不兼容**。官方原文大意：Core2 内置震动马达与 Base 系列结构干涉，禁止叠装以免损坏。若要一边堆模块一边保留 IMU/麦克风/电池，应去掉原电池底、改用 M5GO Bottom2。来源：<https://docs.m5stack.com/en/core/Core2>
- **Core2 + M5GO Bottom2 v1.3**：官方写明专为 Core2 系列设计。来源：<https://docs.m5stack.com/en/base/Base_M5GO_Bottom2_v1.3>
- **CoreS3 + 带磁铁的产品**：BMM150 可能读数异常，需去掉磁铁或远离强磁场。这是传感质量问题，不是不能物理插入。来源：<https://docs.m5stack.com/en/core/CoreS3>
- **Tab5 + Module**：背面 M5-Bus 用于扩展 Module 系列；板载只有 1 个 Grove。C6 是伴随无线 SoC。来源：<https://docs.m5stack.com/en/core/Tab5>
- **CoreMP135 + 模块**：有 M5-Bus 和 PORT.A/C，但脚是 STM32 名、软件是 Linux；总线 5V 默认关闭，扫描 I2C 前必须打开。来源：<https://docs.m5stack.com/en/core/CoreMP135>
- **CM4Stack / ToughC5 / CoreMatrix**：本轮未深挖每一条堆叠脚位。兼容性标未知。

交互式工具：<https://docs.m5stack.com/en/compatible>（「一台宿主、多个模块、一个底座」）。本轮未穷尽其交互结果。

## 3. Grove / Unit：不是任意 HY2.0 都能通用

官方把 Unit 说成「通过 HY2.0-4P Grove 连接各种主控」，这是形态语言，不是「任意口、任意协议」。Core 脚位表把口分成：

- **PORT.A**：I2C
- **PORT.B**：GPIO / ADC / DAC
- **PORT.C**：UART

因此：

- Unit ENV-III、ToF、RFID2、PaHub 走 I2C，应对 PORT.A（或其它被软件初始化成 I2C 的 Grove）。
- Unit Light / Earth / 电位器类走模拟或 GPIO，应对 PORT.B 这类口。
- Unit RS485、GPS、LoRaWAN、CatM 等多走 UART，应对 PORT.C。
- **Unit Ultrasonic-I2C 与 Unit Ultrasonic-IO** 是官方把同一传感功能做成两种电气合约的例子，不能互相当普通 Grove 互换。
- 同一 I2C 地址的两件设备会冲突。官方地址表：<https://docs.m5stack.com/en/product_i2c_addr>
- **PaHub**（PCA9548，默认 0x70）用来按通道隔离 I2C；**PbHub** 是把 GPIO 扩展挂到 I2C 上。二者解决的问题不同。
- Stick / Cardputer / Tab5 / DinMeter 的 Grove 数量和脚位各不相同（Cardputer 为 G2/G1；StickC-Plus2 为 G32/G33；StickS3 为 G9/G10；Tab5 仅 PORT.A G53/G54）。「能插上线」不等于软件脚位正确。

## 4. Stick / HAT 代际

经典 HAT（多份 Hat 产品页，以 Hat DAC2、Hat PowerC、Mini JoyC 为例）：

- 脚位语言：StickC 的 SDA=G0、SCL=G26、5V、GND
- 明确写过兼容：StickC / StickC PLUS / StickC PLUS2（Hat DAC2）
- StickC-Plus2 官方正文写「接口兼容 HAT 与 Unit」，但麦克风 CLK 也占用 G0，与经典 HAT 的 SDA 存在引脚共用风险。官方没有把它写成「不兼容」，本目录也不升级为不兼容。
- Hat SPK2 是 **I2S** 设备，由宿主 **3V3** 供电，不能按 I2C HAT 来用。它和 PAM8303 经典喇叭帽不是同一电气设计。

StickS3 官方说明：

- 扩展是 **Hat2-Bus 2.54-16P**，脚位表与经典 G0/G26 不同。
- **结构不兼容**：Hat Mini JoyC（U156）、Hat Mini EncoderC（U157）、Hat 18650C（U080）。
- 其它经典 HAT 能否直接插上：未知。不要假定全部能用，也不要假定全部不能用。
- 另有专用配件 Display 1.14 For StickS3（A183）。

来源：<https://docs.m5stack.com/en/core/StickS3>、<https://docs.m5stack.com/en/hat/Hat_DAC2>、<https://docs.m5stack.com/en/hat/Hat_SPK2>

## 5. Chain

官方定义：一台 Master + 多个 Node 的 UART 菊花链。

- 推荐主机：Chain DualKey，或 Atom 系列 + Atomic ToChain Base。
- DualKey 有两路互相独立的 Chain UART（G48/G47 与 G5/G6），左右编号各自从 1 开始。
- 节点多为 STM32G031G8U6，双 HY2.0-4P 分为 IN / OUT。箭头从主机指向外侧。
- 寻址：报文里的 ID 沿链路递减，到 1 时由该节点处理；回程再递增。这是顺序寻址，不是 I2C 地址表。
- 心跳与枚举支持热插拔；断链后前一节点会把自己改成尾节点并通知主机。
- Atomic ToChain 默认脚：AtomS3/S3R 为 G5/G6，经典 Atom 为 G22/G19。
- HY2.0 外观像 Grove，协议不是 I2C Unit。把 Unit 电缆当 Chain 用，或把 Chain 节点当普通 I2C 传感器，都不成立。

来源：<https://docs.m5stack.com/en/chain/Chain_DualKey>、<https://docs.m5stack.com/en/arduino/projects/chain/chain_bus>、<https://docs.m5stack.com/en/accessory/Atomic_ToChain_Base>

## 6. Faces（旧生态的现状）

Faces 不是「又一块屏幕」，而是 **Core + Faces 底座 + 可换输入面板**：

- Faces Bottom3：M5-Bus 接 Core1 / Core2 / CoreS3 等；2.54-22P 面板总线；兼容 Gen1 与 Gen3 面板；两侧 RGB；PORT.B/C；600mAh；LED IO 拨动开关用于不同宿主。
- Keyboard3：STM32F030C8T6，I2C 0x08 + 中断，35 键。
- Gamepad3：STM32F030F4P6，I2C 0x08 + 中断。
- Calculator3：STM32G031，I2C 数字键面板（本轮未复核其地址，双面板冲突对它标未知）。
- Keyboard3 与 Gamepad3 默认地址相同，同时使用存在地址冲突风险。
- 面板上的 STM32 是辅助 MCU，不是英雄。

来源：<https://docs.m5stack.com/en/faces/Faces_Bottom3> 及 Keyboard3 / Gamepad3 产品页。历史页 2026-09-04 发布 Faces Keyboard3 / Gamepad3 / Calculator3。

## 7. 给游戏设计的硬约束

- 现实中官方禁止或结构不相容的组合（Core2+普通 Base，StickS3+U156/U157/U080）在游戏里应当是「不能形成兼容羁绊」，必要时还可以是负向的「结构干涉」，**不能**做成正向加成。
- 现实中「要拨码 / 要换脚 / 要分路」的组合，适合做成有上限的配合，而不是无限叠 buff。
- 现实中只是「没查到」的组合，不要写成克制或禁配。
- 接得上 ≠ 该无上限加战力。电源、地址、同一 UART、同一 SPI 都是互斥资源，更适合做成「一轮里只能兑现一次的配合」。

详见 `compatibility.csv`。
