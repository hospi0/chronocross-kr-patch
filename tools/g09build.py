"""타이틀 «バイブレーション機能» 라벨(파일 224·233 TIM 256×325 4bpp, VRAM 960,0) → «진동 기능» 제자리.
라벨 = 259~282행 x10~249(밑줄 286~287행은 그대로). 색인 15 = 투명, 잉크 램프 = CLUT 밝기순(0·8~14).
글꼴 = 나눔명조(원문 명조체), 원문 잉크 높이에 맞춤, 왼쪽 맞춤(원문 시작 x).
2026-11-16 하스피 스샷(진동.sav)으로 확인 — G09 는 영문만 있다고 보고 제외했던 그림"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from timscan import find_tims

FONT = r'C:\claude\utils\font\nanum-myeongjo\NanumMyeongjoBold.ttf'
TEXT = '진동 기능'
R0, R1, X0, X1 = 259, 283, 10, 250


def lum(c):
    return (c & 31) * 0.3 + ((c >> 5) & 31) * 0.59 + ((c >> 10) & 31) * 0.11


def build(b, text=TEXT):
    from PIL import Image, ImageDraw, ImageFont
    b = bytearray(b); t = find_tims(bytes(b))[0]
    assert (t['ix'], t['iy'], t['iw'], t['ih'], t['fl']) == (960, 0, 64, 325, 8)
    d = np.frombuffer(t['data'], np.uint8).reshape(325, -1)
    idx = np.zeros((325, 256), np.uint8); idx[:, 0::2] = d & 15; idx[:, 1::2] = d >> 4
    cl = t['clut'][0]
    ramp = sorted([0] + list(range(8, 15)), key=lambda i: lum(int(cl[i])))   # 어두운 → 밝은
    ink = idx[R0:R1, X0 - 10:X1] != 15
    rows = np.nonzero(ink.any(1))[0]; h0 = rows.max() - rows.min() + 1
    idx[R0:R1, :] = 15
    for size in range(40, 10, -1):
        f = ImageFont.truetype(FONT, size)
        im = Image.new('L', (size * len(text) * 2, size * 3), 0); ImageDraw.Draw(im).text((0, size // 2), text, font=f, fill=255)
        a = np.asarray(im).astype(np.float32) / 255
        ys, xs = np.nonzero(a > 0.06)
        if ys.max() - ys.min() + 1 <= h0 - 2: break
    a = a[ys.min():ys.max() + 1, :xs.max() + 1]
    h, w = a.shape; assert w <= X1 - X0, w
    top = R0 + rows.min() + (h0 - h) // 2
    q = np.full(a.shape, 15, np.uint8); m = a > 0.06
    lv = np.clip((a * len(ramp)).astype(int), 0, len(ramp) - 1)
    q[m] = np.array(ramp, np.uint8)[lv[m]]
    reg = idx[top:top + h, X0:X0 + w]; reg[m] = q[m]
    packed = (idx[:, 0::2] | (idx[:, 1::2] << 4)).astype(np.uint8).tobytes()
    o = t['end'] - len(t['data']); b[o:o + len(packed)] = packed
    return bytes(b)


if __name__ == '__main__':
    from ccget import get_exact
    from PIL import Image
    out = 'work/g09/preview_01'; os.makedirs(out, exist_ok=True)
    for fi in (224, 233):
        a = get_exact('1', fi); n = build(a); assert len(n) == len(a)
        ims = []
        for src in (a, n):
            t = find_tims(src)[0]; d = np.frombuffer(t['data'], np.uint8).reshape(325, -1)
            idx = np.zeros((325, 256), np.uint8); idx[:, 0::2] = d & 15; idx[:, 1::2] = d >> 4
            c = t['clut'][0][idx]; rgb = np.dstack([(c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3]).astype(np.uint8)
            rgb[idx == 15] = (20, 16, 14); ims.append(rgb[250:292])
        S = np.concatenate([ims[0], np.zeros((3, 256, 3), np.uint8), ims[1]])
        Image.fromarray(S).resize((256 * 3, S.shape[0] * 3), Image.NEAREST).save(os.path.join(out, '진동기능_%d_원본대한글_3배.png' % fi))
        print(fi, '바뀐 바이트', sum(x != y for x, y in zip(a, n)))
