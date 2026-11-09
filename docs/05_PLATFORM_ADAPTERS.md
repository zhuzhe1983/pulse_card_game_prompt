# 05 · 平台、读卡器与存储适配

本章定义 ESP32、Android、iOS 与 Web 的适配边界。目标是共用业务语义、存档字节和对战规则，同时允许不同平台使用不同读卡 API。这里的“可实现”不是“已经完成真机认证”；具体驱动、卡型、固件、系统版本和写断电行为均需登记验收结果。

## 1. 分层与职责

| 层 | 负责 | 不负责 |
|---|---|---|
| 规则／经济核心 | 确定性战斗、领取结果、玩家快照修改 | 直接访问 NFC、系统时钟、Wi-Fi 或 UI |
| `PlayerRepository` | 原子本机提交、版本对账、冲突备份 | 自动云迁移、自动写玩家卡 |
| `PlayerCardService` | 保存意图、PCSV 编码、容量检查、写后读回 | 猜测任意卡型的容量／密码／写粒度 |
| `NfcAdapter` | 发现标签、读 NDEF／应用文件、报告能力、受控写入 | 决定奖励、放宽每日资格、修改钱包 |
| `ClockProvider` | 有效绝对时间、来源与单调计时 | 在规则引擎内私自改变 game day |
| `BattleTransport` | 按第 04 章传送对战消息、重连 | 以重连为名替换玩家收藏存档 |
| `ViewAdapter` | 显示场面、输入选择、保存状态 | 用局部 UI 状态取代核心事实 |

通信可以使用 Wi-Fi、互联网、局域网或经过实现的其他链路；NFC 在 v1 中主要承担卡片识别与玩家卡读写，不要求两端手机通过 NFC 持续传输对战数据。

## 2. 能力报告必须细到卡片操作

驱动启动时报告平台能力，发现卡片后再报告具体标签能力。不能只有一个 `supports_nfc = true`。

正式能力对象采用 `schemas/reader-capabilities.schema.json`，字段名不得自行改写；其中 `null` 明确表示尚不知道容量：

```text
reader_id
connection
supported_tag_technologies
supports_stable_uid
supports_ndef_read / supports_ndef_write
supports_raw_read / supports_raw_write
supports_tag_removal
supports_capacity_query
max_ndef_message_bytes: integer | null
raw_application_bytes: integer | null
verified_on_hardware
notes
```

驱动另外保留本机实现元数据：驱动版本、是否可交换 APDU、是否可按地址独立读写、写粒度、两槽故障隔离验收、是否需要用户手势／前台会话，以及可用的保存 profile。这些不是可以随意塞入上述 JSON 的额外字段；Schema 拒绝未知键时必须遵守。

“有 APDU 通道”不足以宣布 `RAW_DUAL`：仍需确认选中的应用／文件、权限、可用空间和独立写入行为。“读到了 UID”也不能宣布已支持玩家卡迁移。

### 2.1 共同接口语义

- `openSession(intent)`：intent 区分登录、英雄领取、保存、读回验证、初始化。保存授权只属于当前会话／玩家，不在后台永久保留。
- `readTag()`：返回标签句柄和能力；句柄失效后禁止复用旧会话进行写入。
- `readPlayerContainer()`：从卡获取新鲜的完整数据，不用 OS 缓存代替写后验证。
- `queryWritableCapacity()`：报告真正可写的 NDEF message 或应用文件容量；未知就是未知。
- `writePlayerContainer()`：仅接受已经本机持久化、完成容量检查的冻结快照。
- `verifyPlayerContainer()`：重新读取、解压、校验，再与待写版本比较。
- `closeSession()`：撤销待写操作，释放读卡器；离开页面、后台或设备断开时执行。

同一读卡器一次只由一个游戏会话占用。UI、后台自动发现、保存流程不能各开一套互相竞争的 NFC 轮询。多张卡同时在场时拒绝写入，要求只放一张。

## 3. 支持矩阵：功能路径而非笼统平台名称

