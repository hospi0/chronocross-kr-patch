"""G05 «属性:» (전투 파일 11·2542 /colo TIM 76×9, 4bpp, CLUT 7 = 흰 글자, 1 = 그림자) → «속성:» 제자리.
属(u0~7)·性(u8~15) 두 칸만 다시 그림, «:»(u16~19)·♂♀·색 공 그대로. 스프라이트 colo 3 = (0,0,u0,w8)(9,0,u8,w8)(18,0,u16,w4) 안 고침"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import drp, smallfont
from timscan import find_tims


def build(b, text='속성'):
    b = bytearray(b); bo, sz = drp.find(bytes(b), '/colo'); t = find_tims(bytes(b[bo:bo + sz]))[0]
    assert (t['ix'], t['iy'], t['iw'], t['ih']) == (940, 289, 19, 9)
    d = np.frombuffer(t['data'], np.uint8).reshape(9, -1)
    idx = np.zeros((9, 76), np.uint8); idx[:, 0::2] = d & 15; idx[:, 1::2] = d >> 4
    idx[:, 0:16] = 0
    for k, c in enumerate(text):
        g = smallfont.cell(c); reg = idx[:, 8 * k:8 * k + 8]
        reg[g == 1] = 1; reg[g == 2] = 7
    packed = (idx[:, 0::2] | (idx[:, 1::2] << 4)).astype(np.uint8).tobytes()
    o = bo + t['end'] - len(t['data']); b[o:o + len(packed)] = packed
    return bytes(b)


if __name__ == '__main__':
    from ccget import get_exact
    from PIL import Image
    out = 'work/g05'; os.makedirs(out, exist_ok=True)
    for fi in (11, 2542):
        a = get_exact('1', fi); n = build(a); assert len(n) == len(a)
        print(fi, '바뀐 바이트', sum(x != y for x, y in zip(a, n)))
    ims = []
    for src in (a, n):
        bo, sz = drp.find(src, '/colo'); t = find_tims(src[bo:bo + sz])[0]
        d = np.frombuffer(t['data'], np.uint8).reshape(9, -1); idx = np.zeros((9, 76), np.uint8); idx[:, 0::2] = d & 15; idx[:, 1::2] = d >> 4
        c = t['clut'][0]; rgb = np.dstack([(c[idx] & 31) << 3, ((c[idx] >> 5) & 31) << 3, ((c[idx] >> 10) & 31) << 3]).astype(np.uint8)
        rgb[idx == 0] = (40, 40, 56); ims.append(rgb)
    S = np.concatenate([ims[0], np.full((3, 76, 3), 16, np.uint8), ims[1]])
    Image.fromarray(S).resize((76 * 6, S.shape[0] * 6), Image.NEAREST).save(os.path.join(out, '속성_원본대한글_6배.png'))
