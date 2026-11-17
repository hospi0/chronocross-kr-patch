"""두 디스크 고유 TIM 전부 → OCR 용 흑백(글자 화소=검정) 3배 그림 + 컬러 그림
→ work/gfx/all/<디스크>_<파일>_<오프셋>.png (컬러) · work/gfx/ocr/img_NNNN.png (흑백) · work/gfx/ocr/index.tsv"""
import sys,os,hashlib,numpy as np; sys.path.insert(0,os.path.dirname(__file__))
from ccget import spans,P; from ccfs import Disc; from timscan import find_tims, render
from PIL import Image
os.makedirs('work/gfx/all',exist_ok=True); os.makedirs('work/gfx/ocr',exist_ok=True)
seen={}; idx=open('work/gfx/ocr/index.tsv','w',encoding='utf8'); n=0
for d in ('1','2'):
    D=Disc(P[d]); sp=spans(D)
    for fi,(l,c) in enumerate(sp):
        if c==0 or c>2000: continue
        b=b''.join(D.sec(l+j) for j in range(c))
        for t in find_tims(b):
            h=hashlib.md5(t['data']).hexdigest()
            if h in seen: seen[h].append(f'{d}:{fi}@{t["off"]:#x}'); continue
            seen[h]=[f'{d}:{fi}@{t["off"]:#x}']
            im=render(t); name=f'{d}_{fi:04d}_{t["off"]:06x}'
            Image.fromarray(im).save(f'work/gfx/all/{name}.png')
            g=im.astype(int).sum(2) if im.ndim==3 else im.astype(int)
            # 바탕 = 최빈값, 그 밖 = 글자 후보(검정)
            vals,cnt=np.unique(g,return_counts=True); bg=vals[cnt.argmax()]
            bw=np.where(g==bg,255,0).astype(np.uint8)
            H,W=bw.shape; s=3 if max(H,W)<1000 else 1
            out=Image.fromarray(bw).resize((W*s,H*s),Image.NEAREST)
            pad=Image.new('L',(W*s+40,H*s+40),255); pad.paste(out,(20,20))
            n+=1; pad.save(f'work/gfx/ocr/img_{n:05d}.png')
            idx.write(f'{n}\t{name}\t{t["iw"]}x{t["ih"]}\tfl{t["fl"]}\t{t["ix"]},{t["iy"]}\t{h}\n')
idx.close()
import json; json.dump(seen,open('work/gfx/all_copies.json','w'))
print('고유',n)
