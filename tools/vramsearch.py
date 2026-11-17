"""VRAM 사각형(바이트 x0..x1, y0..y1)의 줄 조각을 전 파일(+sszl 구간 풀어서)에서 검색 → 출처 파일
사용: vramsearch.py vram.bin x0(워드) y0 w(워드) h [disc]"""
import sys,os,struct,collections; sys.path.insert(0,os.path.dirname(__file__))
from ccget import spans,P; from ccfs import Disc; import sszl
from find_tables import pieces
v=open(sys.argv[1],'rb').read(); x0,y0,w,h=map(int,sys.argv[2:6]); disc=sys.argv[6] if len(sys.argv)>6 else '1'
rows=[v[((y0+y)*1024+x0)*2:((y0+y)*1024+x0+w)*2] for y in range(h)]
probes=[r for r in rows if len(set(r))>4][:6]
print('probes',len(probes))
D=Disc(P[disc]); sp=spans(D)
for fi,(l,c) in enumerate(sp):
    if c==0 or c>800: continue
    b=b''.join(D.sec(l+j) for j in range(c))
    for nm,s in pieces(b):
        hits=[s.find(p) for p in probes]
        n=sum(1 for x in hits if x>=0)
        if n: print(fi,nm,n,'/',len(probes),hex([x for x in hits if x>=0][0]))
