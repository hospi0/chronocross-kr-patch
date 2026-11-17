"""기존 한글판(KO_20260809)이 실행 파일에 넣은 «버그 수정» 코드 이식 — 번역·글꼴 훅이 아닌 것만(2026-11-16 전수 대조).
1) 0x8002B3D4: 카운터(0x80071C88)가 음수가 되면 원본은 오류 처리기 0x80029D44 를 부름(→ 0x803374F8 개발기 램, 실기·에뮬에선 멈춤)
   → 기존 한글판: 카운터를 0 으로 되돌리고 계속(sw zero,0x1c88(v1); nop; nop)
2) 0x800A1DE0: 표에서 읽은 값×4 를 오프셋으로 쓰는 자리에 범위 검사(0x2B4 이상이면 0) — 0x80048350 의 6낱말 스텁으로 갔다 옴
   (스텁 자리 0x80048350~0x80048367 = 기존 한글판이 쓰던 구역, 우리 훅·BUF(0x800480CC~0x8004819D)와 안 겹침)
파일 40 의 메뉴 수정은 menuvsync_fix.py."""
import struct

EXE_BASE = 0x80010000 - 0x800
EDITS = [
    (0x8002B3D4, '0780043c 519d000c 5898842c', 'ac1c0000 00000000 00000000'.replace('ac1c0000', '881c60ac')),
    (0x800A1DE0, '00000000', None),            # 아래에서 j 0x80048350 로
]
STUB_AT = 0x80048350


def stub():
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import mipsasm
    L = [('sltiu', 'v1', 'v0', 0x2B4), ('bne', 'v1', 'zero', 'OK'), ('nop',), ('addu', 'v0', 'zero', 'zero'),
         'OK', ('j', 'BACK'), ('nop',)]
    b, _ = mipsasm.assemble(L, STUB_AT, extra={'BACK': 0x800A1DE8})
    return b


def patch(exe, ko=None):
    exe = bytearray(exe)
    o = 0x8002B3D4 - EXE_BASE
    assert exe[o:o + 12] == bytes.fromhex('0780043c51a7000c58988424'), '0x8002B3D4 원본 다름'
    exe[o:o + 12] = struct.pack('<3I', 0xAC601C88, 0, 0)      # sw zero,0x1c88(v1) ; nop ; nop
    o = 0x800A1DE0 - EXE_BASE
    assert exe[o:o + 4] == bytes(4), '0x800A1DE0 원본 다름'
    exe[o:o + 4] = struct.pack('<I', (0x02 << 26) | ((STUB_AT >> 2) & 0x3FFFFFF))
    s = stub(); o = STUB_AT - EXE_BASE; exe[o:o + len(s)] = s
    if ko is not None:      # 검산: 기존 한글판과 같은 바이트
        for a, n in ((0x8002B3D4, 12), (0x800A1DE0, 4), (STUB_AT, len(s))):
            oo = a - EXE_BASE
            assert exe[oo:oo + n] == ko[oo:oo + n], ('기존 한글판과 다름', hex(a), exe[oo:oo + n].hex(), ko[oo:oo + n].hex())
    return bytes(exe)


if __name__ == '__main__':
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ccget import get_exact
    for d in ('1', '2'):
        patch(get_exact(d, 0), get_exact('ko' + d, 0)); print('디스크', d, '기존 한글판과 같음')
