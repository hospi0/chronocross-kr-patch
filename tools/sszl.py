"""크로노 크로스 sszl 압축 코덱 (SLPS_023.64 0x800335F0 역어셈으로 확정, 2026-11-16).

머리 12B: 'sszl' + u32 풀린 크기 + u32(용도 미확정, 해제기는 안 읽음).
비트열 MSB 먼저(바이트 단위 적재):
  1 + 8비트      → 리터럴
  0 + 12비트 off → off==0 이면 끝, 아니면 + 4비트 n → 창[off..] 에서 n+2 바이트 복사
창 4096B(0x80037E50), 쓰기 위치 1 부터, 초기 내용 0 가정(정적 BSS).
"""
import struct

class _Bits:
    def __init__(s, b, pos):
        s.b = b; s.p = pos; s.m = 0; s.cur = 0
    def bit(s):
        if s.m == 0:
            s.cur = s.b[s.p]; s.p += 1; s.m = 0x80
        r = 1 if s.cur & s.m else 0
        s.m >>= 1
        return r
    def bits(s, n):
        v = 0
        for _ in range(n): v = (v << 1) | s.bit()
        return v

def decode(b, off=0, with_end=False):
    assert b[off:off+4] == b'sszl', b[off:off+4]
    size = struct.unpack_from('<I', b, off+4)[0]
    r = _Bits(b, off+12)
    win = bytearray(4096); wp = 1; out = bytearray()
    while True:
        if r.bit():
            c = r.bits(8); out.append(c); win[wp] = c; wp = (wp+1) & 0xfff
        else:
            o = r.bits(12)
            if o == 0: break
            n = r.bits(4) + 2
            for k in range(n):
                c = win[(o+k) & 0xfff]; out.append(c); win[wp] = c; wp = (wp+1) & 0xfff
    if len(out) != size:
        raise ValueError(f'sszl size mismatch {len(out)} != {size}')
    return (bytes(out), r.p - off) if with_end else bytes(out)

class _W:
    def __init__(s): s.o = bytearray(); s.cur = 0; s.n = 0
    def put(s, v, n):
        for i in range(n-1, -1, -1):
            s.cur = (s.cur << 1) | ((v >> i) & 1); s.n += 1
            if s.n == 8: s.o.append(s.cur); s.cur = 0; s.n = 0
    def flush(s):
        if s.n: s.o.append(s.cur << (8 - s.n)); s.cur = 0; s.n = 0
        return bytes(s.o)

def encode(data, word3=0):
    """탐욕 LZ. 창 시뮬레이션을 해제기와 똑같이 돌려 참조가 정확히 재현되게 한다."""
    win = bytearray(4096); wp = 1
    w = _W(); i = 0; N = len(data)
    # 해시: 3바이트 → 창 위치 목록(최근 것부터)
    from collections import defaultdict
    heads = defaultdict(list)
    def wput(c):
        nonlocal wp
        win[wp] = c; wp = (wp+1) & 0xfff
    while i < N:
        best_n = 0; best_o = 0
        if i + 2 <= N:
            # 후보: 창 전체를 무식하게 보는 대신 데이터 위치 기반 해시 사용
            key = bytes(data[i:i+3]) if i+3 <= N else None
            cands = heads.get(key, []) if key else []
            for pos in reversed(cands[-64:]):
                # pos = 데이터 위치 p 의 창 좌표
                dist = i - pos
                if dist <= 0 or dist > 4096 - 18: continue
                o = (1 + pos) & 0xfff
                if o == 0: continue
                # 창 시뮬레이션으로 길이 측정(겹침 복사 포함)
                n = 0
                tmp = {}
                while n < 17 and i+n < N:
                    src = (o+n) & 0xfff
                    dst_w = (wp+n) & 0xfff
                    c = tmp.get(src, win[src])
                    if c != data[i+n]: break
                    tmp[dst_w] = c; n += 1
                if n > best_n: best_n, best_o = n, o
                if n == 17: break
        if best_n >= 2:
            w.put(0, 1); w.put(best_o, 12); w.put(best_n-2, 4)
            for k in range(best_n):
                if i+k+3 <= N: heads[bytes(data[i+k:i+k+3])].append(i+k)
                wput(data[i+k])
            i += best_n
        else:
            w.put(1, 1); w.put(data[i], 8)
            if i+3 <= N: heads[bytes(data[i:i+3])].append(i)
            wput(data[i]); i += 1
    w.put(0, 1); w.put(0, 12)
    body = w.flush()
    return b'sszl' + struct.pack('<II', N, word3) + body

if __name__ == '__main__':
    import sys
    b = open(sys.argv[1], 'rb').read(); o = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
    d, used = decode(b, o, True)
    print(len(d), 'bytes, compressed', used)
    e = encode(d)
    assert decode(e) == d
    print('roundtrip ok, reenc', len(e))
