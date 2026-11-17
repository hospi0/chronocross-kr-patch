"""크로노 크로스 한글판 전체 빌더 (2026-11-17~)
  python tools/build_full.py [--disc 1] [--dry] [--check]
    --check : 번역 검사만(토큰·인코딩·창 크기·제자리 예산) → work/build/_검사.tsv, 위반 있으면 종료 1
    --dry   : 검사 + 파일 생성까지, 디스크 이미지는 안 씀

입력
  my files/tsv/cc_talk·cc_debug·cc_misc·cc_slot_*.tsv (KO 칸) + work/text/master.json(위치·원문 바이트·창)
  번역 없는 항목 = 원문 바이트 그대로(단 1바이트 한글 칸 0x76~0xC5 가 가나 자리를 덮으므로 원문 가나는 깨져 보임 — 번역 진행 중 정상)
  임시(번역이 들어오면 자동으로 빠짐): 맵 434 대사 PoC·메모리 카드 문구(build_poc), 이름·라벨(work/g04/names_ko.tsv)
쓰는 곳
  talk/debug → 맵 파일 구간 8(sszl 대사 블록, 레코드 = 오프셋·창 w·h·px) · btl → 2667 / 2646 구간 5 / 10 구간 3 / 보스 파일 구간 1(R8 블록)
  exe·slot → 실행 파일 문자열 표(묶음 1 이름·2~22 말투 칸 …) · item → 46/48/218 u16 표 · sjis → 38/40/42/226 제자리(원문 바이트 길이까지)
  prof → 101~151 구간 0(SJIS, ⏎ = CRLF) · 그림·글꼴·코드 수정 = build_g04test 와 같은 단계
규칙(쓰는 순간 강제): 원문 제어 토큰 multiset 같음(⏎ 제외) · 인코딩 가능 · 창 ≤ 원본 최대(32칸·13줄) · 대사 블록 ≤ 64KB · 맵 파일 ≤ 원본 최대 311,840 B
"""
import os, sys, re, json, glob, struct, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
import krenc, kromhook, rebuild, sszl, ccmsg, g04build, namebuild
import build_poc as P
from ccget import get_exact

TSV = os.path.join(ROOT, 'my files', 'tsv')
WIN_MAX = (32, 13)
MAP_MAX = 311840
TOK = re.compile(r'\{[^}]*\}')
JUNK_BTL = {2247, 2252, 2298, 2300, 2302, 2313}
# SJIS 한 줄을 두 문자열로 나눠 찍는 곳(첫 칸 = 바이트÷2 칸을 원문이 꽉 채움, 둘째 칸이 바로 이어짐): (첫 id, 둘째 id, 첫 칸 칸수)
SJIS_CONT = [('S00052', 'S00053', 8), ('S00078', 'S00079', 12), ('S00080', 'S00081', 12), ('S00082', 'S00083', 12), ('S00085', 'S00086', 12),
             ('S00092', 'S00093', 12), ('S00094', 'S00095', 12), ('S00096', 'S00097', 12), ('S00098', 'S00099', 12), ('S00172', 'S00173', 8)]   # 구간 1 이 R8 블록이 아님(추출 오검출 B00074~B00078) — 2026-11-17 검사


# ── 입력 ────────────────────────────────────────────────────────────────────
def load_ko():
    ko = {}
    for p in sorted(glob.glob(os.path.join(TSV, 'cc_*.tsv'))):
        if os.path.basename(p).startswith('cc_movie'): continue
        for l in open(p, encoding='utf-8-sig').read().splitlines()[1:]:
            f = l.split('\t')
            if len(f) >= 6 and f[5].strip(' \t\r\n'): ko[f[0]] = f[5]     # 전각 공백만 있는 칸 = 의도한 빈칸(SJIS 이어지는 둘째 칸)
    return ko


def load_temp_names():
    """임시 이름·라벨(work/g04/names_ko.tsv) — TSV 에 번역이 들어오면 그쪽이 이김"""
    names = {}; labels = {}; lev = iter('abcdefg')
    for ln in open(os.path.join(ROOT, 'work', 'g04', 'names_ko.tsv'), encoding='utf8'):
        if ln.startswith('#') or not ln.strip(): continue
        bnd, k, jp, ko = ln.rstrip('\n').split('\t')
        if bnd == 'L':
            if k == 'levu': k = 'levu_' + next(lev)
            labels[k] = ko.replace('-( %)', '').replace('Ｇ', '')
        else: names[(int(bnd), int(k))] = ko
    labels['paus'] = '진동 기능'
    return names, labels


