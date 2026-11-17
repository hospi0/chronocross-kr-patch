"""크로노 크로스 원문 추출 (2026-11-16)
→ work/text/master.json (모든 위치·창 크기·원문 바이트) + my files/tsv/cc_NNN.tsv (18KB 단위, 번역용)

표기: 줄바꿈 = ⏎ (원문에 ／ 글자가 있어 쓸 수 없음), 제어 = {XX} / {XX:인자hex}, 표에 없는 칸 = {G:칸hex}
종류(kind):
  talk   맵 대사(맵 파일 구간 8, sszl) — 같은 바이트는 한 줄로 묶고 위치를 모두 기록
  btl    전투 메시지(2667)·보스전 대사(머리 02/10 파일 구간 1)
  exe    실행 파일 문자열 표(RAM 0x800600E0) 묶음별
  item   46 재료 이름·48 재료 설명·218 중요 아이템 설명 (u16 표)
  sjis   SJIS 메뉴(38·40·42·226) — BIOS 글꼴 경로(내장 예정)
  debug  디버그 메뉴로 보이는 맵 대사(따로 묶음, 번역 선택)
"""
import sys, os, json, struct, re, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
from ccget import spans, P
from ccfs import Disc
import ccmsg, ccdecode, sszl, exetext

def tok_text(toks):
    return ccdecode.text(toks).replace('\n', '⏎')

DEBUG_PAT = re.compile(r'まっぷ|じゃんぷ|DUMMY|dummy|ＤＵＭＭＹ|モード：|入力|デバッグ|ｎｏｗ　ｃｏｎｓｔｒｕｃｔｉｏｎ|すぺしゃる|各担当')

def field_items():
    rows = [l.split('\t') for l in open(os.path.join(ROOT, 'work', 'sszl_index.tsv'), encoding='utf8').read().splitlines()]
    want = sorted({(r[0], int(r[1])) for r in rows if len(r) > 4 and r[2] == '8' and int(r[3]) >= 12})
    out = collections.OrderedDict()
    for disc, fi in want:
        d = open(os.path.join(ROOT, 'work', 'fieldmsg', f'{disc}_{fi:04d}.bin'), 'rb').read()
        recs = ccmsg.block_offsets(d)
        for ri, rec in enumerate(recs[:-1]):
            o, w, h, px = rec
            end = recs[ri + 1][0]
            try:
                toks, e = ccmsg.parse(d[:end] + b'\0', o)
            except Exception:
                continue
            raw = bytes(d[o:min(e - 1, end)])
            if not any(t[0] == 'g' for t in toks):
                continue
            k = raw
            it = out.get(k)
            if not it:
                txt = tok_text(toks)
                it = out[k] = dict(kind='debug' if DEBUG_PAT.search(txt) else 'talk', jp=txt,
                                   raw=raw.hex(), locs=[], win=[])
            it['locs'].append(f'{disc}:{fi}#{ri}')
            it['win'].append([w, h, px])
    for it in out.values():          # 모든 맵에 공통으로 박힌 디버그 메뉴 묶음
        if len(it['locs']) >= 600: it['kind'] = 'debug'
    return list(out.values())

def exe_items():
    a = open(os.path.join(ROOT, 'work', 'files', '1_0000.bin'), 'rb').read()
    out = []
    G = exetext.groups(a)
    def gtext(gi, si):
        _, g0, _, so = G[gi]
        return tok_text(ccmsg.parse(a, g0 + so[si])[0])
    for gi, g0, g1, so in G:
        for si, s in enumerate(so):
            try:
                toks, e = ccmsg.parse(a, g0 + s)
            except Exception:
                continue
            if 2 <= gi <= 22:
                # 말투 칸: 묶음 gi = 칸 {12:gi-1}, 항목 si = 인물(묶음 1 의 si 번), si=0 은 칸 이름 — 빈 칸({1F})도 전부 싣는다
                title = gtext(gi, 0).replace('{0E:01}', '').replace('{0E:00}', '')
                who = '(칸 이름)' if si == 0 else gtext(1, si)
                out.append(dict(kind='slot', jp=tok_text(toks), raw=a[g0 + s:e - 1].hex(), locs=[f'exe:{gi}-{si}'], win=[],
                                note=f'{{12:{gi - 1:02X}}}{title}·{who}'))
                continue
            if not any(t[0] == 'g' and t[1] != 0x55 for t in toks):   # 전각 공백만인 빈칸 제외
                continue
            out.append(dict(kind='exe', jp=tok_text(toks), raw=a[g0 + s:e - 1].hex(), locs=[f'exe:{gi}-{si}'], win=[]))
    return out

