"""원본 글자의 줄별 투명도 곡선 측정: 줄 마스크 안 |원본 − inpaint(원본)| 평균 → 최대 구간으로 정규화 → work/movie/op_alpha.json"""
import cv2,numpy as np,json
M=dict(np.load('work/movie/op_masks.npz'))
BLOCK={'op1':(350,665),'op2':(668,978)}
res={}
for lid,m in M.items():
    a,b=BLOCK[lid[:3]]; m8=cv2.dilate(m.astype(np.uint8),np.ones((3,3),np.uint8))
    c=[]
    for t in range(a,b+1):
        im=cv2.imread(f'work/movie/op_frames/f{t:04d}.png')
        cl=cv2.inpaint(im,m8*255,3,cv2.INPAINT_TELEA)
        c.append(float(np.abs(im.astype(int)-cl.astype(int))[m].mean()))
    c=np.array(c); base=np.percentile(c,5); top=np.percentile(c,90)
    al=np.clip((c-base)/(top-base),0,1)
    al=np.convolve(al,np.ones(3)/3,'same')
    res[lid]={'start':a,'alpha':[round(float(x),3) for x in al]}
    on=np.where(al>0.5)[0]
    print(lid,'50% on',a+on.min(),'off',a+on.max())
json.dump(res,open('work/movie/op_alpha.json','w'))
