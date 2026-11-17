"""대사 PoC 빌드 (2026-11-16) — 맵 434(꿈속 바다 요새 첫 장면) 대사 7개 + 인물 이름 4개를 한글로(시험용 임시 번역)
→ work/build/poc_d1.bin  (디스크 쓰기·설치 없음)

시험 항목: 갈무리11 글리프 · 1바이트/2바이트 한글 코드 · sszl 재압축 · 맵 파일 구간 재배치 · 창 크기 자동 계산
          · 실행 파일 문자열 표(이름) 재작성 · 디스크 재구성(파일 키우기)
"""
import os, sys, struct, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
import krenc, sszl, ccmsg, exetext, rebuild, kromhook
from ccget import get, get_exact

SRC = 'D:/hospi/My Documents/한글패치/PS1/ps/Chrono Cross (Japan, Asia)/Chrono Cross (Japan, Asia) (Disc 1).bin'
MAP = 434
# 시험용 임시 번역 (실제 번역은 사용자 TSV)
KO_MSG = {
 0: '{08:14}⏎「왜 그래, {12:15}⏎　멍하니 있고?{02:01}　이제부터가 진짜야.{04:14}⏎　죽고 싶지 않으면⏎　정신 바짝 차려!',
 1: '{18:02}⏎「왜 그래,⏎　{12:15},⏎　멍하니 서서?{02:01}　이제부터가 진짜다.{04:14}⏎　죽고 싶지 않으면⏎　정신 바짝 차려라.',
 2: '{08:01}⏎「자, 가자고!⏎　{08:00},⏎　{18:02}!',
 3: '{08:01}⏎「기다려라, 야마네코!⏎　오늘이야말로 네놈의⏎　숨통을 끊어 주마!!{02:01}　울면서 빌 거면⏎　지금 해 둬.{04:14}⏎　용서는 안 하겠지만!',
 4: '{08:01}⏎「크크크……{04:3C}⏎　아-핫핫핫핫!',
 5: '{08:14}⏎「자, {12:15}⏎　가자!',
 6: '{18:02}⏎「자, {12:15}!',
}
KO_NAMES = {0x00: '세르주', 0x01: '키드', 0x14: '레나', 0x24: '반클리프'}   # 실행 파일 묶음 1
# SJIS(BIOS 글꼴 경로) 시험: 부팅 메모리 카드 화면 — 파일 40, 28B 고정 칸(12칸 + 0)
KO_SJIS = {(40, 0x204a4): '사용할 슬롯을 선택해 ', (40, 0x204c0): '주세요',
           (40, 0x204dc): '메모리 카드 슬롯 １', (40, 0x204f8): '메모리 카드 슬롯 ２'}
CONV = {38: 0x3ade, 40: 0x21046, 226: 0xd662}          # 대사 글꼴 칸 0x55.. → SJIS 변환표

def sjis_encode(codec, s, cells=12):
    out = bytearray()
    for ch in s:
        if ch == ' ': out += bytes([0x81, 0x40])
        elif ch in codec.slot: out += kromhook.kr_code(codec.slot[ch])
        else: out += ch.encode('cp932')
    assert len(out) <= cells * 2, s
    while len(out) < cells * 2: out += bytes([0x81, 0x40])
    return bytes(out)

def sjis_files(codec):
    files = {}
    for fi in (38, 40, 226):
        b = bytearray(get_exact('1', fi))
        t0 = CONV[fi]
        for ch, idx in codec.slot.items():
            b[t0 + (idx - 0x55) * 2: t0 + (idx - 0x55) * 2 + 2] = kromhook.kr_code(idx)
        for (f, off), txt in KO_SJIS.items():
            if f == fi:
                enc = sjis_encode(codec, txt); b[off:off + 28] = enc + bytes(28 - len(enc))
        files[fi] = bytes(b)
    return files

def exe_rewrite(exe, codec, names, share=False):
    """문자열 표(0x800600E0)를 원본 규칙으로 다시 짠다: 문자열은 «다음 항목 오프셋까지»(안에 0 이 든 제어 인자 있음),
    묶음 연속·정렬 없음, 묶음 끝 문자열(«いいい» 표지)은 종결 0 없음(홀수 크기면 0 하나 — 다음 묶음 u16 표 정렬).
    names = {(묶음,번호): 새 바이트(종결 0 제외)} · share=True 면 같은 문자열 공유(공간 부족 때만)"""
    exe = bytearray(exe); base = exetext.BASE - 0x80010000 + 0x800
    n = struct.unpack_from('<I', exe, base)[0]; offs = struct.unpack_from('<%dI' % (n + 1), exe, base + 4)
    end = offs[n]
    groups = []
    for gi, g0, g1, so in exetext.groups(bytes(exe)):
        gend = base + offs[gi + 1]; strs = []
        for si, s in enumerate(so):
            nxt = g0 + so[si + 1] if si + 1 < len(so) else gend
            if (gi, si) in names:
                strs.append(names[(gi, si)] + (b'' if si == len(so) - 1 else ZERO))
            else:
                strs.append(bytes(exe[g0 + s:nxt]))
        groups.append(strs)
    out = bytearray(struct.pack('<I', n) + ZERO * 4 * (n + 1)); goffs = []
    for strs in groups:
        goffs.append(len(out))
        tbl = bytearray(2 * len(strs)); body = bytearray(); seen = {}
        for k, s in enumerate(strs):
            if share and s in seen and k != len(strs) - 1:
                struct.pack_into('<H', tbl, 2 * k, seen[s]); continue
            seen[s] = len(tbl) + len(body); struct.pack_into('<H', tbl, 2 * k, seen[s]); body += s
        g = tbl + body
        if len(g) % 2: g += ZERO
        out += g
    goffs.append(len(out))
    struct.pack_into('<%dI' % (n + 1), out, 4, *goffs)
    if len(out) > end:
        if not share: return exe_rewrite(bytes(exe), codec, names, share=True)
        raise SystemExit(f'⛔ 문자열 표 넘침 {len(out)} > {end}')
    exe[base:base + end] = out + ZERO * (end - len(out))
    return bytes(exe)

