# 研究记录

这里的表是资料，不是已经启用的规则。采用结论以 [../docs/14_EXPANSION_DRAFT.md](../docs/14_EXPANSION_DRAFT.md) 为准。

## 当前产品目录

`hardware_catalog.csv` 是当前目录，258 行，正视审核 v3。读图规则在 [front_image_v3.md](front_image_v3.md)。

- 95 条是拆分前的父记录，161 条是从复合行拆出的具体型号，用 `parent_record_id` 指回原来的 ID。
- H050 是 CardputerZero，U109 是 Unit CAM。这两条是新增。
- 严格正面图只有 3 张。220 条备用图不是正面。255 行仍然没有正面图。

`history/hardware_catalog_95.csv` 只是旧的 95 条，不是当前目录。

`image_review_v3.csv` 是逐张审核记录。`verified_front=true` 只有 3 行。备用图的本地文件没有入库，本地路径已清空，官方 URL 还在。

`card_product_image_map.csv` 把 71 张游戏卡对到目录。游戏中文名、英文名和千里眼的器具建议没有退回旧文案。

## 玩法研究笔记

- `compatibility.csv`：20 条组合规则。没写到的组合保持未知。
- `card_candidates.csv`：74 条旧候选。双行动占用和负分没有被草案采用。不要用这张表覆盖 `content/game_catalog.csv`。
- 同目录其他 markdown 是当时的笔记，保留原句。

Core2 与 Faces Bottom3 的处理只看第 14 章。参考裁判不读这些表。
