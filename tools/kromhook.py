"""SJIS 메뉴 «BIOS 내장» 훅 (2026-11-16)

Krom2RawAdd 스텁 0x80022510(파일 38·40·226 이 부름, a0 = SJIS 코드 big-endian 값) 첫 명령을 «j HOOK» 으로.
HOOK(0x800480CC — 어디서도 참조 안 되는 디버그 함수 자리, 원본 스테이트 RAM 에서도 불변 확인):
  한글 코드 = 첫 바이트 0xE0~0xE9 · 둘째 0x40~0xFF → 칸 = (첫−0xE0)·192 + (둘째−0x40)
  → 대사 글꼴(0x8005670C, 22B/칸 u16 LE 11행)을 BIOS 형식(16×15, 행 = 큰 바이트 먼저)으로 BUF 에: 위 2행 0 · 11행 · 아래 2행 0
  → v0 = BUF 반환. 그 밖 코드는 원래대로 BIOS B0:51.
"""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mipsasm
STUB = 0x80022510
HOOK = 0x800480CC
BUF = 0x80048180          # 훅 바로 뒤, 30B — 기존 패치가 덮어 쓰고도 문제없던 구역(0x800480CC~0x80048364) 안
# ★2026-11-16: 예전 BUF 0x80048900 은 «미사용 함수»가 아니라 실제로 쓰이는 함수(파일/CD 계열, fp 프레임)의 끝부분이었다.
#   글리프를 쓸 때마다 그 함수 맺음(sw·move sp,fp …)이 깨져 → 메인 메뉴 스테이터스 진입 멈춤(인터럽트 꺼진 채 대기)·
#   세 번째 동료 고정. 기존 패치는 0x800480CC~0x80048364 만 써서 멀쩡했다.
SAFE_END = 0x80048364     # 이 주소를 넘어 쓰지 말 것
FONT = 0x8005670C
EXE_BASE = 0x80010000 - 0x800

def hilo(a):
    lo = a & 0xFFFF; hi = (a >> 16) + (1 if lo & 0x8000 else 0)
    return hi & 0xFFFF, lo

def code():
    bh, bl = hilo(BUF); fh, fl = hilo(FONT)
    L = [
        'HOOK',
        ('srl', 't0', 'a0', 8),
        ('addiu', 't0', 't0', -0xE0 & 0xFFFF),
        ('sltiu', 't1', 't0', 10),
        ('beq', 't1', 'zero', 'BIOS'),
        ('andi', 't2', 'a0', 0xFF),
        ('addiu', 't2', 't2', -0x40 & 0xFFFF),
        ('sltiu', 't1', 't2', 192),
        ('beq', 't1', 'zero', 'BIOS'),
        ('sll', 't3', 't0', 7),
        ('sll', 't4', 't0', 6),
        ('addu', 't3', 't3', 't4'),
        ('addu', 't0', 't3', 't2'),          # 칸 번호
        ('sll', 't1', 't0', 4),
        ('sll', 't2', 't0', 2),
        ('addu', 't1', 't1', 't2'),
        ('sll', 't2', 't0', 1),
        ('addu', 't1', 't1', 't2'),          # ×22
        ('lui', 't2', fh),
        ('addiu', 't2', 't2', fl),
        ('addu', 't1', 't1', 't2'),          # 원본 글리프 주소
        ('lui', 'v0', bh),
        ('addiu', 'v0', 'v0', bl),           # 반환 = BUF
        ('sh', 'zero', 0, 'v0'),
        ('sh', 'zero', 2, 'v0'),
        ('addiu', 't3', 'v0', 4),
        ('addiu', 't4', 'zero', 11),
        'LOOP',
        ('lhu', 't0', 0, 't1'),
        ('addiu', 't1', 't1', 2),            # 로드 지연 슬롯 사이 명령
        ('srl', 't2', 't0', 8),
        ('andi', 't0', 't0', 0xFF),
        ('sll', 't0', 't0', 8),
        ('or', 't2', 't2', 't0'),
        ('sh', 't2', 0, 't3'),
        ('addiu', 't4', 't4', -1 & 0xFFFF),
        ('bne', 't4', 'zero', 'LOOP'),
        ('addiu', 't3', 't3', 2),            # 지연 슬롯
        ('sh', 'zero', 0, 't3'),
        ('sh', 'zero', 2, 't3'),
        ('jr', 'ra'),
        ('nop',),
        'BIOS',
        ('addiu', 't2', 'zero', 0xB0),
        ('addiu', 't1', 'zero', 0x51),
        ('jr', 't2'),
        ('nop',),
    ]
    return mipsasm.assemble(L, HOOK)

