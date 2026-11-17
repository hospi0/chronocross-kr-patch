"""두 MODE2/2352 이미지의 섹터(사용자 데이터 2048B 또는 form2 2324B) 차이 범위를 나열한다."""
import sys
S=2352
a=open(sys.argv[1],'rb'); b=open(sys.argv[2],'rb')
import os
na=os.path.getsize(sys.argv[1])//S; nb=os.path.getsize(sys.argv[2])//S
print('sectors',na,nb)
runs=[];cur=None
CH=4096
for base in range(0,max(na,nb),CH):
    A=a.read(S*CH); B=b.read(S*CH)
    for i in range(CH):
        s=base+i
        if s>=max(na,nb): break
        x=A[i*S+16:i*S+S-4] if i*S<len(A) else None
        y=B[i*S+16:i*S+S-4] if i*S<len(B) else None
        d = x!=y
        if d:
            if cur and cur[1]==s-1: cur[1]=s
            else:
                cur=[s,s]; runs.append(cur)
print(len(runs),'runs')
for r in runs: print(r[0],r[1],r[1]-r[0]+1)
