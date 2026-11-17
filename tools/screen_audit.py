# -*- coding: utf-8 -*-
r"""화면 경로 검사기 — 빌더가 실제로 쓸 바이트(work/build/_enc_dump.json, build_full --check 가 만듦)를
메뉴 글자 찍기 규칙대로 «화면 칸»으로 재현해 원문과 비교한다.

  python tools/build_full.py --disc 1 --check   # _enc_dump.json 갱신
  python tools/screen_audit.py                  # → work/build/_화면검사.tsv

확정 규칙(2026-11-17, 파일 40 코드 0x801d559c 변환기 · 0x801d5194 찍기):
  변환기(대사 인코딩 → SJIS): 바이트 < 0x20 → 전각 공백 한 칸(제어 코드·줄바꿈이 «공백»으로 찍힘),
      0xF8 이상 → 2바이트 한 칸, 나머지 1바이트 한 칸. 칸 0(반각 공백)은 변환표에서 «81 40» 한 칸.
  찍기: 글자를 8개씩 묶어 VRAM 에 올림(8·16 번째에서 올림) → 한 문자열 16칸 넘으면 뒤 글자가 앞 묶음을 덮음.
      SJIS 문자열의 ASCII 는 공백·숫자만 찍고 나머지는 건너뜀.
장비 설명은 SJIS «앞 10바이트 / 나머지»로 잘라 x+0 / x+80 에 찍음 → 모든 칸이 2바이트여야 함(0x801e7248).
메뉴 경로로 가는 묶음: 실행 파일 이름표 0·1·23·24·25·27, 기술 설명 26, 아이템 46·48·218 + SJIS 문자열.
"""
import json, os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
MENU_GROUPS = ('exe:0-', 'exe:1-', 'exe:23-', 'exe:24-', 'exe:25-', 'exe:26-', 'exe:27-', 'item:46-', 'item:48-', 'item:218-')


def conv_cells(b):
    """변환기 경로: 대사 인코딩 바이트 → 화면 칸 목록(('ctl',x)|('ch',code))"""
    out = []; k = 0
    while k < len(b):
        c = b[k]
        if c < 0x20: out.append(('ctl', c)); k += 1
        elif c >= 0xF8: out.append(('ch', (c << 8) | b[k + 1])); k += 2
        else: out.append(('ch', c)); k += 1
    return out


_CONV = None
def conv_entry(code):
    """build_full --check 가 만든 파일 40 변환표(_conv40.bin)에서 대사 1바이트 코드 → SJIS 2바이트"""
    global _CONV
    if _CONV is None: _CONV = open(os.path.join(ROOT, 'work', 'build', '_conv40.bin'), 'rb').read()   # build_full --check 가 씀
    idx = code - 0x20 if code < 0x100 else ((code >> 8) - 0xF7) * 256 + (code & 0xFF) - 0x20
    o = idx * 2
    return _CONV[o:o + 2]


def sjis_lines(b):
    """SJIS 경로: 줄마다 화면 칸 수(ASCII 공백·숫자 = 1칸, 그 밖 ASCII = 건너뜀 → 사라짐)"""
    lines = []; cur = 0; lost = []; k = 0
    while k < len(b):
        c = b[k]
        if c == 0x0D and b[k + 1:k + 2] == b'\n': lines.append(cur); cur = 0; k += 2; continue
        if c & 0x80: cur += 1; k += 2; continue
        if c == 0x20 or 0x30 <= c <= 0x39: cur += 1
        elif c == 0x25 and b[k + 1:k + 2] in (b's', b'd'): cur += 4; k += 2; continue   # %s(이름 등) 대략
        else: lost.append(chr(c))
        k += 1
    lines.append(cur)
    return lines, lost


