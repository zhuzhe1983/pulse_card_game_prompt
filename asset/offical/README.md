# 官方素材档案（未完成）

目录名 `offical` 按指定拼法保留。这里还不是归档完成稿。StampFly、StamPLC、CoreMatrix、CardputerZero 的新设计包还没进入仓库，不能把现有旧蓝预览当成这一次的终稿。

## 将来的位置

官方档案，文件名不带数字序号：

`asset/offical/card/<官方英文产品名>.png`  
`asset/offical/char/<官方英文产品名>.png`

新设计预览，用父目录区分风格，文件名同样不带序号：

`asset/card/style-a/<官方英文产品名>.<ext>`  
`asset/card/style-b/<官方英文产品名>.<ext>`  
`asset/char/style-a/<官方英文产品名>.<ext>`  
`asset/char/style-b/<官方英文产品名>.<ext>`

官方英文产品名只来自官方页面或本仓库已核对的产品目录。中文游戏卡名和 `template_id` 不能拿来当文件名。对不上唯一产品、或会和另一条记录撞名时，不猜。原文件先按字节留住，再决定能不能改名。

已预留的新产品位：CoreMatrix、StamPLC、CardputerZero。StampFly 的官方大小写等设计包或官方页标题，不在这里现编。Cardputer 不是 CardputerZero。ATOM Matrix 原版不是 v1.1。

## 背景

新卡的版式、字体和标志位置沿用模板。背景是明确的可变 token，不把整套新卡都做成 01_S3 的 `#009ee0` 或 10_CORE 的 `#0079b4`。

token 的真实数值由即将到来的设计包填写。现在清单里的值是空的。旧的蓝色合成稿仍放在 `asset/concepts/cardputerzero-template/`，状态 needs_revision，不是本次终稿，也不改成 accepted。

固定层校验要比对「用同一 token 参数化之后的模板」，不要去和蓝色母版对像素。原 `asset/card` 与 `asset/char` 的 22 张不得改色。字节对照表在 `MANIFEST.json`。

## 现在还没做

22 张原卡和角色图仍在原来的带序号路径。官方档案目录里还没有这些副本。设计包到达之前，不把这一步写成已经归档完成。
