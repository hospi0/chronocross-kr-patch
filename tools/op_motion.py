"""오프닝 배경 움직임: 이웃 프레임 호모그래피(글자 띠 제외 특징점)를 이어 붙여 기준 프레임 → 각 프레임 변환
→ work/movie/op_H.npy (프레임 330~990, 기준 = 첫 프레임)"""
import cv2,numpy as np,sys
F0,F1=330,990
mask=np.full((224,320),255,np.uint8); mask[28:197,:]=0
def load(f): return cv2.imread(f'work/movie/op_frames/f{f:04d}.png')
def H_between(a,b):
    ga,gb=[cv2.cvtColor(x,cv2.COLOR_BGR2GRAY) for x in (a,b)]
    p=cv2.goodFeaturesToTrack(ga,800,0.005,4,mask=mask)
    if p is None or len(p)<12: return np.eye(3),0,0
    q,st,err=cv2.calcOpticalFlowPyrLK(ga,gb,p,None,winSize=(21,21),maxLevel=3)
    ok=st[:,0]==1
    if ok.sum()<12: return np.eye(3),0,0
    H,inl=cv2.findHomography(p[ok],q[ok],cv2.RANSAC,1.0)
    if H is None: return np.eye(3),0,0
    return H,int(inl.sum()),int(ok.sum())
Hs=[np.eye(3)]; prev=load(F0); stats=[]
for f in range(F0+1,F1+1):
    cur=load(f); H,ni,nt=H_between(prev,cur); Hs.append(H@Hs[-1]); stats.append(ni); prev=cur
np.save('work/movie/op_H.npy',np.array(Hs))
print('inliers min/med',min(stats),int(np.median(stats)))
# 검증: 글자 없는 구간 — 330 을 각 프레임으로 옮겨 오차
ref=load(F0)
for f in (340,350,358,640,660,670):
    W=cv2.warpPerspective(ref,Hs[f-F0],(320,224),borderMode=cv2.BORDER_REPLICATE)
    d=np.abs(W.astype(int)-load(f).astype(int)).mean(); print(f,'mean abs diff',round(d,2))
