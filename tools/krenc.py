"""한글 인코더·글꼴 공급 (2026-11-16)

대사 글꼴(실행 파일 0x8005670C, 22B/칸 = u16 LE 행 11, bit15 = 왼쪽) 칸 배정:
  1바이트 한글 = 칸 0x56~0xA5 (코드 0x76~0xC5, 원래 히라가나 자리, 전각 12px) — 사용 빈도 상위 음절
  2바이트 한글 = 칸 0x14C~0x6B5 (원래 한자 자리, 코드 F8~FD xx)
  유지 = 칸 0x00~0x55(반각 ASCII·전각 공백) · 0xA6~0xD7(。「」＃ー～…？！・ 전각 숫자·영문 ／、－‥) · 0x6B6~(기호·아이콘)
글리프 = 갈무리11 BDF 화소 그대로(12×11), «…» 는 한국식 바닥 점 셋으로 다시 그림
표기 규칙(빌더에서 강제): «……» → «…» 한 칸 · 부호 뒤 공백 삭제 · 반각 ,.?! 사용 · 표에 없는 글자 = 오류
"""
import os, re, sys, io, struct
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cctable

BDF = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.bdf'
ONE = list(range(0x56, 0xA6))           # 80칸
TWO = list(range(0x14C, 0x6B6))
HANGUL = re.compile(r'[\uac00-\ud7a3]')
PUNCT_NOSPACE = ',.?!、。，．？！…'
FONT_BASE = 0x8005670C
SMALL_RESERVED = {0x164 + 0x4B}       # 소형 글꼴에서 비워야 하는 칸(스프라이트 번호 + 0x4B)

_bdf = None
def bdf():
    """갈무리11 → {코드포인트: 11행 12비트}  (astronoka-kr-patch/tools/krfont.py load_bdf 를 옮김)"""
    global _bdf
    if _bdf is not None: return _bdf
    out = {}; cp = bbx = rows = None; GW, GH = 12, 11
    for line in io.open(BDF, encoding='utf-8', errors='replace'):
        t = line.strip()
        if t.startswith('ENCODING'): cp = int(t.split()[1])
        elif t.startswith('BBX'): bbx = tuple(map(int, t.split()[1:5]))
        elif t == 'BITMAP': rows = []
        elif t == 'ENDCHAR':
            if cp is not None and rows is not None:
                bbw, bbh, bx, by = bbx; g = [0] * GH
                for k, hx in enumerate(rows):
                    v = int(hx, 16) >> (len(hx) * 4 - bbw) if bbw else 0
                    y = GH - by - bbh + k
                    if 0 <= y < GH: g[y] = (v << (GW - bbw - bx)) & 0xFFF if bbw + bx <= GW else v
                out[cp] = g
            cp = rows = None
        elif rows is not None and t: rows.append(t)
    _bdf = out; return out

def glyph_rows(ch):
    """→ 11개 u16 (bit15 = 왼쪽)"""
    g = bdf().get(ord(ch))
    if g is None: raise KeyError(f'갈무리11 에 없는 글자 {ch!r}')
    return [(v << 4) & 0xFFFF for v in g]

def ellipsis_rows():
    """한국식 말줄임표: 바닥선 점 셋 (12px 칸, 9행째)"""
    r = [0] * 11; r[9] = 0b0100100100000000 >> 0; r[9] = (1 << 14) | (1 << 10) | (1 << 6)
    return r

SUBST = {'~': '～', '·': '・', '#': '＃', '―': 'ー', '—': 'ー', 'ㅡ': 'ー', '‘': '“', '’': '”', '。': '.'}   # 글꼴에 없는 부호 → 있는 전각 부호(2026-11-17)

def normalize(s):
    s = s.replace('……', '…')
    s = re.sub(r'([,.?!、。，．？！…])[ 　]+', r'\1', s)          # 부호 뒤 공백 삭제(사용자 규칙)
    s = s.replace('、', ',').replace('，', ',').replace('？', '?').replace('！', '!')
    for a, b in SUBST.items(): s = s.replace(a, b)
    s = re.sub(r"'([^'⏎]*)'", r'“\1”', s)                       # 홑따옴표 짝 → 전각 “ ”
    return s

