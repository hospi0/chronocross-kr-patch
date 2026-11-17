"""숨은 파일 표 번호로 파일을 꺼낸다 (form1 2048B 기준, 섹터 단위 길이). 사용: ccget.py <disc|ko1|ko2> idx..."""
# ★원본 = D: 백업(md5 988a1af0…/826a66fb…). F: 는 시험본이 덮이므로 원본으로 읽지 말 것(PoC2 가 PoC1 위에 빌드돼 크래시, 2026-11-16)
import sys,os; sys.path.insert(0,os.path.dirname(__file__)); from ccfs import Disc
P={'1':'D:/hospi/My Documents/한글패치/PS1/ps/Chrono Cross (Japan, Asia)/Chrono Cross (Japan, Asia) (Disc 1).bin',
   '2':'D:/hospi/My Documents/한글패치/PS1/ps/Chrono Cross (Japan, Asia)/Chrono Cross (Japan, Asia) (Disc 2).bin',
   'ko1':'work/oracle/CC_KO_Disc1.bin','ko2':'work/oracle/CC_KO_Disc2.bin'}
def spans(D):
    n=len(D.ent)
    while D.ent[n-1]==0: n-=1
    L=[D.lba(i) for i in range(n)]
    s=sorted(set(L[i] for i in range(n) if not D.dummy(i)))+[D.nsec]
    import bisect
    out=[]
    for i in range(n):
        if D.dummy(i): out.append((L[i],0)); continue
        k=bisect.bisect_right(s,L[i]); out.append((L[i],s[k]-L[i]))
    return out
def get(disc,idx):
    D=Disc(P[disc]); l,c=spans(D)[idx]
    return b''.join(D.sec(l+j) for j in range(c))
if __name__=='__main__':
    d=sys.argv[1]; os.makedirs('work/files',exist_ok=True)
    for a in sys.argv[2:]:
        b=get(d,int(a)); fn=f'work/files/{d}_{int(a):04d}.bin'; open(fn,'wb').write(b); print(fn,len(b))

def get_exact(disc, idx):
    """숨은 표 크기(상위 바이트 = 마지막 섹터 빈 바이트/8) 그대로 — 바꾼 파일을 다시 넣을 때는 반드시 이걸로
    (섹터 채움까지 넘기면 표 크기가 커져 오버레이 적재가 뒤 메모리를 덮는다 — PoC2 타이틀 크래시, 2026-11-16)"""
    D = Disc(P[disc]); e = D.ent[idx]
    if e & 0x800000: return b''
    l = e & 0x7FFFFF; nx = D.ent[idx + 1] & 0x7FFFFF
    size = (nx - l) * 2048 - (e >> 24) * 8
    return b''.join(D.sec(l + j) for j in range(nx - l))[:size]
