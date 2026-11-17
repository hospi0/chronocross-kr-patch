"""G04 전투 소형 글꼴 생성기 — 파일 11 / 2542 의 osa1 아틀라스 + 스프라이트 표(osak·stat·levu·paus)를 한글로 다시 만든다.
설계 = docs/그림글자_목록.md «G04 전수 조사·설계».

  스프라이트 번호 = 대사 글꼴 칸 − 0x4B (전투 코드 0x800C3E08, 안 고침) → osak 표를 칸 번호대로 다시 짬
  아틀라스 2겹: 색인 아래 2비트 = A층(CLUT 448,240 = 0x3C1C), 위 2비트 = B층(CLUT = 아틀라스 맨 아랫줄 오른쪽 64px, VRAM 1008,430)
  라벨(공격·상태이상·능력치…)은 음절 칸을 이어 붙인 조각으로

build(file_bytes, cells, labels) → 새 파일 바이트.   cells = {음절: 대사 글꼴 칸}  labels = {키: 번역}
사용(시험): g04build.py preview   → work/g04/preview_02/ (빌드한 바이트를 되읽어 그림)
"""
import os, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import drp, sprtab, smallfont
from timscan import find_tims

AX, AY, AW, AH = 960, 352, 256, 79           # 아틀라스 VRAM 자리·크기(px)
CLUT_A = 0x3C1C                              # (448,240)
CLUT_B = (430 << 6) | (1008 // 16)           # 아틀라스 78행 x 192~255 px
ROWS_A = [16, 25, 34, 43, 52, 61, 70]        # A층 칸 줄(원본 고정 칸 줄)
ROWS_B = [7] + ROWS_A                        # B층은 영숫자 줄 위에도 겹침
SP, PITCH, SPACE = 0x08, 9, 4
BLANK = {356}                               # 숫자 «빈 자리» = '０'(101) + 0xFF — 필드 레벨업 창(파일 4 코드), 원본 표(292개)에선 범위 밖이라 안 그려짐                # 글자 조각 깃발 · 글자 간격 · 공백 간격

# 라벨: (표, 번호) → (지울 조각 판정, [(x, y, 라벨 키)], 옮길 조각 판정·dx)
def _txt(p): return p['tp'] == 0x1F
LABELS = {
    ('osak', 1): (_txt, [(0, 0, 'osak1')]), ('osak', 2): (_txt, [(0, -1, 'osak2')]),
    ('osak', 3): (_txt, [(0, 0, 'osak3')]), ('osak', 4): (_txt, [(0, 0, 'osak4')]),
    ('osak', 7): (lambda p: p['x'] == 0, [(0, 0, 'osak7')]), ('osak', 8): (lambda p: p['x'] == 0, [(0, 0, 'osak8')]),
    ('osak', 9): (lambda p: p['x'] == 0, [(0, 0, 'osak9')]),
    ('osak', 10): (lambda p: p['y'] == -16, [(7, -16, 'osak10')]),
    ('levu', 2): (lambda p: _txt(p) and p['y'] in (32, 44),
                  [(12, 32, 'levu_a'), (56, 32, 'levu_b'), (104, 32, 'levu_c'), (7, 44, 'levu_d'), (56, 44, 'levu_e'), (104, 44, 'levu_f')]),
    ('levu', 3): (lambda p: _txt(p) and p['y'] == 144 and p['x'] >= 96, [(96, 144, 'levu_g')]),
    ('paus', 2): (lambda p: _txt(p) and p['x'] < 25, [(-49, -5, 'paus')]),
    ('paus', 3): (lambda p: _txt(p) and p['x'] < 25, [(-49, -5, 'paus')]),
}
for k in list(range(7, 23)) + [24]:
    LABELS[('stat', k)] = (_txt, [(4, 0, 'stat%d' % k)])
LABELS[('stat', 23)] = (_txt, [(4, 0, 'stat22')])     # 22·23 = 같은 낱말(색만 다름)
PAUS_SHIFT = lambda p: _txt(p) and 25 <= p['x'] < 45   # «:ON/OFF» 를 글자 뒤로 당김


def text_w(s):
    return sum(SPACE if c in ' 　' else PITCH for c in s) - (PITCH - 8)


def load_atlas(b):
    bo, sz = drp.find(b, '/osa1')
    t = find_tims(b[bo:bo + sz])[0]
    assert (t['ix'], t['iy'], t['iw'] * 4, t['ih']) == (AX, AY, AW, AH)
    d = np.frombuffer(t['data'], np.uint8).reshape(AH, -1)
    idx = np.zeros((AH, AW), np.uint8); idx[:, 0::2] = d & 15; idx[:, 1::2] = d >> 4
    return bo, sz, t, idx


def build(b, cells, labels, log=None):
    """cells = {음절: 대사 글꼴 칸} — 이 글꼴로 찍힐 수 있는 음절 전부(이름·입력판). 라벨 음절은 여기 없어도 자리만 받음"""
    T = {p.split('/')[-1]: v for p, v in sprtab.tables(b).items() if p.startswith('/tana/')}
    abo, asz, tim, idx = load_atlas(b)
    assert set(np.unique(idx)) <= {0, 1, 2}, '원본 아틀라스가 3색이 아님'

    def atl(tb, p):      # 조각의 아틀라스 좌표
        if tb['flag']: return p['u'] + (tb['tex'][0] - AX) * 4, p['v'] + tb['tex'][1] - AY
        return p['u'], p['v'] - (AY - 256)

    def unatl(tb, u, v):
        if tb['flag']: return u - (tb['tex'][0] - AX) * 4, v - (tb['tex'][1] - AY)
        return u, v + (AY - 256)

    # 1) 새 조각 목록(글자 자리는 ('G', 음절)) ------------------------------------------------
    need = set(cells)
    new = {}                                   # (표, 번호) → [조각 dict | ('G', x, y, 음절)]
    for (tn, no), (drop, puts) in LABELS.items():
        tb = T[tn][2]; s = tb['spr'][no - 1]
        ps = [dict(p) for p in s['pieces'] if not drop(p)]
        ins = min([k for k, p in enumerate(s['pieces']) if drop(p)] + [len(ps)])   # 새 글자는 지운 첫 조각 자리에(목록 앞 = 위에 그려짐)
        ins = min(ins, len(ps)); G = []
        if tn == 'paus':
            w = text_w(labels['paus']); colon = min(p['x'] for p in ps if PAUS_SHIFT(p))
            dx = (-49 + w + 1) - colon
            for p in ps:
                if PAUS_SHIFT(p): p['x'] += dx
        for x, y, key in puts:
            for c in labels[key]:
                if c in ' 　': x += SPACE; continue
                assert '가' <= c <= '힣', (key, c)
                G.append(('G', x, y, c)); need.add(c); x += PITCH
        new[(tn, no)] = ps[:ins] + G[::-1] + ps[ins:]
    # osak 글자 스프라이트
    maxcell = max(cells.values()) if cells else 0x14B
    assert all(0x56 <= c <= 0xA5 or c >= 0x14C for c in cells.values()), '한글 칸 범위 밖'
    osak = T['osak'][2]
    n_new = max(256, maxcell - 0x4B)
    ospr = [None] * n_new
    for i in range(min(osak['n'], n_new)):
        cell = i + 1 + 0x4B
        if i < 10 or 0xA6 <= cell <= 0xF9: ospr[i] = osak['spr'][i]      # 라벨·부호·영숫자 = 원본(라벨은 아래에서 덮음)
    for syl, cell in cells.items():
        assert cell - 0x4B not in BLANK, ('빈 자리 스프라이트에 음절', syl, hex(cell))
        ospr[cell - 0x4B - 1] = dict(unk=0, pieces=[('G', 0, 0, syl)])
    for k in BLANK:
        if k <= len(ospr): ospr[k - 1] = None
    for (tn, no), ps in new.items():
        if tn == 'osak': ospr[no - 1] = dict(unk=osak['spr'][no - 1]['unk'], pieces=ps)

    # 2) 보호 영역 = 남는 조각이 읽는 아틀라스 화소 + 0~15행 --------------------------------
    prot = np.zeros((AH, AW), bool); prot[:16] = True
    def mark(tb, pieces):
        for p in pieces:
            if isinstance(p, dict) and p['tp'] == 0x1F and p['clut'] == CLUT_A:
                u, v = atl(tb, p)
                if 0 <= v < AH: prot[max(v, 0):v + p['h'], u:u + p['w']] = True
    for tn, (bo, sz, tb) in T.items():
        if tn == 'osak':
            for s in ospr:
                if s: mark(tb, s['pieces'])
            continue
        for i, s in enumerate(tb['spr']):
            if s: mark(tb, new.get((tn, i + 1), s['pieces']))
    A = np.where(prot, idx, 0).astype(np.uint8)
    B = np.zeros((AH, AW), np.uint8)
    freeA = [(x, y) for y in ROWS_A for x in range(0, AW - 8, 8) if not prot[y:y + 9, x:x + 8].any() and not (y + 9 > 78 and x >= 192)]
    freeB = [(x, y) for y in ROWS_B for x in range(0, AW - 8, 8) if not (y + 9 > 78 and x >= 192)]   # x=248 금지(u+w=256 감김)
    slots = [(0, x, y) for x, y in freeA] + [(1, x, y) for x, y in freeB]
    syls = sorted(need)
    if log: log('소형 글꼴 음절 %d / 자리 %d (A층 %d + B층 %d)' % (len(syls), len(slots), len(freeA), len(freeB)))
    if len(syls) > len(slots): raise SystemExit('⛔ 소형 글꼴 음절 %d > 자리 %d' % (len(syls), len(slots)))
    where = {}
    for syl, (ly, x, y) in zip(syls, slots):
        where[syl] = (ly, x, y); g = smallfont.cell(syl)
        (A, B)[ly][y:y + 9, x:x + 8] = g

    # 3) 아틀라스 TIM ---------------------------------------------------------------------
    pix = (A | (B << 2)).astype(np.uint8)
    packed = (pix[:, 0::2] | (pix[:, 1::2] << 4)).astype(np.uint8)
    base = [int(x) for x in tim['clut'][0][:3]]
    ca = [base[i & 3] if (i & 3) < 3 else 0 for i in range(16)]
    cb = [base[i >> 2] if (i >> 2) < 3 else 0 for i in range(16)]
    words = np.frombuffer(packed.tobytes(), '<u2').reshape(AH, AW // 4).copy()
    words[78, 48:64] = cb
    body = bytearray(b[abo:abo + asz]); t0 = tim['off']
    assert body[t0:t0 + 8] == b'\x10\0\0\0\x08\0\0\0'
    struct.pack_into('<16H', body, t0 + 20, *ca)
    doff = tim['end'] - len(tim['data'])
    body[doff:doff + len(tim['data'])] = words.tobytes()
    repl = {'/osa1': bytes(body)}

    # 4) 스프라이트 표 ---------------------------------------------------------------------
    def ser(tb, sprs):
        n = len(sprs); hdr = struct.pack('<HH4H', 0, n | (0x8000 if tb['flag'] else 0), *tb['tex'], *tb['clut'])
        offs = []; data = bytearray(); pad = (n & 1) * 2          # 개수가 홀수면 오프셋 표 뒤 0 두 개(원본과 같음)
        for s in sprs:
            if s is None: offs.append(0); continue
            offs.append(12 + 2 * n + pad + len(data))
            ps = s['pieces']; data += struct.pack('<HH', len(ps), s['unk'])
            for k, p in enumerate(ps):
                if isinstance(p, tuple):
                    _, x, y, syl = p; ly, au, av = where[syl]; u, v = unatl(tb, au, av)
                    fl = SP | (0x10 if k == len(ps) - 1 or not isinstance(ps[k + 1], tuple) else 0)
                    assert 0 <= u <= 255 and 0 <= v <= 255
                    data += struct.pack('<hhBBHBBBB', x, y, u, v, CLUT_B if ly else CLUT_A, 8, 9, 0x1F, fl)
                else:
                    data += struct.pack('<hhBBHBBBB', p['x'], p['y'], p['u'], p['v'], p['clut'], p['w'], p['h'], p['tp'], p['fl'])
        out = hdr + struct.pack('<%dH' % n, *offs) + bytes(pad) + bytes(data)
        assert len(out) < 0x10000 and len(out) % 4 == 0, len(out)
        return out
    repl['/tana/osak'] = ser(osak, ospr)
    for tn in ('stat', 'levu', 'paus'):
        tb = T[tn][2]
        sprs = [None if s is None else dict(unk=s['unk'], pieces=new.get((tn, i + 1), s['pieces'])) for i, s in enumerate(tb['spr'])]
        repl['/tana/' + tn] = ser(tb, sprs)
    out = drp.rebuild(b, repl)
    return out, where


def selftest(b):
    """무변경 직렬화 = 원본 표와 같은 내용인지(조각 단위)"""
    for p, (bo, sz, tb) in sprtab.tables(b).items():
        pass


if __name__ == '__main__' and sys.argv[1:2] == ['preview']:
    from PIL import Image, ImageDraw
    names = []; labels = {}
    lev = iter('abcdefg')
    for ln in open('work/g04/names_ko.tsv', encoding='utf8'):
        if ln.startswith('#') or not ln.strip(): continue
        bnd, k, jp, ko = ln.rstrip('\n').split('\t')
        if bnd == 'L':
            if k == 'levu': k = 'levu_' + next(lev)
            labels[k] = ko.replace('-( %)', '').replace('Ｇ', '')
        else: names.append(ko)
    labels['paus'] = '진동 기능'
    syl = sorted({c for s in names for c in s if '가' <= c <= '힣'})
    cells = {c: 0x14C + i for i, c in enumerate(syl)}                 # 시험: 전부 2바이트 칸 앞쪽
    out_dir = 'work/g04/preview_02'; os.makedirs(out_dir, exist_ok=True)
    for fn in ('work/files/1_0011.bin', 'work/files/1_2542.bin'):
        b = open(fn, 'rb').read()
        nb, where = build(b, cells, labels, log=print)
        print(fn, len(drp.rebuild(b, {})), '→', len(nb), 'B')
        open(os.path.join('work/g04', os.path.basename(fn).replace('.bin', '_g04.bin')), 'wb').write(nb)
    # 되읽어 그림: 원본 | 새것
    b0 = open('work/files/1_0011.bin', 'rb').read(); b1 = open('work/g04/1_0011_g04.bin', 'rb').read()
    v0 = sprtab.vram_from_tims(b0); v1 = sprtab.vram_from_tims(b1)
    T0 = sprtab.tables(b0); T1 = sprtab.tables(b1)
    items = sorted(LABELS)
    for scale in (1, 4):
        W, H = 300, 8 + sum(max(20, 14) for _ in items) + 150
        S = np.zeros((H + 600, W, 3), np.uint8); S[:] = (40, 40, 56); y = 4
        for tn, no in items:
            row_h = 0
            for col, (TT, vv) in enumerate(((T0, v0), (T1, v1))):
                tb = TT['/tana/' + tn][2]; s = tb['spr'][no - 1]
                im = sprtab.render(vv, s, pad=1, rel=tb['tex'] if tb['flag'] else None)
                im = im[:, :140]
                S[y:y + im.shape[0], 4 + col * 150:4 + col * 150 + im.shape[1]] = im; row_h = max(row_h, im.shape[0])
            y += row_h + 3
        # 이름 견본: 표에서 음절 스프라이트를 꺼내 이어 붙임
        tb = T1['/tana/osak'][2]
        for nm in ('세르주', '키드', '개량종 피오', '츠쿠요미', '시간을 먹는 자', '아카시아 용기병', '그림자고양이', '자코츠 대령', '비타　＃１', 'ＳＡＢＬＯＷ'):
            import cctable
            rev = {c: i for i, c in cctable.base_table().items() if len(c) == 1 and (0xA6 <= i <= 0xF9)}
            for col, pitch in enumerate((9, 10)):
                x = 4 + col * 150
                for c in nm:
                    if c in ' 　': x += pitch; continue
                    cell = cells[c] if c in cells else rev[c]
                    s = tb['spr'][cell - 0x4B - 1]
                    im = sprtab.render(v1, s, pad=0, rel=tb['tex'])
                    m = (im != 48).any(axis=2); reg = S[y:y + im.shape[0], x:x + im.shape[1]]; reg[m] = im[m]
                    x += pitch
            y += 13
        S = S[:y + 4]
        Image.fromarray(S).resize((W * scale, S.shape[0] * scale), Image.NEAREST).save(os.path.join(out_dir, '소형글꼴_빌드되읽기_원본대한글_%d배.png' % scale))
    # 아틀라스 층별
    bo, sz, t, _ = load_atlas(b1)
    d = np.frombuffer(t['data'], np.uint8).reshape(AH, -1); px = np.zeros((AH, AW), np.uint8); px[:, 0::2] = d & 15; px[:, 1::2] = d >> 4
    for nm, lay in (('A층', px & 3), ('B층', px >> 2)):
        Image.fromarray(smallfont.rgb(lay)).resize((AW * 4, AH * 4), Image.NEAREST).save(os.path.join(out_dir, '아틀라스_%s_4배.png' % nm))
    print('→', out_dir)


# 전투 코드(파일 6 = 2538, 적재 0x800A9F00) 안 «스프라이트 번호로 적힌» 고정 문자열 — 대상 범위 라벨 3개(u16×11)
SCOPE_OFF = 0x800DE8B8 - 0x800A9F00
SCOPE = ['적·아군 전체', '적 전체', '아군 전체']        # 원문 敵・味方全体 / 敵全体 / 味方全体
def patch_scope(b6, cells, texts=SCOPE):
    """cells = {음절: 대사 글꼴 칸}. 공백 = 6번(오프셋 0 = 안 그려지는 스프라이트, 0 은 끝 표지라 못 씀)"""
    import struct as _s
    b6 = bytearray(b6)
    assert _s.unpack_from('<6H', b6, SCOPE_OFF) == (272, 100, 273, 274, 275, 276), '원본 대상 범위 라벨이 아님'
    for k, t in enumerate(texts):
        v = [6 if c == ' ' else 100 if c == '·' else cells[c] - 0x4B for c in t]
        assert len(v) <= 11, t
        _s.pack_into('<11H', b6, SCOPE_OFF + 22 * k, *(v + [0] * (11 - len(v))))
    return bytes(b6)