class Codec:
    def __init__(self, texts, one_max=None, small=()):
        """small = 전투 소형 글꼴(G04)로도 찍히는 음절(이름·이름 입력판) — 2바이트 칸 맨 앞에 몰아 둔다
        (스프라이트 번호 = 칸 − 0x4B 라서 osak 표 길이가 «가장 뒤 이름 음절 칸»으로 정해짐). self.small = {음절: 칸}"""
        base = cctable.base_table()
        self.rev = {}
        for i, c in base.items():
            if len(c) == 1 and c not in self.rev and not (0x56 <= i <= 0xA5) and i < 0x14C: self.rev[c] = i
        self.icon = {}
        for i, c in cctable.table().items():                      # 0x6B6~ 기호·한자 칸(한글이 안 덮는 자리) — ←→＋（）％．“：『』○”×＆☆□△※＜＞ 등
            if i > TWO[-1] and len(c) == 1 and c not in self.rev: self.rev[c] = i
            if re.fullmatch(r'\{I\d\}', c): self.icon[c[1:-1]] = i
        freq = {}
        for t in texts:
            for ch in HANGUL.findall(normalize(t)): freq[ch] = freq.get(ch, 0) + 1
        order = sorted(freq, key=lambda c: (-freq[c], c))
        if len(order) > len(ONE) + len(TWO): raise SystemExit(f'⛔ 음절 {len(order)} > 칸 {len(ONE)+len(TWO)}')
        self.slot = {}
        nOne = len(ONE) if one_max is None else min(one_max, len(ONE))
        small = set(HANGUL.findall(''.join(small)))
        for ch in small: freq.setdefault(ch, 0)
        order = sorted(freq, key=lambda c: (-freq[c], c))
        one = order[:nOne]; rest = order[nOne:]
        for k, ch in enumerate(one): self.slot[ch] = ONE[k]
        # 소형 글꼴 스프라이트 356(= 숫자 0 의 101 + 0xFF «빈 자리», 필드 레벨업 창) 은 비워 둔다 → 칸 0x1AF 에 이름 음절 금지
        two_small = [c for c in TWO if c not in SMALL_RESERVED]
        rs = [c for c in rest if c in small]; ro = [c for c in rest if c not in small]
        for k, ch in enumerate(rs): self.slot[ch] = two_small[k]
        left = [c for c in TWO if c not in set(self.slot.values())]
        for k, ch in enumerate(ro): self.slot[ch] = left[k]
        self.small = {c: self.slot[c] for c in small}
        self.rev.update(self.slot)
        self.rev['…'] = 0xAC
    @staticmethod
    def code(i):
        if i < 0xD8: return bytes([i + 0x20])
        v = i + 0x20; return bytes([0xF7 + v // 256, v % 256])
    def encode(self, s):
        s = normalize(s); out = bytearray(); k = 0
        while k < len(s):
            c = s[k]
            if c == '{':
                e = s.index('}', k); tok = s[k + 1:e]; k = e + 1
                if tok.startswith('G:'):                       # 표에 없는 칸 그대로(원문 토큰)
                    out += self.code(int(tok[2:], 16))
                elif re.fullmatch(r'I\d', tok):                # 아이콘 칸 {I0}~{I8}
                    out += self.code(self.icon[tok])
                elif ':' in tok:
                    a, b = tok.split(':'); out += bytes([int(a, 16)]) + bytes.fromhex(b)
                else: out.append(int(tok, 16))
                continue
            if c == '⏎': out.append(1); k += 1; continue
            if c == ' ': out.append(0x20); k += 1; continue
            if c not in self.rev: raise KeyError(f'⛔ 인코딩 없는 글자 {c!r} : {s}')
            out += self.code(self.rev[c]); k += 1
        return bytes(out)
    def width_px(self, b):
        """한 줄 바이트의 화면 폭(px): 코드<0x75 반각 8, 그 밖 12, 제어 0 (치환 이름은 호출측이 더함)"""
        return None
    def patch_font(self, exe):
        exe = bytearray(exe); o0 = FONT_BASE - 0x80010000 + 0x800
        for ch, i in self.slot.items():
            struct.pack_into('<11H', exe, o0 + i * 22, *glyph_rows(ch))
        struct.pack_into('<11H', exe, o0 + 0xAC * 22, *ellipsis_rows())
        import punctfont                                  # 문장부호 한국식(갈무리11 화소·바닥 점 줄임표, 2026-11-17)
        for i, rows in punctfont.glyphs().items():
            struct.pack_into('<11H', exe, o0 + i * 22, *rows)
        return bytes(exe)
