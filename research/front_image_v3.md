# 正视审核 v3

日期：2026-11-10。这是当前产品图目录的读图规则。`history/hardware_catalog_95.csv` 是拆分前的 95 条，不是当前目录。

## 数字不要混

- 当前目录 258 行：原来的 95 条，加上拆出的 161 条具体型号，再加上新的 H050 CardputerZero 和 U109 Unit CAM。
- 严格通过正视、并且仓库里有图的产品：**3 个产品，3 张图**。Tab5 是 H015，CardputerZero 是 H050，Unit CAM 是 U109。
- 有官方备用图的产品行：220。这些图是宣传首图、斜视、包装或拼图，**不是正面**。
- 正面列仍空着的目录行：255。
- 71 张游戏卡里，只有大平板（H015）和千里眼（U109）关联到严格正面图。敲键对应的是普通 Cardputer（H031），不是 Zero，没有正面图。

下载或目视过备用图，不等于正面审核通过。

## 字段

- `front_image_url` / `front_image_path`：只有上面 3 张。本地路径是 `research/images/front/`。
- `reference_image_url` / `reference_view_type`：备用图的官方地址和视角说明。
- 备用图文件没有打进这个包。`reference_image_path` 留空，`reference_image_local_status` 为 `unavailable`。官方 URL 保留。
- 未知就空着。不用斜视图去填正面列。

## 授权

这些官方图只作认产品和核对型号的参考。没有获得授权，不能当成正式游戏卡面、印刷稿或客户端资产。

三张正面图的联系表：`research/images/verified_fronts_only.jpg`。
