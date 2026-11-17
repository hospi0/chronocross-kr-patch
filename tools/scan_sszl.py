"""두 디스크 전 파일에서 «머리 n + 오프셋 표» 구조 안 sszl 구간을 찾아 목록을 만든다 → work/sszl_index.tsv"""
import sys,os,struct; sys.path.insert(0,os.path.dirname(__file__))
from ccget import spans,P; from ccfs import Disc; import sszl
out=open('work/sszl_index.tsv','w',encoding='utf8')
for disc in ('1','2'):
    D=Disc(P[disc]); sp=spans(D)
    for fi,(l,c) in enumerate(sp):
        if c==0 or c>2000: continue
        b=b''.join(D.sec(l+j) for j in range(c))
        n=struct.unpack_from('<I',b,0)[0]
        if not (1<=n<=64): continue
        offs=struct.unpack_from('<%dI'%(n+1),b,4)
        if offs[0]!=4+4*(n+1) and offs[0]!=(4+4*(n+1)+3)//4*4: continue
        if any(offs[i]>offs[i+1] for i in range(n)) or offs[n]>len(b): continue
        for si in range(n):
            if b[offs[si]:offs[si]+4]==b'sszl':
                try: d=sszl.decode(b,offs[si])
                except Exception as e: out.write(f'{disc}\t{fi}\t{si}\tERR {e}\n'); continue
                out.write(f'{disc}\t{fi}\t{si}\t{n}\t{len(d)}\t{d[:8].hex()}\n')
out.close()
