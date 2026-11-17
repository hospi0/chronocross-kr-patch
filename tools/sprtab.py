"""drp 종류 3 = 스프라이트 표 읽기·그리기.
머리 12B: u16 0, u16 개수(|0x8000 깃발), u16 텍스처 VRAM x, y, u16 CLUT VRAM x(픽셀), y · u16 오프셋[개수](본문 기준, 0 = 없음)
스프라이트 = u16 조각 수, u16 ?, 조각 12B × n : s16 x, s16 y, u8 u, u8 v, u16 CLUT, u8 w, u8 h, u8 tpage, u8 flag
머리 깃발(개수 0x8000) = 조각 u·v 가 텍스처 원점 기준(아니면 tpage 기준)
게임의 스프라이트 번호는 1부터(그리기 함수가 −1).
사용: sprtab.py <파일bin> [표이름…]   → 표 요약 / --sheet 표이름 출력.png"""
import struct, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import drp
from timscan import find_tims


def read(b, bo, sz):
    d = b[bo:bo + sz]
    n = struct.unpack_from('<H', d, 2)[0] & 0x7FFF
    tx, ty, cx, cy = struct.unpack_from('<4H', d, 4)
    offs = struct.unpack_from('<%dH' % n, d, 12)
    spr = []
    for o in offs:
        if o == 0:
            spr.append(None); continue
        c, unk = struct.unpack_from('<HH', d, o)
        ps = []
        for k in range(c):
            x, y, u, v, clut, w, h, tp, fl = struct.unpack_from('<hhBBHBBBB', d, o + 4 + 12 * k)
            ps.append(dict(x=x, y=y, u=u, v=v, clut=clut, w=w, h=h, tp=tp, fl=fl, off=o + 4 + 12 * k))
        spr.append(dict(off=o, unk=unk, pieces=ps))
    return dict(n=n, flag=struct.unpack_from('<H', d, 2)[0] >> 15, tex=(tx, ty), clut=(cx, cy), offs=offs, spr=spr)


def tables(b):
    out = {}
    for dep, a, p, ty, bo, sz in drp.tree(b):
        if ty == 3:
            out[p] = (bo, sz, read(b, bo, sz))
    return out


def vram_from_tims(b, vram=None):
    """파일 안 TIM 을 전부 가상 VRAM(512×1024 u16)에 올린다"""
    if vram is None:
        vram = np.zeros((512, 1024), '<u2')
    for t in find_tims(b):
        iw, ih = t['iw'], t['ih']
        if t['iy'] + ih > 512 or t['ix'] + iw > 1024: continue
        vram[t['iy']:t['iy'] + ih, t['ix']:t['ix'] + iw] = np.frombuffer(t['data'], '<u2').reshape(ih, iw)
    # CLUT
    for i in range(0, len(b) - 20, 4):
        if b[i:i + 4] == b'\x10\0\0\0' and struct.unpack_from('<I', b, i + 4)[0] in (8, 9):
            cl = struct.unpack_from('<I', b, i + 8)[0]
            if cl < 12 or i + 8 + cl > len(b): continue
            cx, cy, cw, ch = struct.unpack_from('<4H', b, i + 12)
            if cw * ch * 2 + 12 != cl or cx + cw > 1024 or cy + ch > 512: continue
            vram[cy:cy + ch, cx:cx + cw] = np.frombuffer(b[i + 20:i + 8 + cl], '<u2').reshape(ch, cw)
    return vram


