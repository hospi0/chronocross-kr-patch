"""오프닝 한글 줄 합성기 — 원본 줄 위치(시작 x·윗변 y)에 크림색 획 + 어두운 그림자, 이탤릭 기울임, 4배 그려 축소
render_line(frame, text, x, ytop, font, size, alpha) 를 쓰고, 미리보기는 __main__"""
import cv2,numpy as np,sys,os
from PIL import Image,ImageDraw,ImageFont
FILL=(233,224,214); SHADOW=(12,16,26)
LINES=[('op1-1',16,36),('op1-2',16,59),('op1-3',16,96),('op1-4',15,116),('op1-5',50,145),
       ('op2-1',20,34),('op2-2',42,58),('op2-3',111,80),('op2-4',43,98),('op2-5',110,116),('op2-6',19,148),('op2-7',32,171)]
def text_mask(text,font_path,size,index=0,shear=0.18,S=4,stroke=1):
    f=ImageFont.truetype(font_path,size*S,index=index)
    W=330*S; Hh=int(size*S*1.6)
    im=Image.new('L',(W,Hh),0); d=ImageDraw.Draw(im); d.text((S*2,int(size*S*0.15)),text,fill=255,font=f,stroke_width=stroke,stroke_fill=255)
    a=np.asarray(im,np.float32)/255
    if shear:
        M=np.float32([[1,-shear,shear*Hh*0.8],[0,1,0]]); a=cv2.warpAffine(a,M,(W,Hh))
    return cv2.resize(a,(W//S,Hh//S),interpolation=cv2.INTER_AREA)
def composite(frame_bgr,mask,x,y,alpha=1.0):
    out=frame_bgr.astype(np.float32); h,w=mask.shape
    def blend(m,col,dx,dy):
        ys,ye=max(0,y+dy),min(224,y+dy+h); xs,xe=max(0,x+dx),min(320,x+dx+w)
        mm=m[ys-(y+dy):ye-(y+dy),xs-(x+dx):xe-(x+dx)]*alpha
        c=np.array(col[::-1],np.float32)
        out[ys:ye,xs:xe]=out[ys:ye,xs:xe]*(1-mm[...,None])+c*mm[...,None]
    sh=cv2.dilate(mask,np.ones((3,3),np.float32)); sh=np.clip(cv2.GaussianBlur(sh,(3,3),0)*1.5,0,1)
    blend(sh*0.95,SHADOW,1,1)
    blend(sh*0.6,SHADOW,0,0)
    blend(mask,FILL,0,0)
    return np.clip(out,0,255).astype(np.uint8)
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    KO={}
    for l in open('my files/tsv/cc_movie_001.tsv',encoding='utf8').read().splitlines()[1:]:
        f=l.split('\t'); KO[f[2].split()[1]]=f[5]
    FONTS=[('궁서','C:/Windows/Fonts/batang.ttc',2,16),('바탕','C:/Windows/Fonts/batang.ttc',0,15),('함초롬바탕','C:/Windows/Fonts/HANBatang.ttf',0,15),
           ('NotoSerifKR','C:/Windows/Fonts/NotoSerifKR-VF.ttf',0,14),('고운바탕','C:/claude/utils/font/gowunbatang/GowunBatang-Regular.ttf',0,15),
           ('나눔명조','C:/claude/utils/font/nanum-myeongjo/NanumMyeongjoBold.ttf',0,15),('송명','C:/claude/utils/font/songmyung/SongMyung-Regular.ttf',0,15)]
    M=dict(np.load('work/movie/op_masks.npz'))
    os.makedirs('work/movie/preview',exist_ok=True)
    ASCII={'궁서':'gungsuh','바탕':'batang','함초롬바탕':'hanbatang','NotoSerifKR':'notoserif','고운바탕':'gowunbatang','나눔명조':'nanummyeongjo','송명':'songmyung'}
    base={}
    for f,ids in ((620,[l for l in LINES if l[0].startswith('op1')]),(910,[l for l in LINES if l[0].startswith('op2')])):
        im=cv2.imread(f'work/movie/op_frames/f{f:04d}.png'); m=np.zeros((224,320),np.uint8)
        for lid,_,_ in ids: m|=M[lid].astype(np.uint8)
        m=cv2.dilate(m,np.ones((3,3),np.uint8)); base[f]=(im,cv2.inpaint(im,m*255,3,cv2.INPAINT_TELEA),ids)
    for name,path,idx,size in FONTS:
        if not os.path.exists(path): print('없음',name,path); continue
        rows=[]
        for f,(orig,clean,ids) in base.items():
            fr=clean.copy()
            for lid,x,y in ids:
                tm=text_mask(KO[lid],path,size,idx)
                cols=np.where(tm.max(0)>0.05)[0]; wid=cols.max()+1 if len(cols) else 0
                x2=min(x,314-wid) if x+wid>314 else x     # 넘치면 오른쪽 끝에 맞춰 왼쪽으로
                fr=composite(fr,tm,max(4,x2),y-2)
            rows.append(np.hstack([orig,fr]))
        img=cv2.resize(np.vstack(rows),None,fx=2,fy=2,interpolation=cv2.INTER_NEAREST)
        cv2.imwrite(f'work/movie/preview/opening_{ASCII[name]}.png',img); print('ok',name)
