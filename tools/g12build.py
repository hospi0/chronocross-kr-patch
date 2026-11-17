"""G12~14 전투 설명서(파일 2543 /help 스프라이트 7쪽 + 글자판 /help·/hel1·/hel2) 한글판.
조사 = tools/g12survey.py (쪽마다 글 조각 번호 work/g12/survey_pN.png)
방식
  상자 글(흰 글자, 바탕 투명): 블록마다 원래 글 조각들을 «새 조각 하나»로 — 첫 조각 자리에 새 u·v·w·h·x·y, 나머지 조각은 w=h=0(목록·깃발 그대로)
  말풍선 글(검은 글자 + 흰 바탕): 원래 조각들이 덮던 흰 영역 모양 그대로 합성한 뒤 «원래 조각 크기대로 다시 잘라» 각 조각의 u·v 만 바꿈
글꼴 = 갈무리9 BDF 화소 그대로(한글 10px 폭·9px 높이), 줄 간격 = 원문 줄 간격
글자판 빈자리 = 남는 조각이 안 읽는 화소 전부(hel3 사진 구역 제외), u+w ≤ 255·v+h ≤ 255
번역 = Claude 임시(하스피 판정 대상)"""
import os, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import drp, sprtab, g02build
from timscan import find_tims

FONT = 10                     # g02build.render 크기 키 = 갈무리9
TEXT_CLUT = {0x3FF8, 0x3FF9, 0x3FFA}
# 글자판: (drp 이름, tpage, VRAM y → 쪽 안 v 시작)
SHEETS = {'/help': (15, 0), '/hel1': (14, 0), '/hel2': (14, 183)}

