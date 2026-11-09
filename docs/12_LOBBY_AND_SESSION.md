# 12 · 房间服务与会话接入 Profile

本章定义一种可直接实现的共同寻址方式，避免客户端虽然都会发 PCG 消息却找不到同一个房间。Profile ID 为 `pcg.lobby.http-wss.v1`。它是首发跨手机/Web/ESP32 的默认路径；ESP-NOW/RF 可用自己的配对与房主发现，但进入 PCG 后命令语义相同。

## 1. 部署与安全边界

客户端配置 `authority_base_url`，例如开发环境中的实际本机地址；文档不提供虚构的公共服务。远程使用 HTTPS/WSS；本机 loopback 开发模式可显式启用 HTTP/WS。不要在公共网页中默认明文连接远程地址，不要关闭证书验证解决证书配置问题。Web 对局域网访问的浏览器权限和安全来源限制需要目标实测。

authority 可为专用服务器或可信房主。休闲房中的 player_id 来自本地玩家身份，不能当作拥有者的密码学证明；真正操作权限来自本局随机 seat_token。该模式保护另一席位不能被随意操作，无法证明某玩家没有复制别人玩家卡。公开排位应另加账号认证与服务端可验证资格，本包不承诺已定义其完整身份产品。

## 2. 基础 HTTP API

JSON 使用 PCG-C14N-1；Content-Type 为 application/json；请求/响应上限 8192B，字符串错误不返回堆栈/密钥。所有枚举区分大小写。玩家 UUID 用小写 UUIDv4。HTTP 错误返回 `{api_version:"1",error_code,message,retryable}`，并用恰当的 400/401/403/404/409/410/429/503；不得以 200 + 空对象假装成功。

### 创建房间：POST /pcg/v1/rooms

请求字段：api_version="1"、request_id=UUIDv4、player_id=UUIDv4、display_name（32 scalar/96 UTF8 bytes以内）、room_profile="standard14.casual.v1"、rule_id="pcg.core.v1"、content_hash（本包实际 hash）。未知字段拒绝。请求必须使用调用端持久化的 request_id；先查询幂等记录，再执行创建/满房/身份占席检查。同 request_id 不同 body 固定返回 HTTP 409 REQUEST_ID_CONFLICT。响应丢失重试相同 body 返回同一已创建房间，至少保留 10 分钟幂等窗口。客户端不得因超时无限新建房间。

响应字段：api_version="1"、room_id、match_id、seat=0、client_id、player_id、seat_token、invite_code、ws_url、room_profile、rule_id、content_hash、expires_at_ms。room_id/match_id/client_id 满足协议 ASCII ID 约束；client_id 由 authority 分配，随后 HELLO.sender_id 与 HELLO.client_id 使用它。seat_token 为 CSPRNG 32 字节的 base64url 无 padding（43字符），属于私密凭据。invite_code 为 CSPRNG 16字节 base64url（22字符），给对手定位加入，不能取代 seat_token。

### 加入房间：POST /pcg/v1/rooms/join

请求字段：api_version="1"、request_id=UUIDv4、invite_code、player_id=UUIDv4、display_name。先查 request_id 幂等记录再查房间是否已满或该 player_id 已占席；同 request_id 同 body 返回原结果，不同 body 返回 409 REQUEST_ID_CONFLICT。响应结构同创建，seat=1、独立 client_id/seat_token，invite_code 为同房邀请码。不存在/已满/过期/玩家身份已占席均明确拒绝。v1 只允许两席且两个 player_id 不同；相同卡在两端用来打自己会报 PLAYER_ALREADY_IN_ROOM，试玩生成独立临时玩家 ID。

邀请码可写为文本/QR；二维码仅为入口数据，不自动执行其中任意 URL。对于手动输入可使用可复制邀请码，不擅自缩短成易猜的四位码。已知 room_id 也不能绕过 invite_code 和空席检查。

### 房间状态：GET /pcg/v1/rooms/{room_id}

Authorization: Bearer seat_token。响应字段：api_version、room_id、match_id、status、seat、rule_id、content_hash、expires_at_ms。status 为 waiting/playing/suspended/finished/aborted/expired。不返回对手 token、手牌或整份存档。开发诊断端口不能无保护暴露 complete state。

### 主动关闭：POST /pcg/v1/rooms/{room_id}/close

Authorization: Bearer seat_token。请求 `{api_version:"1",request_id:UUIDv4}`。任一合法参与者可明确关闭朋友房，响应含 status="aborted"；若已 finished 保持 finished。aborted 不赋予对手竞技胜利，不调用不存在的 core resign 动作，不修改已接受出牌历史。UI 必须明确“结束房间”与本小局 PASS 的差异。

