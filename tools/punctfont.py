"""대사 글꼴 문장부호 한국식 다시 그리기 (2026-11-17, 하스피 «마침표 쉼표 말줄임표도 한국식으로 · 그밖에 어색해 보이는 것도»)
한글 = 갈무리11 BDF(12×11, 바닥선 = 9~10행) 이므로 부호도 같은 글꼴 화소로 맞춘다.
  반각 칸(코드 < 0x75, 화면 폭 8px): . , ! ? ( ) — 글자 화소는 왼쪽 8열 안
  전각 칸(12px): … ‥ ～ ： “ ” ・
말줄임표·두 점 줄임표 = 마침표와 같은 높이(10행)의 점 — 한국식 바닥 점([[feedback_korean_ellipsis]])
glyphs() → {글꼴 칸: 11개 u16(bit15 = 왼쪽)}"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cctable, krenc

GALMURI = '.!?()～：“”・□○△×'      # 갈무리11 화소 그대로(□○△× = 버튼 기호, «ㅁ» 과 구별 — 2026-11-17)


def dots(cols, row=10):
    r = [0] * 11
    for c in cols: r[row] |= 1 << (15 - c)
    return r


def comma():
    """쉼표 = 마침표 자리(10행 1열) 위로 점 하나 + 아래 꼬리 왼쪽 — 11행 칸 안에 들어가게 9~10행"""
    r = [0] * 11
    r[9] = 1 << (15 - 2); r[10] = 1 << (15 - 1)
    return r


def glyphs():
    t = cctable.base_table(); full = cctable.table()
    rev = {}
    for i, c in list(t.items()) + list(full.items()):
        if len(c) == 1: rev.setdefault(c, i)
    out = {}
    for ch in GALMURI:
        if ch in rev: out[rev[ch]] = krenc.glyph_rows(ch)
    # 따옴표: 여는 것은 칸 오른쪽(뒤 글자에 붙게), 닫는 것은 칸 왼쪽(앞 글자에 붙게)
    def shift(rows, n): return [(r >> n) & 0xFFF0 if n > 0 else (r << -n) & 0xFFF0 for r in rows]
    def ink_cols(rows):
        cs = [x for x in range(12) for r in rows if r >> (15 - x) & 1]; return min(cs), max(cs)
    q = out[rev['“']]; a, b = ink_cols(q); out[rev['“']] = shift(q, 10 - b)
    q = out[rev['”']]; a, b = ink_cols(q); out[rev['”']] = shift(q, -a)
    # 여는 괄호는 칸 오른쪽(뒤 글자 쪽), 닫는 괄호는 칸 왼쪽 — 전투 설명 창은 반각도 12px 간격이라 «( 소비)» 처럼 벌어짐(2026-11-17 하스피)
    #   반각 칸은 대사에서 8px 간격 → 잉크 오른쪽 끝 = 6열(뒤 글자와 1px 띄움), 전각 （ ）는 11열·0열
    q = out[rev['(']]; a, b = ink_cols(q); out[rev['(']] = shift(q, 6 - b)
    q = out[rev[')']]; a, b = ink_cols(q); out[rev[')']] = shift(q, -a)
    if '（' in rev:
        q = krenc.glyph_rows('（'); a, b = ink_cols(q); out[rev['（']] = shift(q, 11 - b)
        q = krenc.glyph_rows('）'); a, b = ink_cols(q); out[rev['）']] = shift(q, -a)
    out[rev[',']] = comma()
    out[rev['…']] = dots((1, 5, 9))
    out[rev['‥']] = dots((3, 8))
    return out
