"""디스크 1 전 파일 대사 인코딩 문자열 집계(맵 대사 블록 제외 — 풀린 sszl 구간은 따로) → work/cctext_inventory.tsv"""
import sys,os,json,collections; sys.path.insert(0,os.path.dirname(__file__))
from ccget import spans,P; from ccfs import Disc; import ccmsg,ccdecode
common=set(json.load(open('work/common_chars.json',encoding='utf8')))
OKC={1,0xe,0x8,0x18,0x19,0x12,0x15,0x5,0x4,0x2,0x3,0xb,0x7}
def scan(b):
    i=0;n=len(b)
    while i<n:
        if i and b[i-1]!=0: i+=1; continue
        try: t,e=ccmsg.parse(b,i)
        except Exception: i+=1; continue
        gl=[ccdecode.T.get(x[1],'?') for x in t if x[0]=='g']
        cs=[x[1] for x in t if x[0]=='c']
        if len(gl)>=4 and sum(c in common for c in gl)>=0.95*len(gl) and all(c in OKC for c in cs) and e-i<800:
            yield i,ccdecode.text(t).replace('\n','⏎'); i=e
        else: i+=1
out=open('work/cctext_inventory.tsv','w',encoding='utf8'); stat=collections.Counter(); chars=collections.Counter()
D=Disc(P['1']); sp=spans(D)
for fi,(l,c) in enumerate(sp):
    if c==0 or c>400: continue
    b=b''.join(D.sec(l+j) for j in range(c))
    for o,s in scan(b):
        out.write(f'{fi}\t{o:#x}\t{s}\n'); stat[fi]+=1; chars[fi]+=len(s)
out.close()
for f,n in sorted(stat.items(),key=lambda t:-chars[t[0]])[:45]: print(f,n,chars[f])
print('files',len(stat))
