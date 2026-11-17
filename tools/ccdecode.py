"""대사 토큰 → 사람이 읽는 문자열. 제어 = {01}·{05:FF}·{07:1234} 꼴, 칸 표에 없으면 {G:칸hex}"""
import os,sys; sys.path.insert(0,os.path.dirname(__file__)); import cctable
T=cctable.table()
def text(toks,mark=None):
    s=[]
    for t in toks:
        if t[0]=='g':
            c=T.get(t[1],'{G:%03X}'%t[1])
            s.append('〔'+c+'〕' if mark is not None and t[1]==mark else c)
        else:
            c,a=t[1],t[2]
            if c==1: s.append('\n')
            else: s.append('{%02X%s}'%(c,(':'+a.hex().upper()) if a else ''))
    return ''.join(s)
