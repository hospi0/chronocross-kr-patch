"""SJIS 문자열 후보(2차): 0 종결 · 앞 바이트 0 또는 4정렬 · 글자 90% 이상이 맵 대사 상용자 → work/sjis_inventory.tsv"""
import sys,os,re,json,collections; sys.path.insert(0,os.path.dirname(__file__))
from ccget import spans,P; from ccfs import Disc
common=set(json.load(open('work/common_chars.json',encoding='utf8')))|set('０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ×○△□　：／＋－（）「」『』【】→←↑↓★☆％')
def scan(b):
    n=len(b); i=0
    while i<n-1:
        if not (i==0 or b[i-1]==0 or i%4==0): i+=1; continue
        j=i; s=''
        while j<n-1:
            c=b[j]
            if 0x81<=c<=0x9f or 0xe0<=c<=0xef:
                try: s+=b[j:j+2].decode('cp932'); j+=2; continue
                except UnicodeDecodeError: break
            elif 0x20<=c<0x7f: s+=chr(c); j+=1; continue
            break
        wide=[ch for ch in s if ord(ch)>0x7f]
        if j<n and b[j]==0 and len(wide)>=2 and sum(ch in common for ch in wide)>=0.9*len(wide):
            yield i,s; i=j+1
        else: i+=1
if __name__=='__main__':
    out=open('work/sjis_inventory.tsv','w',encoding='utf8'); stat=collections.Counter()
    for disc in ('1','2'):
        D=Disc(P[disc]); sp=spans(D)
        for fi,(l,c) in enumerate(sp):
            if c==0 or c>3000: continue
            b=b''.join(D.sec(l+j) for j in range(c))
            for o,s in scan(b): out.write(f'{disc}\t{fi}\t{o:#x}\t{s}\n'); stat[(disc,fi)]+=1
    out.close()
    for (d,f),n in sorted(stat.items(),key=lambda t:-t[1])[:50]: print(d,f,n)
    print('files',len(stat),'strings',sum(stat.values()))