def patch(exe):
    exe = bytearray(exe)
    b, lab = code()
    assert HOOK + len(b) <= BUF and BUF + 30 <= SAFE_END, '훅·BUF 가 안전 구역 밖'
    o = HOOK - EXE_BASE; exe[o:o + len(b)] = b
    o = BUF - EXE_BASE; exe[o:o + 30] = bytes(30)
    j = (0x02 << 26) | ((HOOK >> 2) & 0x3FFFFFF)
    struct.pack_into('<I', exe, STUB - EXE_BASE, j)       # 둘째 명령(addiu t1,0x51)은 지연 슬롯으로 그대로
    return bytes(exe)

def kr_code(idx):
    """대사 글꼴 칸 → SJIS 바이트 2개"""
    q, r = divmod(idx, 192); assert q < 10
    return bytes([0xE0 + q, 0x40 + r])

def test():
    exe = open(os.path.join(os.path.dirname(HERE), 'work', 'files', '1_0000.bin'), 'rb').read()
    p = patch(exe)
    mem = p[0x800:]          # RAM 0x80010000 부터
    fo = FONT - 0x80010000
    def expect(idx):
        rows = struct.unpack_from('<11H', mem, fo + idx * 22)
        out = bytearray(4)
        for v in rows: out += bytes([v >> 8, v & 0xFF])
        return bytes(out + bytearray(4))
    ok = 0
    for idx in (0, 1, 0x56, 0x14C, 191, 192, 1000, 1789):
        c = kr_code(idx); a0 = (c[0] << 8) | c[1]
        s = mipsasm.Sim(mem, 0x80010000); s.r[mipsasm.R['a0']] = a0; s.r[mipsasm.R['ra']] = 0x80001234
        res, r = s.run(STUB, mem, 0x80010000)
        assert res == 'RET' and s.exit_pc == 0x80001234 and r[2] == BUF, (idx, res, hex(r[2]))
        got = bytes(s.m[BUF - 0x80010000:BUF - 0x80010000 + 30])
        assert got == expect(idx), idx
        # 훅·BUF 밖 침범 0
        diff = [i for i in range(len(mem)) if s.m[i] != mem[i] and not (BUF - 0x80010000 <= i < BUF - 0x80010000 + 30)]
        assert not diff, ('침범', hex(diff[0] + 0x80010000))
        ok += 1
    for a0 in (0x8140, 0x82A0, 0x889F, 0xDF40, 0xEA40, 0xE03F, 0xE000, 0x0041):
        s = mipsasm.Sim(mem, 0x80010000); s.r[mipsasm.R['a0']] = a0; s.r[mipsasm.R['ra']] = 0x80001234
        res, r = s.run(STUB, mem, 0x80010000)
        assert res == 'BIOS' and r[mipsasm.R['t1']] == 0x51 and r[mipsasm.R['a0']] == a0, (hex(a0), res)
        ok += 1
    b, lab = code()
    print(f'훅 {len(b)}B @ {HOOK:#x}, BUF {BUF:#x} — 시험 {ok}건 통과 (한글 8 · BIOS 경로 8)')

if __name__ == '__main__':
    test()