ZERO = bytes(1)

def name_px(codec, s):
    return sum(8 if b < 0x75 else 12 for b in codec.encode(s) if b >= 0x20 and b < 0xF8) + 12 * sum(1 for b in codec.encode(s) if b >= 0xF8)

def window(codec, text, sub):
    """창 크기 (칸 w, 줄 h, px): 쪽({02}/{06}) 단위 최대 줄 수 · 줄 최대 폭(반각 8 / 전각 12, 치환 이름은 sub 폭)"""
    import re
    pages = re.split(r'\{0[26]:[0-9A-F]+\}', krenc.normalize(text))
    h = 0; wpx = 0
    for p in pages:
        lines = p.split('⏎'); h = max(h, len([l for l in lines]))
        for l in lines:
            px = 0
            for tok in re.findall(r'\{[^}]*\}|.', l):
                if tok.startswith('{'):
                    px += sub.get(tok, 0)
                elif tok == ' ' or (tok in codec.rev and codec.rev[tok] < 0x55): px += 8
                else: px += 12
            wpx = max(wpx, px)
    w = math.ceil(wpx / 12)
    return w, h, w * 12

def map_rewrite(fb, codec, ko, sub):
    n = struct.unpack_from('<I', fb, 0)[0]; offs = list(struct.unpack_from('<%dI' % (n + 1), fb, 4))
    s8 = fb[offs[8]:offs[9]]; word3 = struct.unpack_from('<I', s8, 8)[0]
    d = sszl.decode(s8)
    recs = ccmsg.block_offsets(d)
    msgs = []
    for ri, (o, w, h, px) in enumerate(recs[:-1]):
        end = recs[ri + 1][0]; _, e = ccmsg.parse(d[:end] + b'\0', o)
        raw = d[o:min(e - 1, end)]
        if ri in ko:
            nb = codec.encode(ko[ri]); w, h, px = window(codec, ko[ri], sub); msgs.append((nb, w, h, px))
        else: msgs.append((raw, w, h, px))
    T = 8 * (len(msgs) + 1); body = bytearray(); tbl = bytearray()
    for nb, w, h, px in msgs:
        tbl += struct.pack('<4H', T + len(body), w, h, px); body += nb + b'\0'
    tbl += struct.pack('<4H', T + len(body), 0, 0, 0)
    blk = bytes(tbl + body)
    if len(blk) > 0xFFFF: raise SystemExit('⛔ 대사 블록 64KB 초과')
    z = sszl.encode(blk, word3); assert sszl.decode(z) == blk
    while len(z) % 4: z += b'\0'
    secs = [fb[offs[i]:offs[i + 1]] for i in range(n)]; secs[8] = z
    out = bytearray(fb[:offs[0]]); new = []
    for s in secs: new.append(len(out)); out += s
    new.append(len(out)); struct.pack_into('<%dI' % (n + 1), out, 4, *new)
    return bytes(out), len(blk), len(d)

def main():
    texts = list(KO_MSG.values()) + list(KO_NAMES.values()) + list(KO_SJIS.values())
    codec = krenc.Codec(texts, one_max=30)   # PoC: 2바이트 경로도 시험
    one = sum(1 for v in codec.slot.values() if v < 0xA6)
    print('음절', len(codec.slot), '(1바이트', one, ')')
    exe = get_exact('1', 0)
    exe = codec.patch_font(exe)
    names = {(1, k): codec.encode(v) for k, v in KO_NAMES.items()}
    exe = exe_rewrite(exe, codec, names)
    exe = kromhook.patch(exe)
    sj = sjis_files(codec)
    sub = {'{08:00}': name_px(codec, KO_NAMES[0]), '{08:01}': name_px(codec, KO_NAMES[1]), '{08:14}': name_px(codec, KO_NAMES[0x14]),
           '{18:02}': 72, '{12:15}': name_px(codec, KO_NAMES[0])}
    fb = get_exact('1', MAP)
    newmap, nb, ob = map_rewrite(fb, codec, KO_MSG, sub)
    print(f'맵 {MAP}: 파일 {len(fb)} → {len(newmap)} B · 대사 블록 {ob} → {nb} B')
    os.makedirs(os.path.join(ROOT, 'work', 'build'), exist_ok=True)
    out = os.path.join(ROOT, 'work', 'build', 'poc_d1.bin')
    repl = {0: exe, MAP: newmap}; repl.update(sj)
    rebuild.rebuild(SRC, out, repl=repl)
    # 검산: 새 디스크에서 다시 읽어 대사 블록 확인
    import rebuild_check
    B, f, ent, n = rebuild_check.files(out)
    assert B[0] == exe and B[MAP][:len(newmap)] == newmap
    print('검산 OK — 새 디스크에서 실행 파일·맵 434 읽힘')

if __name__ == '__main__':
    main()
