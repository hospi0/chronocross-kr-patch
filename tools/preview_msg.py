"""빌드된 디스크에서 맵 대사를 다시 읽어 게임 규칙대로 그림(반각 8 / 전각 12px, 줄 13px, 이름 치환은 실행 파일 표) → PNG"""
import sys,os,struct,numpy as np; sys.path.insert(0,os.path.dirname(__file__))
import rebuild_check, sszl, ccmsg, exetext
from PIL import Image
def main(binp,mapi,out):
    B,f,ent,n=rebuild_check.files(binp)
    exe=B[0]; o0=0x8005670C-0x80010000+0x800
    def glyph(i): return np.array([[ (r>>(15-x))&1 for x in range(16)] for r in struct.unpack_from('<11H',exe,o0+i*22)],np.uint8)
    G=exetext.groups(exe)
    def gstr(gi,si):
        _,g0,_,so=G[gi]; return exe[g0+so[si]:exe.index(0,g0+so[si])]
    fb=B[mapi]; nn=struct.unpack_from('<I',fb,0)[0]; offs=struct.unpack_from('<%dI'%(nn+1),fb,4)
    d=sszl.decode(fb[offs[8]:offs[9]]); recs=ccmsg.block_offsets(d)
    imgs=[]
    for ri,(o,w,h,px) in enumerate(recs[:7]):
        toks,_=ccmsg.parse(d,o)
        canvas=np.zeros((13*12,max(px,12)+24),np.uint8); x=y=0; page=0; pages=[canvas]
        def put(i):
            nonlocal x
            g=glyph(i); wd=8 if i<0x55 else 12
            c=pages[-1]; 
            if y+11<=c.shape[0] and x+wd<=c.shape[1]: c[y:y+11,x:x+wd]=np.maximum(c[y:y+11,x:x+wd],g[:,:wd]*255)
            x+=wd
        def put_bytes(b):
            t,_=ccmsg.parse(b+b'\0',0)
            for z in t:
                if z[0]=='g': put(z[1])
        for z in toks:
            if z[0]=='g': put(z[1])
            elif z[1]==1: x=0; y+=13
            elif z[1]==2: pages.append(np.zeros_like(canvas)); x=y=0
            elif z[1]==8: put_bytes(gstr(1,z[2][0]))
            elif z[1]==0x18: put_bytes(gstr(1,0x24))        # 미리보기: 슬롯2 = 반클리프
            elif z[1]==0x12 and z[2][0]==0x15: put_bytes(gstr(1,0))
        for c in pages:
            fr=np.full((c.shape[0]+4,c.shape[1]+4),60,np.uint8); fr[2:-2,2:-2]=np.maximum(c,20)
            # 창 크기 표시
            fr[1,:]=200; fr[2+h*13,:min(fr.shape[1],px+2)]=120
            imgs.append(fr)
    W=max(i.shape[1] for i in imgs); H=sum(i.shape[0]+6 for i in imgs)
    sheet=np.zeros((H,W),np.uint8); yy=0
    for i in imgs: sheet[yy:yy+i.shape[0],:i.shape[1]]=i; yy+=i.shape[0]+6
    Image.fromarray(sheet).resize((W*2,H*2),Image.NEAREST).save(out)
if __name__=='__main__': main(sys.argv[1],int(sys.argv[2]),sys.argv[3])
