"""work/gfx/tims.tsv 의 그림을 파일별 시트로(라벨=오프셋·크기) → work/gfx/sheet_<파일>_<n>.png"""
import sys,os
from PIL import Image, ImageDraw, ImageFont
rows=[l.rstrip('\n').split('\t') for l in open('work/gfx/tims.tsv',encoding='utf8')]
F=ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf',12)
want=set(sys.argv[1:])
by={}
for r in rows:
    if want and r[1] not in want: continue
    by.setdefault(r[1],[]).append(r)
for fi,L in by.items():
    k=0; page=0
    while k<len(L):
        y=0; W=1100; items=[]; 
        while k<len(L) and y<1400:
            im=Image.open(L[k][6]); s=1 if im.width>500 else 2
            im=im.resize((min(im.width*s,1000),im.height*s),Image.NEAREST)
            items.append((L[k],im,y)); y+=im.height+18; k+=1
        sh=Image.new('RGB',(W,y+4),(40,40,60)); d=ImageDraw.Draw(sh)
        for r,im,yy in items:
            d.text((4,yy),f'{r[2]} {r[5]} vram {r[4]} fl{r[3]}',fill=(255,255,0),font=F); sh.paste(im,(4,yy+15))
        sh.save(f'work/gfx/sheet_{int(fi):04d}_{page}.png'); page+=1
    print(fi,page)
