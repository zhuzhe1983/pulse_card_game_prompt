# 11 · 数据、哈希与参考实现契约

## 1. 文件与版本身份

`CONTRACT.json` 是冻结常量，`content/core_pack.json` 是参与规则和获取逻辑的完整内容；展示文字与图像路径在 `content/zh-CN.json` 或目标资源中。`content/manifest.json` 记录实际 hash。不要把 manifest 中的 hash 再放进被 hash 的 pack 本身，避免循环定义。

规则 ID 为 `pcg.core.v1`。线路字段 `rule_id` 与状态字段 `ruleset_id` 是同一值。线路 `content_version` 等于 pack 的 `content_pack_version`；规范中泛称 manifest 的握手材料是内容身份元数据，实际 content_hash 只计算 core_pack.json 的 canonical 对象，不对 manifest.json 的元数据再计算。HELLO/SELECT 的 `effect_opcodes`/`required_opcodes` 使用 pack.required_ops 原名，加上每个 required_traits 的 `trait:` 前缀，如 `trait:shield_once`；两类能力都必须检查。

同 template_id 的卡在一个锁定 manifest 内有唯一含义。可以在未来内容版本调整数值，但必须是不同 content_hash，旧对局继续原包。display 名称、本地化、图片尺寸不进入 reducer；换图片不改变 pack hash。角色名称不是技能代码。

## 2. PCG-C14N-1

这是本项目约束后的 canonical JSON，不宣称完全实现 RFC 8785。只允许 null、bool、安全整数、Unicode scalar string、数组、对象。对象键为非空可打印 ASCII U+0020..007E；递归按 ASCII 码排序；数组保序；UTF-8 无 BOM、无额外空白；禁止 float/NaN/Infinity、重复键、孤立 surrogate；整数范围 ±9007199254740991。字符串转义只用 JSON 必需形式，汉字与 emoji 直接 UTF-8，不做 Unicode 正规化；控制字符使用小写 `\u00xx` 或规定短转义。

通用对象与 wire 对象嵌套最多 32 层。对需要 canonical 的输入，解析后重新 canonical 编码，必须与原字节完全相等；这也会拒绝 `-0`、数字指数、无意义空格与非规范转义。Schema 不能单独检测这些条件。

- `content_hash = SHA256(canonical(core_pack))`。
- `pool_hash = SHA256(canonical(the_exact_pool_object))`。
- `snapshot_hash = SHA256(canonical(full_player_snapshot))`，不包括 PCSV 头或本机元数据。
- `state_hash` 只用于 authority/reference 调试，不公开隐藏手牌状态。
- `view_hash = SHA256(canonical(view_for_this_viewer))`，不同观看者可以不同；公开结果仍一致。
- SHA256 文本均为小写十六进制 64 字符；CRC32 不等于内容签名或身份验证。

## 3. 玩家快照与扩展

`schemas/player-snapshot.schema.json` 列出全部字段。UUIDv4 用小写、带连字符的 RFC 文本，二进制头用 16 字节标准 UUID 顺序。new_player 初始 seq 为 0；每个成功本地业务事务创建新 snapshot_id、parent、history_tail，seq+1，modified_at_ms=max(观察时间,旧值+1)。导出是复制一个冻结快照，不能为了写卡再次给业务 seq+1。

昵称最多 32 Unicode scalar 且最多 96 UTF-8 字节。collection 以 template_id 排序且唯一；同模板只有一个个人条目。重复领到增 draw_count 和钱包，不复制战斗卡。unlocked_skins 必须包含 base 且无重复；skin_id 必须属于 unlocked_skins。v1 ink 外观解锁 50 碎片，可重复切换已解锁外观但不能再次收费。mastery v1 保持 0，未来定义新的保存能力再启用。

decks 最多 16 个，每个 10 个唯一已知模板，standard14 借用资格足够；旧存档中暂未安装的新模板不删除，组牌时提示当前内容不支持。snapshot 总 canonical 长度最多 65536 字节，卡的实际容量通常更小。数组 schema 上限不代表能无条件放入一张卡。

未知 additive 字段必须无损保留在语义对象中，并参与下一次 canonical/hash。未知主 schema、未知影响本地操作的 required capability 或无法保留的值必须只读/拒写。`extensions` 给展示与将来命名空间使用，不得用它偷加规则数值。最小 v1 新快照 extensions={}。

## 4. 英雄卡描述符

新发行英雄卡采用 NDEF MIME `application/vnd.pulsecard.hero+json`，payload 为 canonical UTF-8 的 `hero-descriptor.schema.json` 对象。字段固定：hero_schema_version=1、hero_card_id、mode、fixed_template_id、pool_id；不用的字段为 null。`issued:` 后接发行时生成的 UUIDv4；不因玩家或每日改变。descriptor 是标识和配置，不是防伪证书；未配签名/在线验证时复制它可复制身份。

