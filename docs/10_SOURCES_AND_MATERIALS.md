# 10 · 官方来源、材料清单与待验收项

核实日期：**2026-11-08**。本章区分三种信息：官方资料中的产品／API 事实、本项目自行规定的协议、尚未完成的真机验证。`PCSV`、`PCG-C14N-1`、每日资格、显式写卡迁移和冲突规则都是本项目设计，不是 NFC Forum 或设备厂商已经实现的功能。

## 1. 如何使用这些来源

- 以当前项目锁定的 SDK／固件版本和真实硬件测试为准。官网或 GitHub `main` 更新后，先评估变化，不能无声升级协议。
- 一项产品支持某 RF 协议，不代表已支持所有标签命令、密钥、文件系统、NDEF 容量或抗断电语义。
- 官方赠卡的外观不能证明内部芯片、写权限、UID 稳定性或容量；本项目没有把未知赠卡假定为 NTAG213／215／216 中的任何一种。
- 以下链接是供后续 coding agent 核验的直接来源；不要把文档中的候选组合改写成“已通过真机认证”。

## 2. 硬件与 M5Stack 官方库

### H01

**M5Stack PaperMono C153 产品文档**  
<https://docs.m5stack.com/en/core/PaperMono>

用于核对显示、处理器、PSRAM、RTC、ST25R3916 支持范围和官方刷新驱动提示。不能把旧款 M5Paper／PaperS3 的参数套到 PaperMono。刷新波形注意事项需要在实际构建时重新确认。

### H02

**M5Stack Dial K130 产品文档**  
<https://docs.m5stack.com/en/core/Dial>

用于核对 240×240 圆屏、旋钮、WS1850S、PORT.A/B 和 USB 角色；具体卡型的实用支持同时参照 H06，而不是仅依赖产品表中的 A/B 协议描述。

### H03

**M5Stack Unit RFID2 U031-B**  
<https://docs.m5stack.com/en/unit/Unit_RFID2>

用于核对 WS1850S、I2C `0x28`、供电／引脚和支持范围。设备读写能力不自动给应用提供完整玩家卡协议。

### H04

**M5Stack Unit NFC U216**  
<https://docs.m5stack.com/en/unit/Unit_NFC>

用于核对 ST25R3916、I2C `0x50`、NFC-A/B/F/V 和模式支持；作为 Grove 新读头候选，不代表所有主机板组合已验收。

### H05

**M5Stack M5Unit-NFC 官方仓库 README**  
<https://github.com/m5stack/M5Unit-NFC/blob/main/README.md>

用于核对具体 PICC 支持表、ISO-DEP／文件操作、共享示例中的 detect-only 范围与软件 I2C 已知限制。实施时固定一个版本或 commit。

### H06

**M5Stack M5Unit-RFID 官方仓库 README**  
<https://github.com/m5stack/M5Unit-RFID/blob/main/README.md>

用于核对 NFC-A／B、DESFire 文件访问及 M5Dial 内置小天线的 NFC-B 限制。它与 H05 的共享示例入口不同，不能混淆“某示例只检测”和“驱动完全不能读写”。

### H07

**Seeed Studio Grove NFC（PN532）官方 Wiki**  
<https://wiki.seeedstudio.com/Grove_NFC/>

用于核对 3.3 V、默认 UART、I2C 模式切换和模块版本。Grove 接头相同，不保证通信模式、引脚和供电可直接互换。

## 3. 标签容量、UID 与卡型

### N01

**NXP NTAG213/215/216 产品页与数据手册**  
<https://www.nxp.com/products/NTAG213_215_216>  
<https://docs.nxp.com/bundle/NTAG213_215_216/page/topics/eeprom.html>

关键事实：用户读写区分别为 144、504、888 字节；芯片的总 EEPROM 与可用用户区不同。手册列出的部分 anti-tearing 保护不能扩展解释为任意整份 NDEF 写入具有事务原子性。

### N02

**NXP MIFARE DESFire EV3 产品页**  
<https://www.nxp.com/products/MF3DHx3>

