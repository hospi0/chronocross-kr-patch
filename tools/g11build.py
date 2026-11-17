"""G11 파티 교체 화면 그림(파일 2051, TIM 256×240 4bpp, CLUT = 회색 16단계라 색인 = 밝기) 한글판 — 제자리, 영문(Status·Current Party·Member) 유지.
자르는 기록을 아직 못 찾음 → 각 낱말·줄을 원문 잉크 상자 안에만, 원문 시작 x 왼쪽 맞춤.
글꼴(2026-11-16 하스피 지시):
  능력치 라벨 = 메인 메뉴와 같은 글꼴(g02build.render: 갈무리11 Bold, 선천속성 갈무리9) — 화면 비율 맞춤으로 가로 2배
  안내문 = 원문처럼 «크고 고운» 글자 — 나눔고딕 안티앨리어싱(16단계 밝기), 줄 높이(12행)에 맞춤"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import g02build
from timscan import find_tims

AAFONT = r'C:\claude\utils\font\nanum-gothic\NanumGothic.ttf'
# (행0, 행1, 열0, 열1, 번역, 글꼴)  행·열 = 지울 범위(라벨은 원문 띠 + 아래 빈 줄 1)
# ★이 화면은 가로 고해상도(512) — 그림 1px 가 화면 반 칸. 원문 글자도 가로로 두 배 넓게 그려져 있다(腕力 = 2자 38px·높이 10)
#   → 한글도 가로 2배로(비트맵은 화소 가로 복제, 안티앨리어싱은 2배 폭으로 다시 맞춤)
BOX = [
    (13, 23, 11, 60, '완력', 'b9'), (13, 23, 103, 180, '정확도', 'b9'),
    (25, 35, 1, 72, '내구력', 'b9'), (25, 35, 103, 180, '민첩성', 'b9'),
    (37, 47, 10, 60, '마력', 'b9'), (37, 47, 113, 180, '항마', 'b9'),
    (49, 59, 0, 190, '선천속성', 'b9'),
    (97, 108, 0, 190, '교대할 멤버를', 'aa'), (109, 119, 0, 190, '선택해 주세요', 'aa'),
    (121, 131, 0, 190, '파티 멤버를', 'aa'), (133, 143, 0, 190, '선택해 주세요', 'aa'),
]


def aa(s, hmax):
    from PIL import Image, ImageDraw, ImageFont
    for size in range(24, 8, -1):
        f = ImageFont.truetype(AAFONT, size)
        im = Image.new('L', (size * len(s) * 2, size * 3), 0); ImageDraw.Draw(im).text((0, size // 2), s, font=f, fill=255)
        a = np.asarray(im).astype(np.float32) / 255
        ys, xs = np.nonzero(a > 0.08)
        if ys.max() - ys.min() + 1 <= hmax: break
    a = a[ys.min():ys.max() + 1, :xs.max() + 1]
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((a.shape[1] * 2, a.shape[0]), Image.BILINEAR)).astype(np.float32) / 255
    return np.clip(np.rint(a * 15), 0, 15).astype(np.uint8)


def build(b):
    b = bytearray(b); t = find_tims(bytes(b))[0]
    assert (t['ix'], t['iy'], t['iw'], t['ih'], t['fl']) == (0, 0, 64, 240, 8)
    d = np.frombuffer(t['data'], np.uint8).reshape(240, -1)
    idx = np.zeros((240, 256), np.uint8); idx[:, 0::2] = d & 15; idx[:, 1::2] = d >> 4
    for r0, r1, c0, c1, s, f in BOX:
        ink = idx[r0:r1 + 1, c0:c1 + 1] > 0
        cols = np.nonzero(ink.any(0))[0]; x0 = c0 + cols.min()
        idx[r0:r1 + 1, c0:c1 + 1] = 0
        if f == 'aa':
            q = aa(s, r1 - r0 + 1)
        elif f == 'b9':                                  # 원문 라벨 크기(높이 9~10)에 맞춘 굵은 글자 = 갈무리9 + 1px 굵게(메뉴 굵은 글자 모양)
            q, _, _ = g02build.render(s, 10); ys = np.nonzero(q.any(1))[0]; q = q[ys.min():ys.max() + 1]
            q = np.pad(q, ((0, 0), (0, 1))); q = np.maximum(q, np.roll(q, 1, axis=1))
            q = np.repeat(q, 2, axis=1)
        else:
            q, _, _ = g02build.render(s, f); ys = np.nonzero(q.any(1))[0]; q = np.repeat(q[ys.min():ys.max() + 1], 2, axis=1)
        h, w = q.shape
        assert h <= r1 - r0 + 1 and x0 + w <= c1 + 1, (s, h, w, r1 - r0 + 1, c1 + 1 - x0)
        top = r0 + (r1 - r0 + 1 - h) // 2
        reg = idx[top:top + h, x0:x0 + w]; m = q > 0; reg[m] = q[m]
    packed = (idx[:, 0::2] | (idx[:, 1::2] << 4)).astype(np.uint8).tobytes()
    o = t['end'] - len(t['data']); b[o:o + len(packed)] = packed
    return bytes(b)


if __name__ == '__main__':
    from ccget import get_exact
    from PIL import Image
    a = get_exact('1', 2051); n = build(a); assert len(n) == len(a)
    out = 'work/g11/preview_04'; os.makedirs(out, exist_ok=True)
    ims = []
    for src in (a, n):
        t = find_tims(src)[0]; d = np.frombuffer(t['data'], np.uint8).reshape(240, -1)
        idx = np.zeros((240, 256), np.uint8); idx[:, 0::2] = d & 15; idx[:, 1::2] = d >> 4
        c = t['clut'][0][idx]; rgb = np.dstack([(c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3]).astype(np.uint8)
        rgb[idx == 0] = (40, 30, 20); ims.append(rgb[:176])
    S = np.concatenate([ims[0], np.zeros((176, 4, 3), np.uint8), ims[1]], 1)
    Image.fromarray(S).resize((S.shape[1] * 3, S.shape[0] * 3), Image.NEAREST).save(os.path.join(out, '파티교체_원본대한글_3배.png'))
    # 화면 비율(가로 고해상도 → 가로 절반으로 보임)
    H = S.shape[0]; Image.fromarray(S).resize((S.shape[1] * 3 // 2, H * 3), Image.BILINEAR).save(os.path.join(out, '파티교체_화면비율_원본대한글.png'))
    print('바뀐 바이트', sum(x != y for x, y in zip(a, n)), '→', out)
