# PULSE · 脉冲对决规格

当前唯一主线：`pcg.clash.v0 / tactical-v1`，已实现、待真人试玩。30 生命、7 台主控位、12 张技能、16/10/4 随机牌组；原昆特式点数方案已归档。

视觉主线为电子工作台，内置 ImageGen 位图组件和 12 张技能插画已接入网页；不使用原木酒馆主题。见 [视觉与交互规范](docs/02_STYLE_AND_UX.md)。

先读 [START_HERE.md](START_HERE.md)、[游戏规格](docs/01_GAMEPLAY.md) 和 [复审报告](docs/09_TUTORIAL_AND_PLAYTEST.md)。网页实现位于隔壁 pulse_card_game_web，当前参考裁判为 reference/clash.js，两边引擎与配置保持字节一致。

```bash
python3 -m unittest discover -s tests
```

检查需要 Python 3 与 Node.js，不需要 pip 包。卡牌加载顺序：clash_playtest → clash_roster_96 → clash_tactics → clash_balance.card_overrides；规则读取 clash_balance.rules。旧 clash_playtest/clash_services/教学 fixture 是基线资料，不是当前数值。根 CONTRACT.json 已改为当前契约。

旧 pcg.core.v1 的源码、契约、数据、测试、存档和联网设计保存在本地 archive/pre-tactical-20261113（6a3ce9d）。查看方式：`git show archive/pre-tactical-20261113:CONTRACT.json`。没有删除设备原图、来源资料或未跟踪的美术草稿。
