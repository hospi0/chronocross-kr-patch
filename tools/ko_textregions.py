"""기존 패치가 바꾼 (맵 대사 외) 파일의 변경 범위 안 원본 문자열(대사 인코딩) 표본 → work/ko_textregions.txt"""
import sys,os,glob,json; sys.path.insert(0,os.path.dirname(__file__)); import ccmsg,ccdecode
from ccget import get
IDX=[6,10,11,38,40,41,42,48,101,102,151,218,224,226,233,2050,2051,2538,2542,2543,2646,2667,2683,2920,3065,3129,3157,4405,4518]
out=open('work/ko_textregions.txt','w',encoding='utf8')
for i in IDX:
    a=get('1',i); k=get('ko1',i)
    n=min(len(a),len(k)); d=[j for j in range(n) if a[j]!=k[j]]
    runs=[]
    for j in d:
        if runs and j-runs[-1][1]<=32: runs[-1][1]=j
        else: runs.append([j,j])
    tot=sum(r[1]-r[0]+1 for r in runs)
    out.write(f'== {i} size {len(a)}->{len(k)} 바뀐 {tot}B 구간 {len(runs)}\n')
    for r0,r1 in runs[:40]:
        # 구간 앞 0 까지 되감아 문자열 시작 찾기
        s=r0
        while s>0 and a[s-1]!=0 and r0-s<200: s-=1
        try: t,e=ccmsg.parse(a,s); txt=ccdecode.text(t).replace('\n','⏎')[:70]
        except Exception as ex: txt='(parse X)'
        out.write(f'  {r0:#07x}-{r1:#07x} ({r1-r0+1}B) {txt}\n')
out.close()