| 平台／入口 | 英雄卡识别 | 完整玩家卡 | v1 定位与条件 |
|---|---|---|---|
| ESP32 + 已适配内置／Grove 读头 | 稳定 UID 映射或发行 payload | NDEF；经验证后可 RAW 双槽 | 嵌入式主路径，需实际卡型驱动与容量验证 |
| Android 原生 + 手机内置 NFC | NDEF 或支持的底层 tag technology | NDEF；ISO-DEP／文件适配后可 RAW | 手机主路径；运行时检查 NFC 与卡型 |
| Android 原生 + USB 读头 | 厂商 SDK／应用层 CCID／专用协议 | 取决于该 SDK 的读写／APDU 支持 | 需要 USB host、权限、供电和指定 reader 支持 |
| iPhone 原生 + Core NFC | NDEF 或受支持协议 | NDEF；声明 AID 并适配后可 RAW | 推荐 iOS 主路径，前台系统 NFC 会话 |
| iOS/iPadOS + 指定 CCID／厂商配件 | 条件支持 | 条件支持 | 单独验证 CryptoTokenKit 或厂商通路；不承诺任意 USB-C 读头 |
| Android Chrome + Web NFC | 有有效发行 payload 的 NDEF 卡 | `NDEF_SINGLE`，且容量来源已确认 | 不支持通用 raw/APDU；legacy UID 不作通用承诺 |
| 桌面 Web + PC/SC 本地桥接 | 由本机读头驱动完成 | NDEF／已适配 RAW | 必须安装或运行本地组件；不是网页零安装直连任意 USB |
| Web + MCU/Grove 桥接 | MCU 负责 NFC | MCU 上已验证的 profile | 桥接协议和浏览器通信能力需另外实现 |
| Safari/iOS 普通网页 | 不设内置 Web NFC 保证 | 不设直接写玩家卡保证 | 使用原生应用、已实现的宿主桥接，或虚拟卡开发入口 |
| 仅输出 UID 的 USB 键盘读头 | 可做受限英雄输入 | 不支持完整玩家快照读写 | 不能把键盘模拟输入宣传成玩家卡存档支持 |

