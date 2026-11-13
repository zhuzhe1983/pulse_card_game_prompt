# 网页实现交接 · tactical-v1

用户本轮授权同时实现技能、平衡和 UI。主线唯一规格是 docs/01_GAMEPLAY.md 与 CONTRACT.json。旧昆特规则在 archive/pre-tactical-20261113，不能混回当前入口。

web/src/clash/engine.js 与本仓库 reference/clash.js 字节一致。新规则来自 clash_balance.json，新技能来自 clash_tactics.json；两份文件和 capabilities.json 同步到 web/content/clash/。设备基线保留。修改引擎后重新同步参考副本及 CONTRACT 的哈希，并在两个仓库跑测试。

网页构建：`python3 tools/build_clash.py`，同时生成图鉴设计数字。检查：`node tools/check.cjs`。浏览器：从 web 根目录启动服务器后运行 `tests/tactical.browser.cjs`，可用 PLAYWRIGHT_MODULE_PATH 指定 Playwright。浏览器自行关闭；不把视口仿真写成真机测试。

人机随机牌组 16/10/4，12 张技能均有执行逻辑。随机牌组完整洗牌，前四张保证两台低费主控；AI 会使用技能和选择场面交换。新卡面效果常驻，手机和横屏独立布局。结束回合、交接、终局和重开需回归。

资料与资产：保留真实型号、SKU、美术和成长关系。技能没有硬件 SKU。旧玩家存档、收藏和联网不在当前已实现范围；独立 M5Dial 固件继续保留于 web，但尚未做本轮实机验证。

两个仓库当前为本地开发版本；构建、提交不等于线上发布。数值仍待真人试玩，尤其检查恢复/过牌的长局和后手补偿。
