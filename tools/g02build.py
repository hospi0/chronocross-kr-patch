"""G02·G03 메뉴 아틀라스(파일 41 /wind·/maru) + 배치 표(파일 42 /main, 스프라이트 186개) 한글판.
원본 글자 = 회색 16단계(색인 = 밝기) 굵은 글꼴, 낱말 단위 조각(セーブ·攻撃·力·率 …)을 이어 붙여 찍음.
방식: 스프라이트마다 일본어 조각을 «줄에서 이어진 묶음»으로 모아 번역 → 한글 낱말 그림을 아틀라스 빈자리(지운 일본어 자리)에 다시 깔고
     묶음의 조각을 새 조각 하나로 바꿈(왼쪽 맞춤).
사용: g02build.py phrases | preview
"""
import os, sys, struct, json, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import drp, sprtab
from timscan import find_tims

FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf'
ATL = {13: ('/wind', 0x34F6, 832, 0), 12: ('/maru', 0x1832, 768, 99)}      # tpage → (이름, CLUT, VRAM x, y)

# 일본어 조각(아틀라스 사각형 tp,u,v,w,h) → 원문.  이름 입력 탭(カタカナ·ひらがな·英数字·初期化)은 이름 입력 단계에서
JP = {
 (12, 0, 99, 40, 13): 'セーブ', (12, 40, 99, 40, 13): 'ロード',
}


def rect_names():
    """work/g02/rects.json(접촉 시트 번호) 기준 원문 표 — 한 번 눈으로 읽어 확정한 것"""
    ks = [tuple(k) for k in json.load(open(os.path.join(HERE, '..', 'work', 'g02', 'rects.json')))]
    N = {0: 'セーブ', 1: 'ロード', 10: 'ボタン', 12: '攻撃', 13: '防御', 14: '命中', 15: '回避', 16: '魔法', 17: '力', 18: '力', 19: '率',
         20: 'ステータス', 21: 'エレメント', 22: 'そうび', 23: 'アイテム', 24: 'ファイル', 25: 'つかう', 26: 'はいち', 27: 'ならびかえ',
         28: 'せいとん', 29: 'オート', 30: '実行', 31: '決定', 32: 'ボ', 33: 'タ', 34: 'ン', 36: 'カタカナ', 37: 'ひらがな', 38: '英数字',
         39: '初期化', 40: '買う', 41: '売る', 42: '鍛造', 43: '分解', 44: '下取り', 45: '武器', 46: '防具', 47: 'アクセサリー',
         191: '先天属性', 195: 'スタミナ回復力', 196: 'カスタマイズ', 197: '上下', 199: '毒', 200: '風邪', 201: '方向キー',
         202: '左右:回転', 203: 'ねんざ', 204: 'やけど', 205: 'マニュアル', 208: '腕力', 209: '耐久', 210: '力', 211: '力',
         212: '正確さ', 213: '身軽', 214: 'さ', 215: '抗魔', 216: '魔'}
    return {ks[i]: s for i, s in N.items()}


