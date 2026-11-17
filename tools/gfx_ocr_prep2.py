"""CLUT 없는 TIM(fl 0=4bpp · 1=8bpp)만 — 흑백 판정용으로 회색조 → work/gfx/all2/ · work/gfx/ocr2/"""
import sys,os,struct,hashlib,numpy as np; sys.path.insert(0,os.path.dirname(__file__))
from ccget import spans,P; from ccfs import Disc
from PIL import Image
os.makedirs('work/gfx/all2',exist_ok=True); os.makedirs('work/gfx/ocr2',exist_ok=True)
seen=set(); idx=open('work/gfx/ocr2/index.tsv','w',encoding='utf8'); n=0
for d in ('1','2'):
    D=Disc(P[d]); sp=spans(D)
    for fi,(l,c) in enumerate(sp):
        if c==0 or c>2000: continue
        b=b''.join(D.sec(l+j) for j in range(c))
        i=b.find(b'\x10\0\0\0')
        while 0<=i<len(b)-20:
            fl=struct.unpack_from('<I',b,i+4)[0]
            if fl in (0,1) and i%4==0:
                il,ix,iy,iw,ih=struct.unpack_from('<I4H',b,i+8)
                if iw and ih and iw*ih*2+12==il and i+8+il<=len(b) and ix<1024 and iy<512 and iw*ih>=64:
                    data=b[i+20:i+8+il]; h=hashlib.md5(data).hexdigest()
                    if h not in seen:
                        seen.add(h); a=np.frombuffer(data,np.uint8)
                        if fl==0: g=np.zeros((ih,iw*4),np.uint8); p=a.reshape(ih,iw*2); g[:,0::2]=p&15; g[:,1::2]=p>>4
                        else: g=a.reshape(ih,iw*2).copy()
                        name=f'{d}_{fi:04d}_{i:06x}'; Image.fromarray((g*(17 if fl==0 else 1)).astype(np.uint8)).save(f'work/gfx/all2/{name}.png')
                        vals,cn=np.unique(g,return_counts=True); bg=vals[cn.argmax()]
                        bw=np.where(g==bg,255,0).astype(np.uint8); H,W=bw.shape; s=3 if max(H,W)<1000 else 1
                        pad=Image.new('L',(W*s+40,H*s+40),255); pad.paste(Image.fromarray(bw).resize((W*s,H*s),Image.NEAREST),(20,20))
                        n+=1; pad.save(f'work/gfx/ocr2/img_{n:05d}.png'); idx.write(f'{n}\t{name}\t{g.shape[1]}x{ih}\tfl{fl}\t{ix},{iy}\n')
            i=b.find(b'\x10\0\0\0',i+4)
idx.close(); print('CLUT 없는 고유',n)
