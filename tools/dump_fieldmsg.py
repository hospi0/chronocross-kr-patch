"""맵 파일 대사 블록(구간 8, sszl) 전부 풀기 → work/fieldmsg/<disc>_<idx>.bin (풀린 원본) + 목록"""
import sys,os,struct; sys.path.insert(0,os.path.dirname(__file__))
from ccget import spans,P; from ccfs import Disc; import sszl
src=sys.argv[1] if len(sys.argv)>1 else ''   # '' 원본, 'ko' 오라클
os.makedirs(f'work/fieldmsg{src}',exist_ok=True)
rows=[l.split('\t') for l in open('work/sszl_index.tsv',encoding='utf8').read().splitlines()]
want=sorted({(r[0],int(r[1])) for r in rows if len(r)>4 and r[2]=='8' and int(r[3])>=12})
for disc,fi in want:
    D=Disc(P[(src+disc) if src else disc]); l,c=spans(D)[fi]
    b=b''.join(D.sec(l+j) for j in range(c))
    n=struct.unpack_from('<I',b,0)[0]; offs=struct.unpack_from('<%dI'%(n+1),b,4)
    if b[offs[8]:offs[8]+4]!=b'sszl': print('skip',disc,fi); continue
    open(f'work/fieldmsg{src}/{disc}_{fi:04d}.bin','wb').write(sszl.decode(b,offs[8]))
print(len(want))