# ── 번역(쪽 → 블록) ─────────────────────────────────────────────────────────────
# box: (조각들, x, y, [줄], 선택)   선택: pitch, right(오른쪽 맞춤 끝 x), maxw, color, tab
# bub: (조각들, x0, y0, [줄], pitch)  — 글 시작점(조각 좌표계)
PAGES = {
 1: dict(box=[([22], 8, 8, ['공격	…타격으로 싸움'], dict(tab=44, maxw=127)),
              ([20], 8, 18, ['엘리먼트	…엘리먼트 사용'], dict(tab=44, maxw=127)),
              ([21], 8, 28, ['방어	…방어 자세 대기'], dict(tab=44, maxw=127)),
              ([19], 8, 38, ['도주	…도망친다'], dict(tab=44, maxw=127))],
         bub=[([18], 66, 61, ['일단 [공격]으로', '상대를', '두들겨 패 버려!'], 10)]),
 2: dict(box=[([45, 48, 47, 46], 8, 24, ['방향키 상하: 커맨드 선택'], dict(maxw=145)),
              ([44, 43, 42, 41], 8, 34, ['방향키 좌우: 조작 캐릭터 변경'], dict(maxw=145)),
              ([40, 39], 8, 44, ['L1·R1 버튼:'], dict(maxw=84)),
              ([36, 35], 22, 56, ['버튼: 결정'], dict(maxw=125)),
              ([33, 32], 22, 68, ['버튼: 취소'], dict(maxw=125)),
              ([30, 29], 22, 80, ['버튼: 다음 캐릭터로 변경'], dict(maxw=128, color=12)),
              ([27, 26], 22, 92, ['버튼: 시점 모드 변경'], dict(maxw=128, color=12)),
              ([25], 8, 104, ['(Sta.가 1.0 이상인 캐릭터는'], dict(maxw=145)),
              ([0, 1], 8, 114, ['방향키 좌우로 언제든 조작을'], dict(maxw=145)),
              ([2], 11, 124, ['바꿀 수 있습니다.)'], dict(maxw=140))]),
 3: dict(box=[([65], 0, 8, ['약…Sta.1 소비'], dict(right=100)),
              ([64], 0, 18, ['중…Sta.2 소비'], dict(right=100)),
              ([63], 0, 28, ['강…Sta.3 소비'], dict(right=100)),
              ([60, 59, 58, 57, 56, 61], 0, 38, ['엘리먼트…Sta.7 소비'], dict(right=100)),
              ([62], 0, 48, ['(Sta.=스태미나)'], dict(right=99)),
              ([33, 32, 31], 20, 84, ['스태미나가 1.0 미만이 되면', '커맨드를 입력할 수 없습니다.'], dict(pitch=10, maxw=135))],
         bub=[([22, 20, 21, 19, 16, 15, 18, 17], 166, 81, ['약·중·강을 잘', '나눠 쓰며 모아!', '어느 정도 모이면', '[엘리먼트]다!'], 11.5)]),
 4: dict(box=[([0, 14, 15, 2, 1, 3, 4, 6, 5, 7, 8], 6, -9,
               ['공격은 ○버튼을 누르고 있기만 하면', '명중률 80% 이상인 공격 중 가장 강한', '공격이 자동으로 선택됩니다. 물론',
                '직접 고를 수도 있습니다. 단 명중률은', '입력한 시점의 명중률이므로, 미리', '입력하면 자동 선택에 반영 안 됩니다.'],
               dict(pitch=11, maxw=174)),
              ([13], 8, 58, ['(미리 입력은'], dict(maxw=60)),
              ([11], 80, 58, ['실행된 건'], dict(maxw=50)),
              ([12], 142, 58, ['로 표시)'], dict(maxw=40))]),
 5: dict(box=[([128], 6, 6, ['엘리먼트'], dict(maxw=150)),
              ([108], 8, 16, ['모든 힘의 근원이라 여겨지는', '수수께끼의 금속판. 아득한 옛날', '다른 성계에서 왔다고 하지만', '자세한 것은 알려지지 않았다.'],
               dict(pitch=10.5, maxw=154)),
              ([34, 33, 32], 58, 80, ['엘리먼트를 발동하려면 그리드의 장착 위치에', '따라 일정한 파워 레벨(공격하면 오른다)이',
                                      '필요하다. 한 번의 전투에서 각각 한 번씩만', '쓸 수 있다(다음 전투에서는 회복된다).'],
               dict(pitch=10.5, maxw=206))],
         bub=[([27, 28, 29, 26], 174, -3, ['엘리먼트는 전투 중에', '하나씩 한 번밖에 못 써.', '쓰는 순서 잘 생각해!!'], 10)]),
 6: dict(box=[([32], 20, 8, ['(레벨 스타)'], dict(maxw=120)),
              ([30, 29], 6, 19, ['　세계에는 ★을 가진 강한 몬스터들이 있다. 이들을',
                                 '쓰러뜨려 ★을 모으면 플레이어는 다음 단계로 성장할',
                                 '수 있다. 쓰러뜨린 적의 강함에 따라 전투 후마다',
                                 '성장할 기회가 있지만, 새로운 ★을 얻지 못하면 결국',
                                 '일정 수준 이상으로는 성장할 수 없게 될 것이다.',
                                 '　또한 소환계 엘리먼트를 쓰려면 ★이 가진 특수한',
                                 '에너지가 필요하다.'], dict(pitch=11, maxw=251))],
         bub=[([28, 27, 9], 44, 103, ['……길다. 읽기 귀찮아.', '얼른 엘리먼트나 쓰자고!', '　그치, 세르주!!'], 10)]),
 7: dict(box=[([33, 32], 6, 8, ['필드 이펙트'], dict(maxw=120)),
              ([31], 9, 21, ['　엘리먼트를 쓸 때마다', '배틀 필드에 지난 3회분의', '잔류 속성이 쌓여 적·아군', '모두의 행동에 영향을 준다.'],
               dict(pitch=10.5, maxw=140)),
              ([30], 170, 32, ['　속성은 6가지 색이다.', '적·청, 녹·황, 백·흑', '세 쌍의 반대 속성은', '서로 효과를 지운다.'],
               dict(pitch=10.5, maxw=112)),
              ([21], 32, 94, ['　소환 엘리먼트는 필드의 3색이', '모두 같을 때만 발동할 수 있다.'], dict(pitch=10.5, maxw=165))],
         bub=[([0, 20], 129, -16, ['왼쪽 위 색 정보 잘 봐 둬!', '같은 색이 늘면 그만큼', '효과가 커져.'], 10)]),
}