def jp_cells(jp):
    """원문 칸 수(토큰 {XX:YY} = 바이트 수, {I3} = 1, 그 밖 글자 1) — 줄별"""
    res = []
    for ln in jp.split('⏎'):
        n = 0
        for tok in re.findall(r'\{[^}]*\}|.', ln):
            if tok.startswith('{'):
                n += 1 if re.fullmatch(r'\{I\d\}', tok) else len(tok[1:-1].replace(':', '')) // 2
            else: n += 1
        res.append(n)
    return res


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.path.insert(0, HERE); import trload
    T = trload.rows(trload.TSV)
    D = json.load(open(os.path.join(ROOT, 'work', 'build', '_enc_dump.json'), encoding='utf8'))
    bad = []
    # 목록 칸 폭 = 그 묶음 원문 중 가장 긴 것(게임은 그 폭으로 칸을 잡았다)
    colmax = collections.Counter()
    for i, v in D.items():
        if v['loc'].startswith(MENU_GROUPS) and i in T:
            g = v['loc'].split('-')[0]; jc = jp_cells(T[i]['jp'])
            colmax[g] = max(colmax[g], sum(jc) + max(0, len(jc) - 1))
    for i, v in D.items():
        loc, ko, b = v['loc'], v['ko'], bytes.fromhex(v['b'])
        jp = T[i]['jp'] if i in T else ''
        jc = jp_cells(jp)
        if v['kind'] == 'sjis':
            lines, lost = sjis_lines(b)
            if lost: bad.append((i, loc, 'SJIS 반각 문자 사라짐 %r' % ''.join(lost), ko))
            for n, ln in enumerate(lines):
                if ln > 16: bad.append((i, loc, '%d번째 줄 %d칸 > 16(8칸 묶음 덮어씀)' % (n + 1, ln), ko))
                j = jc[n] if n < len(jc) else 0
                if ln > j: bad.append((i, loc, '%d번째 줄 %d칸 > 원문 %d칸' % (n + 1, ln, j), ko))
            continue
        if not loc.startswith(MENU_GROUPS): continue
        # 메뉴 경로: 줄바꿈(0x01)도 «공백 한 칸» — 줄 나눔이 안 됨
        cells = conv_cells(b)
        n = len(cells); j = sum(jc) + max(0, len(jc) - 1)
        ctl = [hex(x) for t, x in cells if t == 'ctl']
        jctl = len(re.findall(r'\{[0-9A-F]{2}[:}]', jp)) + jp.count('⏎')
        odd = [hex(x) for t, x in cells if t == 'ch' and conv_entry(x)[:1] and conv_entry(x)[0] < 0x80]
        if odd: bad.append((i, loc, '변환표가 1바이트(ASCII)로 바꾸는 칸 %s(메뉴에서 사라짐·조각 겹침)' % ' '.join(odd), ko))
        if n > 16: bad.append((i, loc, '%d칸 > 16(8칸 묶음 덮어씀 → 엉뚱한 글자·사라짐)' % n, ko))
        cm = colmax[loc.split('-')[0]]
        if n > cm: bad.append((i, loc, '%d칸 > 이 묶음 원문 최대 %d칸(칸 넘침)' % (n, cm), ko))
        if len(ctl) > jctl: bad.append((i, loc, '원문보다 제어 바이트 많음 %s(메뉴에선 공백으로 찍힘)' % ' '.join(ctl), ko))
    out = os.path.join(ROOT, 'work', 'build', '_화면검사.tsv')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('id\tloc\t문제\tKO\n')
        for r in bad: f.write('\t'.join(str(x).replace('\t', ' ') for x in r) + '\n')
    c = collections.Counter(re.sub(r'[\d,]+|%r.*', '#', r[2]).split('(')[0] for r in bad)
    print('문제 %d건 → %s' % (len(bad), out))
    for k, n in c.most_common(): print(' ', n, k)
    g = collections.Counter(r[1].split('-')[0].split('@')[0] for r in bad)
    print('  묶음별', g.most_common())
    return bad


if __name__ == '__main__':
    main()