def u16_items(fi, label):
    b = open(os.path.join(ROOT, 'work', 'files', f'1_{fi:04d}.bin'), 'rb').read()
    T = struct.unpack_from('<H', b, 0)[0]
    offs = struct.unpack_from('<%dH' % (T // 2), b, 0)
    out = []
    for si, o in enumerate(offs):
        try:
            toks, e = ccmsg.parse(b, o)
        except Exception:
            continue
        if not any(t[0] == 'g' and t[1] != 0x55 for t in toks):
            continue
        out.append(dict(kind='item', jp=tok_text(toks), raw=b[o:e - 1].hex(), locs=[f'{label}:{fi}-{si}'], win=[]))
    return out

def r8_block(b, label):
    """R8 레코드 표, 문자열 끝 = 다음 레코드 오프셋(전투 메시지는 00 종결이 아님)"""
    T = struct.unpack_from('<H', b, 0)[0]
    recs = [struct.unpack_from('<4H', b, i * 8) for i in range(T // 8)]
    out = []
    for ri, (o, w, h, px) in enumerate(recs):
        end = recs[ri + 1][0] if ri + 1 < len(recs) else len(b)
        seg = b[o:end]
        try:
            toks, e = ccmsg.parse(seg + b'\0', 0)   # 00 은 «코드 자리»에서만 끝 — {07:0000} 같은 인자 0 은 계속
            seg = seg[:e - 1]
        except Exception:
            continue
        if not any(t[0] == 'g' for t in toks):
            continue
        out.append(dict(kind='btl', jp=tok_text(toks), raw=seg.hex(), locs=[f'{label}#{ri}'], win=[[w, h, px]]))
    return out

def sec(b, i):
    n = struct.unpack_from('<I', b, 0)[0]; offs = struct.unpack_from('<%dI' % (n + 1), b, 4)
    s = b[offs[i]:offs[i + 1]]
    return sszl.decode(s) if s[:4] == b'sszl' else s

def merge(items):
    """같은 종류·같은 원문 바이트는 한 항목으로(위치 합침)"""
    out = collections.OrderedDict()
    for it in items:
        k = (it['kind'], it['raw'])
        if it['kind'] == 'slot':
            k = ('slot', it['locs'][0])        # 말투 칸은 인물마다 다른 번역 — 합치지 않음
        if k in out:
            out[k]['locs'] += it['locs']; out[k]['win'] += it['win']
        else: out[k] = it
    return list(out.values())

def battle_items():
    out = r8_block(open(os.path.join(ROOT, 'work', 'files', '1_2667.bin'), 'rb').read(), 'btl:2667')
    D = Disc(P['1']); sp = spans(D)
    def getf(fi):
        l, c = sp[fi]; return b''.join(D.sec(l + j) for j in range(c))
    out += r8_block(sec(getf(2646), 5), 'btl:2646s5')      # 2667 의 압축 사본(기존 패치는 이쪽을 고침)
    out += r8_block(sec(getf(10), 3), 'btl:10s3')          # 전투 후 결과 화면
    for fi in range(2100, 3300):
        l, c = sp[fi]
        if c == 0 or c > 16: continue
        b = b''.join(D.sec(l + j) for j in range(c))
        if b[:8] != bytes.fromhex('0200000010000000'): continue
        o1, o2 = struct.unpack_from('<II', b, 8)
        s = b[o1:o2]
        if len(s) < 16: continue
        try: out += r8_block(s, f'btl:{fi}')
        except Exception: pass
    return out

def sjis_items():
    common = set(json.load(open(os.path.join(ROOT, 'work', 'common_chars.json'), encoding='utf8')))
    out = []
    for fi in (38, 40, 42, 226):
        b = open(os.path.join(ROOT, 'work', 'files', f'1_{fi:04d}.bin'), 'rb').read()
        i = 0; n = len(b)
        while i < n - 1:
            if i and b[i - 1] != 0:
                i += 1; continue
            j = i; s = ''
            while j < n - 1:
                c = b[j]
                if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xef:
                    try:
                        s += b[j:j + 2].decode('cp932'); j += 2; continue
                    except UnicodeDecodeError:
                        break
                elif 0x20 <= c < 0x7f and s:
                    s += chr(c); j += 1; continue
                break
            wide = [ch for ch in s if ord(ch) > 0x7f]
            if j < n and b[j] == 0 and wide and sum(ch in common or ch in '　：／（）' for ch in wide) >= 0.9 * len(wide) \
                    and (len(wide) >= 2 or re.search(r'[ぁ-ヿ]', s)) and len(wide) >= 0.6 * len(s):
                out.append(dict(kind='sjis', jp=s, raw=b[i:j].hex(), locs=[f'sjis:{fi}@{i:#x}'], win=[]))
                i = j + 1
            else:
                i += 1
    # 외톨이 한 글자(코드·그림 속 우연한 바이트)는 버린다: 앞뒤 64B 안에 다른 문자열이 있어야 남김
    keep = []
    for k, it in enumerate(out):
        f, o = it['locs'][0][5:].split('@'); o = int(o, 16)
        if len([c for c in it['jp'] if ord(c) > 0x7f]) >= 2:
            keep.append(it); continue
        near = [x for x in out if x is not it and x['locs'][0].startswith(f'sjis:{f}@')
                and abs(int(x['locs'][0].split('@')[1], 16) - o) <= 64
                and len([c for c in x['jp'] if ord(c) > 0x7f]) >= 2]
        if near: keep.append(it)
    # 참조 기준 보충(2026-11-16 검산): 오버레이(적재 0x801D2800) 코드·데이터가 가리키는 SJIS 시작점
    import sjis_refcheck as RC
    MAPS = {38: (0x3ade, 0x4826), 40: (0x21046, 0x21d94), 226: (0xd662, 0xe3aa)}   # 칸→SJIS 변환표(번역 대상 아님)
    have = {it['locs'][0] for it in keep}
    keep = [it for it in keep if not (int(it['locs'][0][5:].split('@')[0]) in MAPS and
            MAPS[int(it['locs'][0][5:].split('@')[0])][0] <= int(it['locs'][0].split('@')[1], 16) < MAPS[int(it['locs'][0][5:].split('@')[0])][1])]
    for fi in (38, 40, 226):
        b = open(os.path.join(ROOT, 'work', 'files', f'1_{fi:04d}.bin'), 'rb').read()
        m0, m1 = MAPS[fi]
        for o in sorted(RC.refs(b)):
            if not RC.is_sjis_start(b, o) or m0 <= o < m1 or f'sjis:{fi}@{o:#x}' in have:
                continue
            if o >= 2 and RC.is_sjis_start(b, o - 2) and b[o - 1] >= 0x40:   # 앞이 SJIS 글자 = 문자열 중간(우연한 상수, 예 0x801F3000 버퍼)
                continue
            j = o; s = ''; ok = True
            while j < len(b) and b[j]:
                c = b[j]
                if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xef:
                    try: s += b[j:j + 2].decode('cp932'); j += 2; continue
                    except UnicodeDecodeError: ok = False; break
                if 0x20 <= c < 0x7f: s += chr(c); j += 1; continue
                ok = False; break
            if ok and s:
                keep.append(dict(kind='sjis', jp=s, raw=b[o:j].hex(), locs=[f'sjis:{fi}@{o:#x}'], win=[]))
    # 묶음 구간 보충: 추출 문자열이 모인 구간(간격 < 0x60) 안의 0 구분 조각 중 전각 1자 이상이면 모두 포함
    #   (표를 거쳐 참조되는 문자열 — エレメントの整列·傾斜角度·장 제목 등 — 이 직접 참조 검색에 안 걸림)
    for fi in (38, 40, 42, 226):
        b = open(os.path.join(ROOT, 'work', 'files', f'1_{fi:04d}.bin'), 'rb').read()
        hs = sorted(int(it['locs'][0].split('@')[1], 16) for it in keep if it['locs'][0].startswith(f'sjis:{fi}@'))
        if not hs: continue
        cl = [[hs[0], hs[0]]]
        for o in hs[1:]:
            if o - cl[-1][1] < 0x60: cl[-1][1] = o
            else: cl.append([o, o])
        got = set(hs)
        m0, m1 = MAPS.get(fi, (0, 0))
        for a, z in cl:
            i = a
            while i < min(z + 0x40, len(b)):
                if b[i] == 0: i += 1; continue
                j = i
                while j < len(b) and b[j]: j += 1
                try: s = b[i:j].decode('cp932')
                except UnicodeDecodeError: s = None
                if s and i not in got and not (m0 <= i < m1) and all(ord(c) >= 0x20 for c in s) \
                        and any(ord(c) > 0x7f and not ('｡' <= c <= 'ﾟ') for c in s):
                    keep.append(dict(kind='sjis', jp=s, raw=b[i:j].hex(), locs=[f'sjis:{fi}@{i:#x}'], win=[]))
                i = j
    keep.sort(key=lambda it: (int(it['locs'][0][5:].split('@')[0]), int(it['locs'][0].split('@')[1], 16)))
    return keep

def profile_items():
    """인물 프로필(파일 101~151 구간 0, SJIS, CRLF 줄바꿈) — 상태 화면"""
    D = Disc(P['1']); sp = spans(D); out = []
    for fi in range(101, 152):
        l, c = sp[fi]; b = b''.join(D.sec(l + j) for j in range(c))
        s0 = sec(b, 0); raw = s0.split(b'\0')[0]
        try: txt = raw.decode('cp932')
        except UnicodeDecodeError: continue
        if not txt.strip(): continue
        out.append(dict(kind='prof', jp=txt.replace(chr(13) + chr(10), chr(0x23CE)), raw=raw.hex(), locs=[f'prof:{fi}'], win=[]))
    return out


# 오프닝 동영상(파일 6054, 디스크1) 프레임에 박힌 시 — 2026-11-16 프레임 판독. 빌드는 영상 재인코딩(글자 지우고 한글 합성)
MOVIE_LINES = [
    ('op1-1', '359~630', 'はじまりは、何だったのだろう？'),
    ('op1-2', '359~630', '運命の歯車は、いつまわりだしたのか？'),
    ('op1-3', '359~630', '時の流れのはるかな底から'),
    ('op1-4', '359~630', 'その答えをひろいあげるのは、'),
    ('op1-5', '359~630', '今となっては不可能にちかい……'),
    ('op2-1', '676~958', 'だが、たしかにあの頃わたしたちは、'),
    ('op2-2', '676~958', 'おおくのものを愛し、'),
    ('op2-3', '676~958', 'おおくのものを憎み……'),
    ('op2-4', '676~958', '何かを傷つけ、'),
    ('op2-5', '676~958', '何かに傷つけられ……'),
    ('op2-6', '676~958', 'それでも、風のように駆けていた'),
    ('op2-7', '676~958', '青空に、笑い声を響かせながら……'),
]

def budget(it):
    if it['win']:
        w, h, px = it['win'][0]
        extra = '' if all(x == it['win'][0] for x in it['win']) else '(위치별 다름)'
        return f'{h}줄·{w}칸{extra}'
    if it['kind'] == 'sjis':
        return f'{len(bytes.fromhex(it["raw"]))}B'
    return f'{len(bytes.fromhex(it["raw"]))}B'

def write_split(stem, rows, limit=18 * 1024, outdir=None):
    head = 'id\t종류\t위치\t예산\tJP\tKO\n'
    files = []; cur = head
    for r in rows:
        line = '\t'.join(r) + '\n'
        if len((cur + line).encode('utf8')) > limit and cur != head:
            files.append(cur); cur = head
        cur += line
    if cur != head: files.append(cur)
    os.makedirs(outdir, exist_ok=True)
    for k, s in enumerate(files):
        open(os.path.join(outdir, f'{stem}_{k + 1:03d}.tsv'), 'w', encoding='utf8', newline='\n').write(s)
    return len(files)

def main():
    items = field_items()
    items += battle_items()
    items += exe_items()
    items += u16_items(46, 'item') + u16_items(48, 'item') + u16_items(218, 'item')
    items += sjis_items()
    items += profile_items()
    items = merge(items)
    pref = dict(slot='M', prof='R', talk='T', debug='D', btl='B', exe='E', item='I', sjis='S')
    cnt = collections.Counter()
    for it in items:
        cnt[it['kind']] += 1
        it['id'] = f'{pref[it["kind"]]}{cnt[it["kind"]]:05d}'
    os.makedirs(os.path.join(ROOT, 'work', 'text'), exist_ok=True)
    json.dump(items, open(os.path.join(ROOT, 'work', 'text', 'master.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=0)
    outdir = os.path.join(ROOT, 'my files', 'tsv')
    for p in (os.listdir(outdir) if os.path.isdir(outdir) else []):     # ⛔ KO 가 한 칸이라도 있으면 덮지 않는다(번역·말투 칸 날아감)
        if p.startswith('cc_') and p.endswith('.tsv'):
            for l in open(os.path.join(outdir, p), encoding='utf-8-sig').read().splitlines()[1:]:
                f = l.split('\t')
                if len(f) >= 6 and f[5].strip(): raise SystemExit(f'⛔ {p} 에 번역(KO)이 있어 TSV 를 다시 만들지 않음 — master.json 만 갱신됨')
    for p in (os.listdir(outdir) if os.path.isdir(outdir) else []):
        if p.startswith('cc_') and p.endswith('.tsv'): os.remove(os.path.join(outdir, p))
    def rows(kinds):
        return [[it['id'], it['kind'], it['locs'][0] + (f' 외{len(it["locs"]) - 1}' if len(it['locs']) > 1 else ''),
                 budget(it), it['jp'], ''] for it in items if it['kind'] in kinds]
    n1 = write_split('cc_talk', rows({'talk'}), outdir=outdir)
    n2 = write_split('cc_misc', rows({'btl', 'exe', 'item', 'sjis', 'prof'}), outdir=outdir)
    n3 = write_split('cc_debug', rows({'debug'}), outdir=outdir)
    slot_rows = [[it['id'], 'slot', it['locs'][0] + ' ' + it['note'], '', it['jp'], ''] for it in items if it['kind'] == 'slot']
    n4 = write_split('cc_slot', slot_rows, outdir=outdir)
    print('TSV slot', n4)
    mv = [[f'V{k + 1:05d}', 'movie', f'movie:6054 {lid} 프레임{fr}', '영상 화면 폭', jp, ''] for k, (lid, fr, jp) in enumerate(MOVIE_LINES)]
    print('TSV movie', write_split('cc_movie', mv, outdir=outdir))
    chars = collections.Counter()
    for it in items: chars[it['kind']] += len(re.sub(r'\{[^}]*\}|⏎', '', it['jp']))
    print('항목', dict(cnt)); print('글자', dict(chars)); print('TSV talk', n1, 'misc', n2, 'debug', n3)

if __name__ == '__main__':
    main()
