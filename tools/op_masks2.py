"""오프닝 줄별 글자 마스크(2차): 획 = 밝아진 화소, 그림자 = 획 2px 안의 어두워진 화소, 잡티 = 작은 덩어리 제거 → 1px 팽창
→ work/movie/op_masks.npz , 확인 work/movie/op_masks2.png"""
import cv2,numpy as np
H=np.load('work/movie/op_H.npy'); F0=330
L=lambda f: cv2.imread(f'work/movie/op_frames/f{f:04d}.png').astype(np.float32)
def warp(a,t):
    M=H[t-F0]@np.linalg.inv(H[a-F0]); return cv2.warpPerspective(L(a),M,(320,224),borderMode=cv2.BORDER_REPLICATE)
LINES={'op1-1':(354,380,(33,55)),'op1-2':(392,416,(55,80)),'op1-3':(434,462,(88,114)),'op1-4':(470,498,(112,138)),'op1-5':(506,528,(137,163)),
       'op2-1':(672,696,(32,53)),'op2-2':(710,732,(55,77)),'op2-3':(744,756,(76,97)),'op2-4':(768,784,(95,115)),'op2-5':(788,812,(113,134)),
       'op2-6':(822,846,(146,166)),'op2-7':(848,872,(169,191))}
masks={}; vis=[]
for lid,(a,b,(y0,y1)) in LINES.items():
    s=(L(b)-warp(a,b)).mean(axis=2)
    band=np.zeros((224,320),bool); band[y0:y1]=True
    med=np.median(s[band]); s=s-med
    fill=(s>35)&band
    n,lab,st,_=cv2.connectedComponentsWithStats(fill.astype(np.uint8),connectivity=8)
    keep=np.zeros_like(fill)
    for i in range(1,n):
        if st[i,cv2.CC_STAT_AREA]>=3: keep|=lab==i
    near=cv2.dilate(keep.astype(np.uint8),np.ones((5,5),np.uint8)).astype(bool)
    shadow=(s<-20)&near&band
    m=keep|shadow
    m=cv2.dilate(m.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)&band
    masks[lid]=m
    v=L(b).astype(np.uint8).copy(); v[m]=(0,0,255); vis.append(v[y0-2:y1+2])
np.savez_compressed('work/movie/op_masks.npz',**masks)
cv2.imwrite('work/movie/op_masks2.png',cv2.resize(np.vstack(vis),None,fx=2,fy=2,interpolation=cv2.INTER_NEAREST))
print({k:int(v.sum()) for k,v in masks.items()})