关键事实：NFC Forum Type 4／ISO-DEP、可配置应用文件系统，系列提供 2/4/8/16 KB 容量档位。具体文件可分配容量、应用开销、权限和事务行为必须另做配置与验收；采购“8K”标签不等于能得到 8192 字节本项目有效区。

### N03

**NXP AN10927 — MIFARE product and handling of UIDs**  
<https://www.nxp.com/docs/en/application-note/AN10927.pdf>

关键事实：UID 有不同长度，存在随机 ID 和非唯一情形；UID 字节数组不能不加规则地转为各平台自己的整数。本项目的稳定 legacy 卡号采用显式技术名、规范字节序与 SHA-256。

### N04

**NXP NTAG424 DNA 产品页**  
<https://www.nxp.com/products/rfid-nfc/nfc-hf/ntag-for-tags-and-labels/ntag-424-dna-424-dna-tagtamper-advanced-security-and-privacy-for-trusted-iot-applications:NTAG424DNA>

关键事实：它是 Type 4，但总文件存储为 416 字节，其中 NDEF 文件 256 字节。这个例子用于说明“Type 4”不是容量等级，不能单独作为完整玩家存档选卡条件。

## 4. Apple 官方平台资料

### A01

**Core NFC**  
<https://developer.apple.com/documentation/corenfc>

用于确认 NDEF 读写、支持的协议接口和 `readingAvailable` 能力检查。设备、系统、前台会话与 entitlement 仍需满足条件。

### A02

**NFCNDEFTag 的容量、读写 API**  
<https://developer.apple.com/documentation/corenfc/nfcndeftag/queryndefstatus(completionhandler:)>  
<https://developer.apple.com/documentation/corenfc/nfcndeftag/writendef(_:completionhandler:)>  
<https://developer.apple.com/documentation/corenfc/nfcndeftag/readndef(completionhandler:)>

`queryNDEFStatus` 提供最大 NDEF message 字节数和可写状态。写入完成回调与本项目“重新读回完整快照并验证成功”的业务承诺是两层不同要求。

### A03

**NFCTagReaderSession 与 NFCISO7816Tag**  
<https://developer.apple.com/documentation/corenfc/nfctagreadersession>  
<https://developer.apple.com/documentation/corenfc/nfciso7816tag>

用于核对 NFC capability、用途说明、ISO7816 AID 声明、APDU 通信和 reader session 管理。标准 NDEF Type 4 AID 与自定义应用 AID 不应混用。

### A04

**External Accessory 与 Accessories**  
<https://developer.apple.com/documentation/externalaccessory>  
<https://developer.apple.com/accessories/>

用于说明 External Accessory 针对受支持的 MFi／配件协议和厂商授权，不是任意 USB-C 设备的通用访问 API。

### A05

**Apple Deployment：iPhone/iPad 智能卡能力**  
<https://support.apple.com/guide/deployment/depb75d71d4c/web>  
<https://support.apple.com/guide/deployment/dep8b8c8927a/web>

用于核对 iOS 16／iPadOS 16.1 起的 CCID、NFC 与 PIV 智能卡认证能力及读头兼容性建议。此资料不等于 Apple 承诺任意游戏 NFC 标签可通过任意 USB reader 读写。

### A06

**CryptoTokenKit 智能卡槽与 APDU**  
<https://developer.apple.com/documentation/cryptotokenkit/tksmartcardslotmanager>  
<https://developer.apple.com/documentation/cryptotokenkit/tksmartcard>

用于确认读头槽枚举、会话和 APDU 传输接口；`TKSmartCardSlotManager` 文档列有 smartcard entitlement 要求。外接适配仍需逐 OS、reader 与 card profile 验证。

### A07

**Apple MFi FAQ**  
<https://mfi.apple.com/en/faqs>

用于区分 MFi 技术、普通 USB Device Class、USB-C 充电和 BLE-only 配件。不能笼统要求所有 BLE 或 USB-C 配件均走 MFi，也不能由此推导本游戏已兼容。

## 5. Android 官方及读头厂商资料

### D01

**Android Advanced NFC overview**  
<https://developer.android.com/develop/connectivity/nfc/advanced-nfc>

