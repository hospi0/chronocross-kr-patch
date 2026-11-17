"""전 파일 SJIS 문자열 후보 집계 — 가나가 섞인 4자 이상 · 잡음 거르기(JIS 1수준·가나 비율) → work/sjis_inventory.tsv"""
import sys,os,re,collections; sys.path.insert(0,os.path.dirname(__file__))
from ccget import spans,P; from ccfs import Disc
def runs(b):
    i=0; n=len(b)
    while i<n-1:
        j=i; s=[]
        while j<n-1:
            c=b[j]
            if (0x81<=c<=0x84 or 0x88<=c<=0x9f or 0xe0<=c<=0xea) and 0x40<=b[j+1]<=0xfc and b[j+1]!=0x7f:
                try: s.append(b[j:j+2].decode('cp932')); j+=2; continue
                except UnicodeDecodeError: break
            break
        if len(s)>=3: yield i,''.join(s); i=j
        else: i+=1
def good(s):
    kana=len(re.findall(r'[ぁ-ヿ]',s)); l1=0
    for ch in s:
        try: b=ch.encode('cp932')
        except: return False
        if b[0]>=0x98 and ch>='一': l1-=1
    return kana>=max(2,len(s)//3) and l1>=-1
out=open('work/sjis_inventory.tsv','w',encoding='utf8'); stat=collections.Counter()
for disc in ('1','2'):
    D=Disc(P[disc]); sp=spans(D)
    for fi,(l,c) in enumerate(sp):
        if c==0 or c>3000: continue
        b=b''.join(D.sec(l+j) for j in range(c))
        for o,s in runs(b):
            if good(s): out.write(f'{disc}\t{fi}\t{o:#x}\t{s}\n'); stat[(disc,fi)]+=1
out.close()
for (d,f),n in sorted(stat.items(),key=lambda t:-t[1])[:60]: print(d,f,n)
print('files',len(stat),'strings',sum(stat.values()))
