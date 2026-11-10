# V2 全彩卡片：标语与圆角修复

## 已完成
- 22 张全彩透明 PNG、22 张逐卡 SVG、1 份整页修正 SVG、1 份整页矢量 PDF。PNG 每卡638×1004，300 DPI，物理尺寸54×85mm。保留插画、卡内白色，不重排、不灰阶化。
- 18–22 的黄色 IDEAS FAST TRACKED：直接复用10 CORE卡中原稿已经转曲的完整路径，保留原字体、字距、文字高宽比，没有把整行非等比拉扁。五张均100%原路径大小，只平移到黑色胶囊中心。左右各约1.853mm、上下各约1.915mm安全边距。
- 18–22 的白色标题：上一版所用本机Calibri兼容字体为Carlito，本版将这一渲染转成矢量路径，不再依赖接收机器字体。不是恢复原始Calibri字体；这是额外的字体依赖修复。黑/白重叠标题均转曲，未更换主体插画。
- 22张所有可见底色轮廓与透明裁剪轮廓，统一采用真实圆弧 R3.18mm；SVG A圆弧而非近似二次曲线。所有22张alpha通道逐字节完全相同，检查见validation.json。
- 原图约54×85mm，只规范掉libcdr点坐标的小数舍入误差（不足0.0001mm），未擅自改成标准85.60×53.98mm或放大/缩小插画。

## 圆角核查
原CDR转换出来，01–09是三次Bezier圆角，10–22是二次Bezier圆角。两种路径的直线到转角名义距离都是约5.4mm，但曲线几何不相同，所以可见圆角不一致。并不是01–10恰好一组：第10张已经属于后一种曲线。

本版参考卡厂家CR80/ID-1说明的常用R3.18mm：
https://www.blankplasticcards.com/blog/what-is-cr80-card-size-the-complete-guide-to-standard-plastic-card-dimensions/
厂家给出CR80角半径0.125英寸/3.18mm。本版取其公制名义值3.18mm。这是钱包卡/ID-1形状的参考，不代表所有NFC卡都强制用这一圆角；NFC是通信/芯片属性，实物若有专属刀模，仍应以刀模为准。本轮保持原稿54×85mm尺寸。

## 看图顺序
- contact_sheet_v2.png：全22张。
- slogans_18_22_v2.png：18–22底部放大，核对窄体原转曲标语。
- corners_01_10_11_before_after.png：01/10/11圆角前后对照。
- bounds_review_v2.jpg：原位置编号标框。
- png/：实际素材（无棋盘背景）；svg/：逐卡矢量。

## 原CDR状态：未修改，未生成假fixed.cdr
本次实际编辑的是本地转换出的SVG矢量，不是CDR二进制本身。
Mac的/Applications、/Applications/Utilities、~/Applications内未找到CorelDRAW；已有cdr2xhtml/cdr2raw来自libcdr，只读/转换，不能真实回写CDR。Inkscape也无CDR导出滤镜。未将SVG/PDF改后缀，未手工patch私有CDR数据。
- libcdr：https://github.com/LibreOffice/libcdr
- Inkscape导入/导出能力：https://answers.launchpad.net/inkscape/+question/93604
- Corel官方另存说明：https://product.corel.com/help/CorelDRAW/540111147/CorelDRAW-en/CorelDRAW-Save-drawings.html

供真正CDR另存的本地矢量主稿：m5_RFID_cards_fixed.svg（700×297mm）和同名.pdf。
在本地有效授权CorelDRAW中打开/导入SVG，核对页面700×297mm、22卡、全转曲文字、透明和渐变，再用 File > Save As，选择CorelDRAW(CDR)，另存m5_RFID_cards_fixed.cdr，重新打开并渲染检查。不要覆盖原稿。现在没有声称这一保存已做成。
矢量主稿仍属于保密设计文件，只供本人本地使用，禁止上传在线转换或公开发布。

## 可重跑
依赖Python3、lxml、svgpathtools、CairoSVG、cairocffi、Pillow，以及本地Cairo；原稿读取另需cdr2xhtml。运行不访问网络。

已有V1目录时：
```sh
python3 scripts/fix_cards_v2.py --v1 ../card_export_v1_review --out ../card_export_v2_rerun --radius-mm 3.18
```
脚本拒绝覆盖已存在的输出目录。

从CDR重新开始（原件仅只读；先取V1中间版再应用V2修复）：
```sh
python3 scripts/export_cards_v1_base.py '../m5 RFID  卡.cdr' --out ../card_export_base_new --dpi 300
python3 scripts/fix_cards_v2.py --v1 ../card_export_base_new --out ../card_export_v2_rerun --radius-mm 3.18
```

## 仍需注意
01、04、05、06产品名称仍是上版的临时名称/待确认项，不擅自更名。
源文件包含CMYK、透明、阴影、透视等效果；PNG标记sRGB，但尚未和Corel原生ICC渲染验证完全同色。PDF/SVG保留矢量，但不承诺替代原CDR所有可编辑特效。
保密：无公开上传、无模型图像调用、无Git提交。原CDR SHA256：e299355089a5ac1b49dedb96af81bdccbedd63ddc40418ac2407bb1831965964，未变。
