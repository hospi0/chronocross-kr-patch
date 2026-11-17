"""문맥 OCR 그림: 애매 한자 칸이 든 대사 줄을 게임 글꼴 그대로 4배로 그림 → work/ocr/img_NNNN.png + layout.json
(사립 저스티스 학원 tools/ocrprep.py 방식 이식)"""
import sys,os,glob,json; sys.path.insert(0,os.path.dirname(__file__))
import numpy as np, ccmsg, ccfont
from PIL import Image
S=4; PITCH=16*S+4; LINEH=11*S+36; X0=Y0=30; PER=8
g=ccfont.load()
kt=[l.split('\t') for l in open('work/glyphs/kanji.tsv',encoding='utf8').read().splitlines()]
amb={int(r[0]) for r in kt if r[2]!='exact'}
seen=set(); lines=[]
for f in sorted(glob.glob('work/fieldmsg/*.bin')):
    d=open(f,'rb').read()
    for rec in ccmsg.block_offsets(d):
        try: toks,_=ccmsg.parse(d,rec[0])
        except Exception: continue
        cur=[]
        for t in toks+[('c',1,b'')]:
            if t[0]=='g': cur.append(t[1])
            elif t[1] in (1,2,3,6): 
                if cur: lines.append(tuple(cur))
                cur=[]
            elif t[1] in (7,0xa,0xb,0x12,0x15,0x18,0x19,0x1b): cur.append(None)
cnt={}; chosen=[]
for L in lines:
    if L in seen: continue
    seen.add(L)
    tg=[c for c in L if c in amb]
    if not tg or all(cnt.get(c,0)>=PER for c in tg) or len(L)>40: continue
    for c in tg: cnt[c]=cnt.get(c,0)+1
    chosen.append(L)
os.makedirs('work/ocr',exist_ok=True)
for p in glob.glob('work/ocr/img_*'): os.remove(p)
NL=(9000-2*Y0)//LINEH
layout=[]
for n in range(0,len(chosen),NL):
    grp=chosen[n:n+NL]; W=X0*2+PITCH*max(len(l) for l in grp); H=Y0*2+LINEH*len(grp)
    img=np.full((H,W),255,np.uint8)
    for i,L in enumerate(grp):
        y=Y0+i*LINEH
        for j,c in enumerate(L):
            if c is None: continue
            big=np.kron(g[c],np.ones((S,S),np.uint8))
            x=X0+j*PITCH; img[y:y+11*S,x:x+16*S][big>0]=0
    nm='img_%04d.png'%(n//NL+1); Image.fromarray(img).save('work/ocr/'+nm)
    layout.append(dict(img=nm,lines=[dict(y=Y0+i*LINEH,cells=list(L)) for i,L in enumerate(grp)]))
json.dump(dict(pitch=PITCH,x0=X0,lineh=LINEH,gh=11*S,images=layout),open('work/ocr/layout.json','w'))
print('lines',len(chosen),'images',len(layout),'covered',len(cnt),'/',len(amb))
