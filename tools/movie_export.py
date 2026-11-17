"""STR 영상 → mp4(영상만) 로 뽑아 사람이 보게 함 → work/movie/영상/디스크<d>_<번호>.mp4
영상 섹터 = STR 머리 60 01 + 종류 0x8001(디스크1)/0x8101(디스크2) → 0x8001 로 맞춰 ffmpeg psxstr 로 디코드"""
import sys,os,struct,subprocess; sys.path.insert(0,os.path.dirname(__file__))
from ccget import spans,P; from ccfs import Disc
FF='C:/claude/utils/ps1/ffmpeg.exe'
out_dir='work/movie/영상'; os.makedirs(out_dir,exist_ok=True)
for disc,idxs in (('1',range(6035,6055)),('2',range(6035,6046))):
    D=Disc(P[disc]); sp=spans(D)
    for fi in idxs:
        l,c=sp[fi]; D.f.seek(l*2352); a=D.f.read(c*2352); v=bytearray()
        for j in range(c):
            s=bytearray(a[j*2352:(j+1)*2352])
            if s[24:26]==b'\x60\x01' and s[27]&0x80:
                s[26:28]=b'\x01\x80'; v+=s
        tmp=f'work/movie/tmp_{disc}_{fi}.str'; open(tmp,'wb').write(v)
        mp4=f'{out_dir}/디스크{disc}_{fi}.mp4'
        r=subprocess.run([FF,'-hide_banner','-loglevel','error','-f','psxstr','-i',tmp,'-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-y',mp4],capture_output=True,text=True)
        os.remove(tmp)
        print(disc,fi,len(v)//2352,'OK' if os.path.exists(mp4) and os.path.getsize(mp4)>0 else 'FAIL '+r.stderr[-200:])
