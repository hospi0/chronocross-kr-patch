"""괄호 조사(은(는)·을(를)·이(가)·와(과)·(으)로·(이)라…) 없애기 (2026-11-17 하스피 «조사 뺐다며»)
  고정 이름 {08:XX} = 받침대로 하나 · 세르주 {08:00}/{08:8X} = 받침 없는 쪽(세르주·하스피 기준) · 파티원 {15/18:XX} 주어 = 쉼표
  아이템 {19:XX} 뒤 = 동사 명사형(획득·발견·습득…) 또는 쉼표 · 글자 뒤 = 그 글자 받침대로"""
import re
import trmerge as TM

PAIRS = [('은', '는'), ('이', '가'), ('을', '를'), ('과', '와'), ('으로', '로'), ('이라', '라'), ('이다', '다'), ('이야', '야'), ('이여', '여'), ('아', '야')]
PAREN = re.compile(r'(은\(는\)|는\(은\)|이\(가\)|가\(이\)|을\(를\)|를\(을\)|과\(와\)|와\(과\)|\(으\)로|\(이\)라|\(이\)다|\(이\)야|\(이\)여|\(이\)란)')

def two(form):
    """괄호 꼴 → (받침형, 무받침형)"""
    f = form.replace('(', '').replace(')', '')
    m = {'은는': ('은', '는'), '는은': ('은', '는'), '이가': ('이', '가'), '가이': ('이', '가'), '을를': ('을', '를'), '를을': ('을', '를'),
         '과와': ('과', '와'), '와과': ('과', '와'), '으로': ('으로', '로'), '이라': ('이라', '라'), '이다': ('이다', '다'), '이야': ('이야', '야'), '이여': ('이여', '여'), '이란': ('이란', '란')}
    return m[f]

VERB = [(r'손에 넣었', '획득'), (r'얻었', '획득'), (r'발견했', '발견'), (r'찾았', '발견'), (r'받았', '받음'), (r'익혔', '습득'), (r'터득했', '습득'),
        (r'배웠', '습득'), (r'주웠', '주움'), (r'건넸', '건넴'), (r'설치했', '설치'), (r'떠올렸', '떠올림'), (r'돌려줬', '반환'), (r'땄', '땀')]

def fix(ko, names):
    def tok_name(tok):
        m = re.match(r'\{08:([0-9A-F]{2})\}', tok)
        if not m: return None
        b = int(m.group(1), 16)
        if b == 0 or b & 0x80: return ''          # 세르주(바꿀 수 있는 이름) — 받침 없는 쪽
        return names.get(b)
    out = ko
    # 아이템 뒤 + 동사 → 명사형
    for vp, noun in VERB:
        out = re.sub(r'(\{19:..\}(?:\{0E:00\})?)(?:을\(를\)|를\(을\)|을|를)(⏎?)\s*' + vp + r'다', lambda m: m.group(1) + ' ' + noun, out)
        out = re.sub(r'(\{19:..\}(?:\{0E:00\})?)(?:을\(를\)|를\(을\))(⏎?)\s*' + vp + r'(어|던|으니)', lambda m: m.group(1) + ' ' + noun + '하' + m.group(3) if False else m.group(0), out)
    def rep(m):
        pre = out_s[:m.start()]; form = m.group(0); a, b = two(form)
        mt = re.search(r'(\{[^}]*\})$', pre)
        if mt and mt.group(1) == '{0E:00}' and not re.search(r'\}\{0E:00\}$', pre): mt = None
        if mt:
            tok = mt.group(1)
            if re.match(r'\{0E:00\}', tok):
                mt2 = re.search(r'(\{[^}]*\})\{0E:00\}$', pre)
                if mt2: tok = mt2.group(1)
                else: mt = None                                             # 꾸밈 코드 앞이 글자 — 아래 글자 받침으로
            nm = tok_name(tok)
            if nm is not None:
                if nm == '': return b                                     # 세르주
                return a if TM.jong(nm) else b if (a, b) != ('으로', '로') else ('로' if TM.jong(nm) in (0, 8) else '으로')
            if re.match(r'\{1[58]:', tok) and form in ('은(는)', '는(은)', '이(가)', '가(이)'): return ','
            if re.match(r'\{19:', tok): return ','
            return form                                                     # 모르는 토큰 — 그대로(손으로)
        last = re.sub(r'\{[^}]*\}', '', pre)[-1:]
        j = TM.jong(last) if last else None
        if j is None: return form
        if (a, b) == ('으로', '로'): return '로' if j in (0, 8) else '으로'
        return a if j else b
    for _ in range(3):
        out_s = out
        new = PAREN.sub(rep, out_s)
        if new == out: break
        out = new
    out = re.sub(r',([⏎ ])\s*,', r',\1', out).replace(',,', ',')
    return out
