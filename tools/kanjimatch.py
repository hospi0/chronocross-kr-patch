"""한자 칸 모양 대조 — JIS 1·2수준 한자를 여러 일본어 글꼴·크기로 1비트 렌더해 ±1px 이동 최대 상관.
→ work/glyphs/shape_top.tsv (칸, 상위 8 후보:점수)"""
import sys,os,numpy as np; sys.path.insert(0,os.path.dirname(__file__)); import ccfont
from PIL import Image, ImageDraw, ImageFont
def kanji_candidates():
    out={}
    for lead in list(range(0x88,0xA0))+list(range(0xE0,0xEB)):
        for tr in range(0x40,0xFD):
            if tr==0x7F: continue
            try: ch=bytes([lead,tr]).decode('cp932')
            except UnicodeDecodeError: continue
            if len(ch)==1 and 0x4E00<=ord(ch)<=0x9FFF and ch not in out: out[ch]=1 if (lead,tr)<=(0x98,0x72) else 2
    for ch in '々〆〇': out[ch]=1
    return out
FONTS=[(r'C:\Windows\Fonts\msgothic.ttc',0),(r'C:\Windows\Fonts\msgothic.ttc',1)]
def render(chars,path,idx,size,dy):
    f=ImageFont.truetype(path,size,index=idx)
    R=np.zeros((len(chars),13,18),np.float32)
    for i,ch in enumerate(chars):
        im=Image.new('1',(18,13),0); d=ImageDraw.Draw(im); d.fontmode='1'
        d.text((1,1+dy),ch,fill=1,font=f)
        R[i]=np.asarray(im,np.float32)
    return R
def blur(a):
    p=np.pad(a,[(0,0)]*(a.ndim-2)+[(1,1),(1,1)],mode='constant')
    a=(p[...,:-2,:]+2*p[...,1:-1,:]+p[...,2:,:])/4
    return (a[...,:,:-2]+2*a[...,:,1:-1]+a[...,:,2:])/4
def norm(v):
    v=v.reshape(v.shape[0],-1); v=v-v.mean(1,keepdims=True); n=np.linalg.norm(v,axis=1,keepdims=True); n[n==0]=1; return v/n
if __name__=='__main__':
    lo=int(sys.argv[1],0) if len(sys.argv)>1 else 0x16c
    g=ccfont.load()
    C=kanji_candidates(); chars=list(C)
    tgt=np.zeros((len(g),13,18),np.float32); tgt[:,1:12,1:17]=g
    T=norm(blur(tgt[lo:]))
    best=np.full((len(T),len(chars)),-1.0,np.float32)
    for path,idx in FONTS[:1]:
        for size in (11,12):
            for dy in (-1,0):
                R=render(chars,path,idx,size,dy)
                for sx in (-1,0,1):
                    for sy in (-1,0,1):
                        Rs=np.roll(np.roll(R,sx,2),sy,1)
                        S=T@norm(blur(Rs)).T
                        np.maximum(best,S,out=best)
                print('done',size,dy,file=sys.stderr)
    os.makedirs('work/glyphs',exist_ok=True)
    np.save('work/glyphs/shape_best.npy',best)
    with open('work/glyphs/shape_top.tsv','w',encoding='utf8') as f:
        for k in range(len(T)):
            o=np.argsort(-best[k])[:8]
            f.write(f'{lo+k}\t'+' '.join(f'{chars[j]}:{best[k,j]:.3f}' for j in o)+'\n')
    open('work/glyphs/cands.txt','w',encoding='utf8').write(''.join(chars))
