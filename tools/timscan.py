"""파일 안 TIM 전부 찾아 PNG 로(첫 CLUT 색) → work/gfx/<파일>_<오프셋>.png + work/gfx/tims.tsv
사용: timscan.py <disc|ko1> 파일번호..."""
import sys,os,struct,numpy as np; sys.path.insert(0,os.path.dirname(__file__))
from ccget import get
from PIL import Image
def find_tims(b):
    out=[]
    for i in range(0,len(b)-20,4):
        if b[i:i+4]!=b'\x10\0\0\0': continue
        fl=struct.unpack_from('<I',b,i+4)[0]
        if fl not in (2,3,8,9): continue
        o=i+8; clut=None
        if fl&8:
            cl=struct.unpack_from('<I',b,o)[0]
            if cl<12 or cl>0x10000 or o+cl>len(b): continue
            cx,cy,cw,ch=struct.unpack_from('<4H',b,o+4)
            if cw*ch*2+12!=cl: continue
            clut=np.frombuffer(b[o+12:o+cl],'<u2').reshape(ch,cw); o+=cl
        if o+12>len(b): continue
        il,ix,iy,iw,ih=struct.unpack_from('<I4H',b,o)
        if iw==0 or ih==0 or iw*ih*2+12!=il or o+il>len(b) or ix>=1024 or iy>=512: continue
        out.append(dict(off=i,fl=fl,ix=ix,iy=iy,iw=iw,ih=ih,clut=clut,data=b[o+12:o+il],end=o+il))
    return out
def render(t):
    fl=t['fl']&3; iw,ih=t['iw'],t['ih']; d=np.frombuffer(t['data'],np.uint8)
    if fl==0:
        idx=np.zeros((ih,iw*4),np.uint8); px=d.reshape(ih,iw*2); idx[:,0::2]=px&15; idx[:,1::2]=px>>4
    elif fl==1: idx=d.reshape(ih,iw*2)
    else:
        v=np.frombuffer(t['data'],'<u2').reshape(ih,iw)
        return np.dstack([(v&31)<<3,((v>>5)&31)<<3,((v>>10)&31)<<3]).astype(np.uint8)
    if t['clut'] is None: return (idx*(17 if fl==0 else 1)).astype(np.uint8)
    c=t['clut'][0]; c=c[np.minimum(idx,len(c)-1)]
    return np.dstack([(c&31)<<3,((c>>5)&31)<<3,((c>>10)&31)<<3]).astype(np.uint8)
if __name__=='__main__':
    src=sys.argv[1]; os.makedirs('work/gfx',exist_ok=True)
    log=open('work/gfx/tims.tsv','a',encoding='utf8')
    for a in sys.argv[2:]:
        fi=int(a); b=get(src,fi); T=find_tims(b)
        for t in T:
            im=render(t); fn=f'work/gfx/{src}_{fi:04d}_{t["off"]:06x}.png'
            Image.fromarray(im).save(fn)
            log.write(f'{src}\t{fi}\t{t["off"]:#x}\t{t["fl"]}\t{t["ix"]},{t["iy"]}\t{t["iw"]}x{t["ih"]}\t{fn}\n')
        print(fi,len(T))
