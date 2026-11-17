"""전 파일(+묶음 구간·sszl 풀린 구간)에서 텍스트 표 탐지 → work/text_tables.tsv
 형식 U16: u16 오프셋 표(첫 값/2 = 개수, 비감소) + 대사 인코딩 문자열
 형식 R8 : 8B 레코드 표(첫 u16/8 = 개수) + 문자열 (맵 대사 블록과 같음)"""
import sys,os,json,struct,collections; sys.path.insert(0,os.path.dirname(__file__))
from ccget import spans,P; from ccfs import Disc; import ccmsg,ccdecode,sszl
common=set(json.load(open('work/common_chars.json',encoding='utf8')))
def textq(b,offs):
    good=n=0; chars=0
    for o in offs:
        n+=1
        try: t,e=ccmsg.parse(b,o)
        except Exception: continue
        gl=[ccdecode.T.get(x[1],'?') for x in t if x[0]=='g']
        if not gl: good+=0.5; continue
        if sum(c in common for c in gl)>=0.9*len(gl): good+=1; chars+=len(gl)
    return good/max(n,1),chars
def try_u16(b):
    if len(b)<8: return None
    T=struct.unpack_from('<H',b,0)[0]
    if T<4 or T%2 or T>=len(b) or T>0x8000: return None
    offs=list(struct.unpack_from('<%dH'%(T//2),b,0))
    if any(offs[i]>offs[i+1] for i in range(len(offs)-1)) or offs[-1]>len(b): return None
    q,c=textq(b,[o for o in offs if o<len(b)])
    return ('U16',len(offs),q,c) if q>=0.7 and c>=10 else None
def try_r8(b):
    if len(b)<16: return None
    T=struct.unpack_from('<H',b,0)[0]
    if T<8 or T%8 or T>=len(b): return None
    offs=[struct.unpack_from('<H',b,i*8)[0] for i in range(T//8)]
    if any(offs[i]>offs[i+1] for i in range(len(offs)-1)) or offs[-1]>len(b): return None
    q,c=textq(b,[o for o in offs if o<len(b)])
    return ('R8',len(offs),q,c) if q>=0.7 and c>=10 else None
def pieces(b):
    yield 'whole',b
    n=struct.unpack_from('<I',b,0)[0] if len(b)>=8 else 0
    if 1<=n<=256 and len(b)>=4+4*(n+1):
        offs=struct.unpack_from('<%dI'%(n+1),b,4)
        if all(offs[i]<=offs[i+1] for i in range(n)) and offs[n]<=len(b) and offs[0]>=4+4*n:
            for i in range(n):
                s=b[offs[i]:offs[i+1]]
                if s[:4]==b'sszl':
                    try: s=sszl.decode(s)
                    except Exception: continue
                    yield f'sec{i}z',s
                else: yield f'sec{i}',s
    if b[:4]==b'sszl':
        try: yield 'z',sszl.decode(b)
        except Exception: pass
if __name__=='__main__':
  out=open('work/text_tables.tsv','w',encoding='utf8'); stat=collections.Counter()
  disc=sys.argv[1] if len(sys.argv)>1 else '1'
  D=Disc(P[disc]); sp=spans(D)
  for fi,(l,c) in enumerate(sp):
      if c==0 or c>600: continue
      b=b''.join(D.sec(l+j) for j in range(c))
      for nm,s in pieces(b):
          for f in (try_u16,try_r8):
              r=f(s)
              if r: out.write(f'{disc}\t{fi}\t{nm}\t{r[0]}\t{r[1]}\t{r[2]:.2f}\t{r[3]}\n'); stat[r[0]]+=1
  out.close(); print(stat)