用于核对 NDEF、`TagTechnology`、ISO-DEP 和可选 MIFARE 支持；各 Android 设备能力仍需运行时探测。

### D02

**Android Ndef API**  
<https://developer.android.com/reference/android/nfc/tech/Ndef>

用于核对 `getMaxSize()`、`isWritable()`、写入、当前消息读取与缓存读取的区别。写后校验必须读取卡当前内容，不能使用旧缓存。

### D03

**Android USB host overview**  
<https://developer.android.com/develop/connectivity/usb/host>

用于核对 USB host 并非所有 Android 设备必有、设备枚举、权限与 endpoint 通信。读头协议／驱动仍由应用适配。

### D04

**ACS Android Library 官方页面**  
<https://android.acs.com.hk/en/>

用于识别厂商提供的 Android USB reader 支持路径及 host 要求。它是候选 SDK，不是本项目完整存档测试记录。

## 6. Web 与浏览器能力

### W01

**Chrome：Interact with NFC devices on Chrome for Android**  
<https://developer.chrome.com/docs/capabilities/nfc>

用于核对 Web NFC 的 NDEF 范围、Android Chrome 路径、安全上下文、用户手势、可见页面与不支持的底层操作。

### W02

**Web NFC 规范草案**  
<https://w3c-cg.github.io/web-nfc/>

用于核对 `NDEFReader`／`NDEFReadingEvent` 接口、`serialNumber` 可以为空、全消息写入以及没有通用容量查询／raw APDU API。规范接口存在不代表所有浏览器实现。

### W03

**MDN Web NFC API**  
<https://developer.mozilla.org/en-US/docs/Web/API/Web_NFC_API>

用于浏览器兼容性入口与 limited availability 提醒。它不是产品部署白名单；实现仍需 feature detect 和目标版本实测。

### W04

**WebUSB 规范与规范源文件**  
<https://wicg.github.io/webusb/#has-a-protected-interface-class>  
<https://raw.githubusercontent.com/WICG/webusb/main/index.bs>

用于核对 `0x0B Smart Card` 属于 protected interface class。普通网页不能据此承诺直接控制任意 CCID 读头；专用高信任运行环境属于另行验证的部署方式。

### W05

**Web Smart Card 官方 HOWTO**  
<https://github.com/WICG/web-smart-card/blob/main/HOWTO.md>  
<https://chromeenterprise.google/intl/en_uk/policies/default-smart-card-connect-setting/>

核实时 HOWTO 写明 ChromeOS Chrome 143+、Smart Card Connector、Isolated Web Apps 的使用条件。不能把这条路径当作 Windows/macOS/Linux 所有普通网页已经具备的能力。

### W06

**Chrome：Read from and write to a serial port**  
<https://developer.chrome.com/docs/capabilities/serial>

用于 MCU/Grove 桥接的 Web Serial 路线、用户选端口与 feature detect。它传输串口字节，不自行解释 NFC 标签。

## 7. 桌面 PC/SC 与候选 USB 读头

### P01

**Microsoft WinSCard：SCardTransmit**  
<https://learn.microsoft.com/en-us/windows/win32/api/winscard/nf-winscard-scardtransmit>

用于 Windows 本地桥接的智能卡请求／响应路径。卡命令格式与 reader 驱动仍需适配。

### P02

**pcsc-lite 官方 API 文档**  
<https://pcsclite.apdu.fr/api/>

用于 Linux 本地桥接的资源管理器与客户端库路径。网页通过受控本地服务使用它，不是浏览器直接调用系统库。

### P03

**ACS ACR1252U 官方驱动／工具及技术资料**  
<https://www.acs.com.hk/en/driver/342/acr1252u-usb-nfc-reader-iii-nfc-forum-certified-reader/>  
<https://www.acs.com.hk/download-manual/13476/TSP-ACR1252U-2.02.pdf>

用于候选 USB CCID／PC/SC reader 的型号、OS 工具与 Android／iOS 验证起点。文档列有工具或驱动不等于本游戏已在该组合上完成 NDEF／RAW、供电和掉电验收。

## 8. 项目自定义协议的依据边界

