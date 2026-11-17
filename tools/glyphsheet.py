"""글꼴 칸 시트(라벨=칸 번호 또는 코드). 사용: glyphsheet.py 시작칸 개수 출력.png [글꼴bin]"""
import sys,os; sys.path.insert(0,os.path.dirname(__file__)); import ccfont
from PIL import Image, ImageDraw
s=int(sys.argv[1],0); n=int(sys.argv[2],0); out=sys.argv[3]; src=sys.argv[4] if len(sys.argv)>4 else 'work/files/1_0000.bin'
g=ccfont.load(src); S=3; per=16
def code(i):
    if i<0xd8: return f'{i+0x20:02X}'
    v=i+0x20; return f'{0xf7+v//256:02X}{v%256:02X}'
rows=(n+per-1)//per
img=Image.new('L',(per*(16*S+6)+10, rows*(11*S+14)+10),255); d=ImageDraw.Draw(img)
for k in range(n):
    i=s+k
    if i>=len(g): break
    cx=10+(k%per)*(16*S+6); cy=10+(k//per)*(11*S+14)
    d.text((cx,cy),code(i),fill=0)
    for y in range(11):
        for x in range(16):
            if g[i,y,x]: d.rectangle([cx+x*S,cy+10+y*S,cx+x*S+S-1,cy+10+y*S+S-1],fill=0)
img.save(out)
