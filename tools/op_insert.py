"""오프닝(디스크1 파일 6054) 한글 프레임 삽입: psxavenc 산출(op_ko_enc.str, 2048B 섹터, 프레임 1~)을
원본 STR 프레임 FIRST.. 의 영상 8섹터 자리에 넣음. 머리 12..32(크기·폭·높이·BS 머리 복제)는 새 것, 덩이 번호는 원본.
보조 섹터(종류 0/1/2)는 그대로. EDC/ECC 재계산(Form 1). → work/movie/op_ko_6054.raw (원본과 같은 섹터 수·위치)"""
import sys,os,struct; sys.path.insert(0,os.path.dirname(__file__))
from ccget import spans,P; from ccfs import Disc; import cdecc
FIRST=351; COUNT=626            # STR 프레임 번호(=ffmpeg 순번+1) 351~976 = 순번 350~975
D=Disc(P['1']); l,c=spans(D)[6054]; D.f.seek(l*2352); raw=bytearray(D.f.read(c*2352))
# 규약 검산: 무수정 영상 섹터 하나를 다시 계산해도 같아야 함
s0=bytearray(raw[2*2352:3*2352]); t=cdecc.fix_sector(bytearray(s0)); assert t==s0, 'EDC/ECC 규약 불일치'
enc=open('work/movie/op_ko_enc.str','rb').read()
new={}
for j in range(len(enc)//2048):
    s=enc[j*2048:(j+1)*2048]
    if s[:2]!=b'\x60\x01': continue
    ch,nch=struct.unpack_from('<HH',s,4); f=struct.unpack_from('<I',s,8)[0]
    new.setdefault(f,{})[ch]=s
orig={}
for j in range(c):
    o=j*2352; h=raw[o+24:o+56]
    if h[:2]==b'\x60\x01' and h[3]&0x80:
        ch,nch=struct.unpack_from('<HH',h,4); f=struct.unpack_from('<I',h,8)[0]
        orig.setdefault(f,{})[ch]=j
done=0
for k in range(1,COUNT+1):
    f=FIRST+k-1; src=new[k]; dst=orig[f]
    assert sorted(src)==sorted(dst)==list(range(8)), (f,sorted(src),sorted(dst))
    for ch in range(8):
        j=dst[ch]; o=j*2352; s=src[ch]
        sec=bytearray(raw[o:o+2352])
        hdr=bytearray(sec[24:56]); hdr[12:32]=s[12:32]          # 크기·폭·높이·BS 머리 = 새 것
        sec[24:56]=hdr; sec[56:24+2048]=s[32:2048]
        raw[o:o+2352]=cdecc.fix_sector(sec); done+=1
open('work/movie/op_ko_6054.raw','wb').write(raw)
print('바꾼 섹터',done,'(프레임',COUNT,')')