以下内容无需声称来自硬件厂商，应该在开发中按本项目契约实现：

| 项目决定 | 唯一项目依据 |
|---|---|
| 先玩家卡登录，再英雄卡领取，主动写卡才迁移 | `CONTRACT.json`、第 00／03 章 |
| 每玩家、每英雄卡、每固定 UTC+08 游戏日一次 | 第 03 章、reference 领取算法、fixtures |
| 96 字节 PCSV 头、两个存储 profile | 第 03 章、容器 codec 与黄金向量 |
| UUID 谱系、时间／seq 对账、冲突整份选择 | 第 03／06／07 章 |
| PCG-C14N-1 与整数、深度、解压限制 | 第 11 章与 reference |
| 本地信任层与可选服务端验证 | 第 03／04／06 章 |
| 卡牌战斗、10 张起手全可用与轮次规则 | 第 01 章与 reference 裁判 |

NDEF write API 不给本项目通用的断电原子保证，所以 NDEF profile 的可靠性来自“先本机持久化、再写卡、读回确认”；RAW 双槽则有额外硬件前提。这个边界不能在产品文案或 README 中被省略。

## 9. 仍需收集的真机材料

以下缺项**不阻塞虚拟卡与参考实现开发**；它们只阻止宣称对应实体组合已通过验收。

| 材料 | 目前不能假定的内容 | 开发默认与后续动作 |
|---|---|---|
| 用户实际玩家卡样品 | 芯片、格式、有效容量、写权限 | 先用完整虚拟卡映像；实物查询 capacity 后选择 profile |
| 官方赠送英雄卡样品 | 全部为同一芯片、含已知发行数据或固定 UID | 提供 NFC 扫描报告；核对 UID 稳定性与 legacy 映射 |
| Grove 模块具体 SKU／版本 | PN532 与 WS1850S／ST25R3916 驱动、供电相同 | 记录型号、总线、地址、引脚；只开启匹配适配器 |
| USB reader 型号与 VID/PID | CCID、厂商协议、键盘输出可相互替代 | 明确 reader 能力；只读 UID 设备不得声明玩家卡读写 |
| Android／iPhone／iPad 真机与 OS | SDK 编译通过等于硬件可用 | NFC availability、USB host、权限与真实标签测试 |
| RAW 卡文件／密钥布局 | APDU 能通就能独立写两个槽 | 保存文件结构与权限说明；逐故障点验证两槽隔离 |
| 目标浏览器版本 | Android 浏览器／Safari 全有 Web NFC | feature detect，给 native／bridge／virtual 替代入口 |
| 官方角色图、卡面与素材来源 | 资料页图片自动可用于发布游戏 | 开发使用本项目占位素材；发布素材由用户确认与替换 |
| 产品化发行安全要求 | UID/hash 等于防复制、全局防刷 | 默认 casual_local；有真实需要再定义认证 profile |

扫描报告应包含：技术类型、UID 原始字节与规范化值、ATQA/SAK 或对应协议信息、NDEF 状态、最大 message 字节数、实际读写测试结果；只报告驱动能够可靠获得的字段，不为缺失字段编造值。

## 10. 提交一个真实适配器时的材料包

每个适配器的实现 PR／交付物附以下最小证据：

1. 固定的库版本／commit、构建命令和设备／reader／card 型号。
2. 运行时能力报告，包括 unknown 项及所选 profile。
3. 同一 fixtures 的编码／哈希验证结果和本机原子事务验证结果。
4. 实卡写入前后容量、snapshot_id 与明文 SHA-256 的核对记录。
5. A→B→A 的显式写卡迁移，以及旧卡／本机较新／并行分支场景。
6. 已执行和未执行的断电／拔卡测试列表；NDEF 与 RAW 分开记录。
7. 当前限制和可用替代入口，例如 iOS 仅内置 NFC、Web 仅 NDEF 或需要 bridge。

不要求把玩家私人卡号、完整存档或钱包历史公开到仓库；可以使用专门测试卡和 fixtures 做可复现记录。没有真机证据的提交仍可合并为开发模拟适配，但产品支持表必须保持“待验收”。