def text_img(lines, pitch=11, tab=None, color=15, right=None):
    """줄들 → (색인 배열, 줄마다 폭). 글자 위 = 0행"""
    G, asc = g02build.bdf(FONT)
    rows = []
    for s in lines:
        x = 0; px = []
        for c in s:
            if c == '\t': x = max(x + 4, tab); continue
            if c == '　': x += 10; continue
            w, h, xo, yo, bm, dw = G[ord(c)]
            px.append((x, w, h, xo, yo, bm)); x += dw
        rows.append((px, x))
    W = max(r[1] for r in rows) + 2; H = int(round(pitch * (len(lines) - 1))) + 11
    a = np.zeros((H, W), np.uint8); widths = []
    for i, (px, wsum) in enumerate(rows):
        top = int(round(i * pitch))
        ink = 0
        for x, w, h, xo, yo, bm in px:
            y0 = top + asc - yo - h - 2
            for yy in range(h):
                for xx in range(w):
                    if bm[yy][xx]:
                        a[y0 + yy, x + xo + xx] = color; ink = max(ink, x + xo + xx + 1)
        widths.append(ink)
    ys = np.nonzero(a.any(1))[0]; xs = np.nonzero(a.any(0))[0]
    return a, widths


PLACED = []   # 검사용(g12fit): (쪽, 종류, 줄, 그림, x, y)


