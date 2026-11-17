"""받은 번역(my files/번역) → my files/tsv KO 칸 병합 (2026-11-17, 하스피 «추천대로 ㄱ»)

  python tools/trmerge.py          # 미리보기: work/merge/_바뀜.tsv (자동 수정 전후) · 검사 요약
  python tools/trmerge.py --write  # my files/tsv 의 KO 칸에 씀(cc_slot·cc_movie 는 안 건드림)

순서: 받은 KO → ①용어 통일(원문에 그 말이 있는 줄만, 뒤 조사 받침 맞춤) → ②{08:XX} 고정 이름 뒤 조사
      → ③파티 슬롯 이름 {15/18:XX} 뒤 «는» → «은(는)» → ④이어지는 줄 «　　» → «　»(원문에 두 칸 들여쓰기 없을 때)
      → ⑤손 수정 work/merge/override.tsv (id \t KO, 말투 칸 범용 대사 다시 쓰기 포함) 가 이김
"""
import os, sys, re, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import trload
ROOT = trload.ROOT
OUT = os.path.join(ROOT, 'work', 'merge')

# 원문 낱말 → (새 표기, [바꿀 옛 표기]) — 옛 표기는 «그 원문이 있는 줄»에서만 바꾼다
TERMS = [
    ('ヤマネコ', '야마네코', ['들고양이', '살쾡이', '스라소니', '삵']),
    ('蛇骨', '자코츠', ['사골', '자골', '자코쓰']),
    ('カーシュ', '카슈', ['카시', '카쉬']),
    ('パレポリ', '파레포리', ['파레폴리', '팔레포리', '팔레폴리']),
    ('ガッシュ', '가슈', ['가쉬']),
    ('ラディウス', '라디우스', ['래디우스']),
    ('イルランザー', '일란자', ['일란저']),
    ('ソルトン', '솔튼', ['솔톤']),
    ('コルチャ', '코르차', ['콜차']),
    ('グレン', '글렌', ['그렌']),
    ('レナ', '레나', ['리나']),
    ('ドク', '도크', ['독']),
    ('ファルガ', '팔가', ['파르가']),
    ('カブ夫', '카부오', ['카브오']),
    ('ジルベルト', '질베르토', ['질베르트']),
    ('ギャダラン', '갸다란', ['가달란']),
    ('ジャネス', '자네스', ['재니스']),
    ('ガルドーブ', '가르도브', ['갈도브']),
    ('ノッフ', '놋프', ['노프']),
    ('大佐', '대령', ['대좌']),
    ('ダメージ', '대미지', ['데미지']),
]
# 앞에 한글이 붙으면 안 되는 짧은 옛 표기(아카시아·중독 등과 겹침)
LEFT_GUARD = {'카시', '독', '삵', '리나', '노프', '사골', '자골'}

# 받침 따라 바뀌는 조사: (받침 있을 때, 없을 때) — 긴 것부터
PAIRS = [('이라고', '라고'), ('이라는', '라는'), ('이라면', '라면'), ('이라서', '라서'), ('이라', '라'), ('이란', '란'), ('이랑', '랑'),
         ('이에요', '예요'), ('이었', '였'), ('이야', '야'), ('이여', '여'), ('이다', '다'), ('이지', '지'), ('이나', '나'), ('이네', '네'),
         ('이군', '군'), ('이냐', '냐'), ('이니', '니'), ('이면', '면'), ('으로', '로'), ('은', '는'), ('을', '를'), ('과', '와'), ('이', '가'), ('아', '야')]


def jong(s):
    s = re.sub(r'\{[^}]*\}', '', s).rstrip()
    if not s: return None
    o = ord(s[-1]) - 0xAC00
    return o % 28 if 0 <= o < 11172 else None


def fix_josa(word, post):
    """word 뒤에 오는 글 post 의 첫 조사를 word 받침에 맞춘다 → 새 post"""
    j = jong(word)
    if j is None: return post
    m = re.match(r'[가-힣]+', post)
    if not m: return post
    run = m.group(0)
    cand = [(have, a, b) for a, b in PAIRS for have in (a, b) if run.startswith(have)]
    if not cand: return post
    have, a, b = max(cand, key=lambda t: len(t[0]))
    if len(have) == 1 and run not in (have, have + '도', have + '는', have + '의', have + '만'):
        return post                                               # «이…»·«가…» 가 낱말 시작일 수 있음 — 건드리지 않음
    if (a, b) == ('으로', '로'): want = '로' if j in (0, 8) else '으로'
    else: want = a if j else b
    return want + post[len(have):]


