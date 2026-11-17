"""원본과 기존 한글패치 디스크의 숨은 파일 표 항목별 내용 비교."""
import sys; sys.path.insert(0,'tools'); from ccfs import Disc
disc=sys.argv[1]
O=Disc(f'D:/hospi/My Documents/한글패치/PS1/ps/Chrono Cross (Japan, Asia)/Chrono Cross (Japan, Asia) (Disc {disc}).bin')
K=Disc(f'work/oracle/CC_KO_Disc{disc}.bin')
def spans(D):
    n=len(D.ent)
    while D.ent[n-1]==0: n-=1
    L=[D.lba(i) for i in range(n)]
    out=[]
    for i in range(n):
        if D.dummy(i): out.append((L[i],0)); continue
        nxt=min([x for x in L if x>L[i]]+[D.nsec])
        out.append((L[i],nxt-L[i]))
    return out
so,sk=spans(O),spans(K)
n=min(len(so),len(sk))
print('n',len(so),len(sk))
for i in range(n):
    (lo,co),(lk,ck)=so[i],sk[i]
    if co==0 and ck==0: continue
    same = co==ck and all(O.raw(lo+j)[16:2348]==K.raw(lk+j)[16:2348] for j in range(co))
    if not same:
        print(i, 'lba',lo,lk,'sec',co,ck, 'hi',hex(O.hi(i)),hex(K.hi(i)))
