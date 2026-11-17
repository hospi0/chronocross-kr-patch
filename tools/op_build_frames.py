"""오프닝 한글 프레임 생성: 줄별 원본 투명도 곡선(op_alpha.json)대로 일본어 지우고(inpaint) 한글(Noto Serif KR) 합성
→ work/movie/op_ko_frames/f%04d.png (330~990) + 확인 영상 work/movie/preview/opening_ko_preview.mp4"""
import cv2,numpy as np,json,os,subprocess,sys
sys.path.insert(0,os.path.dirname(__file__)); import op_render as R
FONT='C:/Windows/Fonts/NotoSerifKR-VF.ttf'; SIZE=14
M=dict(np.load('work/movie/op_masks.npz')); A=json.load(open('work/movie/op_alpha.json'))
KO={}
for l in open('my files/tsv/cc_movie_001.tsv',encoding='utf8').read().splitlines()[1:]:
    f=l.split('\t'); KO[f[2].split()[1]]=f[5]
def regular(al):
    """나타나기 전·사라진 뒤 = 0, 나타나는 구간 단조 증가, 사라지는 구간 단조 감소, 가운데 = 1"""
    al=np.array(al,float); on=np.where(al>0.5)[0]; a,b=on.min(),on.max()
    s=max(0,a-24); e=min(len(al)-1,b+30)          # 원본 나타남·사라짐 길이 ≈16~20프레임 — 그 밖은 바닥 잡음
    base_in=np.percentile(al[max(0,s-30):s+1],50) if s>0 else 0
    al=np.clip((al-base_in)/(1-base_in+1e-6),0,1)
    out=np.zeros_like(al)
    hi=np.where(al>0.9)[0]; h0,h1=hi.min(),hi.max()
    out[s:h0]=np.maximum.accumulate(al[s:h0]) if h0>s else 0
    out[h0:h1+1]=1.0
    if e>h1: out[h1+1:e+1]=np.maximum.accumulate(al[h1+1:e+1][::-1])[::-1]
    return out
AL={k:regular(v['alpha']) for k,v in A.items()}
def alpha(lid,t):
    al=AL[lid]; i=t-A[lid]['start']
    return float(al[i]) if 0<=i<len(al) else 0.0
TM={}
for lid,x,y in R.LINES:
    tm=R.text_mask(KO[lid],FONT,SIZE,0)
    cols=np.where(tm.max(0)>0.05)[0]; wid=cols.max()+1
    x2=min(x,314-wid) if x+wid>314 else x
    TM[lid]=(tm,max(4,x2),y-2)
os.makedirs('work/movie/op_ko_frames',exist_ok=True)
for t in range(330,991):
    im=cv2.imread(f'work/movie/op_frames/f{t:04d}.png')
    act=[(lid,alpha(lid,t)) for lid,_,_ in R.LINES]
    act=[(l,a) for l,a in act if a>0.01 or any(alpha(l,t+k)>0.01 for k in (-2,-1,1,2))]
    if act:
        m=np.zeros((224,320),np.uint8)
        for l,_ in act: m|=M[l].astype(np.uint8)
        m=cv2.dilate(m,np.ones((3,3),np.uint8))
        im=cv2.inpaint(im,m*255,3,cv2.INPAINT_TELEA)
        for l,a in act:
            if a>0.005: tm,x,y=TM[l]; im=R.composite(im,tm,x,y,alpha=a)
    cv2.imwrite(f'work/movie/op_ko_frames/f{t:04d}.png',im)
FF='C:/claude/utils/ps1/ffmpeg.exe'
subprocess.run([FF,'-hide_banner','-loglevel','error','-framerate','15','-start_number','330','-i','work/movie/op_ko_frames/f%04d.png',
                '-vf','scale=640:448:flags=neighbor','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-y','work/movie/preview/opening_ko_preview.mp4'])
subprocess.run([FF,'-hide_banner','-loglevel','error','-framerate','15','-start_number','330','-i','work/movie/op_frames/f%04d.png',
                '-vf','scale=640:448:flags=neighbor','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-y','work/movie/preview/opening_jp_original.mp4'])
print('done')
