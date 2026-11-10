#!/usr/bin/env python3
"""Extract per-card subject illustrations as transparent PNGs. Local only; never writes CDR."""
from __future__ import annotations
import argparse,copy,csv,io,json,hashlib
from pathlib import Path
from lxml import etree as E
from svgpathtools import parse_path
import cairosvg
from PIL import Image,ImageDraw,ImageCms

NS='http://www.w3.org/2000/svg'
def q(n):return '{%s}%s'% (NS,n)
def localname(el):return E.QName(el).localname if isinstance(el.tag,str) else ''

def path_bbox(el):
    d=el.get('d')
    if not d:return None
    try:
        b=parse_path(d).bbox();return [float(b[0]),float(b[2]),float(b[1]),float(b[3])]
    except Exception:return None

def el_bbox(el):
    boxes=[]
    if localname(el)=='path':
        b=path_bbox(el)
        if b:boxes.append(b)
    for p in el.xpath('.//*[local-name()="path"]'):
        b=path_bbox(p)
        if b:boxes.append(b)
    if not boxes:return None
    return [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]

def parse_translate(tr):
    if not tr or not tr.startswith('translate'):return 0.0,0.0
    a,b=tr[tr.find('(')+1:tr.find(')')].replace(',', ' ').split()[:2]
    return float(a),float(b)

def style_opacity0(style:str)->bool:
    s=(style or '').replace(' ','')
    return 'fill-opacity:0' in s or 'fill-opacity:0.0000' in s or 'fill-opacity:0.0;' in s

def overlaps(a,b,pad=8.0):
    return not (a[2]+pad<b[0] or b[2]+pad<a[0] or a[3]+pad<b[1] or b[3]+pad<a[1])

def largest_component(items,pad=10.0):
    """items: list of (idx, bbox). Return indices of largest overlap component."""
    n=len(items)
    if n==0:return []
    parent=list(range(n))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(i,j):
        ri,rj=find(i),find(j)
        if ri!=rj:parent[rj]=ri
    for i in range(n):
        for j in range(i+1,n):
            if overlaps(items[i][1],items[j][1],pad):union(i,j)
    groups={}
    for i,(idx,b) in enumerate(items):
        r=find(i);groups.setdefault(r,[]).append((idx,b))
    def area(bs):
        x0=min(b[0] for _,b in bs);y0=min(b[1] for _,b in bs);x1=max(b[2] for _,b in bs);y1=max(b[3] for _,b in bs)
        return (x1-x0)*(y1-y0)
    best=max(groups.values(),key=area)
    return [idx for idx,_ in best]