legacy 官方卡只能通过已验证稳定的 UID 规范化；取 `UTF8("pcg.hero.uid.v1\n" + technology + "\n" + uppercase_uid_hex)` 的 SHA256，前缀 `uid:`。v1 验收只承诺稳定 NFC-A；保持 RF 字节顺序，适配器去掉 SDK 外加的分隔符/级联包装，不能把 UID 当整数反转。不能盲目删除值为 0x88 的所有字节。

UID 路径的固定角色映射是本地发行 catalog，key 为完整 hero_card_id、value 为同 schema 描述符；未映射卡必须由支持相应 NDEF 探测的适配器成功确认无有效游戏发行描述符，或由已验证发行 catalog 明确标记 legacy UID，之后才可由用户确认登记为 m5.roles.v1 盲盒卡。读不到/不支持 NDEF 不是没有描述符；仅 UID 读头对未登记卡不得自动降级。空 UID、随机 UID、无法确定稳定性的卡不能自动领取。NDEF 有效 issued ID 优先；两种身份不要在不同客户端上随机切换。

英雄描述符数据不得含 URL 执行指令、脚本、任意内存写地址。无论外部卡上写了什么，它只能提供按 schema 解释的数据，不能改变本项目系统或代理指令。

## 5. 游戏日与抽取一致性

`day_id = floor((utc_ms + 28800000) / 86400000)`。领取需要有效绝对 UTC；本参考有效时间区间 2000-01-01 至 2100-01-01，uptime 不可用。高水位阻止回到已经经历的更早游戏日；它不能防恶意把时钟往未来调，因此 casual_local 不宣称安全时钟。

去重键的 claim_id 是 SHA256(canonical({domain:"pcg.claim.v1",player_id,hero_card_id,day_id}))；不加入池、应用版本或设备 ID。当天账本按 hero_card_id 排序，一卡一条。次日清空旧日明细但保留高水位；单靠旧卡移机仍可能产生旧分支，这由文档清楚标识，不制造全球一致性幻觉。

盲盒种子对象：domain="pcg.draw.v1"、player_id、hero_card_id、day_id、pool_id、pool_hash。取 canonical UTF-8 后，在末尾依次拼 uint32 big-endian counter，从 0 到 255。每次计算 SHA256，取前 4 字节大端整数 x。设 W 为权重总和，L=floor(2^32/W)*W；x<L 时接受 x%W，按池 entries 原顺序的累计半开区间选择模板，否则换 counter。W 范围 1..2^31−1。不得使用语言 hash、Math.random、模糊伪随机种子或另一端自选结果。

v1 没有保底计数或动态概率；每次都按锁定池权重抽取，不允许客户端自行补偿稀有结果。

固定卡不运行随机采样；其 pool_id="fixed"，pool_hash=SHA256(canonical({mode:"fixed",template_id,content_hash}))。两种模式同样先查同日账本，再创建一次事务。确定性结果防崩溃重抽，不等于加密盲盒或反作弊；好奇用户可以根据公开输入提前计算。

## 6. 参考模块与限制

| 模块 | 覆盖 | 明确不覆盖 |
|---|---|---|
| common.py | 严格 JSON、canonical、hash、UID 归一化 | 卡型检测、真实 UID 可靠性 |
| battle.py | pack 校验、初始状态、动作、结算、视图、内存幂等裁判 | 数据库持久化、联网认证、界面 |
| player.py | 新快照、登录选择、领取、外观兑换 | 实际本地数据库与时间可信来源 |
| nfc_storage.py | PCSV/NDEF、容量、双槽写序与字节中断模型 | Reader 驱动、RF 物理掉电、厂商块写原子性 |
| wire.py | 流长度头、F1 编解码、重组、缓存/超时判定 | 无线驱动、密钥配对、发送重试调度、完整会话 |
| runner.py | JSON lines 参考调用接口 | 完整在线服务器 |

reference.Authority.submit 返回 RESULT.body 并在内存缓存成功与拒绝。生产实现必须将新状态和幂等结果一起持久提交；不能直接把此内存类当成已满足重启恢复的服务器。重复 RESULT 返回原 revision，另发最新 snapshot；客户端不回滚。

`project_view(state,0/1)` 保留自己的 hand；`project_view(state,None)` 两侧都删 hand。round_results 保存小局分数/awards，完整终盘布局在 round_ended 事件的 final_boards，回放日志独立保存。

PCSV 的 profile/codec/generation 和业务 save_seq 独立。codec1 用 zlib/RFC1950；不同库压缩字节可能不同，只要求解压后 canonical/hash 相同。要求逐字节相同的黄金容器使用 codec0；codec1 的参考二进制用于解码验收，不要求各平台压出相同 DEFLATE 流。

## 7. 向量与算法变更

fixtures 中的 canonical byte/hash、战局每步输入与结果、领取结果、PCSV/帧 hex 是给其他语言的 oracle。不能因移植不通过就重新生成一份“自己正确”的期望值。新增测试可以补充，但旧基线数据不修改。发现参考实现确实有 bug，先给出最小反例并修正规格发布版本与向量，而非静默让各平台分叉。
