"""메뉴 오버레이(파일 40, 적재 0x801D2800) — 하위 메뉴(스테이터스 등)에서 돌아올 때 멈추는 원본 경쟁 조건 수정.

구조: 메인 메뉴 루프는 하위 메뉴 함수를 부르는 동안 0x801F375C = 1 로 두고(0x801D3D60), 돌아오면 바로 0으로(0x801D3D6C).
  VSync 인터럽트 안 작업 0x801D3878 은 375C=0 이면 «GPU 놀면 필드 비트 바뀔 때까지» 돌며 버퍼를 바꾼다.
  하위 메뉴에서 막 돌아온 프레임(화면 모드 전환 중)에 이 대기에 들어가면 필드 비트가 안 바뀌어 인터럽트 안에서 영영 돈다 → 멈춤
  (work/states_user/크래시7·8 — SR=0x40000404, 0x801D38B4 루프). 우리 BIOS 글꼴 훅이 빨라 GPU 가 일찍 놀면서 자주 드러남.
수정 = 기존 한글판(KO_20260809)이 넣은 것과 같은 두 낱말: 375C=0 을 돌아온 직후(0x801D3D6C)에서 빼고,
  메인 루프의 프레임 맞춤 대기(0x801D3E5C~0x801D3E74)가 끝난 뒤(0x801D3E7C, 원래 nop)로 옮김.
※ 2026-11-16 1차로 대기 루프에 상한만 둔 수정은 멈춤 대신 매 프레임 3프레임씩 늘어져 실패 — 폐기
"""
import struct

BASE = 0x801D2800
EDITS = [  # (주소, 원본 낱말, 새 낱말)
    (0x801D3D6C, 0xAFC0375C, 0x00000000),   # sw zero,0x375c(fp) → nop
    (0x801D3E7C, 0x00000000, 0xAFC0375C),   # nop → sw zero,0x375c(fp)
]


def patch(f40):
    f40 = bytearray(f40)
    for a, old, new in EDITS:
        o = a - BASE
        assert struct.unpack_from('<I', f40, o)[0] == old, ('원본 코드가 다름', hex(a))
        struct.pack_into('<I', f40, o, new)
    return bytes(f40)


if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ccget import get_exact
    for d in ('1', '2'):
        b = get_exact(d, 40); n = patch(b); k = get_exact('ko' + d, 40)
        print('디스크', d, '기존 한글판과 같은 낱말', all(n[a - BASE:a - BASE + 4] == k[a - BASE:a - BASE + 4] for a, _, _ in EDITS))
