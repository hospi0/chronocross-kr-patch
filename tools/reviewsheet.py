"""모양 대조 애매 칸 검토 시트: 게임 칸(3배) | 후보 4개(MS고딕 12px 1비트 3배) — work/glyphs/review_NN.png"""
import sys,os,numpy as np; sys.path.insert(0,os.path.dirname(__file__)); import ccfont
from PIL import Image, ImageDraw, ImageFont
g=ccfont.load()
rows=[l.split('\t') for l in open('work/glyphs/shape_top.tsv',encoding='utf8').read().splitlines()]
thr=float(sys.argv[1]) if len(sys.argv)>1 else 0.9995
items=[]
for idx,top in rows:
    t=[x.rsplit(':',1) for x in top.split()]
    if float(t[0][1])<thr: items.append((int(idx),t[:4]))
F=ImageFont.truetype(r'C:\Windows\Fonts\msgothic.ttc',12)
LBL=ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf',12)
S=3; CW=16*S+8; PER=6; RH=11*S+22; ROWS=20
def cell(d,x0,y0,bm):
    for y in range(bm.shape[0]):
        for x in range(bm.shape[1]):
            if bm[y,x]: d.rectangle([x0+x*S,y0+y*S,x0+x*S+S-1,y0+y*S+S-1],fill=0)
def rend(ch):
    im=Image.new('1',(16,12),0); dd=ImageDraw.Draw(im); dd.fontmode='1'; dd.text((0,0),ch,fill=1,font=F); return np.asarray(im)
page=0
for p in range(0,len(items),PER*ROWS):
    chunk=items[p:p+PER*ROWS]
    W=PER*(CW*5+30); H=ROWS*RH+10
    img=Image.new('L',(W,H),255); d=ImageDraw.Draw(img)
    for k,(idx,t) in enumerate(chunk):
        x0=10+(k%PER)*(CW*5+30); y0=5+(k//PER)*RH
        d.text((x0,y0),f'{idx:04X}',fill=0,font=LBL)
        d.rectangle([x0-2,y0+14,x0+16*S+1,y0+14+11*S+2],outline=128)
        cell(d,x0,y0+16,g[idx])
        for j,(ch,sc) in enumerate(t):
            xx=x0+CW*(j+1)
            cell(d,xx,y0+16,rend(ch)); d.text((xx+16*S-10,y0),f'{j+1}',fill=100,font=LBL)
    img.save(f'work/glyphs/review_{page:02d}.png'); page+=1
print(len(items),'items',page,'pages')
json=__import__('json'); json.dump([(i,[c for c,s in t]) for i,t in items],open('work/glyphs/review_items.json','w',encoding='utf8'),ensure_ascii=False)