# 번역(묶음 원문 → 한글).  ⚠임시 — 하스피 판정 대상
KO = {
 'セーブ': '세이브', 'ロード': '로드', 'ボタン': '버튼', 'ボ': '버', 'タン': '튼',
 '攻撃': '공격', '攻撃力': '공격력', '防御力': '방어력', '命中率': '명중률', '回避率': '회피율',
 '魔法': '마법', '魔法攻撃': '마법공격', '魔法防御': '마법방어',
 'ステータス': '스테이터스', 'エレメント': '엘리먼트', 'そうび': '장비', 'アイテム': '아이템', 'カスタマイズ': '커스터마이즈', 'ファイル': '파일',
 'つかう': '사용', 'はいち': '배치', 'ならびかえ': '순서변경', 'せいとん': '정돈', 'オート': '오토', '実行': '실행', 'オート実行': '오토실행', '決定': '결정',
 'カタカナ': '한글1', 'ひらがな': '한글2', '英数字': '영숫자', '初期化': '초기화',     # 이름 입력 탭(임시 — 입력판 설계 때 확정)
 '買う': '구입', '売る': '판매', '鍛造': '단조', '分解': '분해', '下取り': '보상', '武器': '무기', '防具': '방어구', 'アクセサリー': '액세서리',
 '先天属性': '선천속성', 'スタミナ回復力': '스태미나회복력', '上下': '상하', '方向キー': '방향키', '左右:回転': '좌우:회전',
 '毒': '독', '風邪': '감기', 'ねんざ': '염좌', 'やけど': '화상', 'マニュアル': '매뉴얼',
 '腕力': '완력', '耐久力': '내구력', '正確さ': '정확도', '身軽さ': '민첩성', '身軽': '민첩성', 'さ': '', '抗魔': '항마', '魔力': '마력',
}
# 메뉴 화면마다 실행 중 /maru 101행 u64~79(VRAM 784~787,200)에 CLUT 이 올라온다(스테이트 9개 전부, 2026-11-16 «내구력 찌꺼기»·«아이템 가로줄» 원인)
RUNTIME_OVERWRITE = [(12, 101, 102, 64, 80)]            # (tpage, 행0, 행1, 열0, 열1) — 스테이트 9개에서 실측한 바뀐 화소 그대로
SKIP = set()                                            # (이름 입력 탭도 2026-11-16 하스피 지시로 포함)


def phrases(b42):
    """→ [(스프라이트 번호, [조각 색인…], 원문, x, y, 폭, 높이)]"""
    RN = rect_names()
    bo, sz, T = sprtab.tables(b42)['/main']
    out = []
    for i, s in enumerate(T['spr']):
        if not s: continue
        js = []
        for k, p in enumerate(s['pieces']):
            key = (p['tp'], p['u'], p['v'], p['w'], p['h'])
            if key in RN: js.append((p['y'], p['x'], k, RN[key], p))
        js.sort(key=lambda t: (t[1], t[0]))            # 왼쪽부터 — 높이 다른 조각(オート|実行)은 y 가 1~2 어긋남
        groups = []
        for it in js:
            g = next((g for g in groups if abs(it[0] - g[-1][0]) <= 2 and -2 <= it[1] - (g[-1][1] + g[-1][4]['w']) <= 4), None)
            if g: g.append(it)
            else: groups.append([it])
        for g in groups:
            x = g[0][1]; y = min(t[0] for t in g); w = g[-1][1] + g[-1][4]['w'] - x; h = max(t[4]['h'] for t in g)
            out.append((i + 1, [t[2] for t in g], ''.join(t[3] for t in g), x, y, w, h))
    return out, T, bo, sz


BDF = {12: r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11-Bold.bdf', 10: r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri9.bdf'}
_bd = {}
def bdf(size):
    """→ ({코드: (w,h,xo,yo,rows,dw)}, ascent)"""
    if size in _bd: return _bd[size]
    import io
    G = {}; cur = None; asc = 0
    it = iter(io.open(BDF[size], encoding='utf-8', errors='replace'))
    for ln in it:
        if ln.startswith('FONT_ASCENT'): asc = int(ln.split()[1])
        elif ln.startswith('ENCODING'): cur = int(ln.split()[1])
        elif ln.startswith('DWIDTH'): dw = int(ln.split()[1])
        elif ln.startswith('BBX'): bb = tuple(map(int, ln.split()[1:]))
        elif ln.startswith('BITMAP'):
            w, h, xo, yo = bb; rows = []
            for _ in range(h):
                t = next(it).strip(); v = int(t, 16); nb = len(t) * 4
                rows.append([(v >> (nb - 1 - x)) & 1 for x in range(w)])
            G[cur] = (w, h, xo, yo, rows, dw)
    _bd[size] = (G, asc); return _bd[size]


