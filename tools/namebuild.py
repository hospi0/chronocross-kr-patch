"""이름 입력판 한글화(파일 38, 적재 0x801D2800).
구조(2026-11-17 조사)
  - 보이는 글자 = SJIS 5자 줄(12 B: 10 B + 0 0)을 줄마다 BIOS 글꼴 경로로 찍음(우리 훅 = 한글 SJIS E0xx → 대사 글꼴)
      가타카나 쪽: 왼쪽 0x3260+12k(k=0..9) · 오른쪽 0x32D8+12k(k=0..6) · 오른쪽 7~9줄 = 0x332C/0x3338/0x3344 (두 쪽 공용: 기호 2줄·빈 줄)
      히라가나 쪽: 왼쪽 0x3350+12k · 오른쪽 0x33C8+12k(k=0..6) · 오른쪽 7~9줄 = 같은 공용 줄
  - 고른 글자 = 쪽마다 u32 코드표 10×10(행 = 40 B): 가타카나 0x3554 · 히라가나 0x36E4 · 영숫자 0x3874 (0x801D3A0C~)
      값 = 대사 인코딩(1바이트 코드, 또는 0xF8xx 두 바이트를 hi<<8|lo), 0x75 = 빈칸
  - 이름 버퍼 = 인물마다 16 B(0x800786F8), 글자 6개 — 2바이트 한글 6자 = 12 B 로 들어감
설계: 가타카나 쪽 → «한글1», 히라가나 쪽 → «한글2», 각 85칸(왼쪽 10줄 + 오른쪽 7줄), 음절 170개 가나다순. 공용 기호 줄·영숫자 쪽은 원본 그대로."""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kromhook

# 음절 170 = 자음 14 × 모음 8(ㅏㅓㅗㅜㅡㅣㅔㅐ) + 이름·음역에 잦은 것 58
_CONS = 'ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ'
_CI = [0, 2, 3, 5, 6, 7, 9, 11, 12, 14, 15, 16, 17, 18]          # 초성 번호
_VI = [0, 4, 8, 13, 18, 20, 5, 1]                                    # ㅏㅓㅗㅜㅡㅣㅔㅐ
BASE = [chr(0xAC00 + (c * 21 + v) * 28) for c in _CI for v in _VI]
EXTRA = list('야여요유와워위의예웨' '류료려녀뉴슈쇼샤휴효큐'
             '인은안민진준현연윤한린란렌론선원순' '영성승상용정경동강' '일엘율철' '엠람' '석혁빈별훈')
SYL = sorted(set(BASE + EXTRA))
assert len(SYL) == 170, len(SYL)
assert all(c in SYL for c in '하스피세르주키드레나'), '필수 음절'

KATA = dict(left=0x3260, right=0x32D8, code=0x3554)
HIRA = dict(left=0x3350, right=0x33C8, code=0x36E4)
PROMPT = (0x34C4, 0x34D8)     # «名前を決めてくだ» «さい。» — 대사 번역 몫(여기선 안 건드림)


def cells(page):
    """쪽(0/1) → [(행, 열, 음절)] 85칸: 행 0~6 은 왼5+오른5, 행 7~9 는 왼5"""
    s = SYL[page * 85:(page + 1) * 85]; out = []; k = 0
    for r in range(10):
        for c in range(10 if r < 7 else 5):
            out.append((r, c, s[k])); k += 1
    return out


def build(b38, codec):
    b = bytearray(b38)
    for page, P in enumerate((KATA, HIRA)):
        grid = {(r, c): ch for r, c, ch in cells(page)}
        for r in range(10):
            for half in (0, 1):
                if half == 1 and r >= 7: continue
                o = (P['left'] if half == 0 else P['right']) + 12 * r
                assert b[o + 10:o + 12] == b'\0\0'
                b[o:o + 10] = b''.join(kromhook.kr_code(codec.slot[grid[(r, half * 5 + i)]]) for i in range(5))
        for r in range(10):
            for c in range(10):
                o = P['code'] + 40 * r + 4 * c
                if r >= 7 and c >= 5: continue                      # 공용 기호 줄 코드 = 원본 그대로
                v = int.from_bytes(codec.code(codec.slot[grid[(r, c)]]), 'big')
                struct.pack_into('<I', b, o, v)
    return bytes(b)


def preview(out):
    """글자판 미리보기(원본 가나 | 한글) — 갈무리11 화소, 화면 칸 간격 그대로(가로 16·세로 19 비례)"""
    import numpy as np, krenc
    from PIL import Image
    b = open(os.path.join(os.path.dirname(HERE), 'work', 'files', '1_0038.bin'), 'rb').read() if False else None
    from ccget import get_exact
    b = get_exact('1', 38)
    def row_str(o): return b[o:o + 10].decode('cp932')
    SH = [row_str(0x332C), row_str(0x3338), row_str(0x3344)]
    def page_chars(P, ko):
        g = {}
        for r in range(10):
            L = row_str(P['left'] + 12 * r); R = row_str(P['right'] + 12 * r) if r < 7 else SH[r - 7]
            for i in range(5): g[(r, i)] = L[i]; g[(r, 5 + i)] = R[i]
        if ko is not None:
            for r, c, ch in cells(ko): g[(r, c)] = ch
        return g
    CW, CH, S = 22, 14, 3
    def draw(g):
        a = np.zeros((10 * CH + 8, 10 * CW + 16 + 8), np.uint8)
        for (r, c), ch in g.items():
            if ch == '　': continue
            try: rows = krenc.glyph_rows(ch)
            except KeyError: continue
            x0 = 4 + c * CW + (16 if c >= 5 else 0); y0 = 4 + r * CH
            for yy, v in enumerate(rows):
                for xx in range(12):
                    if v & (0x8000 >> xx): a[y0 + yy, x0 + xx] = 1
        return a
    os.makedirs(out, exist_ok=True)
    for i, (P, nm) in enumerate(((KATA, '한글1'), (HIRA, '한글2'))):
        o = draw(page_chars(P, None)); k = draw(page_chars(P, i))
        sep = np.full((o.shape[0], 6), 2, np.uint8)
        a = np.hstack([o, sep, k])
        pal = np.array([[60, 40, 25], [235, 235, 235], [0, 0, 0]], np.uint8)
        Image.fromarray(pal[a]).resize((a.shape[1] * S, a.shape[0] * S), Image.NEAREST).save(os.path.join(out, '이름입력_%s쪽_원본과한글.png' % nm))


if __name__ == '__main__':
    os.chdir(os.path.dirname(HERE))
    print('음절', len(SYL)); print(''.join(SYL[:85])); print(''.join(SYL[85:]))
    preview('work/name/preview_01')
    print('→ work/name/preview_01')
