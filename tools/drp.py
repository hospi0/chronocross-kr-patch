"""drp 묶음(메뉴·전투 리소스) 읽기. 머리 'drp\\0', u32 0, u32 항목수<<6, u32 머리 크기, u32 오프셋[항목수]
항목 = u32 0, 이름 4자, u32 (크기<<4 … | 종류), 본문.  종류 1 = 안에 또 drp, 4 = TIM, 3·5 … = 스프라이트·배치 자료
사용: drp.py <파일> [--tree]"""
import struct, sys


def parse(b, base=0):
    """→ [(abs_off, name, type, body_off, body_size)]"""
    assert b[base:base + 4] == b'drp\0', hex(base)
    n = struct.unpack_from('<I', b, base + 8)[0] >> 6          # 항목 수(첫 항목은 머리 바로 뒤, 표에는 둘째부터)
    hdr = struct.unpack_from('<I', b, base + 12)[0]
    assert hdr == 16 + (n - 1) * 4, (hex(base), n, hdr)
    offs = (hdr,) + struct.unpack_from('<%dI' % (n - 1), b, base + 16)
    out = []
    for o in offs:
        a = base + o
        name = b[a + 4:a + 8].rstrip(b'\0').decode('latin1')
        v = struct.unpack_from('<I', b, a + 8)[0]
        out.append((a, name, v & 0xFF, a + 12, v >> 12))
    return out


def tree(b, base=0, depth=0, path=''):
    rows = []
    for a, name, ty, bo, sz in parse(b, base):
        p = path + '/' + name
        rows.append((depth, a, p, ty, bo, sz))
        if ty == 1 and b[bo:bo + 4] == b'drp\0':
            rows += tree(b, bo, depth + 1, p)
    return rows


def find(b, path):
    for d, a, p, ty, bo, sz in tree(b):
        if p == path:
            return bo, sz
    raise KeyError(path)


if __name__ == '__main__':
    b = open(sys.argv[1], 'rb').read()
    for d, a, p, ty, bo, sz in tree(b):
        print('%s%-28s 종류 %d  머리 0x%05X 본문 0x%05X 크기 0x%X' % ('  ' * d, p, ty, a, bo, sz))


def rebuild(b, repl, base=0, path=''):
    """repl = {경로: 새 본문} 으로 묶음을 다시 짠다(크기·오프셋 갱신, 안쪽 drp 재귀). 바꾼 것 없으면 원본과 바이트 동일.
    → 새 drp 바이트(base 부터 묶음 끝까지; 최상위는 원본 꼬리 0 채움 없이 본문만)"""
    ents = parse(b, base)
    n = len(ents)
    hdr = 16 + (n - 1) * 4
    out = bytearray(b[base:base + hdr])
    offs = []
    for a, name, ty, bo, sz in ents:
        p = path + '/' + name
        if (p, ty) in repl:                 # 같은 이름이 둘(예: 2543 /help 표·그림) → (경로, 종류)로 고름
            body = repl[(p, ty)]
        elif p in repl:
            assert sum(1 for e in ents if e[1] == name) == 1, ('같은 이름 항목이 여럿 — (경로, 종류) 로 지정', p)
            body = repl[p]
        elif ty == 1 and b[bo:bo + 4] == b'drp\0' and any(k.startswith(p + '/') for k in repl):
            body = rebuild(b, repl, bo, p)
        else:
            body = b[bo:bo + sz]
        assert len(body) % 4 == 0, (p, len(body))
        offs.append(len(out))
        low = struct.unpack_from('<I', b, a + 8)[0] & 0xFFF
        out += b[a:a + 8] + struct.pack('<I', (len(body) << 12) | low) + body
    struct.pack_into('<%dI' % (n - 1), out, 16, *offs[1:])
    assert offs[0] == hdr
    return bytes(out)
