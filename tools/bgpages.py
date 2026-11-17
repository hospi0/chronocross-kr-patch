"""맵 배경 그림 파일(8bpp CLUT 없는 TIM 페이지 + 끝 구간 CLUT TIM) → 페이지를 이어 붙인 컬러 띠
→ work/gfx/bg/<디스크>_<파일>.png  (그림 글자·간판 눈 검토용)"""
import sys,os,struct,numpy as np; sys.path.insert(0,os.path.dirname(__file__))
from ccget import spans,P; from ccfs import Disc
from PIL import Image
os.makedirs('work/gfx/bg',exist_ok=True)
def tim(s):
    try: return _tim(s)
    except Exception: return None
def _tim(s):
    if s[:4]!=b'\x10\0\0\0': return None
    fl=struct.unpack_from('<I',s,4)[0]; o=8; clut=None
    if fl&8:
        cl,cx,cy,cw,ch=struct.unpack_from('<I4H',s,o); clut=np.frombuffer(s[o+12:o+cl],'<u2').reshape(ch,cw); o+=cl
    il,ix,iy,iw,ih=struct.unpack_from('<I4H',s,o)
    return fl,clut,ix,iy,iw,ih,s[o+12:o+il]
def rgb(c): return np.dstack([(c&31)<<3,((c>>5)&31)<<3,((c>>10)&31)<<3]).astype(np.uint8)
cnt=0
for d in ('1','2'):
    D=Disc(P[d]); sp=spans(D)
    for fi,(l,c) in enumerate(sp):
        if c<10 or c>400: continue
        h=D.sec(l)
        n=struct.unpack_from('<I',h,0)[0]
        if not 2<=n<=40: continue
        offs=struct.unpack_from('<%dI'%(n+1),h,4)
        if offs[0]!=4+4*(n+1) and offs[0]!=(4+4*(n+1)+3)//4*4: continue
        b=b''.join(D.sec(l+j) for j in range(c))
        if offs[n]>len(b) or list(offs)!=sorted(offs): continue
        T=[tim(b[offs[i]:offs[i+1]]) for i in range(n)]
        pages=[t for t in T if t and t[0]==1]; cl=[t for t in T if t and t[0]==9]
        if len(pages)<2 or not cl: continue
        pal=cl[-1][1]
        vram=np.zeros((512,1024),np.uint16); x0=min(t[2] for t in pages); x1=max(t[2]+t[4] for t in pages); y0=min(t[3] for t in pages); y1=max(t[3]+t[5] for t in pages)
        for fl,_,ix,iy,iw,ih,data in pages:
            vram[iy:iy+ih,ix:ix+iw]=np.frombuffer(data,'<u2').reshape(ih,iw)
        reg=vram[y0:y1,x0:x1]; idx=np.zeros((y1-y0,(x1-x0)*2),np.uint8); idx[:,0::2]=reg&255; idx[:,1::2]=reg>>8
        # 팔레트 여러 줄이면 줄마다 따로 그려 세로로 쌓기(최대 4)
        ims=[rgb(pal[r][idx]) for r in range(min(len(pal),2))]
        Image.fromarray(np.vstack(ims)).save(f'work/gfx/bg/{d}_{fi:04d}.png'); cnt+=1
print('배경 파일',cnt)