def piece_px(vram, p, rel=None):
    """조각 하나 → (h, w) u16 색(0 = 투명)"""
    tp = p['tp']; bx = (tp & 15) * 64; by = 256 if tp & 16 else 0; bpp = (tp >> 7) & 3 if False else 0
    cx = (p['clut'] & 63) * 16; cy = p['clut'] >> 6
    uo = vo = 0
    if rel:                                   # 머리 깃발 1 = u·v 가 표의 텍스처 원점 기준
        uo = (rel[0] - bx) * 4; vo = rel[1] - by
    out = np.zeros((p['h'], p['w']), '<u2')
    for yy in range(p['h']):
        for xx in range(p['w']):
            u = p['u'] + xx + uo; v = p['v'] + yy + vo
            wv = vram[(by + v) & 511, (bx + u // 4) & 1023]
            ix = (int(wv) >> (4 * (u & 3))) & 15
            out[yy, xx] = vram[cy, cx + ix]
    return out


def render(vram, s, pad=2, rel=None):
    """스프라이트 → RGB 배열(바탕 진회색)과 원점"""
    ps = s['pieces']
    x0 = min(p['x'] for p in ps); y0 = min(p['y'] for p in ps)
    x1 = max(p['x'] + p['w'] for p in ps); y1 = max(p['y'] + p['h'] for p in ps)
    im = np.full((y1 - y0 + 2 * pad, x1 - x0 + 2 * pad, 3), 48, np.uint8)
    for p in reversed(ps):
        px = piece_px(vram, p, rel)
        for yy in range(p['h']):
            for xx in range(p['w']):
                c = int(px[yy, xx])
                if c:
                    im[p['y'] - y0 + pad + yy, p['x'] - x0 + pad + xx] = ((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3)
    return im


def sheet(b, name, out, cols=16, scale=3, vram=None):
    from PIL import Image, ImageDraw
    bo, sz, T = tables(b)[name]
    vram = vram_from_tims(b) if vram is None else vram
    ims = [None if s is None else render(vram, s, rel=T['tex'] if T['flag'] else None) for s in T['spr']]
    cw = max(im.shape[1] for im in ims if im is not None) * scale + 6
    chh = max(im.shape[0] for im in ims if im is not None) * scale + 14
    rows = (len(ims) + cols - 1) // cols
    S = Image.new('RGB', (cols * cw, rows * chh), (16, 16, 64)); dr = ImageDraw.Draw(S)
    for i, im in enumerate(ims):
        x = (i % cols) * cw; y = (i // cols) * chh
        dr.text((x + 1, y), '%d' % (i + 1), fill=(255, 255, 0))
        if im is None: continue
        S.paste(Image.fromarray(im).resize((im.shape[1] * scale, im.shape[0] * scale), Image.NEAREST), (x + 2, y + 11))
    S.save(out)


if __name__ == '__main__':
    b = open(sys.argv[1], 'rb').read()
    if len(sys.argv) > 2 and sys.argv[2] == '--sheet':
        sheet(b, sys.argv[3], sys.argv[4]); sys.exit()
    for p, (bo, sz, T) in tables(b).items():
        if len(sys.argv) > 2 and p.split('/')[-1] not in sys.argv[2:]: continue
        tps = sorted({(q['tp'], hex(q['clut'])) for s in T['spr'] if s for q in s['pieces']})
        print('%-14s 본문 0x%05X 크기 0x%04X 개수 %3d 깃발 %d 텍스처 %s CLUT %s  tpage·clut %s' % (p, bo, sz, T['n'], T['flag'], T['tex'], T['clut'], tps[:6]))


def write(tb, sprs=None):
    """표 dict(read 결과) → 바이트. sprs 를 주면 그 목록으로(조각 = dict). 개수가 홀수면 오프셋 표 뒤 0 두 개(원본과 같음)"""
    sprs = tb['spr'] if sprs is None else sprs
    n = len(sprs); pad = (n & 1) * 2
    hdr = struct.pack('<HH4H', 0, n | (0x8000 if tb['flag'] else 0), *tb['tex'], *tb['clut'])
    offs = []; data = bytearray()
    for s in sprs:
        if s is None: offs.append(0); continue
        offs.append(12 + 2 * n + pad + len(data))
        data += struct.pack('<HH', len(s['pieces']), s['unk'])
        for p in s['pieces']:
            data += struct.pack('<hhBBHBBBB', p['x'], p['y'], p['u'], p['v'], p['clut'], p['w'], p['h'], p['tp'], p['fl'])
    out = hdr + struct.pack('<%dH' % n, *offs) + bytes(pad) + bytes(data)
    assert len(out) < 0x10000 and len(out) % 4 == 0, len(out)
    return out