def build(b, log=print):
    PLACED.clear()
    b = bytearray(b)
    tr = {p: (bo, sz) for d, a, p, ty, bo, sz in drp.tree(bytes(b)) if ty in (3, 4)}
    hb, hs = drp.find(bytes(b), '/help')                         # 첫 /help = 표(종류 3)
    T = sprtab.read(bytes(b), hb, hs)
    # 글자판
    sheets = {}
    for d, a, p, ty, bo, sz in drp.tree(bytes(b)):
        if ty == 4 and p in SHEETS:
            t = find_tims(bytes(b[bo:bo + sz]))[0]
            dd = np.frombuffer(t['data'], np.uint8).reshape(t['ih'], -1)
            idx = np.zeros((t['ih'], t['iw'] * 4), np.uint8); idx[:, 0::2] = dd & 15; idx[:, 1::2] = dd >> 4
            sheets[p] = dict(bo=bo, t=t, idx=idx, tp=SHEETS[p][0], v0=SHEETS[p][1])
    page = {14: np.zeros((256, 256), np.int16) - 1, 15: np.zeros((256, 256), np.int16) - 1}   # 쪽 화소 → 판 (없음=-1)
    for nm, s in sheets.items():
        h = s['idx'].shape[0]; page[s['tp']][s['v0']:s['v0'] + h, :] = list(SHEETS).index(nm)
    usable = {tp: page[tp] >= 0 for tp in page}
    # 바꿀 조각
    repl = {}
    for no, spec in PAGES.items():
        for blk in spec.get('box', []) + spec.get('bub', []):
            for k in blk[0]: repl.setdefault(no, set()).add(k)
    prot = {tp: np.zeros((256, 256), bool) for tp in page}
    oldtxt = {tp: np.zeros((256, 256), bool) for tp in page}
    for i, s in enumerate(T['spr']):
        if not s: continue
        for k, p in enumerate(s['pieces']):
            if p['tp'] not in prot: continue
            (oldtxt if k in repl.get(i + 1, ()) else prot)[p['tp']][p['v']:p['v'] + p['h'], p['u']:p['u'] + p['w']] = True
    free = {tp: usable[tp] & ~prot[tp] for tp in page}
    for tp in free: free[tp][:, 255:] = False; free[tp][255:, :] = False
    # 지우기
    for nm, s in sheets.items():
        tp, v0 = s['tp'], s['v0']; h = s['idx'].shape[0]
        s['idx'][free[tp][v0:v0 + h, :]] = 0

    images = []        # (쪽, 블록종류, 조각 번호(첫), 그림, x, y, 대상 조각들)
    sprs = [None if s is None else dict(unk=s['unk'], pieces=[dict(p) for p in s['pieces']]) for s in T['spr']]
    over = []
    inserted = []; spare = []       # 끼운 조각 수만큼 다른 쪽의 빈 조각(w=h=0, 0x10 깃발 아님)을 빼서 표 크기를 원본과 같게(2026-11-17 — 파일 2543 원본 크기 유지)
    for no, spec in PAGES.items():
        ps = sprs[no - 1]['pieces']
        for ks, x, y, lines, o in spec.get('box', []):
            col = o.get('color', 15); pitch = o.get('pitch', 11)
            slots = [ps[k] for k in sorted(ks)]
            for i, line in enumerate(lines):          # 줄마다 조각 하나(글자판 자리 아끼기)
                img, widths = text_img([line], 11, o.get('tab'), col)
                ys = np.nonzero(img.any(1))[0]; xs = np.nonzero(img.any(0))[0]
                img = img[ys.min():ys.max() + 1, :xs.max() + 1]
                w = img.shape[1]
                if o.get('maxw') and w > o['maxw']: over.append((no, line[:12], w, o['maxw']))
                lx = o['right'] - w if 'right' in o else x
                ly = y + int(round(i * pitch)) + ys.min()
                if i < len(slots):
                    pc = slots[i]
                else:                                  # 조각이 모자라면 첫 조각 앞에 끼움(깃발 0x10 은 빼고)
                    pc = dict(slots[0], fl=slots[0]['fl'] & ~0x10)
                    ps.insert(ps.index(slots[0]), pc); inserted.append(pc)
                images.append(('box', no, pc, img, lx, ly, None))
                PLACED.append((no, 'box', line, img, lx, ly))
            for pc in slots[len(lines):]:
                pc.update(w=0, h=0)
                if not pc['fl'] & 0x10: spare.append((no, pc))
        for ks, x0, y0, lines, pitch in spec.get('bub', []):
            # 흰 영역 = 원래 조각들의 흰(15) 화소 모양
            rects = [ps[k] for k in ks]
            X0 = min(p['x'] for p in rects); Y0 = min(p['y'] for p in rects)
            X1 = max(p['x'] + p['w'] for p in rects); Y1 = max(p['y'] + p['h'] for p in rects)
            canvas = np.zeros((Y1 - Y0, X1 - X0), np.uint8); mask = np.zeros(canvas.shape, bool)
            for p in rects:
                sh = sheets[[n for n, s in sheets.items() if s['tp'] == p['tp'] and s['v0'] <= p['v'] < s['v0'] + s['idx'].shape[0]][0]]
                # 원본 조각 화소(원본 판에서)
                orig = sprtab_piece_idx(b, p)
                reg = canvas[p['y'] - Y0:p['y'] - Y0 + p['h'], p['x'] - X0:p['x'] - X0 + p['w']]
                white = orig != 0
                reg[white] = 15; mask[p['y'] - Y0:p['y'] - Y0 + p['h'], p['x'] - X0:p['x'] - X0 + p['w']] |= white
            img, widths = text_img(lines, pitch, color=1)
            ys = np.nonzero(img.any(1))[0]; xs = np.nonzero(img.any(0))[0]; img = img[ys.min():ys.max() + 1, :xs.max() + 1]
            ox, oy = x0 - X0, min(y0 - Y0, canvas.shape[0] - img.shape[0])   # 흰 영역 높이에 맞춤
            sub = canvas[oy:oy + img.shape[0], ox:ox + img.shape[1]]
            ink = img > 0
            okm = mask[oy:oy + img.shape[0], ox:ox + img.shape[1]]
            hh, ww = sub.shape
            if (ink[:hh, :ww] & ~okm).any() or img.shape[0] > hh or img.shape[1] > ww:
                over.append((no, '말풍선 ' + lines[0][:10], '흰 영역 밖'))
            sub[ink[:hh, :ww]] = 1
            for li, line in enumerate(lines):
                PLACED.append((no, 'bub', line, None, x0, y0 + int(round(li * pitch))))
            PLACED.append((no, 'bubimg', lines[0], img, X0 + ox, Y0 + oy))
            for k in ks:
                p = ps[k]
                p['clut'] = 0x3FF9          # 말풍선 안 흰 채움 조각(3FF8)도 검은 글자가 들어가므로 말풍선 팔레트로
                piece = canvas[p['y'] - Y0:p['y'] - Y0 + p['h'], p['x'] - X0:p['x'] - X0 + p['w']].copy()
                images.append(('bub', no, p, piece, p['x'], p['y'], None))
    if over: log('⚠ 넘침: %s' % over)
    for no, pc in spare[-len(inserted):] if inserted else []:
        lst = sprs[no - 1]['pieces']
        del lst[next(i for i, q in enumerate(lst) if q is pc)]          # 같은 값 다른 조각을 지우지 않게 정체성으로
    if len(inserted) > len(spare): log('⚠ 빈 조각 모자람: 끼움 %d · 빈 조각 %d — 표가 커짐' % (len(inserted), len(spare)))
    # 배치(큰 것부터, 띠 모서리 우선)
    def place(img):
        hh, ww = img.shape; best = None
        for tp in (15, 14):
            f = free[tp]
            for v in range(0, 256 - hh):
                row = f[v]
                for u in range(0, 256 - ww):
                    if not row[u]: continue
                    if (u > 0 and f[v, u - 1]) and (v > 0 and f[v - 1, u]): continue
                    if page[tp][v, 0] != page[tp][v + hh - 1, 0]: continue      # 판(hel1/hel2) 경계를 넘지 않게
                    if f[v:v + hh, u:u + ww].all():
                        cost = (tp != 15, v, u); best = (tp, u, v); break
                if best: break
            if best: break
        if not best: raise SystemExit('⛔ 설명서 글자판 자리 부족 %s' % (img.shape,))
        tp, u, v = best; free[tp][v:v + hh, u:u + ww] = False
        return tp, u, v
    order = sorted(range(len(images)), key=lambda i: -images[i][3].size)
    for i in order:
        kind, no, p, img, x, y, _ = images[i]
        tp, u, v = place(img)
        nm = [n for n, s in sheets.items() if s['tp'] == tp and s['v0'] <= v < s['v0'] + s['idx'].shape[0]][0]
        s = sheets[nm]; r = v - s['v0']; hh, ww = img.shape
        assert r + hh <= s['idx'].shape[0], ('판 경계를 넘음', nm)
        s['idx'][r:r + hh, u:u + ww] = img
        p.update(u=u, v=v, w=ww, h=hh, tp=tp, x=x, y=y)
    # 쓰기
    for nm, s in sheets.items():
        idx = s['idx']; t = s['t']
        packed = (idx[:, 0::2] | (idx[:, 1::2] << 4)).astype(np.uint8).tobytes()
        o = s['bo'] + t['end'] - len(t['data']); b[o:o + len(packed)] = packed
    newtab = sprtab.write(T, sprs)
    assert len(newtab) <= hs or True
    out = drp.rebuild(bytes(b), {('/help', 3): newtab}) if len(newtab) != hs else None
    if out is None:
        b[hb:hb + hs] = newtab; out = bytes(b)
    return out