浏览器能力随版本变化；发行前必须 feature detect 并实测。Web NFC 当前官方实现说明明确面向 Android Chrome，MDN 也将其标为非广泛可用能力。[W01](10_SOURCES_AND_MATERIALS.md#w01) [W03](10_SOURCES_AND_MATERIALS.md#w03)

## 4. ESP32 与 Grove

### 4.1 推荐设备组合

| 设备／模块 | 已核实的官方事实 | 本项目实现决定 |
|---|---|---|
| PaperMono C153 | ESP32-S3R8、8 MB PSRAM、480×800 触摸墨水屏，内置 ST25R3916；支持 NFC-A/B/F/V | 作为完整嵌入式终端优先；用官方例程确认供电／IO 与库配置 |
| M5Dial K130 | ESP32-S3FN8、240×240 圆屏、旋钮；内置 WS1850S | 小屏终端；需要折叠场面和卡牌详情，不能删掉规则信息 |
| Unit RFID2 U031-B | WS1850S，I2C `0x28`，官方称 A/B 读写，Grove | 复用已适配驱动；不要将连接器相同理解为全部协议相同 |
| Unit NFC U216 | ST25R3916，I2C `0x50`，A/B/F/V | 新增 Grove 通用 NFC 路径的优先评估对象 |
| Seeed Grove NFC（PN532） | I2C／UART，默认 UART，文档给出 3.3 V；切 I2C 可能需改焊盘 | 必须核对版本、供电和通信模式；不能直接照搬 M5 PORT.A 引脚假设 |

事实来源：[H01](10_SOURCES_AND_MATERIALS.md#h01)、[H02](10_SOURCES_AND_MATERIALS.md#h02)、[H03](10_SOURCES_AND_MATERIALS.md#h03)、[H04](10_SOURCES_AND_MATERIALS.md#h04)、[H07](10_SOURCES_AND_MATERIALS.md#h07)。

### 4.2 官方库存在的细粒度差异

核实时，`M5Unit-RFID` 的支持表列出 DESFire 2/4/8K 的 ISO-DEP 原始／文件访问，但同时指出 M5Dial 内置小天线不能可靠激活 NFC-B，NFC-B 应使用外接 Unit RFID2。因此项目共同玩家卡优先评估 **NFC-A / Type 4**；不能仅凭 Dial 产品页的 A/B 标注承诺所有 Type B 卡。[H06](10_SOURCES_AND_MATERIALS.md#h06)

`M5Unit-NFC` 的部分共享示例将 Dial／RFID2 接入列为 detect-only，这不等于 `M5Unit-RFID` 自身没有读写能力。移植必须选对库与示例层，实际跑通读取、容量查询、完整写入和读回，而不是停在示例输出 UID。[H05](10_SOURCES_AND_MATERIALS.md#h05)

库支持表也不能替代卡上应用权限配置。DESFire 等卡的文件尚未创建、密钥未知或文件只读时，ISO-DEP 通信成功仍不等于可以保存玩家数据。不得尝试格式化非本游戏初始化的未知卡。

### 4.3 Grove 与 USB 的边界

Grove 是接线生态，不是统一 NFC 命令。适配配置必须记录供电电压、I2C／UART、地址、波特率、引脚和时序。对软件 I2C 时序不满足驱动要求的板子，应更换硬件 I2C 路径或报告不支持，不能只延长 UI 超时掩盖底层错误。

ESP32 上的 USB-C 插口可能用于供电、下载、Serial/JTAG 或 USB OTG；是否能给外部 USB 读头提供 host 模式与 VBUS，必须按具体板级设计验证。v1 不把“有 USB-C”视作 USB CCID 即插即用保证。

### 4.4 本机存储和显示调度

本机玩家存档使用一个完整快照事务。可以选择经过验证的 NVS blob 日志、文件双副本，或可保证原子提交的存储层；不能分别写 `wallet` 和 `day_ledger` 两个键就宣称它们必然一起提交。驱动只有在数据已经满足本机持久化承诺后才返回成功。

NFC 读写、网络心跳和界面刷新分开调度。墨水屏刷新时不得阻塞网络超时或导致重复轮询领取。PaperMono 官方文档目前提醒特定 M5GFX 波形仍需谨慎，应采用当时官方推荐的 OTP／稳定刷新配置并实测；本规格不保证某个毫秒级刷新值。[H01](10_SOURCES_AND_MATERIALS.md#h01)

Dial 至少始终可访问：双方分数、谁行动、谁已过牌、剩余手牌数、场上单位及效果详情、玩家卡是否已保存。旋钮翻页和详情弹层可以改变布局，不能使对手持续效果在小屏端不可查询。

## 5. Android 原生

### 5.1 内置 NFC

使用 `android.nfc` 发现标签，再按 `Tag.getTechList()` 选择 `Ndef`、`IsoDep` 或其他已实现技术。Android 官方将 MIFARE Classic 等支持列为可选；不能假设所有安卓机都能读任何 MIFARE 卡。[D01](10_SOURCES_AND_MATERIALS.md#d01)

`NDEF_SINGLE` 实现顺序：

1. 获取 NDEF 对象并连接；确认可写。
2. 用 `getMaxSize()` 获取最大 NDEF message 字节数，比较完整编码后的消息。
3. 调用 `writeNdefMessage()`。
4. 使用 `getNdefMessage()` 重新从卡读取并验证；**不能使用 `getCachedNdefMessage()` 作为写后读回**。
5. 关闭连接；处理 `TagLostException`、权限与 IO 错误。

上述 I/O 不放在主 UI 线程。官方 API 明确区分缓存数据与当前卡数据，写入 API 也可能因离场而失败。[D02](10_SOURCES_AND_MATERIALS.md#d02)

`RAW_DUAL` 需要独立实现 ISO-DEP/APDU 与卡上文件协议，或对应卡型块访问。`IsoDep.transceive()` 是传输能力，不会自动完成 DESFire 认证、文件创建、容量推导或断电恢复。

### 5.2 USB 外接读头

Android USB host 负责枚举设备、申请用户授权和读写 endpoints；不是自动把所有 USB NFC 读头变成内置 `NfcAdapter` 的 tag。应用必须接入明确型号的厂商 SDK、已验证的 CCID 实现或 reader 专有协议。[D03](10_SOURCES_AND_MATERIALS.md#d03)

支持名单必须记录手机是否有 USB host／OTG、连接线、读头 VID/PID、供电、驱动版本与可用协议。ACS 官方提供面向 USB host 的 Android 库和指定读头支持，可作为候选；仍需验证具体玩家卡与 NDEF／应用文件读写。[D04](10_SOURCES_AND_MATERIALS.md#d04) [P03](10_SOURCES_AND_MATERIALS.md#p03)

内置 NFC 和 USB 读头共用 `PlayerCardService`；不得复制一套不同的每日领取规则。SQLite／Room 等本机存储实现必须把完整快照更新和 claim 幂等记录放在同一事务，事务提交失败不能只保留其中一半。

## 6. iOS / iPadOS 原生

### 6.1 首选 Core NFC 的内置读卡路径

Core NFC 官方提供 NDEF 读写与 ISO7816、ISO15693、FeliCa、MIFARE 等协议接口；是否可用仍要检查设备及 `readingAvailable`。SDK 中存在符号或 iPadOS availability，不等于每台 iPad 具有相应 NFC 硬件。[A01](10_SOURCES_AND_MATERIALS.md#a01)

实现必须配置 NFC capability、必要 entitlement、`NFCReaderUsageDescription`。ISO7816 自定义应用访问需声明允许的 AID；标准 NDEF Type 4 路径与自定义应用文件路径分别适配。[A03](10_SOURCES_AND_MATERIALS.md#a03)

NDEF 保存使用 `queryNDEFStatus` 获取可写状态与 message capacity，写入后再执行 `readNDEF` 并验证。系统写入回调无 error 并不代替本协议的完整读回校验。[A02](10_SOURCES_AND_MATERIALS.md#a02)

### 6.2 刷卡交互与系统会话

iOS NFC 是受系统管理的会话，不把它模拟成永久后台读头。读取登录结束后，再点“保存到玩家卡”开启一次保存会话并重新贴卡。保存 intent 必须先于写操作；不能把登录的检测回调直接改成写卡调用。

发生后台切换、系统取消、超时或卡离场时，关闭会话并保持本机进度。未完成新鲜读回时停在待验证状态；可以另开明确的验证会话要求再贴一次卡。只有验证成功才显示可迁移。

### 6.3 USB、CCID、External Accessory 的真实边界

不能写成“iOS 完全不能接 USB 读卡器”。Apple 官方已说明 iOS 16／iPadOS 16.1 及以上对合规 CCID／NFC PIV 智能卡提供原生认证等支持；但这不自动保证游戏标签能经任意 USB NFC 读头完成读写。[A05](10_SOURCES_AND_MATERIALS.md#a05)

可评估的外接路径分为：

- **系统可枚举的智能卡槽 + CryptoTokenKit。**核实目标 SDK availability 与 entitlement，确认 `TKSmartCardSlotManager` 能看到读头，并以 `TKSmartCard` 建立会话、发送 APDU；再验证实际标签、文件命令与供电。Apple 提供这些接口，但不能将 PIV 认证功能等同于全部自定义 NFC 标签协议都已适配。[A06](10_SOURCES_AND_MATERIALS.md#a06)
- **厂商明确支持的配件／SDK。**以其 reader、iOS 版本与 API 为准。ACS 对特定型号列有 iOS APDU 工具，可以作为验证起点，不能据此扩展为所有 ACS 或所有 USB 卡机都支持。[P03](10_SOURCES_AND_MATERIALS.md#p03)
- **External Accessory / MFi。**这是针对受支持配件协议的框架，官方说明涉及 MFi 配件及厂商对第三方应用的授权；不是一个向所有 USB-C 设备开放的通用 USB API。[A04](10_SOURCES_AND_MATERIALS.md#a04)
- **BLE／网络读头。**仅在已经实现的协议和原生宿主中启用。BLE-only 配件不因连接 iPhone 就自动需要 MFi；也不因此自动与本游戏兼容。[A07](10_SOURCES_AND_MATERIALS.md#a07)

v1 的默认 iPhone 用户路线仍是内置 Core NFC。外接路径在能力表中标为条件支持，未验收前 UI 不能宣称可完整保存。

## 7. Web

### 7.1 Android Chrome 的 Web NFC

Web NFC 的公开能力以 NDEF message 为中心，不支持通用 ISO-DEP、NFC-A/B/F 原始命令、P2P 或 HCE。需要安全上下文、用户手势与权限，且页面保持可见；手机锁屏／页面隐藏时不能按常驻读卡器设计。[W01](10_SOURCES_AND_MATERIALS.md#w01)

因此纯 Web NFC 的 v1 合同是：

- 支持发行 payload 为 NDEF 的英雄卡。
- 支持 `NDEF_SINGLE` 玩家卡；不支持自定义 RAW 双槽应用文件。
- 通过 `NDEFReader` feature detect 决定按钮是否可用；没有 API 就显示具体替代路径。
- `serialNumber` 允许为空，且不能提供本规格的完整技术／UID 规范化保证；不得为空值临时生成 hero_card_id。[W02](10_SOURCES_AND_MATERIALS.md#w02)
- 接收未知网页 URL 记录不等于识别到游戏卡；必须解析本游戏 MIME／发行记录。

### 7.2 Web NFC 的容量与读回限制

Web NFC 标准接口没有对应原生 `queryNDEFStatus`／`getMaxSize()` 的通用容量查询方法。本项目只能在容量由已验收、预配置卡片 profile 或桥接层可靠提供时允许完整写卡；能力未知时返回 `CARD_CAPACITY_UNKNOWN`，转到原生／桥接初始化工具。不能从现有短消息长度推算标签最大容量，也不能先破坏性覆盖再把失败当容量探测。

原生工具预配置卡片时，可以关联一个精确的卡片 profile／文件布局供网页使用；这一配置必须对应实际可写 NDEF message 字节数，不能仅填写“8K 卡”。每次网页写入仍比较实际编码长度。

容量配置属于读头／卡片适配资料，不能仅凭 `player_id` 推断，因为同一玩家可以换不同容量的卡。若浏览器不能可靠绑定到已验证的物理卡或专用发行批次，默认允许读取但拒绝写入，使用原生或桥接路径完成保存。不要为了显示 Web“全功能”而假造一个容量值。

`write()` 成功后，新的 `reading` 数据必须确认为写后读取，不能拿写前缓存的事件验证。若浏览器无法立即提供可靠的新鲜读回，显示“已写入，移开再贴完成验证”，重新开启验证会话。只有读回 payload 与目标完全匹配才标记成功。

初始化网页／PWA 后可以离线运行已缓存的业务与内容。持久化使用 IndexedDB 的完整事务；应在 transaction complete 后才承诺本机提交。浏览器清站点数据、隐私模式或存储回收会影响本机持久性，因此界面要清楚显示是否已完成玩家卡保存；不得把浏览器缓存叫作已写入实体卡。

### 7.3 桌面 USB NFC：默认 PC/SC 本地桥接

普通网页的 WebUSB 不是所有 USB 设备的通行证。WebUSB 规范将 Smart Card 接口类 `0x0B` 列为 protected interface class；常见 CCID 读头不能作为普通网页的通用直接访问方案。[W04](10_SOURCES_AND_MATERIALS.md#w04)

推荐桌面结构为：

```text
游戏 Web UI → 本机桥接服务 → 系统 PC/SC／厂商驱动 → USB 读头 → 标签
```

这是一条实现路径，不是零安装承诺。Windows 使用 WinSCard，Linux 可使用 pcsc-lite，macOS 使用可用的系统智能卡接口／厂商驱动；实际卡命令仍由标签 profile 实现。[P01](10_SOURCES_AND_MATERIALS.md#p01) [P02](10_SOURCES_AND_MATERIALS.md#p02)

本地桥接至少要做到：

1. 默认只监听 loopback，限制允许的 UI origin，并使用一次配对令牌或同源会话；不向任意网页开放写卡。
2. 推荐由桥接提供同源本地 UI；若远程 HTTPS 页面连接 loopback，必须实测浏览器的混合内容、Local Network Access 与权限策略，不能假定跨浏览器一致。
3. 提供读卡器列表、能力报告、互斥会话、请求 ID、取消和有上限的消息长度。
4. 同一次写入重试保持相同请求语义，并先读回判断是否已完成；不能把重试变成重复领取。
5. 只有 `PlayerCardService` 明确请求保存时执行写入；后台 PC/SC 卡出现事件只做发现／读取。

Web Smart Card 是另一条专门路线。核实时官方 HOWTO 已说明 ChromeOS Chrome 143+、Smart Card Connector 与 Isolated Web Apps 的使用条件；它不能推广成所有桌面浏览器或普通网页已有通用 PC/SC。[W05](10_SOURCES_AND_MATERIALS.md#w05)

### 7.4 Web + Grove / MCU 桥接

网页不能直接访问一根 Grove I2C 线。MCU 必须作为 NFC 主机，实现标签协议，再把受控读写能力通过 USB serial、受支持的 vendor USB、BLE 或局域网 API 暴露给客户端。

首选简单开发路线是桌面受支持浏览器的 Web Serial 或本地桥接连接 MCU；浏览器和 OS 支持要 runtime detect。若使用 WebUSB，接口必须符合浏览器允许的类别与驱动约束，不能依赖绕开 CCID 保护类。[W06](10_SOURCES_AND_MATERIALS.md#w06)

MCU 桥接在返回保存成功前必须完成真实卡读回校验。浏览器不能仅因为串口收到 `OK` 就假定卡片内容可靠，除非这个 `OK` 的协议定义明确包含目标 snapshot_id 与验证后的 payload SHA-256。

## 8. 虚拟卡文件是默认开发入口

没有真机型号、SDK 或卡容量信息，不应阻塞规则、UI、保存状态机和跨平台对战开发。所有平台先接入 `VirtualCardAdapter`，读取同一组 fixtures：

- NDEF profile：一份完整、可解析的 NDEF message 文件。
- RAW profile：8192 字节逻辑卡映像，含两个 4096 字节槽。
- 英雄卡：固定 payload／legacy UID 的输入事件。

**设备本机存档与虚拟玩家卡文件必须分开。**领取只更新 device store；只有显式保存事件才修改 cardfile。切换虚拟 device_id／清空第二台设备 store，再从 cardfile 登录，应准确复现“未写卡不能迁移”。

虚拟驱动应能注入：只读、容量不足、卡移开、部分写入、读回不匹配、无有效时钟、重复发现、两张卡在场、不同谱系。测试通过只能证明业务和容器逻辑，不能宣称射频读写、系统权限、掉电可靠性或苹果配件认证已经完成。

## 9. 平台验收必须记录的结果

每个声称支持的组合至少记录以下实际结果：

| 维度 | 必填内容 |
|---|---|
| 设备 | 型号、板卡修订、OS／固件版本、供电方式 |
| 驱动 | SDK／库、固定版本或 commit、构建选项 |
| 读头 | 内置芯片或外接 SKU，USB VID/PID 或总线配置 |
| 卡片 | 芯片、协议、NDEF／应用文件布局、权限、实际可用字节 |
| profile | NDEF_SINGLE 或 RAW_DUAL；是否仅开发模拟 |
| 基础功能 | 登录、固定卡、盲盒卡、重复领取、本机较新版本保护 |
| 保存 | 容量边界、写后新鲜读回、断线、失败后本机恢复 |
| 迁移 | A 保存→B 登录→B 修改→B 保存→A 登录，以及冲突分支 |
| 耐故障 | 声称的掉电保证和实际注入位置；未测试项必须显式标明 |

未出现在通过表中的硬件可以作为候选，不能自动继承其他平台的认证结果。完整错误和恢复验收见第 07 章；用户仍可以先用虚拟卡与正常对战功能验证产品。
