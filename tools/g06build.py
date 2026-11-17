"""G06 필드 포즈 띠(파일 2049 /paus TIM 192×10 + /paus 스프라이트 표, 사본 = 파일 2050 구간 3) 한글판 — 크기 불변 제자리 수정.
띠 = «バイブレーション機能:O»(x1~83) N(85~89) FF(91~99) PAUSE ワールド名表示(131~183) ↑ — 한 색(색인 15), 그림자 없음
  스프라이트 2·3 = 낱말 조각(-49, u65 w83) + N/FF(x35)        → «진동 기능» + :O 사본, N/FF 를 뒤로 당김
  스프라이트 4·5 = 낱말 조각(-39, u195 w53) + :O(x16, u140) + N/FF(x25) → «월드명 표시», :O·N/FF 를 뒤로 당김
글리프 = 갈무리7 잉크만(2~8행). 사용: build(drp 바이트, 라벨) → 같은 크기 바이트"""
import os, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import drp, sprtab, smallfont
from timscan import find_tims

INK, PITCH, SPACE = 15, 8, 3
LAB = {'vib': '진동 기능', 'world': '월드명 표시'}


def draw(idx, x, s):
    for c in s:
        if c == ' ': x += SPACE; continue
        g = smallfont.cell(c)                   # 9×8, 잉크 = 2 (1~7행)
        reg = idx[1:10, x:x + 8]; reg[g == 2] = INK
        x += PITCH
    return x - 1                                # 마지막 글자 오른쪽 빈 열 제외


def build(b, lab=LAB):
    b = bytearray(b)
    tr = {(p, ty): (bo, sz) for d, a, p, ty, bo, sz in drp.tree(bytes(b))}
    tbo, tsz = tr[('/paus', 4)]; t = find_tims(bytes(b[tbo:tbo + tsz]))[0]
    assert (t['ix'], t['iy'], t['iw'] * 4, t['ih']) == (912, 96, 192, 10)
    d = np.frombuffer(t['data'], np.uint8).reshape(10, -1)
    idx = np.zeros((10, 192), np.uint8); idx[:, 0::2] = d & 15; idx[:, 1::2] = d >> 4
    colonO = idx[:, 76:84].copy()               # «:O» (스프라이트 4·5 가 u140 으로 따로 씀 — 제자리 유지)
    idx[:, 1:76] = 0
    e1 = draw(idx, 1, lab['vib']); assert e1 + 9 <= 75, e1
    idx[:, e1 + 1:e1 + 9] = colonO; w1 = e1 + 9 - 1          # 낱말 + :O
    idx[:, 131:184] = 0
    e2 = draw(idx, 131, lab['world']); assert e2 <= 184, e2
    w2 = e2 - 131
    packed = (idx[:, 0::2] | (idx[:, 1::2] << 4)).astype(np.uint8).tobytes()
    doff = tbo + t['end'] - len(t['data']); b[doff:doff + len(packed)] = packed
    # 표: 조각 x·w 만 제자리 수정
    sbo, ssz = tr[('/paus', 3)]; T = sprtab.read(bytes(b), sbo, ssz)
    def poke(p, **kw):
        o = sbo + p['off']
        for k, v in kw.items():
            if k == 'x': struct.pack_into('<h', b, o, v)
            if k == 'w': b[o + 8] = v
    for no in (2, 3):
        for p in T['spr'][no - 1]['pieces']:
            if (p['u'], p['w']) == (65, 83): poke(p, w=w1)
            elif p['x'] == 35 and p['u'] in (149, 155): poke(p, x=-49 + w1 + 1)
    for no in (4, 5):
        for p in T['spr'][no - 1]['pieces']:
            if (p['u'], p['w']) == (195, 53): poke(p, w=w2)
            elif (p['x'], p['u']) == (16, 140): poke(p, x=-39 + w2 + 2)
            elif p['x'] == 25 and p['u'] in (149, 155): poke(p, x=-39 + w2 + 2 + 9)
    return bytes(b)


def build_2050(c, lab=LAB):
    n = struct.unpack_from('<I', c, 0)[0]; offs = struct.unpack_from('<%dI' % (n + 1), c, 4)
    sec = c[offs[3]:offs[4]]; new = build(sec, lab); assert len(new) == len(sec)
    return c[:offs[3]] + new + c[offs[4]:]


if __name__ == '__main__':
    from ccget import get_exact
    from PIL import Image
    b = get_exact('1', 2049); nb = build(b); assert len(nb) == len(b)
    c = get_exact('1', 2050); nc = build_2050(c); assert len(nc) == len(c)
    out = 'work/g04/preview_03'; os.makedirs(out, exist_ok=True)
    sprtab.sheet(b, '/paus', os.path.join(out, '필드포즈_원본.png'), cols=3, scale=4)
    sprtab.sheet(nb, '/paus', os.path.join(out, '필드포즈_한글.png'), cols=3, scale=4)
    print('바뀐 바이트', sum(1 for x, y in zip(b, nb) if x != y), '→', out)