_orig = None
def sprtab_piece_idx(b, p):
    """원본 파일 2543 에서 조각 화소 색인(지우기 전)"""
    global _orig
    if _orig is None:
        from ccget import get_exact
        ob = get_exact('1', 2543); pg = {14: np.zeros((256, 256), np.uint8), 15: np.zeros((256, 256), np.uint8)}
        for d, a, pth, ty, bo, sz in drp.tree(ob):
            if ty == 4 and pth in SHEETS:
                t = find_tims(ob[bo:bo + sz])[0]; tp, v0 = SHEETS[pth]
                dd = np.frombuffer(t['data'], np.uint8).reshape(t['ih'], -1)
                idx = np.zeros((t['ih'], t['iw'] * 4), np.uint8); idx[:, 0::2] = dd & 15; idx[:, 1::2] = dd >> 4
                pg[tp][v0:v0 + t['ih'], :] = idx
        _orig = pg
    return _orig[p['tp']][p['v']:p['v'] + p['h'], p['u']:p['u'] + p['w']]


if __name__ == '__main__':
    from ccget import get_exact
    from PIL import Image
    a = get_exact('1', 2543); n = build(a)
    print('파일 2543', len(a), '→', len(n))
    open('work/g12/1_2543_ko.bin', 'wb').write(n)
    out = sys.argv[1] if len(sys.argv) > 1 else 'work/g12/preview_02'; os.makedirs(out, exist_ok=True)
    for src, tag in ((a, '원본'), (n, '한글')):
        v = sprtab.vram_from_tims(get_exact('1', 11)); v = sprtab.vram_from_tims(src, v)
        hb, hs = drp.find(src, '/help'); T = sprtab.read(src, hb, hs)
        for i, s in enumerate(T['spr']):
            if not s: continue
            ps = [p for p in s['pieces'] if p['w'] and p['h']]
            im = sprtab.render(v, dict(pieces=ps), pad=2)
            Image.fromarray(im).resize((im.shape[1] * 3, im.shape[0] * 3), Image.NEAREST).save(os.path.join(out, '설명서%d쪽_%s.png' % (i + 1, tag)))
    print('→', out)
