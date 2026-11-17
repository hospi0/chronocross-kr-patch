"""불일치·OCR 없음 칸 검토: 게임 칸(4배) | 모양 후보 3 | OCR 후보 2 (MS고딕 12px 1비트) → work/glyphs/rev2_NN.png"""
import sys,os,json,numpy as np; sys.path.insert(0,os.path.dirname(__file__)); import ccfont
from PIL import Image, ImageDraw, ImageFont
g=ccfont.load()
shape={int(l.split('\t')[0]):[x.rsplit(':',1)[0] for x in l.split('\t')[1].split()] for l in open('work/glyphs/shape_top.tsv',encoding='utf8').read().splitlines()}
votes={int(k):v for k,v in json.load(open('work/glyphs/ocr_votes.json',encoding='utf8')).items()}
items=[]
for l in open('work/glyphs/ocr_check.tsv',encoding='utf8'):
    k,i,c,_=l.rstrip('\n').split('\t'); 
    if k!='EXACT≠OCR': items.append(int(i,16))
F=ImageFont.truetype(r'C:\Windows\Fonts\msgothic.ttc',12); LB=ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf',13)
S=4; CW=16*S+6; PER=4; RH=11*S+24; ROWS=18
def draw(d,x0,y0,bm):
    for y in range(bm.shape[0]):
        for x in range(bm.shape[1]):
            if bm[y,x]: d.rectangle([x0+x*S,y0+y*S,x0+x*S+S-1,y0+y*S+S-1],fill=0)
def rend(ch):
    im=Image.new('1',(16,12),0); dd=ImageDraw.Draw(im); dd.fontmode='1'; dd.text((0,0),ch,fill=1,font=F); return np.asarray(im)
for pg in range(0,len(items),PER*ROWS):
    ch=items[pg:pg+PER*ROWS]; img=Image.new('L',(PER*(CW*6+40),ROWS*RH+10),255); d=ImageDraw.Draw(img)
    for k,i in enumerate(ch):
        x0=10+(k%PER)*(CW*6+40); y0=5+(k//PER)*RH
        ov=[c for c,_ in sorted(votes.get(i,{}).items(),key=lambda t:-t[1]) if len(c)==1 and '\u4e00'<=c<='\u9fff'][:2]
        cands=[('s',c) for c in shape[i][:3]]+[('o',c) for c in ov if c not in shape[i][:3]]
        d.text((x0,y0),f'{i:04X}',fill=0,font=LB); draw(d,x0,y0+18,g[i]); d.rectangle([x0-2,y0+16,x0+16*S+1,y0+18+11*S+1],outline=150)
        for j,(kind,c) in enumerate(cands[:5]):
            xx=x0+CW*(j+1); draw(d,xx,y0+18,rend(c)); d.text((xx,y0),f'{"S" if kind=="s" else "O"}{j+1}',fill=90,font=LB)
    img.save(f'work/glyphs/rev2_{pg//(PER*ROWS):02d}.png')
json.dump(items,open('work/glyphs/rev2_items.json','w'))
print(len(items))