def render(text, size):
    """갈무리 BDF 화소 그대로(보간 없음) → (색인 배열 15/0, 잉크 위, 잉크 아래)
    ※ 2026-11-16 나눔 12px 안티앨리어싱은 «민첩성»의 첩이 뭉개져(하스피 실기 지적) 비트맵으로 바꿈
    size 'n12' = 메뉴 굵은 글꼴 그대로 좌우만 좁힘(작은 칸 — 선천속성, 하스피 «폰트는 같게 하고 좌우만 좁히면»)"""
    if size == 'n12':                                  # 같은 글꼴(갈무리11 Bold)을 «좌우만 좁힘» — 글자마다 겹치는(같은) 세로줄 하나씩 빼고 1px 띄움
        G, asc = bdf(12); cols = []
        for c in text:
            w, h, xo, yo, rows, dw = G[ord(c)]
            g = np.zeros((asc + 6, w), np.uint8)
            for yy in range(h):
                for xx in range(w):
                    if rows[yy][xx]: g[asc - yo - h + yy + 2, xx] = 15
            same = [k for k in range(1, w) if (g[:, k] == g[:, k - 1]).all() and g[:, k].any()]
            k = min(same, key=lambda k: abs(k - w / 2)) if same else int(np.argmin(g.astype(int).sum(0)))
            g = np.delete(g, k, axis=1)
            cols.append(g); cols.append(np.zeros((asc + 6, 1), np.uint8))
        q = np.concatenate(cols[:-1], 1); ys = np.nonzero(q.any(1))[0]
        return q, ys.min() - 2, ys.max() - 2
    G, asc = bdf(size)
    H = asc + 6; W = sum(G[ord(c)][5] for c in text) + 4
    a = np.zeros((H, W), np.uint8); x = 0
    for c in text:
        w, h, xo, yo, rows, dw = G[ord(c)]
        y0 = asc - yo - h
        for yy in range(h):
            for xx in range(w):
                if rows[yy][xx]: a[y0 + yy + 2, x + xo + xx] = 15
        x += dw
    ys, xs = np.nonzero(a)
    return a[:, xs.min():xs.max() + 1], ys.min() - 2, ys.max() - 2


_fc = {}
def render_aa(text, size):
    """→ (h, w) 색인 0~15. 줄 높이 = size+1, 왼쪽·위 빈 화소 없이"""
    from PIL import Image, ImageDraw, ImageFont
    f = _fc.setdefault(size, ImageFont.truetype(FONT, size))
    im = Image.new('L', (size * len(text) * 2 + 8, size * 2 + 8), 0); d = ImageDraw.Draw(im)
    d.text((2, 2), text, font=f, fill=255)
    a = np.asarray(im).astype(np.float32) / 255.0
    a = np.clip(a * 1.15, 0, 1)                      # 살짝 진하게(원본은 획 안이 꽉 찬 15)
    q = np.rint(a * 15).astype(np.uint8)
    ys, xs = np.nonzero(q)
    return q[:, xs.min():xs.max() + 1], ys.min() - 2, ys.max() - 2      # 세로는 공통 기준선 유지하려고 호출측에서 자름


SMALL = {'上下', '方向キー', '左右:回転', '先天属性', 'スタミナ回復力'}
BOLD_SMALL = {'先天属性', 'スタミナ回復力'}                                # 2026-11-16 하스피 «메인 메뉴 선천속성 혼자 튄다» — 옆 굵은 라벨과 맞춤
def size_of(jp, h):
    if jp in BOLD_SMALL: return 'n12'
    return 10 if (jp in SMALL or h <= 10) else 12


def word_images(items):
    """items = {(한글, 크기)} → {(한글, 크기): 색인 배열}. 같은 크기는 같은 세로 범위(공통 기준선)로 자름"""
    raw = {k: render(k[0], k[1]) for k in items}
    out = {}
    for size in sorted({k[1] for k in items}, key=str):
        ks = [k for k in items if k[1] == size]
        top = min(raw[k][1] for k in ks); bot = max(raw[k][2] for k in ks)
        for k in ks: out[k] = raw[k][0][top + 2:bot + 3]
    return out


def load_idx(b41, name):
    bo, sz = drp.find(b41, name); t = find_tims(b41[bo:bo + sz])[0]
    d = np.frombuffer(t['data'], np.uint8).reshape(t['ih'], -1)
    idx = np.zeros((t['ih'], t['iw'] * 4), np.uint8); idx[:, 0::2] = d & 15; idx[:, 1::2] = d >> 4
    return bo, sz, t, idx


