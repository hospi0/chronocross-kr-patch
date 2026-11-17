"""G12 설명서 — 글이 상자/말풍선 «안쪽»에 들어가는지 자동 검사(눈대중 금지).
바탕 = 원본 표에서 바꾸는 글 조각을 뺀 렌더. 상자 속 = 회색 결 화소, 말풍선 속 = 원본 말풍선 조각의 흰+글자 화소.
둘 다 MARGIN px 깎은 뒤, 새 글 잉크가 밖에 있으면 보고 + work/g12/fit/쪽N.png 빨간 점."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import drp, sprtab, g12build
from ccget import get_exact

MARGIN = 2


def erode(m, k):
    e = m.copy()
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            e &= np.roll(np.roll(m, dy, 0), dx, 1)
    return e


def check(outdir=None, log=print):
    from PIL import Image
    ob = get_exact('1', 2543)
    g12build.build(ob, log=lambda *a: None)
    vo = sprtab.vram_from_tims(get_exact('1', 11)); vo = sprtab.vram_from_tims(ob, vo)
    oh, osz = drp.find(ob, '/help'); TO = sprtab.read(ob, oh, osz)
    bad = []; room = []
    for no, spec in g12build.PAGES.items():
        ops = [p for p in TO['spr'][no - 1]['pieces']]
        boxk = {k for blk in spec.get('box', []) for k in blk[0]}
        bubk = {k for blk in spec.get('bub', []) for k in blk[0]}
        vis = [p for p in ops if p['w'] and p['h']]
        X0 = min(p['x'] for p in vis) - 40; Y0 = min(p['y'] for p in vis) - 20
        X1 = max(p['x'] + p['w'] for p in vis) + 40; Y1 = max(p['y'] + p['h'] for p in vis) + 20
        W, H = X1 - X0, Y1 - Y0
        def draw(pieces):
            im = np.full((H, W, 3), 48, np.uint8); cov = np.zeros((H, W), bool)
            for p in reversed(pieces):
                px = sprtab.piece_px(vo, p)
                for yy in range(p['h']):
                    for xx in range(p['w']):
                        c = int(px[yy, xx])
                        if c:
                            im[p['y'] - Y0 + yy, p['x'] - X0 + xx] = ((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3)
                            cov[p['y'] - Y0 + yy, p['x'] - X0 + xx] = True
            return im, cov
        def binary_fill_holes(m):
            outside = np.zeros_like(m); outside[0, :] = ~m[0, :]; outside[-1, :] = ~m[-1, :]; outside[:, 0] |= ~m[:, 0]; outside[:, -1] |= ~m[:, -1]
            while True:
                g2 = outside.copy()
                g2[1:] |= outside[:-1]; g2[:-1] |= outside[1:]; g2[:, 1:] |= outside[:, :-1]; g2[:, :-1] |= outside[:, 1:]
                g2 &= ~m
                if (g2 == outside).all(): return ~outside
                outside = g2
        def red(p):        # 키드(빨간 자리 표시 그림) 조각 — 상자 위에 겹쳐 그려져도 상자 판정에서 뺀다
            px = sprtab.piece_px(vo, p); c = px[px > 0].astype(int)
            return len(c) and ((c & 31) > ((c >> 10) & 31) + 6).mean() > 0.5
        bgp = [p for k, p in enumerate(ops) if k not in boxk and k not in bubk and p['w'] and p['h']]
        bg, _ = draw(bgp)
        bgn, _ = draw([p for p in bgp if not red(p)])
        _, bcov = draw([p for k, p in enumerate(ops) if k in bubk and p['w'] and p['h']])
        r, g, b = [bgn[..., i].astype(int) for i in range(3)]
        boxin = erode((abs(r - g) < 28) & (abs(g - b) < 28) & (r >= 72) & (r <= 190), MARGIN)
        wr, wg, wb = [bg[..., i].astype(int) for i in range(3)]
        bubin = erode(binary_fill_holes(bcov | ((wr >= 230) & (wg >= 230) & (wb >= 230))), MARGIN)   # 말풍선 테두리 조각의 흰 부분까지   # 검은 글자 화소(색 0 = 투명)로 뚫린 구멍 메움
        mark = bg.copy(); mark[bcov] = (240, 240, 240)
        for (pno, kind, line, img, x, y) in g12build.PLACED:
            if pno != no or img is None: continue
            ink = img > 0; hh, ww = ink.shape
            okm = (boxin if kind == 'box' else bubin)[y - Y0:y - Y0 + hh, x - X0:x - X0 + ww]
            reg = mark[y - Y0:y - Y0 + hh, x - X0:x - X0 + ww]
            reg[ink] = (255, 255, 255) if kind == 'box' else (0, 0, 0)
            out = ink & ~okm
            if out.any():
                ys, xs = np.nonzero(out)
                bad.append((no, kind, line[:16], int(out.sum()), int(xs.min()), int(ys.min())))
                reg[out] = (255, 0, 0)
            if kind == 'box':        # 가용 폭: 이 줄 가운데 높이에서 x 부터 상자 속이 이어지는 길이
                yy = y - Y0 + hh // 2; xx = x - X0; n = 0
                while xx + n < W and boxin[yy, xx + n]: n += 1
                room.append((no, line[:16], ww, n))
        if outdir:
            os.makedirs(outdir, exist_ok=True)
            Image.fromarray(mark).resize((W * 3, H * 3), Image.NEAREST).save(os.path.join(outdir, '쪽%d.png' % no))
    for x in room:
        if x[2] > x[3]: log('  폭 넘침 쪽%d «%s» 글 %d / 가용 %d' % x)
    for x in bad: log('  밖 잉크 쪽%d %s «%s» %d점 (블록 안 x%d y%d부터)' % x)
    return bad


if __name__ == '__main__':
    os.chdir(os.path.dirname(HERE))
    n = check('work/g12/fit')
    print('넘침', len(n))
