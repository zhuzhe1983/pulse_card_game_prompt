# 官方素材档案

目录名 `offical` 按指定拼法保留。22 张原卡和 22 张角色图已经按原字节复制到这里，原路径上的数字序号也已去掉。StampFly、StamPLC、CoreMatrix、CardputerZero 的新设计包还没到，所以这次还不是最终完成。

## 文件名

文件名是卡面或原资源标签，大小写跟原来的文件名（去掉 `01_` 这类序号）一致。例如卡面写 S3 就叫 `S3.png`，不改成 CoreS3；卡面写 M5PAPER 就叫 `M5PAPER.png`，不改成 Paper、PaperS3 或 PaperMono。

`official_card_label` 是这个卡面标签。`hardware_product_name` 只有在目录里能唯一对上某一款硬件时才填写，对不上就是 null。系列卡名不是某一款具体产品。

同一标签的卡面和角色图分开放：

`asset/offical/card/<标签>.png`  
`asset/offical/char/<标签>.png`

工作副本在：

`asset/card/<标签>.png`  
`asset/char/<标签>.png`

两边字节相同。映射和 SHA-256 在 `MANIFEST.json`，可以从现在的文件名回到原来的带序号文件名。

能填硬件产品名的只有：StickS3、NanoH2、Chain DualKey（卡面仍叫 DUALKEY）、StickC（卡面仍叫 STICKC）、StickC-Plus（卡面仍叫 STICKC_PLUS，不是 Plus2）、Core2（卡面仍叫 CORE2）、CoreInk（卡面仍叫 CORE_INK）。

## 新设计还没到

新设计预览以后放在：

`asset/card/style-a/`、`asset/card/style-b/`  
`asset/char/style-a/`、`asset/char/style-b/`

文件名仍不带序号。已留的名字是 CoreMatrix、StamPLC、CardputerZero。StampFly 的官方页是 https://docs.m5stack.com/en/app/StampFly ，文件名等设计包再核对。Cardputer 不是 CardputerZero。

新卡背景是可变 token，数值等设计包。不把 `#009ee0` 或 `#0079b4` 当成全部新卡的底色。固定层以后只和同一 token 的模板比较，不和蓝色母版比较。旧的 CardputerZero 概念稿仍是 needs_revision 或 superseded，不是本次新设计，也不改为 accepted。

原图没有改色。
