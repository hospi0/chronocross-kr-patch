"""G07 DISC 교체 안내(파일 2050 구간 5, TIM 256×32 4bpp) · G08 상태이상 아이콘(구간 7, 116×16) 한글판 — 제자리(크기·배치 불변).
자르는 표는 아직 못 찾음(코드가 2050 을 번호 상수로 안 부름) → 원문 글자 구간 안에만 쓴다(기존 패치도 같은 구간 유지, 실기 문제 보고 없음).
G07: 1줄 «DISC [숫자] に入れ換えて下さい。» = DISC(x4~38) · 숫자 자리(39~57) · 뒤 글(58~205)
     2줄 «DISCが違います。 １ ２» = DISC(4~37) · が違います。(41~125) · 숫자 조각(144~165)
     색인 = 15 − 밝기(0·1 = 흰색, 15 = 투명)
G08: 毒(글 2~16)·ねんざ(19~52)·やけど(55~84)·風邪(86~113) — 색 공(색인 1~4) 위에 흰 글자(15) + 어두운 테두리(5~14)
"""
import os, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import krenc
from timscan import find_tims

FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothic.ttf'
DISC1 = '로 교체해 주세요.'          # 「DISC n に入れ換えて下さい。」
DISC2 = '가 다릅니다.'              # 「DISCが違います。」
ICON = [('독', 2, 16, 0, 17), ('염좌', 19, 52, 18, 54), ('화상', 55, 84, 55, 84), ('감기', 86, 113, 85, 115)]   # 글 시작·끝, 지울 구간


def secs(c):
    n = struct.unpack_from('<I', c, 0)[0]; offs = struct.unpack_from('<%dI' % (n + 1), c, 4)
    return offs


def tim_idx(sec):
    t = find_tims(sec)[0]
    d = np.frombuffer(t['data'], np.uint8).reshape(t['ih'], -1)
    idx = np.zeros((t['ih'], t['iw'] * 4), np.uint8); idx[:, 0::2] = d & 15; idx[:, 1::2] = d >> 4
    return t, idx


def put(c, off, t, idx):
    c = bytearray(c); packed = (idx[:, 0::2] | (idx[:, 1::2] << 4)).astype(np.uint8).tobytes()
    o = off + t['end'] - len(t['data']); assert len(packed) == len(t['data']); c[o:o + len(packed)] = packed
    return bytes(c)


def aa_text(s, size=12):
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(FONT, size)
    im = Image.new('L', (size * len(s) * 2, size * 3), 0); ImageDraw.Draw(im).text((0, size // 2), s, font=f, fill=255)
    a = np.asarray(im).astype(np.float32) / 255
    ys, xs = np.nonzero(a > 0.05)
    return a[ys.min():ys.max() + 1, :xs.max() + 1]


def g07(idx):
    idx = idx.copy()
    for (y0, x0, x1, s) in ((0, 58, 206, DISC1), (16, 41, 126, DISC2)):
        band = idx[y0:y0 + 16]
        ink = band[:, x0:x1] < 15
        rows = np.nonzero(ink.any(1))[0]; r0, r1 = rows.min(), rows.max()
        band[:, x0:x1] = 15
        for size in range(18, 10, -1):              # 원문 잉크 높이에 맞춤
            a = aa_text(s, size)
            if a.shape[0] <= r1 - r0 + 1 and a.shape[1] <= x1 - x0: break
        h, w = a.shape
        top = r0 + ((r1 - r0 + 1) - h) // 2
        q = np.clip(np.rint(15 - a * 15), 0, 15).astype(np.uint8)
        reg = band[top:top + h, x0:x0 + w]; m = a > 0.05; reg[m] = q[m]
    return idx


def g08(idx):
    idx = idx.copy()
    for s, x0, x1, e0, e1 in ICON:
        seg = idx[:, e0:e1 + 1]
        col = [c for c in (1, 2, 3, 4) if (seg == c).sum() > 20][0]
        top = np.nonzero(idx[0, e0:e1 + 1] == col)[0] + e0; cx = top.mean()
        # 2026-11-16 하스피 «동그라미를 그려 두고 글자를 넣어» — 구간을 비우고 온전한 원(지름 16)부터 다시 그린 뒤 글자
        seg[:] = 0
        yy, xx = np.mgrid[0:16, e0:e1 + 1]
        disc = (xx + 0.5 - (cx + 0.5)) ** 2 + (yy + 0.5 - 8) ** 2 <= 8 ** 2
        seg[disc] = col
        reg = seg
        g = np.zeros((16, e1 - e0 + 1), np.uint8)
        gw = 0
        for ch in s:
            rows = krenc.glyph_rows(ch)
            gw += max((16 - (v & -v).bit_length() + 1 for v in rows if v), default=0) if ch == s[-1] else 12
        x = int(round(cx + 0.5 - e0 - gw / 2))
        assert x >= 1 and x + gw <= g.shape[1] - 1, (s, x, gw)
        for ch in s:
            rows = krenc.glyph_rows(ch)
            for r, v in enumerate(rows):
                for k in range(12):
                    if v & (0x8000 >> k) and x + k < g.shape[1]: g[3 + r, x + k] = 1
            x += 12
        assert x - 12 + 12 <= g.shape[1] + 1, s
        ol = np.zeros_like(g)
        for dy, dx in ((0, 1), (1, 0), (1, 1)):         # 오른쪽·아래 그림자만 — 테두리를 두르면 원이 가려짐
            ol |= np.roll(np.roll(g, dy, 0), dx, 1)
        reg[(ol == 1) & (g == 0)] = 5                  # 원(배경) 위에 그림자 있는 글자를 그대로 얹음(하스피 지시)
        reg[g == 1] = 15
    return idx


def build(c):
    offs = secs(c)
    t5, i5 = tim_idx(c[offs[5]:offs[6]]); c = put(c, offs[5], t5, g07(i5))
    t7, i7 = tim_idx(c[offs[7]:offs[8]]); c = put(c, offs[7], t7, g08(i7))
    return c


if __name__ == '__main__':
    from ccget import get_exact
    from PIL import Image
    c = get_exact('1', 2050); n = build(c); assert len(n) == len(c)
    out = 'work/g07/preview_01'; os.makedirs(out, exist_ok=True)
    offs = secs(c)
    for k, nm, sc in ((5, 'DISC교체안내', 4), (7, '상태이상아이콘', 6)):
        ims = []
        for src in (c, n):
            t, idx = tim_idx(src[offs[k]:offs[k + 1]]); cl = t['clut'][0]
            rgb = np.dstack([(cl[idx] & 31) << 3, ((cl[idx] >> 5) & 31) << 3, ((cl[idx] >> 10) & 31) << 3]).astype(np.uint8)
            tr = 15 if k == 5 else 0; rgb[idx == tr] = (40, 40, 90); ims.append(rgb)
        S = np.concatenate([ims[0], np.zeros((2, ims[0].shape[1], 3), np.uint8), ims[1]])
        Image.fromarray(S).resize((S.shape[1] * sc, S.shape[0] * sc), Image.NEAREST).save(os.path.join(out, '%s_원본대한글_%d배.png' % (nm, sc)))
    print('바뀐 바이트', sum(x != y for x, y in zip(c, n)), '→', out)
