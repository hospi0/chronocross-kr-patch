"""말투 칸 안전장치 (docs/말투칸_설계안.md 4장) — 범용 대사 × 동료 전원 전수 렌더링 + 받침·조사·틀 검사

  python tools/slot_check.py            # my files/tsv 의 cc_slot·cc_talk·cc_misc(이름) KO 로 검사
  python tools/slot_check.py --demo     # 설계안 예시 값으로 동작 시험

→ work/slot_review/<번호>_<이름>.txt (화자별 읽기 파일) · work/slot_review/_검사.tsv (위반 목록) · 위반 있으면 종료 코드 1
"""
import os, sys, re, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
import krenc
OUT = os.path.join(ROOT, 'work', 'slot_review')
TSV = os.path.join(ROOT, 'my files', 'tsv')
MEMBERS = list(range(1, 0x2C))           # 동료(묶음 1 의 1~0x2B, 0x2C~0x30 은 ツマル 사본)
PRONOUN = {'0C', '0D', '0E', '0F', '10', '15'}          # 받침 없는 값 규칙
JOSA = {'은': 1, '는': 0, '을': 1, '를': 0, '과': 1, '와': 0, '이야': 1, '야': 0, '으로': 1, '로': 0, '이': 1, '가': 0}

def jong(ch):
    """받침 번호(0 = 없음), 한글 아니면 None"""
    o = ord(ch) - 0xAC00
    return o % 28 if 0 <= o < 11172 else None

def last_hangul(s):
    for ch in reversed(re.sub(r'\{[^}]*\}', '', s)):
        if jong(ch) is not None: return ch
        if ch.strip() and ch not in '.,!?…~-': return None
    return None

def read_tsv(pattern):
    rows = []
    for p in sorted(glob.glob(os.path.join(TSV, pattern))):
        for l in open(p, encoding='utf8').read().splitlines()[1:]:
            f = l.split('\t')
            if len(f) >= 6: rows.append(f)
    return rows

def load_real():
    slots = collections.defaultdict(dict)      # 칸코드 → {인물번호: 값}
    for f in read_tsv('cc_slot_*.tsv'):
        m = re.match(r'exe:(\d+)-(\d+)', f[2])
        if not m: continue
        gi, si = int(m.group(1)), int(m.group(2))
        if si and f[5].strip(): slots[f'{gi - 1:02X}'][si] = f[5]
    names = {}
    for f in read_tsv('cc_misc_*.tsv'):
        m = re.match(r'exe:1-(\d+)', f[2])
        if m and f[5].strip(): names[int(m.group(1))] = f[5]
    lines = [(f[0], f[4], f[5]) for f in read_tsv('cc_talk_*.tsv') if '{12:' in f[4] and f[5].strip()]
    return slots, names, lines

def load_demo():
    names = {0: '세르주', 1: '키드', 6: '리델', 0x0C: '포슈르', 0x10: '라디우스'}
    V = {'0C': ['나', '저', '포슈르', '이 몸'], '12': ['내가', '제가', '포슈르가', '이 몸이'], '15': ['세르주', '세르주 씨', '세르주 쒸', '세르주'],
         '02': ['거야', '거예요', '거예여', '걸세'], '08': ['야', '예요', '예여', '일세'], '01': ['이야', '이에요', '이에여', '일세'],
         '07': ['아', '아요', '아여', '은가'], '05': ['', '요', '여', ''], '0A': ['야', '저기요', '저기여', '이보게']}
    who = [1, 6, 0x0C, 0x10]
    slots = {k: {who[i]: v[i] for i in range(4)} for k, v in V.items()}
    lines = [('DEMO1', '', '{18:02}⏎「왜 그래,{12:15}? 멍하니 서서는.{02:01}이제부터가 진짜{12:08}. 정신 바짝 차리는 게 좋을 {12:02}.'),
             ('DEMO2', '', '{18:02}⏎「{12:0C}는 먼저 갈 {12:02}.⏎{12:0C}가 길을 열{12:02}.'),        # 일부러 틀림: 12:0C가 · 틀 위반
             ('DEMO3', '', '{18:02}⏎「사실{12:08}. 무섭지 않{12:07}?{12:0A}, 서둘러{12:05}!')]       # 일부러 틀림: 받침명사 뒤 12:08
    return slots, names, lines, who

def expand(text, who, slots, names):
    def sub(m):
        a, b = m.group(1), m.group(2)
        if a == '12': return slots.get(b, {}).get(who, '⟦빈칸 12:%s⟧' % b)
        if a in ('18', '15'): return names.get(who, '⟦이름%02X⟧' % who)
        if a == '08':
            k = int(b, 16)
            if k & 0x80: return names.get(0, '세르주')[:k & 0x7F]
            return names.get(k, '⟦이름%02X⟧' % k)
        if a == '02': return '\n▼\n'
        return ''
    t = re.sub(r'\{([0-9A-F]{2}):([0-9A-F]+)\}', sub, text)
    t = re.sub(r'\{[0-9A-F]{2}\}', '', t)
    return t.replace('⏎', '\n')

