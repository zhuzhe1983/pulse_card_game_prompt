# 04 · PCG/1.0 通信协议

> 状态：v1 可实现契约。本文中的 **MUST / MUST NOT / SHOULD / MAY** 分别表示必须、禁止、建议、可选。规则语义由核心规则文档与 reference engine 的 golden fixtures 规定；本章定义消息、会话、裁判边界、传输与恢复。`schemas/envelope.schema.json`、`schemas/frame.schema.json` 和 `examples/wire_examples.json` 是本章的机器可读配套。
>
> 协议名 `pcg`；线路版本 `1.0`；基线规则 `pcg.core.v1`；基线内容包 `m5.core.v1`。消息中的 `rule_id` 与规则状态中的 `ruleset_id` 指向同一个不可变规则契约，数值必须相等。

## 1. 互战的边界与裁判

一场对战 MUST 只有一个逻辑 `AuthorityAdapter`。它可以运行在专用服务端，也可以运行在可信房主设备上。所有玩家把意图提交给它；只有它调用 reducer、分配 revision、记录结果并生成各玩家的可见状态。ESP32、Android、iOS、Web MAY 使用不同 UI、动画和通信模块，但 MUST 使用完全相同的命令语义。客户端本地模拟仅用于预览；不得把模拟结果作为其他玩家的权威状态。

| 组件 | 输入与输出契约 | 不可替代的职责 |
|---|---|---|
| `TransportAdapter` | 发送/接收一份完整 envelope 的字节串；报告连接关闭与传输错误 | 可靠、有序、允许重复地交付消息；实现 WebSocket、字节流或本章分片 |
| 认证上下文 | 已验证的对端身份、当前 session、对应玩家/旁观者权限 | 把 `sender_id` 映射到玩家，不接受消息自报的 seat 或权限 |
| `AuthorityAdapter` | 已认证身份 + `COMMAND.body` → 持久结果 + 各自的 snapshot | 幂等、revision 检查、单次规则执行、日志与信息过滤 |
| `RulesEngine` | 完整规则状态 + 合法意图 → 下一状态 | 纯规则；不依赖屏幕、网络、NFC UID 或客户端时钟 |
| `ViewAdapter` | 完整状态 + 已认证观看者 → 可见状态 | 本人手牌列表、对手手牌数量；旁观者看不到任何私有手牌 |

`authority_mode=trusted_host` 是明确的信任房主模式，适合朋友局和离线局。房主程序能够接触裁判的完整信息。`authority_mode=dedicated_server` 才是本规格的排位部署基线；客户端自行声称这个枚举不产生信任。服务器运营方的认证、持久化和访问控制仍须成立。PCG/1.0 不宣称通过状态哈希就能证明房主没有作弊。

NFC 在此系统里承担实体卡的识别、导入与选择。它不是远程战斗传输链路。NFC 原始 UID、实体卡身份材料和收藏所有权证明 MUST NOT 放进公开战斗 snapshot 或发给对手；战斗使用本局实例 ID，例如 `p0:00`。

## 2. 标识、编码与规范 JSON

### 2.1 基础值

- 所有协议 ID 使用 ASCII，匹配 `^[A-Za-z0-9][A-Za-z0-9._:-]*$`，长度 1–64。大小写敏感，不自动 trim、改大小写或做 Unicode 标准化。版本字符串及 opcode 也使用此约束。
- 所有 JSON 对象键 MUST 是非空可打印 ASCII（U+0020–U+007E）。协议定义的键使用下划线形式。用户展示名字可以是 Unicode **值**。
- 所有整数绝对值 MUST ≤ `9007199254740991`（2^53−1）；计数、seq、revision、时间间隔 MUST 非负。协议禁止浮点、NaN、Infinity、指数记数法和 `-0`。涉及更大空间的标识使用字符串。
- SHA-256 表示为 64 个小写十六进制字符。ID、散列值、牌名和 token 不可互换。
- 每个完整 envelope 的规范 UTF-8 字节长度 MUST 为 1–8192；PCG-C14N-1 与本 wire profile 的嵌套深度上限均为32（根值 depth=0，进入数组元素或对象值加1）。超过上限拒绝，不能截断后执行。基线接收方 MUST 能处理 8192 字节。

### 2.2 `PCG-C14N-1`

所有发送的 envelope、规则状态/可见状态哈希输入和幂等比较输入，使用以下精确定义的规范 JSON 子集：

