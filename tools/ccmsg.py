"""크로노 크로스 대사 바이트열 파서 (맵 오버레이 파일4 0x800D84C8 분기표로 확정, 2026-11-16).
글자: 0x20..0xF7 → 칸 b-0x20 (0x75 미만 반각 8px, 이상 전각 12px), F8..FF xx → 칸 (hi-0xF7)*256+(xx-0x20)
제어(인자 바이트 수): 00 끝 / 01 줄바꿈 / 02 X 쪽넘김 / 03 / 04 X 대기 / 05 X 속도 / 06 X / 07 lo hi 문자열 치환 /
08 X / 0A X, 0B X 치환 / 0E X 색 / 10 X 선택지 / 12 X / 15 X / 16 X / 17 X / 18 X / 19 X / 1B X 치환 / 1F
"""
import struct
ARGS={1:0,2:1,3:0,4:1,5:1,6:1,7:2,8:1,0xa:1,0xb:1,0xe:1,0x10:1,0x12:1,0x15:1,0x16:1,0x17:1,0x18:1,0x19:1,0x1b:1,0x1f:0}
def parse(d,o):
    """→ (토큰 목록, 끝 위치). 토큰: ('g',칸) / ('c',코드,인자bytes) / 오류는 ValueError"""
    out=[]; i=o
    while True:
        c=d[i]
        if c==0: return out,i+1
        if c<0x20:
            if c not in ARGS: raise ValueError(f'bad ctl {c:#x} at {i:#x}')
            n=ARGS[c]; out.append(('c',c,bytes(d[i+1:i+1+n]))); i+=1+n
        elif c>=0xf8:
            out.append(('g',(c-0xf7)*256+(d[i+1]-0x20))); i+=2
        else:
            out.append(('g',c-0x20)); i+=1
def block_offsets(d):
    T=struct.unpack_from('<H',d,0)[0]
    return [struct.unpack_from('<4H',d,i*8) for i in range(T//8)]
