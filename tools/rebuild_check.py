"""재구성 검산: 새 디스크의 표로 모든 파일을 읽어 원본(또는 교체 내용)과 대조 + 옮긴 섹터 EDC/ECC·MSF 표본 검사"""
import sys,os,struct,random; sys.path.insert(0,os.path.dirname(__file__))
import rebuild, cdecc
S=2352
def files(path):
    f=open(path,'rb'); ent,n=rebuild.read_table(f); out={}
    for i in range(n-1):
        e=ent[i]
        if e&0x800000: out[i]=b''; continue
        lba=e&0x7fffff; nxt=ent[i+1]&0x7fffff; size=(nxt-lba)*2048-(e>>24)*8
        f.seek(lba*S); raw=f.read((nxt-lba)*S)
        out[i]=b''.join(raw[k*S+24:k*S+24+2048] for k in range(nxt-lba))[:size]
    return out,f,ent,n
def check(orig,new,repl={}):
    A,_,_,_=files(orig); B,f,ent,n=files(new); bad=[]
    for i in A:
        want=repl.get(i,A[i])
        if i in repl: want=want+b'\0'*((-len(want))%8)
        if B.get(i)!=want: bad.append(i)
    # 표본 섹터 검사
    nsec=os.path.getsize(new)//S; errs=0
    for lba in random.sample(range(38,nsec),3000):
        f.seek(lba*S); sec=bytearray(f.read(S))
        m=sec[12:15]; t=cdecc.set_header(bytearray(sec),lba)
        if bytes(t[12:15])!=bytes(m): errs+=1; continue
        if not (sec[18]&0x20):
            if bytes(cdecc.fix_sector(bytearray(sec)))!=bytes(sec): errs+=1
    return bad,errs
if __name__=='__main__':
    print(check(sys.argv[1],sys.argv[2]))
