"""G04(전투 소형 글꼴) 실기 시험 빌드 — PoC2 구성(대사 PoC·BIOS 내장 훅·메모리 카드 문구) + 이름 전부(임시 번역) + 파일 11/2542 한글판
→ work/build/g04_d1.bin   (원본 = D: 백업. 설치는 따로)
확인할 것: 늘린 osak 표 적재 · 2겹 아틀라스 CLUT 두 자리 · 전투 메뉴/이름/상태이상/포즈 띠
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
import krenc, kromhook, rebuild, g04build, build_poc as P
from ccget import get_exact


def load_names():
    names = {}; labels = {}; lev = iter('abcdefg')
    for ln in open(os.path.join(ROOT, 'work', 'g04', 'names_ko.tsv'), encoding='utf8'):
        if ln.startswith('#') or not ln.strip(): continue
        bnd, k, jp, ko = ln.rstrip('\n').split('\t')
        if bnd == 'L':
            if k == 'levu': k = 'levu_' + next(lev)
            labels[k] = ko.replace('-( %)', '').replace('Ｇ', '')
        else:
            names[(int(bnd), int(k))] = ko
    labels['paus'] = '진동 기능'
    return names, labels


def main():
    names, labels = load_names()
    if '--poc-names' in sys.argv:                     # 차분 시험: 이름은 PoC2 와 같은 4개만
        names = {(1, k): v for k, v in P.KO_NAMES.items()}
    texts = list(P.KO_MSG.values()) + list(names.values()) + list(P.KO_SJIS.values())
    import namebuild                                  # 이름 입력판 음절 170 — 이름이라 전투 소형 글꼴에도
    codec = krenc.Codec(texts + g04build.SCOPE + namebuild.SYL, small=list(names.values()) + g04build.SCOPE + namebuild.SYL)
    print('음절', len(codec.slot), '· 소형 글꼴', len(codec.small), '· 가장 뒤 이름 칸 0x%X' % max(codec.small.values()))
    exe = get_exact('1', 0)
    exe = codec.patch_font(exe)
    # 같은 이름이 여러 번호에 겹쳐 있다(적으로 나오는 동료·색 다른 적) → 원문 바이트가 같은 번호 전부에 적용
    import exetext, struct
    base = exetext.BASE - 0x80010000 + 0x800
    G = {gi: (g0, so) for gi, g0, g1, so in exetext.groups(exe)}
    noff = struct.unpack_from('<I', exe, base)[0]; goffs = struct.unpack_from('<%dI' % (noff + 1), exe, base + 4)
    def raw(gi, si):
        g0, so = G[gi]; nxt = g0 + so[si + 1] if si + 1 < len(so) else base + goffs[gi + 1]
        return bytes(exe[g0 + so[si]:nxt]).rstrip(b'\0')
    byraw = {}
    for (gi, si), ko in names.items(): byraw.setdefault(raw(gi, si), ko)
    left = []
    for gi in (1, 25):
        for si in range(len(G[gi][1]) - 1):
            r = raw(gi, si)
            if (gi, si) in names: continue
            if r in byraw and '--poc-names' not in sys.argv: names[(gi, si)] = byraw[r]
            elif any(c >= 0x76 for c in r): left.append((gi, si, r.hex()))
    print('이름 번호', len(names), '· 번역 없이 남은 이름', left)
    if left and '--poc-names' not in sys.argv: raise SystemExit('⛔ 번역 없는 이름이 있다(소형 글꼴에서 가나가 빠져 안 보임)')
    enc = {k: codec.encode(v) for k, v in names.items()}
    exe = P.exe_rewrite(exe, codec, enc)
    exe = kromhook.patch(exe)
    import kofixes                                    # 기존 한글판의 버그 수정 2건(카운터 음수·표 범위)
    exe = kofixes.patch(exe, get_exact('ko1', 0))
    repl = {0: exe}
    repl.update(P.sjis_files(codec))
    repl[38] = namebuild.build(repl[38], codec)       # 이름 입력판 글자줄·코드표
    nm = {k: names[(1, k)] for k in (0, 1, 0x14, 0x24)}
    sub = {'{08:00}': P.name_px(codec, nm[0]), '{08:01}': P.name_px(codec, nm[1]), '{08:14}': P.name_px(codec, nm[0x14]),
           '{18:02}': 72, '{12:15}': P.name_px(codec, nm[0])}
    fb = get_exact('1', P.MAP)
    newmap, nb, ob = P.map_rewrite(fb, codec, P.KO_MSG, sub)
    repl[P.MAP] = newmap
    for fi in (11, 2542):
        b = get_exact('1', fi)
        out, where = g04build.build(b, codec.small, labels, log=print)
        print('파일', fi, len(b), '→', len(out), 'B')
        repl[fi] = out
    for fi in (6, 2538):
        repl[fi] = g04build.patch_scope(get_exact('1', fi), codec.small)
    import g06build
    repl[2049] = g06build.build(get_exact('1', 2049)); repl[2050] = g06build.build_2050(get_exact('1', 2050))
    import g05build
    repl[11] = g05build.build(repl[11]); repl[2542] = g05build.build(repl[2542])
    import g02build
    repl[41], repl[42], over = g02build.build(get_exact('1', 41), get_exact('1', 42))
    if '--no-menu' in sys.argv:                       # 차분 시험: 메뉴 그림·표만 원본(2026-11-16 스테이터스 크래시)
        del repl[41], repl[42]
    if '--no-map' in sys.argv:                        # 차분 시험: 맵 434(대사 PoC)만 원본
        del repl[P.MAP]
    import g07build, g09build
    repl[2050] = g07build.build(repl[2050])
    repl[224] = g09build.build(get_exact('1', 224)); repl[233] = g09build.build(get_exact('1', 233))
    import g11build
    repl[2051] = g11build.build(get_exact('1', 2051))
    if '--no-2051' in sys.argv:                       # 차분 시험: 파티 교체 그림만 원본
        del repl[2051]
    import g12build                                   # 전투 설명서 그림(G12~14)
    repl[2543] = g12build.build(get_exact('1', 2543), log=print)
    import menuvsync_fix                              # 메뉴 화면 전환 작업의 필드 대기 무한 루프 상한(스테이터스 멈춤)
    repl[40] = menuvsync_fix.patch(repl[40])
    # 줄어든 drp 파일은 원래 크기까지 0 채움 — 섹터 수·뒤 파일 LBA 를 원본과 같게(차분 시험에서 변수 하나만 바뀌도록)
    for fi in (11, 2542, 41, 42):
        if fi in repl:
            o = len(get_exact('1', fi))
            if len(repl[fi]) < o: repl[fi] = repl[fi] + bytes(o - len(repl[fi]))
    # 검사: 스프라이트 조각 u+w·v+h 가 256 을 넘으면 그리기에서 8비트로 감겨 뭉개진다(원본 표엔 0건)
    import sprtab
    bad = []
    for fi in (11, 2542, 42, 2049, 2543):
        if fi not in repl: continue
        for pth, (bo, sz, tb) in sprtab.tables(repl[fi]).items():
            ox = (tb['tex'][0] % 64) * 4 if tb['flag'] else 0; oy = tb['tex'][1] % 256 if tb['flag'] else 0
            for i, sp in enumerate(tb['spr']):
                if not sp: continue
                for q in sp['pieces']:
                    if q['w'] and (q['u'] + ox + q['w'] > 255 or q['v'] + oy + q['h'] > 256): bad.append((fi, pth, i + 1, q['u'], q['w']))
    if bad: raise SystemExit('⛔ u+w>255 조각: %s' % bad[:10])
    if '--dry' in sys.argv: print('바꿀 파일', sorted(repl)); return
    dst = os.path.join(ROOT, 'work', 'build', 'g04_d1.bin')
    rebuild.rebuild(P.SRC, dst, repl=repl)
    import rebuild_check
    B, f, ent, n = rebuild_check.files(dst)
    for k, v in repl.items():
        assert B[k][:len(v)] == v, k
    print('검산 OK —', sorted(repl), '새 디스크에서 그대로 읽힘 →', dst)


if __name__ == '__main__':
    main()