def check(slots, names, lines, members):
    errs = []
    # (1) 대명사·호칭 칸 값 받침
    for k in PRONOUN:
        for who, v in slots.get(k, {}).items():
            ch = last_hangul(v)
            if ch and jong(ch): errs.append(('값받침', f'12:{k}', names.get(who, who), v, '대명사·호칭 칸은 받침 없는 값'))
    for lid, jp, ko in lines:
        # (2) 틀 위반 (번역문 자체)
        for m in re.finditer(r'\{12:([0-9A-F]{2})\}', ko):
            k = m.group(1); pre = ko[:m.start()]
            prev = re.sub(r'\{[^}]*\}$', '', pre)[-1:] if pre else ''
            j = jong(prev) if prev else None
            if k == '01' and not j: errs.append(('틀', lid, f'12:01', pre[-6:], '받침 있는 명사 뒤에만'))
            if k == '08' and (j is None or j): errs.append(('틀', lid, f'12:08', pre[-6:], '받침 없는 명사 뒤에만'))
            if k in ('02', '04'):
                if not pre.endswith(' ') or jong(pre[-2:-1] or 'a') not in (4, 8):
                    errs.append(('틀', lid, f'12:{k}', pre[-6:], '«ㄹ/ㄴ 관형형 + 띄어쓰기» 뒤에만'))
            if k == '07' and not pre.endswith('않'): errs.append(('틀', lid, '12:07', pre[-6:], '«않» 뒤에만'))
            # (3) 칸 뒤 조사 — 인물별 값 받침
            post = ko[m.end():]
            for js, need in sorted(JOSA.items(), key=lambda t: -len(t[0])):
                if post.startswith(js) and (len(post) == len(js) or not ('가' <= post[len(js)] <= '힣')):
                    if k in ('0C', '0D') and js in ('이', '가'):
                        errs.append(('조사', lid, f'12:{k}{js}', '', '주격은 12:12(일인칭)·12:11(이인칭) 칸을 쓸 것'))
                        break
                    for who in members:
                        v = slots.get(k, {}).get(who)
                        if v is None: continue
                        ch = last_hangul(v)
                        if ch is None: continue
                        has = bool(jong(ch))
                        if js in ('으로', '로') and jong(ch) == 8: has = False
                        if has != bool(need): errs.append(('조사', lid, f'12:{k}{js}', f'{names.get(who, who)}={v}', '값 받침과 조사 불일치'))
                    break
    # (4) 펼친 결과 공백·부호
    reviews = collections.defaultdict(list)
    for lid, jp, ko in lines:
        for who in members:
            if not any(who in d for d in slots.values()): continue
            t = expand(ko, who, slots, names)
            reviews[who].append(f'[{lid}]\n{t}\n')
            tn = krenc.normalize(t)                                   # 빌더가 찍는 꼴(부호 뒤 공백 삭제 뒤)로 검사
            if re.search(r'(?<=\S)  (?=\S)', tn) or re.search(r' [,.!?…]', tn) or re.search(r'!,', tn):   # 전각 들여쓰기(선택지)는 제외 · 혀차기 값 «!» 뒤 쉼표
                errs.append(('공백', lid, names.get(who, who), t.replace('\n', '⏎')[:60], '빈칸 값 때문에 공백 겹침/부호 앞 공백'))
            if '⟦빈칸' in t:
                errs.append(('빈칸', lid, names.get(who, who), re.findall(r'⟦빈칸 [^⟧]*⟧', t)[0], '칸 값 없음'))
    return errs, reviews

def main():
    demo = '--demo' in sys.argv
    if demo:
        slots, names, lines, members = load_demo()
    else:
        slots, names, lines = load_real(); members = MEMBERS
    errs, reviews = check(slots, names, lines, members)
    os.makedirs(OUT, exist_ok=True)
    tag = '_demo' if demo else ''
    for who, rs in reviews.items():
        nm = names.get(who, f'{who:02X}')
        open(os.path.join(OUT, f'{who:02X}_{nm}{tag}.txt'), 'w', encoding='utf8').write('\n'.join(rs))
    with open(os.path.join(OUT, f'_검사{tag}.tsv'), 'w', encoding='utf8') as f:
        f.write('종류\t위치\t칸\t내용\t설명\n')
        for e in errs: f.write('\t'.join(map(str, e)) + '\n')
    print(f'범용 대사 {len(lines)} · 화자 {len(reviews)} · 위반 {len(errs)}')
    for e in errs[:30]: print('  ', *e)
    sys.exit(1 if errs else 0)

if __name__ == '__main__':
    main()
