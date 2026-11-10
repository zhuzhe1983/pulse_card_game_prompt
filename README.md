# 脉冲对决

中文显示名为「脉冲对决」，英文显示名为 PULSE。技术标识保持 `pulse-card` 与协议 `pcg`。

现在能打的是基础 14 张牌：10 张牌组、最多 3 个小局、每小局最多打出 5 张、可以停手、比整数战力。中文显示名在 `content/zh-CN.json`，英文显示名在 `content/en.json`，都不含官方型号。扩展目录在 `docs/13_WORLD_AND_FACTIONS.md`、`docs/14_EXPANSION_DRAFT.md` 和 `content/game_catalog.csv`，**还没有启用**。千里眼在现有规则里仍是角色；草案建议改成器具，卡包哈希没有因此改动。

卡面实验在 `docs/16_CARD_FACE_STYLES.md`。第一轮整卡生成在 `asset/concepts/cardputerzero/`，已放弃。当前模板预览在 `asset/concepts/cardputerzero-template/`，状态 needs_revision，不是验收稿。产品图见 `research/front_image_v5.md`。v3 的 3 张不是最新结论，也不是官方一共只有 3 张。

素材归档还没完成，规则在 `asset/offical/README.md`。新卡背景是可变 token，不把旧蓝母版当成这次终稿。原卡和角色图还在带序号的路径，字节没有改。

## 进阶：实现与协议

本目录仍是实现基线。它定义玩法、角色获取、玩家卡保存、跨平台对战、传输适配、版本兼容和互操作验证。显示名可以再改，协议字段、规则、序列化和黄金测试向量必须一致。

## 使用方法

把整个目录或 ZIP 放进目标开发项目，首先将 `START_HERE.txt` 的完整内容交给 coding agent。需要单文件提示词时使用 `UNIVERSAL_PROMPT_FULL.txt`。不同平台可以采用不同语言、界面框架与读卡驱动，但必须通过同一组测试向量。

`CONTRACT.json` 是本次确认的参数表。详细字段以对应规范、JSON Schema、内容包和 fixtures 为准。发现相互冲突必须报告并修订规范，禁止客户端自行选择不同解释。

## 交付范围

本包是可执行规格和参考裁判，不是已经完成的 ESP32 固件、手机应用或联网服务。参考实现用于确定行为和测试移植；真实 NFC 读写、无线传输、系统权限和电源中断恢复仍必须在目标硬件验收。

## 读取顺序

1. `START_HERE.txt` 与 `CONTRACT.json`。
2. `docs/00_PRODUCT_AND_DECISIONS.md`、`01_GAMEPLAY.md`、`02_STYLE_AND_UX.md`。
3. `03_NFC_PLAYER_SAVE.md`、`04_WIRE_PROTOCOL.md`、`05_PLATFORM_ADAPTERS.md`。
4. `06_VERSION_COMPATIBILITY.md`、`07_ACCEPTANCE_AND_RECOVERY.md`、`08_AGENT_IMPLEMENTATION_CONTRACT.md`。
5. `09_TUTORIAL_AND_PLAYTEST.md`、`10_SOURCES_AND_MATERIALS.md`、`11_REFERENCE_AND_DATA_CONTRACT.md`、`12_LOBBY_AND_SESSION.md`。
6. `schemas/`、`content/`、`examples/`、`fixtures/` 与 `reference/`。

## 验证

在本目录执行 `python -m unittest discover -s tests -v`。标准库参考测试不需要联网。另有 JSON Schema 验证时，需要运行环境提供 `jsonschema`，并必须在验证报告中明确有没有执行。

所有日期样例都是固定测试数据，不应用来设置设备的当前时间。随机 UUID、首局种子与平台当前 UTC 时间由实际运行环境提供；确定性规则引擎不得自行读系统时间或抽随机数。

## 单文件与完整开发包

`UNIVERSAL_PROMPT_FULL.txt` 包含主提示词、全部需求章节和关键机器契约，供只能粘贴文本的工具使用。完整开发包额外提供 Python 参考实现、完整状态/二进制 fixtures 和测试。上下文较小的 coding agent 应优先接收 ZIP 与 START_HERE，按章节读取；不要在不支持的上下文长度下截断尾部协议。

核心命令行参考：`python -m reference.runner`。输入是一行一份 JSON 的开发 oracle，和 PCG 的线上 envelope/帧边界不同。可选操作见参考实现；例如 `{"op":"game_day","args":{"utc_ms":1794103200000}}`。