1. 拒绝重复对象键、非法 UTF-8、BOM、孤立 UTF-16 surrogate。禁止把解析错误静默替换为 U+FFFD。
2. 递归按对象键的原始 ASCII 码值升序排列。数组保持原顺序。
3. 不输出 token 之间的空格、换行或其他空白。
4. 整数使用十进制、无前导零、无加号，不输出 `.0` 或指数。布尔和 null 分别为 `true`、`false`、`null`。
5. 字符串中的 `"` 与 `\` 必须转义；U+0008/0009/000A/000C/000D 使用 `\b/\t/\n/\f/\r`；其他 U+0000–001F 使用小写 `\u00xx`。
6. 其余 Unicode 标量直接编码为 UTF-8，不转义 `/`，不把汉字或 emoji 改成 `\u` 序列；不执行 NFC/NFD 等 Unicode 标准化。`é` 和 `e` 加组合重音是不同字节。
7. `SHA256(canonical_utf8_bytes)` 对规范字节计算，不对内存结构、带缩进 JSON 或平台默认 serializer 输出直接计算。

本子集参考 RFC 8785 的字符串、Unicode 保留和规范序列化原则，但通过 **ASCII 键与安全整数** 缩小输入范围；不允许用“任意合法 JSON”代替它。[S2] Python 的 `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)` 只有在先验证这些输入限制后才适用。JavaScript 需递归排序键，不能把一次 `JSON.stringify` 当作排序器；使用 `Number.isSafeInteger` 验证数字。Android/iOS/ESP32 也必须明确编码选项。

接收流程为：限制字节数 → 严格解析并检测重复键/非法 token → 检查值范围/深度 → 规范重编码 → 与收到的字节逐字节比较 → JSON Schema → 会话/游戏语义。重编码不同则报 `NON_CANONICAL_JSON`，不得悄悄改写后执行。Schema 本身无法检测重复键、数字原始写法或 UTF-8 字节长度，不能省略这一层。

## 3. Envelope

```json
{"ack_seq":3,"body":{"action_id":"player_a-000001","card_instance_id":"p0:00","expected_revision":0,"kind":"play","match_id":"match_demo_01","row":"front","target_instance_id":null},"msg_id":"command_a_1","protocol":"pcg","protocol_version":"1.0","sender_id":"client_a","seq":2,"session_id":"session_demo_a_01","type":"COMMAND"}
```

| 字段 | 约束 | 含义 |
|---|---|---|
| `protocol` | 固定 `pcg` | 协议家族 |
| `protocol_version` | 基线固定 `1.0` | 本条消息的已协商线路版本 |
| `type` | 已知大写类型，或 `X_...` 可忽略扩展 | 消息分派；区分大小写 |
| `session_id` | HELLO 为 null；其余为 authority 分配的 ID | 一条已认证玩家—裁判逻辑会话，不是整个房间的 ID |
| `msg_id` | 此 sender 在 session 中唯一 | 消息去重和错误关联；不是 action 幂等键 |
| `sender_id` | 与已认证连接身份绑定 | 不能用它伪装另一玩家 |
| `seq` | HELLO 为 0；其余每方向从 1 严格递增 | 单 session、单发送方向的消息序号 |
| `ack_seq` | 0 或已接受的对向最大连续 seq | 接收确认；不是游戏动作执行确认 |
| `body` | 对应消息类型的封闭 schema | 游戏意图/协商/状态 |

Session 是双向连接的逻辑标识。A 和 B 加入同一 `match_id` 时使用不同 session。客户端的 seq 与 authority 对该客户端的 seq 各自递增，不能混用整个房间的一根计数器。

只有 `HELLO` 使用 `session_id=null,seq=0,ack_seq=0`。认证完成后客户端发送一次 HELLO；裁判返回 seq=1 的 CAPS 并赋予 session_id。重连创建新的 session，重新从 1 计数。旧 session 上的消息不得进入新 session。

`msg_id` 重用且内容不同是 `MESSAGE_ID_CONFLICT`。已经交付过的 `(session_id,sender_id,seq,msg_id)` 重复消息不再次执行，必要时重发接收确认。同 seq 但不同消息视为协议错误。正常 Adapter 保证有序；若接收 seq 大于期望值，报 `SEQ_GAP` 并重新建会话/RESUME，不在客户端猜测缺失的意图。`ack_seq` 不能倒退，也不能超过本端已发送的最大 seq。

收到普通消息后，如果 100ms 内没有其他出站消息带回累计 `ack_seq`，SHOULD 发 `ACK`。收到 `ACK`、`PONG` 或 `ERROR` 不单独触发 ACK，避免确认循环；后续消息仍带累计序号。这依赖底层 Adapter 的可靠有序交付。ACK 丢失不能导致重复扣牌或重复执行动作。

## 4. 协商与状态机

### 4.1 开局路径

1. Adapter 建立经过认证的链路，authority 将它绑定到账户/临时玩家或只读旁观者。房间码只定位房间，不自动等于玩家身份认证。
2. **Client → HELLO**：支持的线路版本、规则 ID、缓存内容 manifest 的精确 hash、effect opcodes（含trait能力）、features、资源限制和请求的 match。
3. **Authority → CAPS**：确定线路版本、认证后分配的玩家 ID、房间 match、authority 模式、共同 features 和限制。HELLO 中的 `client_id` MUST 等于 envelope.sender_id；CAPS.authority_id MUST 等于其 sender_id。
4. **Authority → SELECT**：唯一选定 `selection_id + rule_id + content_pack_id + content_version + content_hash + required_features + required_opcodes + room_policy`。客户端须真正加载并验证该 manifest，不能仅把 hash 字符串抄回。
5. **各 Client → READY**：回显相同 match、selection、rule、content_hash，并私下提交有顺序的 `deck_template_ids[10]`。所有参与对战玩家的牌组验证通过且均 READY 后，authority 才建立初始规则状态并发送各自 **SNAPSHOT**。旁观者不阻塞开局。
6. **Client → COMMAND → Authority → RESULT + 各自 SNAPSHOT**，直到规则状态 finished。

trait能力与opcode共用数组，不增加第二个traits字段：包中的 `required_ops` 保留原名，`required_traits` 则添加 `trait:` 前缀。因此core需要 `NONE,BOOST,DAMAGE,SELF_BOOST_OTHER_ROW,trait:shield_once,trait:stable`。HELLO用 `effect_opcodes`、SELECT用 `required_opcodes`，未知trait与未知op一样拒绝。`platform`支持`esp32/android/ios/macos/windows/linux/web/test`。

基线共同 features 固定为 `pcg.snapshot.v1`、`pcg.command.v1`、`pcg.resume.v1`、`pcg.canonical.v1`。SELECT 所需 feature/opcode/trait 必须是该客户端 HELLO 宣告支持的子集。`rule_id`、`content_hash` 和完整必需 opcode/trait 支持必须全部通过；“卡片显示得出来”不代表能执行它的效果。

新内容的获取是 `ContentLoader` 的职责，可通过预装、HTTPS、经认证桥接传输或本地安装同一个包完成。PCG/1.0 战斗消息不夹带图片或整包文件。若内容尚未就绪，客户端发非 fatal 的 `CONTENT_MISSING` / `UNSUPPORTED_EFFECT` 等 ERROR，保持未 READY；加载成功后再 READY。此时不得运行开局时限。authority 更换 SELECT 后会清空旧 READY，必须生成新的 selection_id。对局开始后 SELECT 不可变。

如果 HELLO 没有共同线路/规则版本，authority 在已认证链路上分配临时 session 后发送 fatal ERROR 并关闭。不得自动选择近似规则。客户端若仅实现未来主版本，必须另实现 v1 协商 shim 或使用独立入口；不能将不可解析的未来消息伪装为 `1.0`。

### 4.2 牌组提交与房间策略

`SELECT.body.room_policy` 是authority发给所有参与者的同一份不可变房间策略：

| 字段 | 约束与语义 |
|---|---|
| `mode` | `casual` 或 `ranked`；ranked只能使用经过认证的专用server authority |
| `deck_source` | `shared_pool`：所有玩家使用同一允许池；`verified_collection`：authority还须检查玩家的已验证可用资格 |
| `allowed_template_ids` | 10–128个互异模板ID，全部来自锁定manifest；对所有玩家公开 |
| `turn_timeout_ms` | v1固定0：无自动回合判负、无强制PASS |
| `reconnect_grace_ms` | v1固定300000：失联5分钟仍未重连时房间suspended，纯规则状态保持不变 |

READY的`deck_template_ids`必须是**恰好10个不同模板ID的有序数组**，均在允许池中，且按core.v1至少有6张unit。客户端提交只表达选择；服务端必须自行验证包、模板、数量与访问资格。该数组只发给authority，不广播对手。数组顺序对应本局`p0:00..09`或`p1:00..09`实例的创建顺序，不能被某个平台自行排序。seed只控制规则规定的先手；不要自创洗牌算法。

某个 selection 的第一次合法 READY 锁定该玩家有序牌组；相同 selection、rule、content_hash 与同一有序 deck 的重复 READY 不改变状态。若重连时看到 waiting，但在重发 READY 前房间已刚刚开局，authority 对上述重复 READY 只向该认证观看者返回当前 SNAPSHOT，不重建 match、不重新发牌、不改变 revision，也不把原牌组当成一次修改。尚未开局时，修改牌组或 room_policy 需要 authority 签发新的 selection_id 并清空所有 READY。开始后牌组、rule、hash 及 room_policy 不变化，不接受不同牌组的 READY。RESUME 不携带新牌组；只能恢复原局。

缺一份牌组、牌组不合法、未知模板、访问资格失败或能力不全时，authority发ERROR且不创建规则状态。`shared_pool`的免费基础池是默认试玩方案。`verified_collection`所需身份/收藏验证通过独立认证数据路径完成，不把原始玩家卡、UID或所有权证明泄漏给对手。

HTTP-WSS profile 的默认连接心跳为空闲每15秒 PING；45秒没有收到所请求的 PONG 或其他有效已认证 PCG 响应，标记失联并显示重连。PCG-F1 适用第9.4节的传输计时例外：完整 envelope 可能传输超过45秒，不能仅因没有完整应用消息而提前关闭仍在合法传输的 link。房间的5分钟重连宽限从 TransportAdapter 确认失联或关闭连接时开始，不从一个大包开始发送或最后一条完整 envelope 的时刻开始。宽限到期仍未恢复，房间层标记 `suspended`，不修改战斗 revision，不替玩家 PASS，不判输赢。房间与幂等日志至少保留24小时以供原玩家恢复。关闭/放弃房间记录为房间元数据 `aborted`，无竞技胜负；纯规则引擎仍只有 points 产生的正常终局。定时判负、resign 操作及异步长回合策略需未来独立协商 profile 及完整状态契约，v1不能宣称已实现。这些连接/房间状态与墙钟不加入纯规则状态 hash。

### 4.3 消息表

| 类型 | 方向 | body 关键字段与效果 |
|---|---|---|
| `HELLO` | Client → Authority | `client_id,platform,app_version,protocol_versions,rule_ids,content_manifests,effect_opcodes,features,limits,requested_match_id` |
| `CAPS` | Authority → Client | `authority_id,authority_mode,selected_protocol_version,assigned_player_id,match_id,features,limits` |
| `SELECT` | Authority → Client | `match_id,selection_id,rule_id,content_pack_id,content_version,content_hash,required_features,required_opcodes,room_policy` |
| `READY` | Client → Authority | `match_id,selection_id,rule_id,content_hash,deck_template_ids`；内容与牌组验证完成才发 |
| `SNAPSHOT` | Authority → Client | `match_id,revision,rule_id,content_pack_id,content_hash,view_player_id,view,view_hash` |
| `COMMAND` | Client → Authority | 第 5 节的七个固定字段 |
| `RESULT` | Authority → 发命令者 | `match_id,action_id,status,revision,error_code,events,snapshot_required` |
| `ACK` | 双向 | `received_msg_id`；累计确认以 envelope.ack_seq 为准 |
| `RESUME` | Client → Authority | `match_id,last_revision,rule_id,content_hash,pending_action_ids` |
| `ERROR` | 双向 | `code,message,fatal,ref_msg_id,retryable`；message 仅作展示 |
| `PING/PONG` | 双向 | `nonce,monotonic_ms`；PONG 原样回显二者，不修改状态 |
| `X_*` | 协商允许的方向 | 可忽略扩展；永远不能改变战斗规则或必需安全行为 |

各 body 的必填/可选和上限以 envelope schema 为准。`presentation` 是允许未知展示字段的专用子对象；不参与规则判断。COMMAND 没有这个扩展入口，固定七个字段，以免幂等比较含义不明确。`events` 的内容来自 reducer 或已验证事件过滤器，只含该收件者可见的信息；客户端不依靠 events 重建唯一状态，SNAPSHOT 才是恢复依据。

## 5. 命令、幂等与 revision

### 5.1 固定命令

```json
{"action_id":"player_a-000001","card_instance_id":"p0:00","expected_revision":0,"kind":"play","match_id":"match_demo_01","row":"front","target_instance_id":null}
```

`play` 的 `card_instance_id` MUST 非 null。若所选模板为 `unit`，`row` MUST 为该模板允许的 `front` 或 `rear`；若为 `tactic`，`row` MUST 为 null。Schema允许play.row为null，具体单位/战术校验由authority对照锁定的manifest执行。目标可为实例 ID 或 null，是否必须指定、能否选择该排位和该目标，由规则与卡包决定。`pass` 的 `card_instance_id,row,target_instance_id` MUST 全部为 null；不能用省略或空串代替 null。

命令中没有 player、actor 或 seat 字段。authority 从已认证 session 映射到 seat0/1，然后调用 reducer。`p0:00`..`p0:09` 和 `p1:00`..`p1:09` 只表示本局固定实例；收藏卡编号与实体 NFC UID 不进入 reducer。

客户端 MUST 在发送前持久保存未完成动作的 `action_id` 与原始七字段。一个 action_id 在该玩家该局里只能对应一个确切意图。

### 5.2 裁判处理顺序

1. 校验身份、session、房间权限、消息大小及 schema。
2. 查询幂等键 `(match_id,authenticated_player_id,action_id)`。存在且规范命令 body 相同：返回已记录的 **同一 RESULT.body**；不能先因 expected_revision 旧而拒绝。存在但 body 不同：`ACTION_ID_CONFLICT`，不覆盖原记录。
3. 新 action 的 `expected_revision` 必须等于当前 revision；否则返回 `status=rejected,error_code=STALE_REVISION` 和当时的当前 revision，并发送新 snapshot。
4. reducer 进行回合、手牌、目标、排位、通过状态等规则校验。合法动作调用一次 reducer。
5. 一个已接受动作让 revision 精确 +1，包括动作引起的小局结算；纯显示、PING、ACK、拒绝和重复动作均不增加 revision。
6. 原动作、命令摘要、结果与新状态 MUST 一起持久提交，再发送 `accepted` RESULT。若 advertise `pcg.resume.v1`，进程重启后也必须保留已提交的幂等结果。先发成功再保存会产生重复执行风险，不符合此规格。
7. 按每位已认证收件者重新生成 snapshot；先向发命令者发 RESULT，再发最新 snapshot。对手只需要自己的 snapshot，不能接收发命令者的私有响应副本。

被规则拒绝的新 action 也保存原始 RESULT；重复它仍返回原来的拒绝结果。用户修改意图或按新 revision 重试时必须使用新 action_id。若只是不知道第一次是否已送达，必须复用原 action_id 与**完全相同**的 body，并使用新的 envelope.msg_id/seq。

每局每玩家至少保留 1024 个动作结果；超出协议资源限额时停止接纳新的 action 并发 `RESOURCE_LIMIT`，不得丢弃尚可重试的旧记录。终局后至少保留 24 小时的状态及幂等日志；服务可保留更久，但必须对到期返回 `MATCH_EXPIRED`，不能把旧 action 当作一场新局。速率限制可在动作入列前返回 ERROR，不形成已执行的 RESULT。

`RESULT.revision` 是该动作原始处理时的 revision，不保证等于此刻最新 revision。因此重复 RESULT 的旧 revision 不能让客户端回滚。客户端如果需要最新状态，应用另发的 snapshot 或 RESUME。`error_code=null` 当且仅当 status=accepted；accepted 的 `snapshot_required=true`。

## 6. 可见状态与重连

### 6.1 Snapshot

`SNAPSHOT.body.view` 是规则定义的 viewer-filtered 状态。自己的玩家记录带 `hand:[{instance_id,template_id}]`；对手记录只带 `hand_count`。所有玩家的公开 board、discard、小局结果和比分可见。旁观者的两位玩家都只有 hand_count。完整随机 seed、对手隐藏实例 ID、完整牌组/未公开收藏记录、原始实体卡内容不可出现。authority 内存里的 full-state 不可直接 `json.dumps` 后广播。

`view_player_id` MUST 与认证上下文对应；旁观者为 null。`view_hash=SHA256(PCG-C14N-1(view))` 只保证本次可见状态的稳定校验；不能使用 authority 完整状态 hash 冒充它。完整状态 hash 仅供服务端/引擎 golden fixtures 校验，不作为客户端判断隐藏信息的依据。

客户端检查 body.revision 与 view.revision 相同、rule_id 与 view.ruleset_id 相同、content_hash 与已选 hash 相同，再校验 view_hash。只应用比本局当前 revision 更新的 snapshot；相同 revision 与相同 view_hash 为重复，同 revision 但不同 hash 是 `STATE_CONFLICT`，需要暂停输入并 RESUME/诊断。比较必须限定同一 match 与同一观看者。`view` 不放本地时钟、动画位置或临时网络 RTT，避免同 revision 的 hash 随 UI 改变。

权威快照允许跨过多个 revision，客户端无需收到每个事件才可恢复。不得为补一帧动画先应用比当前状态更旧的 snapshot。

### 6.2 Resume

断线后重新认证，创建新 session，走 HELLO/CAPS/SELECT。客户端重新验证 SELECT，然后发送 RESUME（此时不另发 READY 重开棋局）：

```json
{"content_hash":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","last_revision":7,"match_id":"match_demo_01","pending_action_ids":["player_a-000004"],"rule_id":"pcg.core.v1"}
```

上面 hash 是测试占位，实际值来自所选内容包。authority 根据认证身份找回同一个玩家 seat，不能因客户端提供 player_id 而换座。即使 last_revision 已是最新，基线实现也返回当前完整 viewer-filtered SNAPSHOT；随后返回 pending_action_ids 中仍在日志中的原始 RESULT，最多 16 个。未找到的 pending action 不伪造成功；发命令者可用原七字段重发，幂等处理照常。

若 last_revision 大于 authority 当前 revision，返回 `REVISION_AHEAD` 并暂停自动恢复，避免隐藏服务端回滚或错误房间。规则/内容不同返回 `CONTENT_MISMATCH` 或 `RULE_MISMATCH`；客户端不能自动迁移正在进行中的对局。旧 session 的 seq/msg_id 不转移，新封装可携带同一历史 RESULT.body。

客户端超时只能显示等待/重连，不能自行判负、通过、移动牌或推导对手动作。v1默认失联后仅suspended；终止房间记aborted，不创造reducer timeout/resign动作或竞技胜负。墙钟与重连宽限不进入纯 reducer 的状态哈希输入。跨 Authority 接力、自动主机迁移与双裁判容错不属于 v1；房主丢失时恢复原房主持久状态，或明确结束对局，不允许双方各选一个新结果。

## 7. 已知与未知消息

- 已知消息的未知顶层字段、未知 body 规则字段：`INVALID_MESSAGE`。不能把拼错的字段静默忽略。
- 已知 body 的 `presentation` 中未知字段：可忽略；不得执行脚本、改变牌力或权限。展示值也受 JSON 范围、深度和尺寸上限限制。
- 未知 `type` 如果匹配 `^X_[A-Z0-9_]{1,48}$`：消费 seq、可确认并忽略，不改变规则状态。对端不能依靠这种消息实现不可省略的功能。
- 其他未知类型：`UNSUPPORTED_MESSAGE`。在 match 开始前拒绝所需 feature；运行中出现未协商的必需消息则 fatal，关闭并诊断。
- 已认识 template_id 但其内容包含未知 opcode、schema major 或必需字段：拒绝 READY/开局。绝不能跳过效果后继续打。
- 客户端处理未知 ERROR.code 时仍尊重 `fatal/retryable`，显示安全的 message 或通用错误；不得把“未知错误”当作成功。

基线错误码：`INVALID_MESSAGE`、`NON_CANONICAL_JSON`、`JSON_DUPLICATE_KEY`、`JSON_KEY`、`JSON_INVALID_UNICODE`、`JSON_INTEGER_RANGE`、`JSON_FLOAT`、`JSON_DEPTH`、`JSON_INVALID`、`JSON_TYPE`、`UNSUPPORTED_PROTOCOL`、`UNSUPPORTED_MESSAGE`、`UNSUPPORTED_FEATURE`、`UNSUPPORTED_EFFECT`、`CONTENT_MISSING`、`CONTENT_MISMATCH`、`RULE_MISMATCH`、`UNAUTHENTICATED`、`NOT_AUTHORIZED`、`SESSION_EXPIRED`、`SEQ_GAP`、`MESSAGE_ID_CONFLICT`、`ACTION_ID_CONFLICT`、`STALE_REVISION`、`REVISION_AHEAD`、`STATE_CONFLICT`、`MATCH_EXPIRED`、`RATE_LIMITED`、`RESOURCE_LIMIT`，以及核心引擎的规则拒绝码。ERROR.message 不回显私有手牌、认证 token 或原始卡数据。解析坏包可以直接关闭；不得向不可识别/未认证的来源反射大段 ERROR。

## 8. 大 MTU 与字节流传输

### 8.1 WebSocket 基线

- WebSocket 子协议名为 `pcg.v1`，跨互联网使用 WSS；玩家凭证通过认证适配器建立，不放在战斗 body。统一房间服务/WSS接入的创建、加入、seat bearer与`pcg.auth.v1`前导认证由本项目房间接入文档（第12章）定义；该认证JSON在HELLO之前，属于TransportAdapter，不是PCG envelope，不调用reducer。
- 每一条 **binary WebSocket message** 恰好是一份 PCG-C14N-1 UTF-8 envelope。不加长度前缀，不使用 PCG-F1。WebSocket 自身 frame fragmentation 由其库复原后再交给 PCG。
- 不得把多条 JSON 拼接在一个 message；也不得把一条 JSON 拆成多个应用 message。基线拒绝 text message；实现不能只按字符串发送却宣称通过基线互通测试。
- 完整解压后也必须满足 8192 字节上限；v1 不要求压缩。推荐关闭 WebSocket 扩展压缩以简化 ESP32 实现和资源上限。

### 8.2 可靠字节流

用于 TCP/TLS、USB/串口桥、可靠 BLE GATT 字节流等：

`uint32_be byte_length | byte_length 个 canonical UTF-8 字节`

长度 1–8192；0 或超上限立即报协议错误/断开。接收器必须支持长度头分多次到达、JSON 跨多次 read、一次 read 同时包含多条消息。不得用 `\n` 找消息边界，也不能假设一次 read 等于一条 envelope。BLE Adapter 须处理 GATT 分块和顺序，不能把每个 ATT notification 当成一份 PCG 消息。

认证后的可靠传输必须把鉴权结果传给 authority，不以连接地址、客户端自报 sender_id 或设备型号代替身份。离线自动化测试可以使用明确标记的 in-process 已认证 fixture；这不等于生产端可省略认证。

## 9. 低 MTU 数据报：PCG-F1

ESP-NOW、支持足够应用负载的 RF 数据报和它们的桥接链路可使用 PCG-F1。每一份完整 JSON 被顺序切片，receiver 重组后才进行 envelope 解析。**Frame checksum、frame ACK、envelope ACK、RESULT 是四种不同含义**：分别为传输损坏检测、片接收、消息接收、动作裁决。

### 9.1 MTU 与链路打开

`frame_mtu` 表示 Adapter 认证/加密封装之后仍可提供给 PCG-F1 的一包最大字节数，包含本章 24 字节头。基线支持 128，推荐同能力双方选 200；固定到本 link 结束，不在中途改变。Espressif 官方文档说明 ESP-NOW v1 最大数据长度为 250 字节，v2 为 1470，混合版本要遵守 ≤250 的兼容边界；因此本规格不把新版大包作为共同能力。[S1]

若真实物理包仅能承载 20/32 等更小字节数，须由该 Adapter 提供可靠字节流或经桥接聚合，不能直接发送一个装不下的 PCG-F1 frame。不能以“有无线”推断两端原生互通。

PCG-F1 在**已经绑定到认证对端**的数据报链路上工作，不用于广播秘密信息。Client 生成非零 uint32 link_id，发 OPEN；Authority 选定参数回 ACCEPT。控制帧本身只有 32 字节，在 128 的基线下可收。Client 收到有效 ACCEPT 后才发送 HELLO；Authority 收到 HELLO 后才发送 CAPS 等应用消息，所以 ACCEPT 丢失不会造成服务器提前发送大包。重复同一个 OPEN 回相同 ACCEPT，不重置已建立的链路状态。参数改变或 link_id 改变须建立新会话并 RESUME。

OPEN 最多初次发送 + 4 次重发，每次等待所请求的 RTO。无 ACCEPT 则失败关闭；不是无限重试。认证适配器 MUST 防止旧 OPEN 在已使用的 link_id 上重置计数；link_id 是路由/重组标记，不是身份密钥。

### 9.2 精确二进制头

所有多字节整数 **big-endian/network byte order**。无结构体 padding、无 C ABI 对齐、无字符串终止符。payload 直接紧随第 24 字节。

| 起始 offset | 大小 | 字段 | 值/约束 |
|---:|---:|---|---|
| 0 | 2 | magic | `0x50 0x43`，ASCII `PC` |
| 2 | 1 | frame_version | `1` |
| 3 | 1 | kind | DATA=1、ACK=2、OPEN=16、ACCEPT=17 |
| 4 | 4 | link_id | 非零 uint32，绑定已认证对端 |
| 8 | 4 | transfer_id | DATA/ACK 为 1..2^32−1；OPEN/ACCEPT 为 0 |
| 12 | 2 | total_len | 完整 JSON 的字节数；DATA/ACK 为 1..8192；控制帧为 0 |
| 14 | 1 | frag_index | DATA 为 0..frag_count−1；其他为 0 |
| 15 | 1 | frag_count | DATA/ACK 为 1..128；控制帧为 0 |
| 16 | 2 | payload_len | 当前 payload 字节数，不能由无线库的 buffer 容量代替 |
| 18 | 2 | flags | v1 固定 0；其他值拒绝 |
| 20 | 4 | crc32 | 下节定义，编码为 big-endian uint32 |
| 24 | payload_len | payload | 当前帧内容 |

`actual_datagram_length` MUST 恰好等于 `24+payload_len` 且 ≤ frame_mtu。任何多余字节、缺失字节、未知 version/kind/flags、非法 index/count 或 CRC 错误都丢弃，不确认该片，不分配大 buffer。

**CRC32/ISO-HDLC**：reflected polynomial `0xEDB88320`，init=`0xFFFFFFFF`，xorout=`0xFFFFFFFF`，refin/refout=true。计算对象为 `header[0:20] || payload`，**不含 offset20..23 的 crc 字段**。Python `zlib.crc32(first20 + payload) & 0xffffffff` 与此定义等价。CRC 在头中仍以 big-endian 写入。测试标准串 `123456789` 的 CRC 为 `0xcbf43926`。

CRC 只能发现损坏，不能阻止伪造、篡改或重放。私有 battle 数据必须经认证且具完整性/保密性的 Adapter 传输：例如 WSS/TLS 或正确配对并使用非默认密钥的加密单播链路。ESP-NOW 支持 CCMP 保护，但不可因此把任意明文广播或 MAC 地址自动视为已认证。[S1] 裸 RF 的实现须补齐安全 Adapter 或只接到可信本地桥，不得宣称已经达到排位安全边界。

### 9.3 各 kind 的 payload

**OPEN / ACCEPT** 的 payload 固定 8 字节：

| payload offset | 大小 | OPEN 含义 | ACCEPT 含义 |
|---:|---:|---|---|
| 0 | 2 | maximum_frame_mtu：128 或 200 | selected_frame_mtu：双方最大值的较小者 |
| 2 | 2 | max_envelope_bytes：固定 8192 | 固定 8192；不支持则拒绝连接 |
| 4 | 4 | minimum_rto_ms：1000..60000 | 双方最低 RTO 的较大者，1000..60000 |

header 的 transfer_id/total_len/frag_index/frag_count 都为0，payload_len=8。既定参数随后由 HELLO/CAPS.limits 反映；HELLO/CAPS 不重新调整 frame_mtu。CAPS 内容与实际 Adapter 参数不符就断开，不能偷偷重解释后续分片。

**DATA**：设 `C=frame_mtu−24`，`N=ceil(total_len/C)`。frag_count 必须等于 N。第 i 片承载 JSON 字节 `[i*C:min((i+1)*C,total_len)]`；非最后片 payload_len=C，最后片恰好剩余字节。UTF-8 字符可能被切开，必须完整重组后解码。MTU128 的 C=104；MTU200 的 C=176。最大 8192 字节在两档分别需要 79、47 片，都在128片上限内。

**ACK**：复制所确认 DATA 的 transfer_id、total_len、frag_count；frag_index=0；payload_len=16。payload 是 128-bit 接收 bitmap；第 i 片的位为 `payload[i//8] & (1 << (i%8))`。1 表示该片已收到并通过结构/CRC校验。索引≥frag_count 的所有位必须0，不能将bitmap当作整数再按平台端序处理。ACK 不再被 ACK；任一合法重复 DATA 会触发新的累计 ACK。

### 9.4 发送、重组、重试与限额

- 每个已认证对端、每个方向同一时刻最多 **1 个 transfer**。双方可各有一个反向 transfer，但半双工无线 Adapter 要排程发送。
- 基线发送窗为 **1 片**：发送最低尚未确认的 index；收到包含该位的有效 ACK 再发下一片。不要求实现滑动窗口或压缩。
- 每片初次发送后启动选定的 RTO；无确认则原字节重传，最多4次。初发与四次重发分别在0、RTO、2RTO、3RTO、4RTO；5RTO仍未确认则关闭该 link，报告传输失败并重连/RESUME。不能换新 action_id 来“绕过”失败。
- 接收端收到任意合法片都可初始化该 transfer 的缓冲区，不要求先收到 index0；支持乱序、重复与跨回调到达。只在 bitmap完整且恰好 total_len 后交付 envelope 一次。
- 对正在重组的 transfer，total_len/frag_count 必须保持一致。同 index 重复 payload 不同，或同 transfer 参数冲突，视为损坏/攻击并关闭链路，不任选一个版本。已完成 transfer 的旧片也 MUST 核对 metadata 和对应片的 payload SHA-256；不一致关闭链路，一致时只回复原完整 ACK，不再次交付。
- 收到每一片有效 DATA 之后立即发累计 ACK；如果重复片来自已完成 transfer，则回该 transfer 的完整 ACK，不再次交付。最后一片 ACK 遗失也靠此规则恢复。
- 每个方向的 transfer_id 从1递增，不循环使用。到2^32−1后须新 link/session。重发沿用同 transfer_id。若当前 transfer未完成却收到新的 transfer_id，则拒绝新 transfer并关闭/恢复；正常 stop-and-wait sender不会产生这种顺序。
- 已完成 transfer 的 metadata、各片 payload 的 SHA-256 与完整 bitmap 只缓存最近8个完成 transfer；每项 TTL 为 `max(60000,6*RTO)` 毫秒，新增第9项时允许先淘汰最旧项，不承诺每项都存满 TTL。超过容量或 TTL 而不在缓存中的旧片，只要不大于最高完成 ID 就丢弃，不能当新消息。向前的新 transfer 只能是预期的下一个 ID。
- 单个未完成 transfer 无任何**新片**超过6RTO即清理并关闭 link；重复片不延长此计时。硬期限从第一片开始为 `(frag_count+6)*5*RTO`，超过则清理，无限慢滴数据不能无限占内存。
- F1 链路空闲时可每15秒发一条 PING 探测，不能让它插队或中断已开始的 transfer。已有活跃 transfer 时，按以上片 ACK、重试、6RTO 与硬期限判断传输失败；不得套用 WSS 的45秒完整消息阈值关闭仍有合法传输进展的链路。PING 已完整交付且没有活跃 transfer 时，等待应用 PONG 或其他有效 PCG 响应的探测期限为 `max(45000,5*RTO)` 毫秒；收到有效响应即结束本次探测，不重复堆积 PING。探测期限或以上传输期限耗尽时 Adapter 才报告失联，并开始房间的5分钟重连宽限。
- 每个已认证对端至多一个8192字节入站重组缓冲区；出站也至多一个。设备可以限制同时认证 peer 数量，拒绝超额连接。CRC/长度验证先于按 total_len 分配内存。
- ACK丢失、DATA丢失、重复、乱序都只影响交付时延，不增加 reducer 执行次数。低带宽 RF 的 RTO 和 airtime 限制可能让一条消息花很久；这不适合高频实时对战，但可承载本项目的离散回合消息。

`schemas/frame.schema.json` 是解码后字段的检查形式，**JSON 本身不发送到无线链路**。它不能替代 CRC、index<count、精确切片尺寸、位图空位、实际长度等跨字段校验。二进制 codecs 必须通过 examples 中的原始十六进制向量。

## 10. 跨平台与桥接

| 两端 | 推荐共同通路 | 关键边界 |
|---|---|---|
| M5Dial / PaperMono / 其他 ESP32 ↔ Android/iOS/Web | 双方各用 Wi-Fi/互联网连接同一个 WSS authority | 设备屏幕与 NFC 读取方式不同，不改变命令 |
| ESP32 ↔ ESP32，近距离无路由器 | 经认证的 ESP-NOW 单播 + PCG-F1 + 一方房主 authority | 保持旧设备可用的≤250字节物理负载边界 |
| RF/LoRa/nRF 等设备 ↔ 手机/Web | 对应无线模块 → 可信桥 → WSS 或可靠字节流 authority | 需要真实兼容无线硬件与桥接；不能只写相同 JSON 就直连 |
| BLE 外设 ↔ Android/iOS | 配对的 GATT可靠字节流 Adapter → PCG长度前缀 | GATT分块由Adapter负责，手机系统API不自动提供ESP-NOW |
| NFC读卡器 ↔ M5/手机 | 本地 CardReaderAdapter → 已验证卡选择/收藏 | 不把刷卡链路当远程对战网络 |

iOS、Android 和浏览器不可因为使用 Wi-Fi 硬件，就被宣称可通过普通应用 API 原生接收 ESP-NOW。不同频段/调制/物理协议的 RF 也不原生互通。桥接可以更换消息的传输封装，但不能更改 COMMAND.body、选择另一份规则或独立生成游戏结果。若桥终止认证，它就是信任边界的一部分，必须把已验证身份正确带给 authority。

## 11. 必须通过的互操作测试

1. 四平台对 `canonical_vectors` 产生同字节、同SHA256；拒绝重复键、1.0、1e0、-0、unsafe integer、非ASCII键和孤立surrogate。
2. HELLO/CAPS/SELECT/READY 使用同rule与content_hash能进入snapshot；不同hash、缺opcode、缺requiredfeature都不能开局。
3. ESP32发play，Web/iOS/Android收本人的filtered snapshot，最终revision和公开分数一致；每端不同的私有hand不影响一致性。
4. 同action同body发两次，只有一次revision增长且两个RESULT.body完全相等；同action改row报ACTION_ID_CONFLICT。
5. 用新action_id发旧expected_revision，只拒绝并补snapshot；不得重新计算到另一结果。
6. authority保存成功后在发RESULT前崩溃，重启+RESUME+重发原action仍执行一次。
7. 把任一玩家序列化view递归扫描：不存在对手hand、隐藏instance_id、seed、NFC UID、原始卡内容或另一个玩家的收藏证明。
8. 从最后1字节长度头、1字节JSON、两条串联消息等任意切分读取流，重组出的envelope相同。
9. 解析PCG-F1官方项目向量；反向到达、重复任意片、丢最后ACK、CRC损坏、count/index冲突、超额缓存、RTO耗尽都得到规定结果。
10. 旧客户端忽略X_展示消息仍继续同局；未知必需消息/未知效果拒绝；旧snapshot和重复RESULT不回滚当前view。

`examples/wire_examples.json` 中的内容hash是明确的格式测试占位值，手工view只测试wire/privacy，不是另一个规则引擎。规则执行与起手实例顺序以 reference engine 的 golden fixtures 为准；core v1 的起手是提交牌组的全部10张牌，不另行洗牌。发布集成测试时，须将真实卡包manifest hash填入双方已验证的运行环境。

## 12. 参考依据

- **[S1] Espressif，ESP-NOW Programming Guide**：v1/v2数据长度、混合版本兼容边界、CCMP与发送可靠性说明。https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/network/esp_now.html （核对日期：2026-11-08）
- **[S2] IETF RFC 8785，JSON Canonicalization Scheme**：字符串转义、Unicode原样保留、重复键与规范排序原则。https://www.rfc-editor.org/rfc/rfc8785.html （PCG-C14N-1采用文中明确规定的更窄子集。）

本章的消息字段、帧格式、重试次数和资源上限是本项目设计，不是上述外部标准已经定义的“通用NFC对战协议”。
