"""칸 확대 비교: zoom.py 출력.png 칸hex:후보글자들 ..."""
import sys,os,numpy as np; sys.path.insert(0,os.path.dirname(__file__)); import ccfont
from PIL import Image, ImageDraw, ImageFont
g=ccfont.load(); F=ImageFont.truetype(r'C:\Windows\Fonts\msgothic.ttc',12); LB=ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf',14)
S=7; items=[a.split(':') for a in sys.argv[2:]]
W=10+max(len(c)+1 for _,c in items)*(16*S+10); H=len(items)*(12*S+24)+10
img=Image.new('L',(W,H),255); d=ImageDraw.Draw(img)
def draw(x0,y0,bm):
    for y in range(bm.shape[0]):
        for x in range(bm.shape[1]):
            if bm[y,x]: d.rectangle([x0+x*S,y0+y*S,x0+x*S+S-2,y0+y*S+S-2],fill=0)
for r,(i,cs) in enumerate(items):
    y0=10+r*(12*S+24); d.text((10,y0-2),i,fill=0,font=LB); draw(10,y0+16,g[int(i,16)])
    for j,c in enumerate(cs):
        im=Image.new('1',(16,12),0); dd=ImageDraw.Draw(im); dd.fontmode='1'; dd.text((0,0),c,fill=1,font=F)
        draw(10+(j+1)*(16*S+10),y0+16,np.asarray(im))
img.save(sys.argv[1])
