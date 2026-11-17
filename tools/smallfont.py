"""전투 소형 글꼴(G04, 파일 11/2542 osa1 아틀라스) 한글 글리프 — 갈무리7 BDF 화소 그대로.
칸 8×9: 잉크(색 2) 7×7 을 1~7행에, 그림자(색 1) = 잉크 바로 아래 한 화소(원본 글꼴과 같은 규칙).
사용: smallfont.py preview  → work/g04/preview_01/ 글자판(원본|한글)"""
import io, os, sys
import numpy as np

BDF = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri7.bdf'
CW, CH = 8, 9
_g = None


def bdf():
    global _g
    if _g is not None: return _g
    out = {}; cur = None; asc = 9
    it = iter(io.open(BDF, encoding='utf-8', errors='replace'))
    for ln in it:
        if ln.startswith('FONT_ASCENT'): asc = int(ln.split()[1])
        elif ln.startswith('ENCODING'): cur = int(ln.split()[1])
        elif ln.startswith('BBX'): bb = tuple(map(int, ln.split()[1:]))
        elif ln.startswith('BITMAP'):
            w, h, xo, yo = bb; rows = []
            for _ in range(h):
                s = next(it).strip(); v = int(s, 16); nb = len(s) * 4
                rows.append([(v >> (nb - 1 - x)) & 1 for x in range(w)])
            out[cur] = (w, h, xo, yo, rows)
    _g = (out, asc); return _g


def cell(ch):
    """글자 → (9, 8) 색인 배열(0 투명 · 1 그림자 · 2 글자). 칸을 넘으면 오류"""
    G, asc = bdf()
    if ch == ' ' or ch == '\u3000': return np.zeros((CH, CW), np.uint8)
    w, h, xo, yo, rows = G[ord(ch)]
    y0 = asc - yo - h - 1                      # 한글 7행 → 1~7행
    a = np.zeros((CH, CW), np.uint8)
    for y in range(h):
        for x in range(w):
            if rows[y][x]:
                yy, xx = y0 + y, xo + x
                assert 0 <= yy < CH - 1 and 0 <= xx < CW, (ch, xx, yy)
                a[yy, xx] = 2
    for y in range(CH - 1):
        for x in range(CW):
            if a[y, x] == 2 and a[y + 1, x] == 0: a[y + 1, x] = 1
    return a


def text(s, pitch=8):
    a = np.zeros((CH, pitch * len(s) + CW), np.uint8)
    for i, ch in enumerate(s):
        c = cell(ch); r = a[:, i * pitch:i * pitch + CW]; r[c > 0] = c[c > 0]
    return a[:, :pitch * (len(s) - 1) + CW]


PAL = np.array([(0, 0, 0), (8, 8, 8), (248, 248, 248)], np.uint8)


def rgb(a, bg=(40, 40, 56)):
    im = np.zeros(a.shape + (3,), np.uint8); im[:] = bg
    im[a == 1] = (8, 8, 8); im[a == 2] = (248, 248, 248)
    return im


if __name__ == '__main__' and sys.argv[1:] == ['preview']:
    from PIL import Image, ImageDraw
    sys.path.insert(0, os.path.dirname(__file__)); import sprtab
    b = open('work/files/1_0011.bin', 'rb').read()
    T = sprtab.tables(b); vram = sprtab.vram_from_tims(b)
    def orig(tab, no):
        bo, sz, tb = T['/tana/' + tab]
        return sprtab.render(vram, tb['spr'][no - 1], pad=0, rel=tb['tex'] if tb['flag'] else None)
    rowsL = []
    for ln in open('work/g04/names_ko.tsv', encoding='utf8'):
        if ln.startswith('L\t'):
            _, k, jp, ko = ln.rstrip('\n').split('\t'); rowsL.append((k, jp, ko))
    samples = ['세르주', '키드', '개량종 피오', '츠쿠요미', '시간을 먹는 자', '아카시아 용기병', '그림자고양이', '왓호이 탱크', '지옥의 주방장', '젤리킹']
    out = 'work/g04/preview_01'; os.makedirs(out, exist_ok=True)
    for scale, nm in ((1, '소형글꼴_라벨_원본대한글_1배.png'), (4, '소형글꼴_라벨_원본대한글_4배.png')):
        H = (len(rowsL) + len(samples)) * 14 + 8
        S = np.zeros((H, 230, 3), np.uint8); S[:] = (40, 40, 56); y = 4
        for k, jp, ko in rowsL:
            if k.startswith('osak') or k.startswith('stat'):
                tab = k[:4]; no = int(k[4:]); o = orig(tab, no)
                o = np.where(o == 48, np.array((40, 40, 56), np.uint8), o)
                o = o[:12, :100]; S[y:y + o.shape[0], 4:4 + o.shape[1]] = o
            t = rgb(text(ko.replace('-( %)', '')))
            S[y:y + CH, 110:110 + t.shape[1]] = t; y += 14
        for s in samples:
            t = rgb(text(s, 9)); S[y:y + CH, 4:4 + t.shape[1]] = t      # 파티 칸 간격 9
            t = rgb(text(s, 10)); S[y:y + CH, 110:110 + t.shape[1]] = t  # 대상 이름 간격 10
            y += 14
        Image.fromarray(S).resize((230 * scale, H * scale), Image.NEAREST).save(os.path.join(out, nm))
    # 전체 음절판
    syl = sorted({c for ln in open('work/g04/names_ko.tsv', encoding='utf8') if not ln.startswith('#') for c in ln.rstrip('\n').split('\t')[-1] if '가' <= c <= '힣'})
    cols = 32; R = (len(syl) + cols - 1) // cols
    A = np.zeros((R * CH, cols * CW), np.uint8)
    for i, c in enumerate(syl):
        A[(i // cols) * CH:(i // cols + 1) * CH, (i % cols) * CW:(i % cols + 1) * CW] = cell(c)
    for scale in (1, 4):
        Image.fromarray(rgb(A)).resize((A.shape[1] * scale, A.shape[0] * scale), Image.NEAREST).save(os.path.join(out, '소형글꼴_음절판_%d배.png' % scale))
    print(len(syl), '음절 →', out)
