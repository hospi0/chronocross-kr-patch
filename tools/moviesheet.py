"""디스크의 STR 영상(숨은 표 6035~)을 영상 섹터만 골라 ffmpeg 로 2초 간격 썸네일 시트 → work/movie/sheet_<disc>_<idx>.png"""
import sys,os,struct,subprocess; sys.path.insert(0,os.path.dirname(__file__))
from ccget import spans,P; from ccfs import Disc
FF='C:/claude/utils/ps1/ffmpeg.exe'
disc=sys.argv[1]; idxs=[int(x) for x in sys.argv[2:]]
D=Disc(P[disc]); sp=spans(D)
os.makedirs('work/movie',exist_ok=True)
for fi in idxs:
    l,c=sp[fi]; D.f.seek(l*2352); a=D.f.read(c*2352); out=bytearray()
    for j in range(c):
        s=a[j*2352:(j+1)*2352]
        if s[24:26]==b'\x60\x01' and struct.unpack_from('<H',s,26)[0]==0x8001: out+=s
    vp=f'work/movie/{disc}_{fi}_v.str'; open(vp,'wb').write(out)
    sh=f'work/movie/sheet_{disc}_{fi}.png'
    subprocess.run([FF,'-hide_banner','-loglevel','error','-f','psxstr','-i',vp,'-an','-vf',
                    "select='not(mod(n\,30))',scale=160:-1,tile=8x12",'-fps_mode','passthrough','-frames:v','1','-update','1','-y',sh])
    print(fi, len(out)//2352, os.path.exists(sh))