def build(b41, b42, log=print):
    ph, T, tbo, tsz = phrases(b42)
    RN = rect_names()
    atl = {tp: load_idx(b41, ATL[tp][0]) for tp in ATL}
    v0 = {tp: ATL[tp][3] % 256 for tp in ATL}
    # 지울 조각·남길 조각
    drop = {}                                           # 스프라이트 → {조각 색인}
    todo = []
    for no, ks, jp, x, y, w, h in ph:
        if jp in SKIP: continue
        if jp not in KO: raise SystemExit('⛔ 번역 없는 메뉴 낱말 ' + jp)
        drop.setdefault(no, set()).update(ks); todo.append((no, ks, jp, x, y, w, h))
    free = {tp: np.zeros(atl[tp][3].shape, bool) for tp in ATL}
    prot = {tp: np.zeros(atl[tp][3].shape, bool) for tp in ATL}
    for i, s in enumerate(T['spr']):
        if not s: continue
        for k, p in enumerate(s['pieces']):
            if p['tp'] not in ATL: continue      # ★CLUT 무관 — 강조(주황) 등 다른 CLUT 조각도 같은 화소를 읽는다(2026-11-16 «아이템» 줄 깨짐)
            H = atl[p['tp']][3].shape[0]
            a0 = max(p['v'] - v0[p['tp']], 0); a1 = min(p['v'] - v0[p['tp']] + p['h'], H)
            if a1 <= a0: continue                        # 이 아틀라스 밖(같은 tpage 의 다른 그림)
            r = (slice(a0, a1), slice(p['u'], p['u'] + p['w']))
            (free if k in drop.get(i + 1, ()) else prot)[p['tp']][r] = True
    for tp in ATL:
        # 빈자리 = 남는 조각이 하나도 안 읽는 화소 전부(지울 일본어 + 어떤 표도 안 가리키는 죽은 그림·빈 화소).
        # 죽은 그림 근거: 디스크 1 전 drp 표·조각 기록 + 메뉴 스테이트 9화면 그리기 명령에서 참조 0(docs/그림글자_목록.md)
        free[tp] = ~prot[tp]
    for tp, r0, r1, c0, c1 in RUNTIME_OVERWRITE:
        free[tp][r0:r1, c0:c1] = False                   # 실행 중 다른 자료(CLUT)가 덮는 자리 — 낱말 금지
    for tp in ATL:
        free[tp][:, 255:] = False                        # ★u+w 가 256 이 되면 그리기에서 u 끝값(8비트)이 0 으로 감겨 한 줄 전체가 뭉개져 찍힘
                                                         #   (2026-11-16 선천속성 u216+40·파일 u234+22 깨짐) → 마지막 열 금지
    for tp in ATL:
        atl[tp][3][free[tp]] = 0                         # 일본어·죽은 그림 지움(남는 조각이 읽는 화소는 그대로)
    # 낱말 그림 → 빈자리에 깔기
    words = {(KO[jp], size_of(jp, h)) for no, ks, jp, x, y, w, h in todo if KO[jp]}
    imgs = word_images(words); place = {}
    for key in sorted(words, key=lambda k: (-imgs[k].shape[1], k)):     # 같은 폭은 글자순 — 실행마다 배치가 같게
        im = imgs[key]; hh, ww = im.shape; done = False
        best = None                                     # 띠 위에 붙이고(선반 채우기) 왼쪽부터 — 띠 높이 낭비가 가장 적은 자리
        for tp in (12, 13):
            f = free[tp]; H, W = f.shape
            for v in range(0, H - hh + 1):
                for u in range(0, W - ww + 1):
                    if not f[v, u]: continue
                    edge = (v == 0 or not f[v - 1, u]) and (u == 0 or not f[v, u - 1])
                    if f[v:v + hh, u:u + ww].all():
                        bh = 0
                        while v + bh < H and f[v + bh, u]: bh += 1
                        cost = (0 if edge else 1, bh - hh, tp, v, u)     # 띠 모서리 우선, 안 되면 아무 빈자리
                        if best is None or cost < best[0]: best = (cost, tp, u, v)
        if best:
            _, tp, u, v = best; f = free[tp]
            atl[tp][3][v:v + hh, u:u + ww] = im
            f[v:v + hh, u:u + ww] = False                       # 원본도 낱말끼리 틈 없이 붙어 있음(セーブ|ロード)
            place[key] = (tp, u, v + v0[tp], ww, hh); done = True
        if not done: raise SystemExit('⛔ 아틀라스 자리 부족: %s' % (key,))
    log('메뉴 낱말 %d종 배치 · 남은 빈 화소 %s' % (len(place), {tp: int(free[tp].sum()) for tp in ATL}))
    # 표
    sprs = []; over = []
    for i, s in enumerate(T['spr']):
        if not s: sprs.append(None); continue
        ps = [dict(p) for p in s['pieces']]; rep = {}
        for no, ks, jp, x, y, w, h in todo:
            if no != i + 1: continue
            if KO[jp]:
                tp, u, v, ww, hh = place[(KO[jp], size_of(jp, h))]
                fl = ps[min(ks)]['fl'] | (0x10 if any(ps[k]['fl'] & 0x10 for k in ks) else 0)
                rep[min(ks)] = dict(x=x, y=y + (h - hh) // 2, u=u, v=v, clut=ATL[tp][1], w=ww, h=hh, tp=tp, fl=fl)
                if ww > w: over.append((i + 1, jp, KO[jp], w, ww))
            for k in ks:
                if k not in rep: rep[k] = None
        out = [rep.get(k, p) for k, p in enumerate(ps)]
        newps = [p for p in out if p is not None]
        if ps[-1]['fl'] & 0x10 and not newps[-1]['fl'] & 0x10:      # 원본 마지막 조각의 끝 표시(0x10)를 새 마지막 조각에 유지
            newps[-1] = dict(newps[-1], fl=newps[-1]['fl'] | 0x10)
        sprs.append(dict(unk=s['unk'], pieces=newps))
    new42 = drp.rebuild(b42, {'/main': sprtab.write(T, sprs)})
    repl = {}
    for tp in ATL:
        bo, sz, t, idx = atl[tp]
        packed = (idx[:, 0::2] | (idx[:, 1::2] << 4)).astype(np.uint8).tobytes()
        body = bytearray(b41[bo:bo + sz]); doff = t['end'] - len(t['data']); body[doff:doff + len(packed)] = packed
        repl[ATL[tp][0]] = bytes(body)
    new41 = drp.rebuild(b41, repl)
    assert len(new41) == len(drp.rebuild(b41, {}))
    return new41, new42, over


if __name__ == '__main__':
    from ccget import get_exact
    b41 = get_exact('1', 41); b42 = get_exact('1', 42)
    ph, T, bo, sz = phrases(b42)
    cnt = collections.Counter((p[2], p[5], p[6]) for p in ph)
    if sys.argv[1:] == ['phrases']:
        for (jp, w, h), n in sorted(cnt.items()):
            print('%-12s %-10s 폭 %3d 높이 %2d ×%d' % (jp, KO.get(jp, '(뺌)' if jp in SKIP else '⛔없음'), w, h, n))
        print(len(cnt), '종')
    if sys.argv[1:2] == ['preview']:
        from PIL import Image
        vram = sprtab.vram_from_tims(b41); vram = sprtab.vram_from_tims(b42, vram)
        RN = rect_names(); inv = {}
        out = 'work/g02/preview_01'; os.makedirs(out, exist_ok=True)
        rows = []
        seen = set()
        for no, ks, jp, x, y, w, h in ph:
            if jp in seen or jp in SKIP: continue
            seen.add(jp)
            s = T['spr'][no - 1]; ps = [dict(s['pieces'][k]) for k in ks]
            o = sprtab.render(vram, dict(pieces=ps), pad=0)
            small = h <= 12 and jp in ('先天属性', 'スタミナ回復力', '上下', '方向キー', '左右:回転')
            size = 10 if small else 12
            q, y0, y1 = render(KO[jp], size)
            q = q[2:2 + size + 2]
            k = np.zeros(q.shape + (3,), np.uint8); g = (q.astype(np.uint16) * 255 // 15).astype(np.uint8)
            k[:] = 48; m = q > 0; k[m] = np.stack([g, g, g], -1)[m] * 0 + np.stack([g, g, g], -1)[m]
            rows.append((jp, o, k, w, q.shape[1]))
        H = sum(max(r[1].shape[0], r[2].shape[0]) + 4 for r in rows) + 8
        S = np.zeros((H, 220, 3), np.uint8); S[:] = (16, 16, 64); y = 4
        for jp, o, k, w, kw in rows:
            S[y:y + o.shape[0], 4:4 + o.shape[1]] = o
            S[y:y + k.shape[0], 110:110 + k.shape[1]] = k
            if kw > w: S[y:y + 2, 200:210] = (255, 0, 0)          # 원문 폭 넘침 표시
            y += max(o.shape[0], k.shape[0]) + 4
        for sc in (1, 3):
            Image.fromarray(S).resize((220 * sc, H * sc), Image.NEAREST).save(os.path.join(out, '메뉴글자_원본대한글_%d배.png' % sc))
        print(len(rows), '→', out, ' 폭 넘침:', [(jp, w, kw) for jp, o, k, w, kw in rows if kw > w])
    if sys.argv[1:2] == ['build']:
        from PIL import Image, ImageDraw
        n41, n42, over = build(b41, b42)
        print('파일 42', len(b42), '→', len(n42), '· 원문 폭 넘는 낱말', sorted(set(o[1:] for o in over)))
        open('work/g02/1_0041_ko.bin', 'wb').write(n41); open('work/g02/1_0042_ko.bin', 'wb').write(n42)
        v0 = sprtab.vram_from_tims(b41); v0 = sprtab.vram_from_tims(b42, v0)
        v1 = sprtab.vram_from_tims(n41); v1 = sprtab.vram_from_tims(n42, v1)
        T0 = sprtab.tables(b42)['/main'][2]; T1 = sprtab.tables(n42)['/main'][2]
        ph, _, _, _ = phrases(b42); nos = sorted({p[0] for p in ph if p[2] not in SKIP})
        out = 'work/g02/preview_02'; os.makedirs(out, exist_ok=True)
        pages = []; cur = []; hh = 0
        for no in nos:
            a = sprtab.render(v0, T0['spr'][no - 1], pad=1); c = sprtab.render(v1, T1['spr'][no - 1], pad=1)
            h = max(a.shape[0], c.shape[0]) + 14
            if hh + h > 900 and cur: pages.append(cur); cur = []; hh = 0
            cur.append((no, a, c)); hh += h
        if cur: pages.append(cur)
        for pi, pg in enumerate(pages):
            W = max(max(a.shape[1], c.shape[1]) for _, a, c in pg) * 2 + 30
            H = sum(max(a.shape[0], c.shape[0]) + 14 for _, a, c in pg)
            S = Image.new('RGB', (W, H), (16, 16, 64)); d = ImageDraw.Draw(S); y = 0
            for no, a, c in pg:
                d.text((2, y), '#%d' % no, fill=(255, 255, 0))
                S.paste(Image.fromarray(a), (4, y + 11)); S.paste(Image.fromarray(c), (W // 2 + 10, y + 11))
                y += max(a.shape[0], c.shape[0]) + 14
            S.resize((W * 2, H * 2), Image.NEAREST).save(os.path.join(out, '메뉴_빌드되읽기_원본대한글_%02d.png' % pi))
        for tp in ATL:
            bo, sz, t, idx = load_idx(n41, ATL[tp][0])
            g = (idx.astype(np.uint16) * 17).astype(np.uint8)
            Image.fromarray(g).resize((idx.shape[1] * 3, idx.shape[0] * 3), Image.NEAREST).save(os.path.join(out, '아틀라스%s_3배.png' % ATL[tp][0].replace('/', '_')))
        print(len(pages), '쪽 →', out)