def select_subject(root, card_id:int):
    layer=root.xpath('.//*[@id="Layer1005"]')[0]
    art=root.xpath('.//*[@transform]')[0]
    tx,ty=parse_translate(art.get('transform'))
    notes=[]
    # 01-09: content wrapped in one group
    kids=list(layer)
    if len(kids)==1 and localname(kids[0])=='g':
        content=list(kids[0]);mode='badge_group'
    else:
        content=kids;mode='flat_layer'
    kept=[];meta=[]
    for i,ch in enumerate(content):
        style=ch.get('style') or ''
        if style_opacity0(style):
            notes.append(f'skip[{i}] invisible/sunburst');continue
        b=el_bbox(ch)
        if not b:notes.append(f'skip[{i}] no bbox');continue
        lb=[b[0]+tx,b[1]+ty,b[2]+tx,b[3]+ty]
        area=(lb[2]-lb[0])*(lb[3]-lb[1])
        # chrome rules
        if card_id<=9:
            if lb[3] <= 40: # Tap to Build
                notes.append(f'skip[{i}] top title text');continue
            if lb[1] >= 165: # NTAG texts + bottom logo pill
                notes.append(f'skip[{i}] bottom chrome');continue
        else:
            if lb[1] >= 188: # titles + slogan capsule
                notes.append(f'skip[{i}] title/slogan');continue
            # top-left M5 logo cluster
            if lb[3] < 70 and lb[2] < 85 and area < 900:
                notes.append(f'skip[{i}] top logo');continue
            ww=lb[2]-lb[0];hh=lb[3]-lb[1]
            # colored ground oval / shadow plate under feet (not part of character)
            if hh>1 and ww/hh >= 3.2 and 145 <= lb[1] <= 185 and area >= 2000:
                notes.append(f'skip[{i}] colored ground oval');continue
            if area > 3000 and lb[1] > 145 and lb[3] < 195 and ww > 100:
                notes.append(f'skip[{i}] ground shadow band');continue
        kept.append((i,ch,lb,area))
        meta.append({'child_index':i,'id':ch.get('id'),'tag':localname(ch),'local_bbox':[round(v,3) for v in lb],'area':round(area,1)})
    if not kept:
        raise RuntimeError(f'card {card_id}: nothing kept')
    # 18-22: drop fireworks/stars first, then grow from large body seeds to keep hats/props.
    if card_id >= 18:
        import re as _re
        def _fill(style):
            m=_re.search(r'fill:\s*(#[0-9a-fA-F]+)', style or '')
            return m.group(1).lower() if m else None
        FW={ '#8db94f','#ffcb00','#40a58f','#7fcedc','#00afb2','#fff200','#ffff66' }
        filtered=[];meta2=[];fw_skip=0
        for (i,ch,lb,area),m in zip(kept,meta):
            fill=_fill(ch.get('style') if localname(ch)=='path' else '')
            ww=max(1e-6,lb[2]-lb[0]);hh=max(1e-6,lb[3]-lb[1]);aspect=max(ww/hh,hh/ww)
            is_fw=False
            if fill in FW and lb[1] < 130 and area < 1200: is_fw=True
            if fill=='#ffffff' and area < 200 and lb[1] < 130 and aspect >= 1.5: is_fw=True
            if fill=='#ffffff' and area < 40 and lb[1] < 100: is_fw=True
            # tiny gold alignment marks / stray stars far from torso
            if fill in ('#ffcb00','#ffec00','#f6eb16','#f4c430','#e6b422') and area < 120 and (lb[0] > 110 or lb[1] > 165): is_fw=True
            if is_fw:
                notes.append(f'skip[{i}] firework/star decor fill={fill} area={area:.0f}');fw_skip+=1;continue
            filtered.append((i,ch,lb,area));meta2.append(m)
        kept,meta=filtered,meta2
        seeds=[]
        for i,ch,lb,area in kept:
            ww=lb[2]-lb[0];hh=max(1.0,lb[3]-lb[1]);aspect=ww/hh
            if area >= 1800 and 0.55 <= aspect <= 1.8 and lb[1] < 160: seeds.append((i,lb))
        if not seeds:
            seeds=[(i,lb) for i,_,lb,area in sorted(kept,key=lambda t:t[3],reverse=True)[:3]]
        kept_idx={i for i,_ in seeds}; frontier=[lb for _,lb in seeds]
        changed=True
        while changed:
            changed=False
            for i,ch,lb,area in kept:
                if i in kept_idx: continue
                for f in frontier:
                    if overlaps(lb,f,pad=6):
                        kept_idx.add(i); frontier.append(lb); changed=True; break
        filtered=[];meta2=[]
        for (i,ch,lb,area),m in zip(kept,meta):
            if i in kept_idx: filtered.append((i,ch,lb,area)); meta2.append(m)
            else: notes.append(f'skip[{i}] outside body+prop cluster area={area:.0f}')
        kept,meta=filtered,meta2
        notes.append(f'firework_skipped={fw_skip}; body_seeds={len(seeds)}; kept_after_grow={len(kept)}')
        # Drop tiny leftover sparkles / alignment marks not overlapping a sizable subject piece.
        sizable=[lb for i,ch,lb,area in kept if area >= 120]
        filtered=[];meta2=[]
        for (i,ch,lb,area),m in zip(kept,meta):
            if area < 45:
                if not any(overlaps(lb,s,pad=4) for s in sizable):
                    notes.append(f'skip[{i}] tiny isolated sparkle/mark area={area:.0f}');continue
            filtered.append((i,ch,lb,area));meta2.append(m)
        kept,meta=filtered,meta2
    # Additional pass for 10-17: keep largest component only to drop stray logo pieces
    if 10 <= card_id <= 17:
        items=[(i,lb) for i,ch,lb,area in kept]
        main=set(largest_component(items,pad=14.0))
        filtered=[];meta2=[]
        for (i,ch,lb,area),m in zip(kept,meta):
            if i in main:filtered.append((i,ch,lb,area));meta2.append(m)
            else:notes.append(f'skip[{i}] outside main body cluster')
        kept,meta=filtered,meta2
    selected_nodes=[ch for _,ch,_,_ in kept]
    union=[min(lb[0] for _,_,lb,_ in kept),min(lb[1] for _,_,lb,_ in kept),max(lb[2] for _,_,lb,_ in kept),max(lb[3] for _,_,lb,_ in kept)]
    return selected_nodes,union,dict(mode=mode,notes=notes,selected=meta,union_local_bbox=[round(v,3) for v in union])

