"""종결자 없는(다음 오프셋까지) R8 표 탐지 — 전 파일·묶음 구간·sszl 구간 (맵 대사 구간 8 제외) → work/r8b_tables.tsv"""
import sys,os,json,struct,collections; sys.path.insert(0,os.path.dirname(__file__))
from ccget import spans,P; from ccfs import Disc; import ccmsg,ccdecode
from find_tables import pieces
common=set(json.load(open('work/common_chars.json',encoding='utf8')))
def r8b(b):
    if len(b)<16: return None
    T=struct.unpack_from('<H',b,0)[0]
    if T<8 or T%8 or T>=len(b) or T>0x4000: return None
    recs=[struct.unpack_from('<4H',b,i*8) for i in range(T//8)]
    if recs[0][0]!=T or any(recs[i][0]>recs[i+1][0] for i in range(len(recs)-1)) or recs[-1][0]>len(b): return None
    good=0; chars=0
    for i,(o,w,h,px) in enumerate(recs):
        end=recs[i+1][0] if i+1<len(recs) else len(b)
        try: t,_=ccmsg.parse(b[o:end]+b'\0',0)
        except Exception: continue
        gl=[ccdecode.T.get(x[1],'?') for x in t if x[0]=='g']
        if gl and sum(c in common for c in gl)>=0.85*len(gl): good+=1; chars+=len(gl)
    return (len(recs),good,chars) if good>=max(1,len(recs)*0.5) and chars>=8 else None
if __name__=='__main__':
    out=open('work/r8b_tables.tsv','w',encoding='utf8')
    for disc in ('1','2'):
        D=Disc(P[disc]); sp=spans(D)
        for fi,(l,c) in enumerate(sp):
            if c==0 or c>600: continue
            b=b''.join(D.sec(l+j) for j in range(c))
            for nm,s in pieces(b):
                if nm=='sec8z': continue
                r=r8b(s)
                if r: out.write(f'{disc}\t{fi}\t{nm}\t{r[0]}\t{r[1]}\t{r[2]}\n')
    out.close()