def tokens(s):
    """원문과 같아야 하는 제어 토큰. 뺌: {12:XX} 말투 칸(한국어 칸 뜻이 달라 자리·개수가 바뀜 — slot_check 가 틀 검사),
    {G:XXX} 글꼴 표 밖 원문 글자(번역하면 사라짐), {04:00} 한 글자씩 찍기 0 멈춤(글자 수 따라 개수가 바뀜) — 2026-11-17"""
    return collections.Counter(t for t in TOK.findall(s) if not (t.startswith('{12:') or t.startswith('{G:') or t == '{04:00}'))


# ── 블록 쓰기 ───────────────────────────────────────────────────────────────
def r8_rewrite(blk, tr, codec, sub, err, tag):
    """R8 레코드 블록(u16×4 표: 오프셋·w·h·px) 다시 짜기. tr = {레코드: KO}. 번역 레코드 = 새 바이트 + 원문 끝(0 이후) 꼬리 그대로"""
    T = struct.unpack_from('<H', blk, 0)[0]
    recs = [list(struct.unpack_from('<4H', blk, i * 8)) for i in range(T // 8)]
    segs = []
    for ri, (o, w, h, px) in enumerate(recs):
        end = recs[ri + 1][0] if ri + 1 < len(recs) else len(blk)
        seg = blk[o:end]
        if ri in tr:
            # 꼬리 = 원문 종결 0 부터 끝까지. 원문에 0 이 없으면(보스 블록 — 레코드가 0 없이 이어짐) 덧붙이지 않음(2026-11-17)
            try:
                _, e = ccmsg.parse(seg + b'\0', 0); tail = seg[e - 1:] if e - 1 < len(seg) else b''
            except Exception: tail = b'\0'
            # 전투 쪽 글 찍기는 반각 공백도 12px(전투 결과 화면 실측 2026-11-17 — 8px 로 재면 줄 끝 글자가 잘림 «회복 안 함»→«회복 안»)
            nb = codec.encode(tr[ri]); w2, h2, px2 = P.window(codec, tr[ri].replace(' ', '　'), sub)
            if w2 > WIN_MAX[0] or h2 > WIN_MAX[1]: err.append((tag, ri, '창 %d칸×%d줄 > %d×%d' % (w2, h2) + WIN_MAX, tr[ri][:30]))
            # 전투 결과 화면(10 구간 3)은 문장을 원문 바이트 길이만큼만 찍음(2026-11-17 실기 «회복 안 함»→«회복 안»)
            if tag == '10s3' and len(nb + tail) > len(seg):
                err.append((tag, ri, '전투 결과 문장 %d B > 원문 %d B(넘는 글자 잘림)' % (len(nb + tail), len(seg)), tr[ri][:30]))
            segs.append((nb + tail, w2, h2, px2))
        else: segs.append((seg, w, h, px))
    body = bytearray(); tbl = bytearray()
    for seg, w, h, px in segs:
        tbl += struct.pack('<4H', T + len(body), w, h, px); body += seg
    out = bytes(tbl + body)
    if len(out) > 0xFFFF: err.append((tag, '-', '블록 %d B > 64KB' % len(out), ''))
    return out


def map_rewrite(fb, codec, tr, sub, err, tag):
    """맵 구간 8(sszl 대사 블록) — 번역 안 한 레코드는 원본 바이트 그대로, 번역 레코드는 새 바이트 + 원문 0 이후 꼬리(예 «00 01»)
    (build_poc.map_rewrite 는 꼬리를 버림 — 2026-11-17 발견)"""
    n, offs, secs = sec_split(fb)
    s8 = secs[8]; w3 = struct.unpack_from('<I', s8, 8)[0]; d = sszl.decode(s8)
    recs = ccmsg.block_offsets(d)
    out = []
    for ri, (o, w, h, px) in enumerate(recs[:-1]):
        end = recs[ri + 1][0]; seg = d[o:end]
        if ri in tr:
            _, e = ccmsg.parse(d[:end] + b'\0', o); tail = d[e - 1:end] if e - 1 < end else b'\0'
            w, h, px = P.window(codec, tr[ri], sub)
            if w > WIN_MAX[0] or h > WIN_MAX[1]: err.append((tag, ri, '창 %d칸×%d줄 > %d×%d' % ((w, h) + WIN_MAX), tr[ri][:30]))
            seg = codec.encode(tr[ri]) + tail
        out.append((seg, w, h, px))
    last = recs[-1]
    T = 8 * (len(out) + 1); body = bytearray(); tbl = bytearray()
    for seg, w, h, px in out:
        tbl += struct.pack('<4H', T + len(body), w, h, px); body += seg
    tbl += struct.pack('<4H', T + len(body), *last[1:]); body += d[last[0]:]
    blk = bytes(tbl + body)
    if len(blk) > 0xFFFF: err.append((tag, '-', '대사 블록 %d B > 64KB' % len(blk), '')); return fb
    if blk == d: return fb
    z = sszl.encode(blk, w3); assert sszl.decode(z) == blk
    while len(z) % 4: z += b'\0'
    secs[8] = z
    return sec_join(fb, secs)


def sec_split(b):
    n = struct.unpack_from('<I', b, 0)[0]; offs = list(struct.unpack_from('<%dI' % (n + 1), b, 4))
    return n, offs, [b[offs[i]:offs[i + 1]] for i in range(n)]


def sec_join(b, secs):
    n, offs, _ = sec_split(b)
    out = bytearray(b[:offs[0]]); new = []
    for s in secs: new.append(len(out)); out += s
    new.append(len(out)); struct.pack_into('<%dI' % (n + 1), out, 4, *new)
    return bytes(out)


def sec_replace(b, i, fn):
    """구간 i 를 fn(풀린 바이트) 결과로. 원래 sszl 이면 다시 sszl(같은 word3)"""
    n, offs, secs = sec_split(b)
    s = secs[i]
    if s[:4] == b'sszl':
        w3 = struct.unpack_from('<I', s, 8)[0]; d = sszl.decode(s); nd = fn(d)
        if nd == d: return b
        z = sszl.encode(nd, w3); assert sszl.decode(z) == nd
        while len(z) % 4: z += b'\0'
        secs[i] = z
    else:
        nd = fn(s)
        if nd == s: return b
        nd = bytes(nd)
        while len(nd) % 4: nd += b'\0'
        secs[i] = nd
    return sec_join(b, secs)


def u16tab_rewrite(b, tr, codec):
    """46/48/218: u16 오프셋 표 + 00 종결 문자열. tr = {번호: KO}"""
    T = struct.unpack_from('<H', b, 0)[0]; offs = list(struct.unpack_from('<%dH' % (T // 2), b, 0))
    uniq = sorted(set(offs)); new = {}; body = bytearray()
    for k, o in enumerate(uniq):
        end = uniq[k + 1] if k + 1 < len(uniq) else len(b)
        seg = b[o:end]
        idx = [si for si, x in enumerate(offs) if x == o]
        ko = next((tr[si] for si in idx if si in tr), None)
        if ko is not None:
            z = seg.find(b'\0'); tail = seg[z:] if z >= 0 else b'\0'
            seg = codec.encode(ko) + tail
        new[o] = T + len(body); body += seg
    out = bytearray(struct.pack('<%dH' % len(offs), *[new[o] for o in offs])) + body
    if len(out) > 0xFFFF: raise SystemExit('⛔ u16 표 64KB 초과')
    return bytes(out)


def sjis_enc(codec, s):
    # ★메뉴 SJIS 글자 찍기(파일 40·226 …)는 ASCII 중 공백·숫자 말고는 «건너뛴다»(찍지 않음) → 반각 부호·영문이 사라짐
    #   (2026-11-17 대장간 «자, 하나 완성!» → «자하나 완성»). 반각 부호·영문은 대사 글꼴 칸(한국식 부호 그림)으로 훅 코드,
    #   글꼴에 없으면 전각 SJIS. printf 형식(%s·%d)만 ASCII 그대로.
    out = bytearray(); k = 0
    while k < len(s):
        ch = s[k]
        if ch == '%' and s[k + 1:k + 2] in ('s', 'd'): out += s[k:k + 2].encode(); k += 2; continue
        if ch == '⏎': out += b'\r\n'
        elif ch == ' ' or ch.isdigit() and ord(ch) < 0x80: out += ch.encode()
        elif ch in codec.slot: out += kromhook.kr_code(codec.slot[ch])
        elif ord(ch) < 0x80 and ch in codec.rev: out += kromhook.kr_code(codec.rev[ch])
        elif ord(ch) < 0x80: out += chr(ord(ch) + 0xFEE0).encode('cp932')
        else: out += ch.encode('cp932')
        k += 1
    return bytes(out)


# ── 본체 ────────────────────────────────────────────────────────────────────
def main():
    disc = sys.argv[sys.argv.index('--disc') + 1] if '--disc' in sys.argv else '1'
    # 디스크 2: 맵 밖 대상 파일 187개(0·6·10·11·38·40~48·101~151·218~233·2049~2051·2538~2543·2646·2667·보스) = 디스크 1 과
    # 같은 번호·같은 바이트(2026-11-17 md5 전수) → 같은 단계 그대로. 맵만 «2:파일#레코드» 위치로. MAP_MAX = 디스크 2 1781 번 크기
    if disc not in ('1', '2'): raise SystemExit('--disc 1|2')
    M = json.load(open(os.path.join(ROOT, 'work', 'text', 'master.json'), encoding='utf8'))
    byid = {it['id']: it for it in M}
    ko = load_ko()
    err = []
    # 1) 검사(쓰는 순간): 토큰·KO=JP
    use = {}
    for i, k in ko.items():
        it = byid.get(i)
        if it is None: err.append((i, '-', 'master.json 에 없는 id', k[:30])); continue
        if k == it['jp']: continue                                  # 원문 그대로 = 원문 바이트
        if any(re.match(r'btl:(\d+)#', l) and int(re.match(r'btl:(\d+)#', l).group(1)) in JUNK_BTL for l in it['locs']):
            err.append((i, it['locs'][0], '가짜 항목(R8 블록 아닌 파일을 대사로 잘못 읽음) — 번역 금지', k[:30])); continue
        if re.fullmatch(r'い+', it['jp']) and it['kind'] != 'slot':
            err.append((i, it['locs'][0], '표 끝 표지(いい…) — 번역 금지', k[:30])); continue
        if it['kind'] != 'slot':
            a = tokens(it['jp']); b = tokens(k)
            if a != b: err.append((i, it['locs'][0], '제어 토큰 다름 원문%s 번역%s' % (dict(a - b), dict(b - a)), k[:30]))
        use[i] = k
    # SJIS 이어지는 두 칸: 둘째 칸은 «첫 칸 칸수» 자리부터 찍힘 → 첫 칸이 덜 차면 가운데가 벌어짐(«파일을 선택해 … 주세요», 2026-11-17 실기)
    for a, b, k in SJIS_CONT:
        if a in use and b in use:
            ka = krenc.normalize(use[a]); kb = krenc.normalize(use[b])
            if len(ka) != k and kb.strip('　 '): err.append((a, byid[a]['locs'][0], 'SJIS 이어지는 칸: 첫 칸 %d칸이어야 함(지금 %d칸) — 둘째 칸이 이어 붙음' % (k, len(ka)), ka))
    # 버튼 이름 {1B:XX} = «○버튼»·«L1버튼» 등(받침 ㄴ) — 뒤 조사는 받침형, 앞뒤 «버튼» 중복 금지(2026-11-17 실기 «□버튼 로»)
    for i, k in use.items():
        for m in re.finditer(r'\{1B:..\}(\s*)(를|로|가|는|와|버튼)(?![가-힣])', k):
            err.append((i, byid[i]['locs'][0], '버튼 이름 뒤 «%s%s» — 받침 있는 조사(을·으로·이·은·과)·«버튼» 중복 금지' % m.groups(), k[:30]))
    # 주인공 이름 {08:00}/{08:8X}(바꿀 수 있음)·호칭 칸 {12:15}(31명 = 이름 그대로) 뒤 받침 타는 조사 금지(2026-11-17 하스피 — 문장으로 피함:
    #   «{08:00},» «{08:00} 본인이라고» «이름이 {08:00}인» «{08:00}하고» «{08:00}의» 등)
    for i, k in use.items():
        for m in re.finditer(r'\{(?:08:(?:00|8[0-9A-F])|12:15)\}(은|는|이|가|을|를|과|와|으로|로|라는|라고|이라|라|란|여|냐|다|나|야|로서)(?![가-힣])', k):
            err.append((i, byid[i]['locs'][0], '주인공 이름·호칭 뒤 받침 타는 조사 «%s»(이름에 따라 틀림)' % m.group(1), k[:30]))
    # 장비 설명(파일 48): SJIS 로 바꿔 찍음 — 반각 공백은 «20 20» 두 칸으로 벌어짐 → 전각 공백만, 한 줄 10칸(원문 최대)
    for i, k in use.items():
        if byid[i]['locs'][0].startswith('item:48-'):
            kk = krenc.normalize(k)
            if ' ' in kk or len(kk) > 10: err.append((i, byid[i]['locs'][0], '장비 설명: 반각 공백 금지·10칸 이하(지금 %d칸)' % len(kk), kk))
    # 기술·엘리먼트 설명(실행 파일 묶음 26): 설명 창 한 줄 = 원문 최대 120px(10칸), 공백도 12px 로 찍힘(2026-11-17 실기)
    for i, k in use.items():
        if byid[i]['locs'][0].startswith('exe:26-'):
            for ln in re.sub(r'\{[^}]*\}', '', krenc.normalize(k)).split('⏎'):
                px = sum(12 if (c == ' ' or not (c.isascii() and c.isprintable())) else 8 for c in ln)
                if px > 120: err.append((i, byid[i]['locs'][0], '기술 설명 줄 %dpx > 120px(10칸)' % px, ln))
    # 2) 이름·라벨: TSV 우선, 없으면 임시
    tnames, labels = load_temp_names()
    names = {}
    for i, k in use.items():
        it = byid[i]
        for l in it['locs']:
            m = re.match(r'exe:(1|25)-(\d+)$', l)
            if m: names[(int(m.group(1)), int(m.group(2)))] = k
    exe0 = get_exact(disc, 0)
    import exetext
    base = exetext.BASE - 0x80010000 + 0x800
    G = {gi: (g0, so) for gi, g0, g1, so in exetext.groups(exe0)}
    noff = struct.unpack_from('<I', exe0, base)[0]; goffs = struct.unpack_from('<%dI' % (noff + 1), exe0, base + 4)
    def raw(gi, si):
        g0, so = G[gi]; nxt = g0 + so[si + 1] if si + 1 < len(so) else base + goffs[gi + 1]
        return bytes(exe0[g0 + so[si]:nxt]).rstrip(b'\0')
    byraw = {raw(*k): v for k, v in tnames.items()}
    ntemp = 0
    for gi in (1, 25):
        for si in range(len(G[gi][1]) - 1):
            if (gi, si) in names: continue
            r = raw(gi, si)
            if r in byraw: names[(gi, si)] = byraw[r]; ntemp += 1
            elif any(c >= 0x76 for c in r): err.append(('exe:%d-%d' % (gi, si), '-', '이름 번역 없음(소형 글꼴에서 안 보임)', r.hex()))
    # 3) 코덱
    texts = list(use.values()) + list(names.values()) + list(P.KO_SJIS.values()) + list(P.KO_MSG.values())
    small = list(names.values()) + g04build.SCOPE + namebuild.SYL
    for i, k in list(use.items()):
        if byid[i]['kind'] in ('sjis', 'prof'): texts.append(k)
    codec = krenc.Codec(texts + g04build.SCOPE + namebuild.SYL, small=small)
    json.dump(codec.slot, open(os.path.join(ROOT, 'work', 'build', '_codec_slot.json'), 'w', encoding='utf8'), ensure_ascii=False)  # 화면 판독용
    one = sum(1 for v in codec.slot.values() if v < 0xA6)
    print('번역 항목 %d · 이름 %d(임시 %d) · 음절 %d(1바이트 %d) · 소형 %d' % (len(use), len(names), ntemp, len(codec.slot), one, len(codec.small)))
    for i, k in list(use.items()):
        try: codec.encode(k) if byid[i]['kind'] not in ('sjis', 'prof') else sjis_enc(codec, krenc.normalize(k))
        except (KeyError, UnicodeEncodeError, ValueError) as e:
            err.append((i, byid[i]['locs'][0], '인코딩 불가 %s' % e, k[:30])); del use[i]
    # 화면 경로 검사기(tools/screen_audit.py)용: 실제로 쓰일 바이트
    enc_dump = {}
    for i, k in use.items():
        kd = byid[i]['kind']
        enc_dump[i] = dict(kind=kd, loc=byid[i]['locs'][0], ko=k,
                           b=(sjis_enc(codec, krenc.normalize(k)) if kd in ('sjis', 'prof') else codec.encode(k)).hex())
    json.dump(enc_dump, open(os.path.join(ROOT, 'work', 'build', '_enc_dump.json'), 'w', encoding='utf8'), ensure_ascii=False)
    # 치환 폭: {08:XX} = 이름, {12:XX} = 동료 전원 중 최대, {18:XX}/{15:XX} = 동료 이름 최대
    nm = {si: v for (gi, si), v in names.items() if gi == 1}
    sub = {'{08:%02X}' % si: P.name_px(codec, v) for si, v in nm.items()}
    member_px = max(P.name_px(codec, nm[k]) for k in range(0, 0x2C) if k in nm)
    slotv = collections.defaultdict(list)
    for i, k in use.items():
        it = byid[i]
        if it['kind'] == 'slot':
            gi, si = map(int, it['locs'][0][4:].split('-'))
            if 1 <= si < 0x31: slotv['{12:%02X}' % (gi - 1)].append(k)
    def px_of(s):
        t = 0
        for tok in re.findall(r'\{[^}]*\}|.', krenc.normalize(s)):
            if tok.startswith('{'): t += sub.get(tok, 0)
            elif tok == ' ' or (tok in codec.rev and codec.rev[tok] < 0x55): t += 8
            else: t += 12
        return t
    for c, vs in slotv.items(): sub[c] = max(px_of(v) for v in vs)
    for c in range(0x100):
        sub.setdefault('{18:%02X}' % c, member_px); sub.setdefault('{15:%02X}' % c, member_px)

    # 4) 위치별로 나누기
    maps = collections.defaultdict(dict); btl = collections.defaultdict(dict); exe_enc = {}
    items = collections.defaultdict(dict); sj = []; prof = {}
    for i, k in use.items():
        it = byid[i]
        for l in it['locs']:
            m = re.match(r'(\d):(\d+)#(\d+)$', l)
            if m:
                if m.group(1) == disc: maps[int(m.group(2))][int(m.group(3))] = k
                continue
            m = re.match(r'btl:(\w+)#(\d+)$', l)
            if m: btl[m.group(1)][int(m.group(2))] = k; continue
            m = re.match(r'exe:(\d+)-(\d+)$', l)
            if m: exe_enc[(int(m.group(1)), int(m.group(2)))] = k; continue
            m = re.match(r'item:(\d+)-(\d+)$', l)
            if m: items[int(m.group(1))][int(m.group(2))] = k; continue
            m = re.match(r'sjis:(\d+)@(0x[0-9a-f]+)$', l)
            if m and int(m.group(1)) == 38 and 0x3260 <= int(m.group(2), 16) < 0x34C4:
                print('  ※ %s 는 이름 입력판 글자줄(namebuild 소유) — 번역 무시' % i); continue
            if m: sj.append((int(m.group(1)), int(m.group(2), 16), len(bytes.fromhex(it['raw'])), k, i)); continue
            m = re.match(r'prof:(\d+)$', l)
            if m: prof[int(m.group(1))] = k; continue
            err.append((i, l, '모르는 위치', k[:30]))
    # 임시 PoC(번역이 들어오면 빠짐)
    if P.MAP not in maps: maps[P.MAP] = dict(P.KO_MSG); print('임시: 맵 %d 대사 PoC' % P.MAP)
    sjtemp = [(f, o, 28, t, 'PoC') for (f, o), t in P.KO_SJIS.items() if not any(x[0] == f and x[1] == o for x in sj)]

    # 5) 쓰기
    repl = {}
    exe = codec.patch_font(exe0)
    enc = {}
    for k, v in list(names.items()) + [(k, v) for k, v in exe_enc.items() if k[0] not in (1, 25)]:
        try: enc[k] = codec.encode(v)
        except Exception as e: err.append(('exe:%d-%d' % k, '-', '인코딩 불가 %s' % e, v[:30]))
    exe = P.exe_rewrite(exe, codec, enc)
    exe = kromhook.patch(exe)
    import kofixes
    exe = kofixes.patch(exe, get_exact('ko' + disc, 0))
    repl[0] = exe
    repl.update(P.sjis_files(codec))                                 # 38/40/226 칸→SJIS 변환표 (+PoC 메모리 카드 문구)
    open(os.path.join(ROOT, 'work', 'build', '_conv40.bin'), 'wb').write(repl[40][0x21046 - 0xAA:0x21046 + 0x1000])   # screen_audit 용 변환표
    sj_written = []
    for f, o, n, t, tag in sj + [(f, o, n, t, tag) for f, o, n, t, tag in sjtemp]:
        b = bytearray(repl.get(f) or get_exact(disc, f))
        if tag == 'PoC': continue                                     # sjis_files 가 이미 씀
        tt = krenc.normalize(t)
        if f == 42 and 0x6b60 <= o <= 0x6f50:
            # 저장 목록 장 제목: 16바이트씩 끊어 찍음 → 반각(1 B)이 섞이면 2바이트 글자가 경계에서 갈라짐(«부는»→«부 ,尾», 2026-11-17 실기) → 전각만
            tt = tt.translate(str.maketrans({' ': '　', '!': '！', ',': '，', '?': '？', '.': '．', ':': '：', '(': '（', ')': '）'}))
            tt = ''.join(chr(ord(ch) + 0xFEE0) if ch.isascii() and ch.isalnum() else ch for ch in tt)
        nb = sjis_enc(codec, tt)
        if len(nb) > n: err.append((tag, 'sjis:%d@%#x' % (f, o), '제자리 예산 %d B 초과(%d B)' % (n, len(nb)), t[:30])); continue
        if f == 42 and 0x6b60 <= o <= 0x6f50 and len(nb) % 2:
            err.append((tag, 'sjis:%d@%#x' % (f, o), '장 제목에 1바이트 글자(16바이트 조각 경계에서 갈라짐)', t[:30])); continue
        # 원문이 남는 칸을 전각 공백(81 40)으로 채운 문자열은 같은 칸 수까지 전각 공백으로 — 0 으로 채우면 메모리 카드 화면에서
        # 빈 칸 자리에 쓰레기 글자 스프라이트가 그려짐(2026-11-17 실기 노이즈, 스테이트 GPU 명령 16×16 글자 4개)
        orig = get_exact(disc, f)[o:o + n]
        pad = b''
        if orig.rstrip(b'\0').endswith(b'\x81\x40'):
            cells = len(krenc.normalize(t))
            pad = b'\x81\x40' * max(0, min(n // 2 - cells, (n - len(nb)) // 2))
        b[o:o + n] = nb + pad + bytes(n - len(nb) - len(pad)); repl[f] = bytes(b); sj_written.append((f, o, nb, t, tag))
    repl[38] = namebuild.build(repl[38], codec)
    for fi, tr in sorted(maps.items()):
        fb = get_exact(disc, fi)
        nb = map_rewrite(fb, codec, tr, sub, err, 'map%d' % fi)
        if len(nb) > MAP_MAX: err.append(('map', fi, '맵 파일 %d B > %d' % (len(nb), MAP_MAX), ''))
        repl[fi] = nb
    for tag, tr in btl.items():
        if tag == '2667':
            repl[2667] = r8_rewrite(get_exact(disc, 2667), tr, codec, sub, err, tag)
        elif tag == '2646s5':
            repl[2646] = sec_replace(get_exact(disc, 2646), 5, lambda d: r8_rewrite(d, tr, codec, sub, err, tag))
        elif tag == '10s3':
            repl[10] = sec_replace(get_exact(disc, 10), 3, lambda d: r8_rewrite(d, tr, codec, sub, err, tag))
        else:
            fi = int(tag); repl[fi] = sec_replace(get_exact(disc, fi), 1, lambda d: r8_rewrite(d, tr, codec, sub, err, tag))
    for fi, tr in items.items():
        repl[fi] = u16tab_rewrite(get_exact(disc, fi), tr, codec)
    for fi, t in prof.items():
        def fp(d, t=t, fi=fi):
            # 구간 0 = SJIS 글 전체(0 종결 없음), 4 B 맞춤은 뒤에 'w'(0x77) 채움 — 원본 그대로 흉내
            # 원본 크기 안에만(적재 버퍼 미확인 — 2026-11-17 하스피 «줄여서 맞추면 될듯»)
            nb = sjis_enc(codec, krenc.normalize(t.rstrip('w')))
            nb += b'w' * (-len(nb) % 4)
            if len(nb) > len(d): err.append(('prof', fi, '프로필 %d B > 원본 %d B' % (len(nb), len(d)), t[:30]))
            for ln in krenc.normalize(t.rstrip('w')).split('⏎'):      # 프로필 상자 = 한 줄 10칸(공백·반각도 전각 한 칸으로 찍힘, 2026-11-17 실기)
                if len(ln) > 10: err.append(('prof', fi, '프로필 한 줄 %d칸 > 10칸' % len(ln), ln))
            return nb
        repl[fi] = sec_replace(get_exact(disc, fi), 0, fp)
    # 그림·글꼴·코드 수정 (build_g04test 와 같은 단계)
    for fi in (11, 2542):
        repl[fi] = g04build.build(get_exact(disc, fi), codec.small, labels, log=lambda *a: None)[0]
    for fi in (6, 2538):
        repl[fi] = g04build.patch_scope(repl.get(fi) or get_exact(disc, fi), codec.small)
    import g06build, g05build, g02build, g07build, g09build, g11build, g12build, menuvsync_fix
    repl[2049] = g06build.build(get_exact(disc, 2049))
    repl[2050] = g07build.build(g06build.build_2050(get_exact(disc, 2050)))
    repl[11] = g05build.build(repl[11]); repl[2542] = g05build.build(repl[2542])
    # ★42 는 SJIS 번역(30줄)을 먼저 썼으므로 그 위에 — 원본에서 다시 만들면 번역이 사라짐(저장 목록 «はじまりは…» 미번역, 2026-11-17 실기)
    repl[41], repl[42], _ = g02build.build(get_exact(disc, 41), repl.get(42) or get_exact(disc, 42))
    repl[224] = g09build.build(get_exact(disc, 224)); repl[233] = g09build.build(get_exact(disc, 233))
    repl[2051] = g11build.build(get_exact(disc, 2051))
    repl[2543] = g12build.build(get_exact(disc, 2543), log=lambda *a: None)
    repl[40] = menuvsync_fix.patch(repl.get(40) or get_exact(disc, 40))
    # 뒤 단계 덮어쓰기 검산: 써 넣은 SJIS 번역 바이트가 최종 파일에 그대로 있는지(묶음 다시 짜기로 자리는 옮겨도 됨)
    for f, o, nb, t, tag in sj_written:
        if nb and nb not in repl.get(f, b''): err.append((tag, 'sjis:%d@%#x' % (f, o), '뒤 단계가 SJIS 번역을 덮어씀', t[:30]))
    for fi in (11, 2542, 41, 42):
        o = len(get_exact(disc, fi))
        if len(repl[fi]) < o: repl[fi] += bytes(o - len(repl[fi]))
    import sprtab
    for fi in (11, 2542, 42, 2049, 2543):
        for pth, (bo, sz, tb) in sprtab.tables(repl[fi]).items():
            ox = (tb['tex'][0] % 64) * 4 if tb['flag'] else 0; oy = tb['tex'][1] % 256 if tb['flag'] else 0
            for ix, sp in enumerate(tb['spr']):
                for q in (sp or {}).get('pieces', []):
                    if q['w'] and (q['u'] + ox + q['w'] > 255 or q['v'] + oy + q['h'] > 256): err.append(('gfx', fi, 'u+w>255 %s #%d' % (pth, ix + 1), ''))
    # 6) 보고
    os.makedirs(os.path.join(ROOT, 'work', 'build'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'build', '_검사.tsv'), 'w', encoding='utf-8-sig') as f:
        f.write('항목\t위치\t문제\t번역 앞부분\n')
        for e in err: f.write('\t'.join(str(x) for x in e) + '\n')
    grow = [(fi, len(get_exact(disc, fi)), len(v)) for fi, v in sorted(repl.items()) if len(v) > len(get_exact(disc, fi))]
    known = {0, 11, 2542} | set(maps)          # 실행 파일 = 제자리 · 11/2542 = 힙(여유 확인됨) · 맵 = MAP_MAX 검사
    print('원본보다 커진 파일:', ', '.join('%d(+%d)%s' % (fi, n - o, '' if fi in known else '⚠적재 버퍼 확인 필요') for fi, o, n in grow) or '없음')
    print('바꿀 파일 %d개 · 맵 %d · 위반 %d → work/build/_검사.tsv' % (len(repl), len(maps), len(err)))
    for e in err[:15]: print('  ⛔', *e)
    if err: raise SystemExit(1)
    if '--check' in sys.argv or '--dry' in sys.argv: return repl
    dst = os.path.join(ROOT, 'work', 'build', 'full_d%s.bin' % disc)
    import ccget
    # 오프닝 동영상(디스크 1 파일 6054) 한글 프레임 — work/movie/op_ko_6054.raw (tools/op_insert.py 산출, 원본과 같은 섹터 수, 2026-11-16 하스피 «좋다»)
    raw = {}
    op = os.path.join(ROOT, 'work', 'movie', 'op_ko_6054.raw')
    if disc == '1':
        if not os.path.exists(op): raise SystemExit('⛔ 오프닝 동영상 없음: ' + op)
        # op_ko_6054.raw 는 ccget.spans 로 뽑아 디스크 끝 포스트갭 150섹터까지 포함(원본 그대로 확인) → 숨은 표 크기(27,050)만
        f0 = open(ccget.P[disc], 'rb'); ent0, n0 = rebuild.read_table(f0); f0.close()
        cnt = (ent0[6055] & 0x7FFFFF) - (ent0[6054] & 0x7FFFFF)
        raw[6054] = open(op, 'rb').read()[:cnt * 2352]; print('오프닝 동영상 삽입: 6054 (%d 섹터)' % cnt)
    rebuild.rebuild(ccget.P[disc], dst, repl=repl, raw_repl=raw)
    import rebuild_check
    B, f, ent, n = rebuild_check.files(dst)
    for k, v in repl.items(): assert B[k][:len(v)] == v, k
    for k, rr in raw.items():                                             # 동영상: 섹터 본문(헤더 뒤 2328 B)이 삽입본과 같은지
        e = ent[k] & 0x7FFFFF; f.seek(e * 2352); got = f.read(len(rr))
        assert all(got[j * 2352 + 16:(j + 1) * 2352] == rr[j * 2352 + 16:(j + 1) * 2352] for j in range(len(rr) // 2352)), ('동영상 삽입 불일치', k)
        print('동영상 %d 삽입 검산 OK' % k)
    print('검산 OK → %s' % dst)
    return repl


if __name__ == '__main__':
    main()