def apply_terms(jp, ko, log, tid):
    for jt, new, olds in TERMS:
        if jt not in jp: continue
        for old in olds:
            pat = (r'(?<![가-힣])' if old in LEFT_GUARD else '') + re.escape(old)
            pos = 0
            while True:
                m = re.compile(pat).search(ko, pos)
                if not m: break
                rest = ko[m.end():]
                if old == '독' and re.match(r'[가-힣]', rest[:1] or ' ') and not re.match(r'(은|는|이|가|을|를|과|와|의|에게|한테|도|만|님|씨|선생|로|으로|아|야|여)(?![가-힣])', rest):
                    pos = m.end(); continue                        # 독약·독침 등
                post = fix_josa(new, rest) if bool(jong(old)) != bool(jong(new)) else rest
                ko = ko[:m.start()] + new + post; pos = m.start() + len(new)
    return ko


def main():
    write = '--write' in sys.argv
    R = trload.rows(trload.SRC)
    names = {}
    for r in R.values():
        m = re.match(r'exe:1-(\d+)$', r['loc'].split(' ')[0])
        if m and r['ko'].strip(): names[int(m.group(1))] = r['ko']
    log = []; new = {}
    # 이름표부터 용어 통일
    for k, v in list(names.items()):
        for jt, nw, olds in TERMS:
            if v in olds: names[k] = nw
    for r in R.values():
        ko = r['ko']
        if not ko.strip() or r['kind'] == 'slot': continue
        o = ko
        ko = apply_terms(r['jp'], ko, log, r['id'])
        # ② {08:XX} 뒤 조사
        def r08(m):
            b = int(m.group(1), 16)
            nm = names.get(0, '세르주')[:b & 0x7F] if b & 0x80 else names.get(b)
            if not nm: return m.group(0)
            if '(' in m.group(2):
                # «이(가)» 꼴: 세르주(바꿀 수 있는 이름 0·애칭)는 그대로, 고정 이름은 받침대로 하나만
                pm = re.match(r'(은|이|을|과|으로|아|이야|이라|이여)\((는|가|를|와|로|야|라|여)\)', m.group(2))
                if b == 0 or b & 0x80 or not pm: return m.group(0)
                one = (pm.group(1) if jong(nm) else pm.group(2)) if pm.group(1) != '으로' else ('로' if jong(nm) in (0, 8) else '으로')
                return m.group(0)[:len(m.group(0)) - len(m.group(2))] + one + m.group(2)[pm.end():]
            return m.group(0)[:len(m.group(0)) - len(m.group(2))] + fix_josa(nm, m.group(2))
        ko = re.sub(r'\{08:([0-9A-F]{2})\}([가-힣(][가-힣()]*)', r08, ko)
        # ③ 파티 슬롯 이름 뒤 «는»·«은» 홀로 → «은(는)»
        ko = re.sub(r'(\{(?:15|18):[0-9A-F]{2}\})(은|는)(?![(가-힣])', r'\1은(는)', ko)
        # ④ 이어지는 줄 두 칸 들여쓰기
        if r['kind'] == 'talk':
            jl = re.split(r'⏎|\{02:01\}', r['jp'])
            if not any(re.match(r'(\{[^}]*\})*　　(?!　)', x) for x in jl):
                ko = re.sub(r'((?:⏎|\{02:01\})(?:\{[^}]*\})*)　　(?!　)', r'\1　', ko)
        # ⑤ 프로필: 원본 바이트 크기 안에(하스피 «줄여서 맞추면 될듯») — 항목 이름을 두 글자+：로 통일(줄 맞춤 유지, 줄마다 2 B 절약)
        if r['kind'] == 'prof':
            for a, b in (('출신지：', '출신：'), ('신장　：', '신장：'), ('체중　：', '체중：'), ('체격　：', '체격：'), ('주손　：', '주손：')):
                ko = ko.replace(a, b)
        if ko != o: log.append((r['id'], '자동', o, ko))
        new[r['id']] = ko
    # 이름표 줄 반영
    for r in R.values():
        m = re.match(r'exe:1-(\d+)$', r['loc'].split(' ')[0])
        if m and int(m.group(1)) in names and names[int(m.group(1))] != r['ko'] and r['ko'].strip():
            log.append((r['id'], '이름표', r['ko'], names[int(m.group(1))])); new[r['id']] = names[int(m.group(1))]
    # ⑥ 말투 칸 범용 대사 다시 쓰기(work/merge/slot_rewrite.tsv — 묶음번호 = slot_lines.json 순서, @XX = {12:XX}, {SP} = 줄마다 원래 화자 코드 차례대로)
    import json
    for sl, sr in ((os.path.join(OUT, 'slot_lines.json'), os.path.join(OUT, 'slot_rewrite.tsv')),
                   (os.path.join(OUT, 'slot_lines2.json'), os.path.join(OUT, 'slot_rewrite2.tsv'))):   # 2차 = 번역이 칸을 다 뺀 줄
      if os.path.exists(sl) and os.path.exists(sr):
          G = json.load(open(sl, encoding='utf8'))
          for l in open(sr, encoding='utf-8-sig').read().splitlines():
              if not l.strip() or l.startswith('#'): continue
              n, t = l.split('\t', 1); ids = G[int(n)][0]
              t = re.sub(r'@([0-9A-F]{2})', r'{12:\1}', t)
              for i in ids:
                  sp = iter(re.findall(r'\{(?:15|18):0[0-2]\}', R[i]['ko']))
                  k = re.sub(r'\{SP\}', lambda m: next(sp), t)
                  log.append((i, '말투', new.get(i, R[i]['ko']), k)); new[i] = k
    # ⑥-2 말투 칸 대명사·호칭(값 = 받침 없음) 뒤 조사 정리 — 모든 범용 대사
    for i, k in list(new.items()):
        if '{12:' not in k: continue
        o = k
        k = re.sub(r'\{12:0C\}(?:이\(가\)|이|가)(?![가-힣(])', '{12:12}', k)                # 일인칭 주격
        k = re.sub(r'\{12:0D\}(?:이\(가\)|이|가)(?![가-힣(])', '{12:11}', k)                # 이인칭 주격
        k = re.sub(r'(\{12:(?:0C|0D|0E|0F|10|15)\})(?:은\(는\)|은)(?![가-힣])', r'\1는', k)
        k = re.sub(r'(\{12:(?:0C|0D|0E|0F|10|15)\})(?:을\(를\)|을)(?![가-힣])', r'\1를', k)
        k = re.sub(r'(\{12:(?:0C|0D|0E|0F|10|15)\})(?:과\(와\)|과)(?![가-힣])', r'\1와', k)
        k = re.sub(r'(\{12:(?:0E|0F|10|15)\})(?:이\(가\)|이)(?![가-힣])', r'\1가', k)
        k = re.sub(r'(\{12:(?:0C|0D|0E|0F|10|15)\})으로(?![가-힣])', r'\1로', k)
        k = re.sub(r'\{12:14\},', '{12:14}', k)                                            # 혀차기 값이 «!» 로 끝남
        if k != o: log.append((i, '말투조사', o, k)); new[i] = k
    # ⑦ 손 수정
    ov = {}
    p = os.path.join(OUT, 'override.tsv')
    if os.path.exists(p):
        for l in open(p, encoding='utf-8-sig').read().splitlines():
            if not l.strip() or l.startswith('#'): continue
            i, k = l.split('\t', 1); ov[i] = k
    for i, k in ov.items():
        if i not in R: raise SystemExit('⛔ override 에 없는 id ' + i)
        log.append((i, '손', new.get(i, R[i]['ko']), k)); new[i] = k
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, '_바뀜.tsv'), 'w', encoding='utf-8-sig') as f:
        f.write('id\t종류\t전\t후\n')
        for e in log: f.write('\t'.join(e) + '\n')
    c = collections.Counter(e[1] for e in log)
    print('병합 대상 %d줄 · 바뀜 %s · 손 수정 %d → work/merge/_바뀜.tsv' % (len(new), dict(c), len(ov)))
    if not write: return new
    n = 0
    for p in sorted(glob.glob(os.path.join(trload.TSV, 'cc_*.tsv'))):
        b = os.path.basename(p)
        if b.startswith('cc_slot') or b.startswith('cc_movie'): continue
        raw = open(p, 'rb').read(); bom = raw.startswith(b'\xef\xbb\xbf')
        text = raw.decode('utf-8-sig'); nl = '\r\n' if '\r\n' in text else '\n'
        out = []
        for ln in text.split(nl):
            f = ln.split('\t')
            if len(f) >= 6 and f[0] in new and f[5] != new[f[0]]: f[5] = new[f[0]]; n += 1
            out.append('\t'.join(f))
        open(p, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + nl.join(out).encode('utf-8'))
    print('TSV 에 쓴 칸', n)
    return new


if __name__ == '__main__':
    main()