## 3. WSS 鉴权前导

连接响应里的 ws_url，必须使用完整 WebSocket message 边界。打开后 10 秒内，客户端发送唯一一条规范 JSON。AUTH 请求、响应及后续 PCG envelope 全部使用 WebSocket binary message（UTF-8 字节）；不使用 text message，不以单个网络 frame 当完整消息：

```json
{"auth_protocol":"pcg.auth.v1","seat_token":"<响应的私密令牌>"}
```

authority 检查令牌对应房间、席位、有效期；成功返回：

```json
{"auth_protocol":"pcg.auth.v1","client_id":"<已分配ID>","room_status":"waiting","status":"ok"}
```

`room_status` 为 waiting/playing/suspended/finished/aborted/expired，来自裁判持久房间状态；它指导恢复入口，不替代 battle snapshot。

失败返回 `{auth_protocol:"pcg.auth.v1",status:"error",error_code:"UNAUTHENTICATED"}` 并关闭，不暴露匹配线索。这个前导属于 TransportAdapter，不是 PCG envelope，不占 seq；成功后才允许 HELLO。前导最大 1024 字节且深度不超过4，不接受第二次认证改变席位。Web 浏览器不需要能设置 WebSocket 自定义 Authorization header。

令牌存目标平台安全/本地存储供恢复，禁止写入玩家卡、二维码邀请、公开日志、query string 或对战 snapshot。它不是跨设备迁移收藏凭证。新连接使用同 token 可恢复同席；默认替换旧连接并使旧 session 失效，防止两个活跃连接同时发动作。必要的 Token 轮换属于部署管理，必须显式处理恢复失败。

## 4. PCG 开始与恢复

本 profile 对 SELECT.room_policy 的精确映射为：mode="casual"、deck_source="shared_pool"、allowed_template_ids 等于 core_pack.standard_loan_template_ids 的同序完整 14 项、turn_timeout_ms=0、reconnect_grace_ms=300000。不能将教学 10 张误作全部构筑池。

认证成功后走 HELLO/CAPS/SELECT；HELLO.requested_match_id 必须匹配鉴权房间。READY 提交锁定 deck_template_ids（恰好10唯一模板，顺序用于 instance_id 分配）；两席牌组有效才建立初始状态。牌组只交裁判，不发给对手。v1 standard14 允许全部公共模板；必须检查 ≥6单位、内容hash与模板存在。第一局 seed 由 authority CSPRNG 生成 uint32；只需要最低位决定先手，不把 seed 放入对手视图。

若 AUTH.room_status=waiting，重新 HELLO/CAPS/SELECT 后按该 selection 发送 READY，沿用本地持久的同一有序牌组；此时可能尚无 battle state，不能要求 RESUME 返回不存在的 snapshot。authority 保留 waiting 阶段已锁定的牌组；同 selection 重复 READY 只确认，不改牌。AUTH 返回 waiting 后可能另一方已准备并开局：此时同 selection、同 deck 的重复 READY 直接返回该观看者当前 SNAPSHOT，不重建战局；不同 deck 则拒绝。若 playing/suspended/finished，重新鉴权、HELLO/CAPS/SELECT 后发送 RESUME；不再次 READY 修改已开局牌组。aborted/expired 直接显示房间结束，不新建同 ID 对局。authority 持久状态与结果日志至少保存到最后活动后 24h；未开始等待房间 30min 后可过期。明确过期返回 MATCH_EXPIRED，不默默另开一个同 ID 的 match。

## 5. 连接与时间默认

空闲 15s 发送 PING，45s 未收到对向有效消息时显示失联并尝试重新连接；这只是网络状态。没有网络包不等于玩家 PASS。任一方失联时规则状态可以暂停接收新动作，避免对方界面不清楚现状；authority 统一决定是否接收当前合法单步，客户端不自裁。

5min 无恢复将房间标 suspended；仍保留至少 24h 的持久恢复窗口。core v1 默认没有自动回合倒计时、无超时判负，也无时间触发的战力效果。任何长期异步、定时判负或排位模式须另定义房间 profile 和状态/终局契约；不能只加 UI 倒计时就宣称支持。

## 6. 参考服务必须完成的工作

生产代码不在本包中，但使用本规格开发客户端的 agent 在没有现成服务时必须附最小运行服务：上述房间接口、WSS AUTH、协议协商、固定内容、两席独立视图、事务性 authority/replay、断线恢复、可配置绑定地址与 TLS 入口。参考运行默认只绑定本机；部署到外网是另一步。

独立供应商可实现其他 LobbyAdapter，但首发客户端至少支持本 profile 才有共同互操作入口。换服务不能换规则；跨 gateway 只改传输封装和认证上下文，不重复执行 reducer。