def build_subject_svg(card_svg:Path, selected, union_local, pad_pt=6.0):
    root=E.parse(str(card_svg)).getroot()
    art=root.xpath('.//*[@transform]')[0]
    tx,ty=parse_translate(art.get('transform'))
    # Collect gradient defs referenced indirectly by keeping all defs from card
    x0,y0,x1,y1=union_local
    x0-=pad_pt;y0-=pad_pt;x1+=pad_pt;y1+=pad_pt
    w=x1-x0;h=y1-y0
    out=E.Element(q('svg'),nsmap={None:NS})
    out.set('viewBox',f'{x0} {y0} {w} {h}');out.set('width',f'{w/72}in');out.set('height',f'{h/72}in')
    defs=E.SubElement(out,q('defs'))
    for d in root.xpath('.//*[local-name()="defs"]'):
        for ch in d:
            # skip card clip
            if localname(ch)=='clipPath':continue
            defs.append(copy.deepcopy(ch))
    g=E.SubElement(out,q('g'))
    g.set('transform',f'translate({tx} {ty})')
    for node in selected:
        g.append(copy.deepcopy(node))
    return out, (w,h)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cards-svg-dir',type=Path,required=True)
    ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--out-png',type=Path,required=True)
    ap.add_argument('--out-review',type=Path,required=True);ap.add_argument('--long-edge',type=int,default=1024)
    a=ap.parse_args();a.out_png.mkdir(parents=True,exist_ok=True);a.out_review.mkdir(parents=True,exist_ok=True)
    (a.out_review/'char_svg').mkdir(exist_ok=True)
    cards=json.loads(a.manifest.read_text())['cards'];srgb=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    report=[];thumbs=[];issues=[]
    for c in cards:
        svg_path=a.cards_svg_dir/f"{c['stem']}.svg";root=E.parse(str(svg_path)).getroot()
        selected,union,info=select_subject(root,c['id'])
        sub,wh=build_subject_svg(svg_path,selected,union,pad_pt=6.0)
        # scale: long edge 1024 while preserving physical aspect; report DPI equivalent
        Wpt,Hpt=wh;scale=a.long_edge/max(Wpt,Hpt);px=(max(1,round(Wpt*scale)),max(1,round(Hpt*scale)))
        dpi=round(scale*72)
        data=E.tostring(sub,xml_declaration=True,encoding='utf-8')
        (a.out_review/'char_svg'/f"{c['stem']}.svg").write_bytes(data)
        im=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=data,output_width=px[0],output_height=px[1]))).convert('RGBA')
        # QA
        alpha=im.getchannel('A');hist=alpha.histogram();corners=[im.getpixel(p)[3] for p in [(0,0),(px[0]-1,0),(0,px[1]-1),(px[0]-1,px[1]-1)]]
        opaque=sum(hist[1:]);qa=dict(non_empty=opaque>100,corners_transparent=corners==[0]*4,opaque_pixels=opaque,partial_alpha=sum(hist[1:254]),size_px=px,dpi_equiv=dpi)
        if not qa['non_empty']:issues.append(f"{c['id']} empty")
        if not qa['corners_transparent']:issues.append(f"{c['id']} non-transparent corner {corners}")
        # crude residual card-color detector: if a near-full-frame dominant color exists, flag
        bbox=im.getbbox()
        if bbox is None:issues.append(f"{c['id']} no bbox")
        out_name=f"{c['id']:02d}_{c['stem'].split('_',1)[1]}.png" if '_' in c['stem'] else f"{c['id']:02d}_{c['stem']}.png"
        # Keep stable ASCII names matching card stems already used
        out_name=f"{c['stem']}.png"
        im.save(a.out_png/out_name,dpi=(dpi,dpi),icc_profile=srgb)
        thumb=im.copy();thumb.thumbnail((180,180));thumbs.append((c,thumb,out_name))
        report.append(dict(id=c['id'],name=c['name'],stem=c['stem'],file=out_name,name_confidence=c.get('name_confidence'),selection=info,png_px=px,dpi_equiv=dpi,pad_pt=6.0,qa=qa))
    # checkerboard contact
    cols=6;rows=(len(thumbs)+cols-1)//cols;sheet=Image.new('RGB',(cols*200+20,rows*220+40),'#e8e8e8');d=ImageDraw.Draw(sheet)
    d.text((10,10),'Character extract | transparent | no card background',fill='black')
    for i,(c,th,name) in enumerate(thumbs):
        x=10+(i%cols)*200;y=35+(i//cols)*220
        for u in range(0,180,10):
            for v in range(0,180,10):
                d.rectangle((x+u,y+v,x+u+9,y+v+9),fill='#fff' if ((u+v)//10)%2==0 else '#d0d0d0')
        sheet.paste(th,(x+(180-th.width)//2,y+(180-th.height)//2),th)
        d.text((x,y+185),f"{c['id']:02d} {c['name'][:18]}",fill='black')
    sheet.save(a.out_review/'char_contact_sheet.png')
    # write manifests into review dir only
    (a.out_review/'char_manifest.json').write_text(json.dumps({'long_edge_px':a.long_edge,'padding_pt':6.0,'strategy':'vector group/path selection; no AI redraw; no white-key; card fill/sunburst/title/slogan/top logo/ground shadow removed; 18-22 keep largest overlap cluster to drop fireworks','cards':report,'issues':issues},ensure_ascii=False,indent=2))
    with (a.out_review/'char_manifest.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['id','file','name','name_confidence','width_px','height_px','dpi_equiv','selected_count','union_bbox','issues_flag'])
        for r in report:
            w.writerow([r['id'],r['file'],r['name'],r['name_confidence'],*r['png_px'],r['dpi_equiv'],len(r['selection']['selected']),r['selection']['union_local_bbox'],';'.join(x for x in issues if x.startswith(str(r['id']))) ])
    print(json.dumps({'count':len(report),'issues':issues,'out':str(a.out_png)},ensure_ascii=False))

if __name__=='__main__':main()
