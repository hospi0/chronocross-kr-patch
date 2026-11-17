"""들여쓰기·줄바꿈 검사(2026-11-17 실기 «마지막 줄 들여쓰기 빠짐·쓰이/면»)
  python tools/indentcheck.py → 쪽마다 원문 이어지는 줄이 «　» 로 시작하는데 번역 줄이 안 그런 곳 · 낱말 중간 줄바꿈 후보"""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import trload
PG = r'\{02:01\}'
TOKLEAD = re.compile(r'^((?:\{[^}]*\})*)')
def lines_of(page):
    return page.split('⏎')
def lead_ws(l):
    m = TOKLEAD.match(l); rest = l[m.end():]
    return rest[:len(rest) - len(rest.lstrip('　'))], m.group(1), rest
def missing_indent(jp, ko):
    """쪽마다: 원문에서 «「» 다음 줄들이 모두 «　»(한 칸)로 시작하면, 번역의 «「» 다음 줄 중 들여쓰기 없는 줄 번호"""
    out = []
    jps = re.split(PG, jp); kos = re.split(PG, ko)
    if len(jps) != len(kos): return out
    for pi, (jpg, kpg) in enumerate(zip(jps, kos)):
        jl = lines_of(jpg); kl = lines_of(kpg)
        def cont(ls):
            # «「» 가 나온 줄 다음부터(쪽 첫 줄이 이어짐 «　…» 이면 그 줄부터)
            for i, l in enumerate(ls):
                if '「' in l: return i + 1
            return 0 if ls and lead_ws(ls[0])[0] == '　' else None
        js = cont(jl); ks = cont(kl)
        if js is None: continue
        if ks is None: ks = js if not any('「' in l for l in kl) else None
        if ks is None: continue
        jc = [l for l in jl[js:] if l.strip()]
        if not jc or not all(lead_ws(l)[0] == '　' for l in jc): continue
        for li in range(ks, len(kl)):
            l = kl[li]
            if not re.sub(r'\{[^}]*\}', '', l).strip(): continue
            ws = lead_ws(l)[0]
            if ws == '': out.append((pi, li))
    return out
ENDINGS = re.compile(r'^(면|다|요|고|서|니|는|은|을|를|이|가|에|의|도|만|지|며|게|야|어|아|죠|네|군|까|나|든|던|해|했|하|된|되|며)([,. !?…]|$)')
def midword(ko):
    out = []
    for page in re.split(PG, ko):
        ls = lines_of(page)
        for i in range(len(ls) - 1):
            a = re.sub(r'\{[^}]*\}', '', ls[i]).rstrip(); b = re.sub(r'\{[^}]*\}', '', ls[i + 1]).lstrip('　 ')
            if a and b and re.match(r'[가-힣]', a[-1]) and ENDINGS.match(b): out.append(a[-6:] + '⏎' + b[:6])
    return out
def main():
    T = trload.rows(trload.TSV); mi = []; mw = []
    for i, r in T.items():
        if r['kind'] not in ('talk', 'btl') or not r['ko'].strip() or r['ko'] == r['jp']: continue
        m = missing_indent(r['jp'], r['ko'])
        if m: mi.append((i, m))
        w = midword(r['ko'])
        if w: mw.append((i, w))
    print('들여쓰기 빠진 항목', len(mi), '· 줄', sum(len(m) for _, m in mi))
    print('낱말 중간 줄바꿈 후보', len(mw))
    return T, mi, mw
if __name__ == '__main__':
    T, mi, mw = main()
    for i, w in mw[:60]: print(' ', i, w)


def fix_indent(jp, ko):
    """missing_indent 줄 앞(앞 토큰 뒤)에 «　» 하나"""
    m = missing_indent(jp, ko)
    if not m: return ko
    pages = re.split('(' + PG + ')', ko)
    pi = 0
    for k in range(0, len(pages), 2):
        ls = pages[k].split('⏎')
        for (p, li) in m:
            if p == pi:
                t = TOKLEAD.match(ls[li]); ls[li] = ls[li][:t.end()] + '　' + ls[li][t.end():]
        pages[k] = '⏎'.join(ls); pi += 1
    return ''.join(pages)
