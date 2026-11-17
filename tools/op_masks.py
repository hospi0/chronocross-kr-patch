"""오프닝 줄별 글자 마스크: (줄이 다 나타난 프레임) − (나타나기 직전 프레임을 짧은 구간 보정으로 옮긴 것) → 문턱 + 팽창
→ work/movie/op_masks.npz (줄id → bool 224×320), 확인 그림 work/movie/op_masks.png"""
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
    d=np.abs(L(b)-warp(a,b)).max(axis=2)
    m=np.zeros((224,320),bool); band=d[y0:y1]>28
    m[y0:y1]=band
    m=cv2.dilate(m.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
    masks[lid]=m
    v=L(b).astype(np.uint8).copy(); v[m]=(0,0,255); vis.append(v[max(0,y0-4):y1+4])
np.savez_compressed('work/movie/op_masks.npz',**masks)
cv2.imwrite('work/movie/op_masks.png',cv2.resize(np.vstack(vis),None,fx=2,fy=2,interpolation=cv2.INTER_NEAREST))
print({k:int(v.sum()) for k,v in masks.items()})
