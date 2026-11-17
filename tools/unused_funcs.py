"""실행 파일(SLPS_023.64) 함수 중 «어디서도 참조되지 않는» 것 찾기
함수 머리 = addiu sp,sp,-N 이 있는 자리(바로 앞이 jr ra+지연 슬롯) · 참조 = 실행 파일·전 오버레이의 jal/j 대상, 32비트 데이터 값, lui+addiu/ori 쌍
→ work/unused_funcs.tsv (시작, 끝, 크기)"""
import sys,os,struct; sys.path.insert(0,os.path.dirname(__file__))
from ccget import spans,P; from ccfs import Disc
exe=open('work/files/1_0000.bin','rb').read(); B=0x80010000-0x800
starts=[]
for i in range(0x800,len(exe)-4,4):
    w=struct.unpack_from('<I',exe,i)[0]
    if (w>>16)==0x27bd and (w&0x8000):
        p1=struct.unpack_from('<I',exe,i-8)[0] if i>=0x808 else 0
        if p1==0x03e00008 or struct.unpack_from('<I',exe,i-4)[0]==0: starts.append(B+i)
starts=sorted(set(starts))
refs=set()
def scan(b,base=None):
    regs={}
    for i in range(0,len(b)-3,4):
        w=struct.unpack_from('<I',b,i)[0]; op=w>>26
        if op in (2,3): refs.add(((w&0x3ffffff)<<2)|0x80000000)
        if 0x80010000<=w<0x800b0000: refs.add(w)
        rs=(w>>21)&31; rt=(w>>16)&31; imm=w&0xffff; simm=imm-0x10000 if imm&0x8000 else imm
        if op==0xf: regs[rt]=(imm<<16,i)
        elif op in (9,0xd) and rs in regs and i-regs[rs][1]<=64:
            refs.add((regs[rs][0]+(imm if op==0xd else simm))&0xffffffff)
scan(exe)
D=Disc(P['1']); sp=spans(D)
for fi,(l,c) in enumerate(sp):
    if fi==0 or c==0 or c>800: continue
    scan(b''.join(D.sec(l+j) for j in range(c)))
D2=Disc(P['2']); sp2=spans(D2)
for fi,(l,c) in enumerate(sp2):
    if fi==0 or c==0 or c>800: continue
    scan(b''.join(D2.sec(l+j) for j in range(c)))
out=[]
for k,s in enumerate(starts):
    e=starts[k+1] if k+1<len(starts) else s+4
    if s not in refs:
        # 함수 안쪽 주소를 가리키는 참조도 없어야(분기 대상 등은 내부라 무시, 데이터 포인터는 검사)
        inner=[r for r in refs if s<r<e and (r-s)>8]
        out.append((s,e,e-s,len(inner)))
open('work/unused_funcs.tsv','w').write(''.join(f'{s:#x}\t{e:#x}\t{n}\t{i}\n' for s,e,n,i in out))
print('함수',len(starts),'참조 없음',len(out)); 
for s,e,n,i in sorted(out,key=lambda t:-t[2])[:25]: print(hex(s),hex(e),n,'inner refs',i)
