"""크로노 크로스 디스크 재구성기 (2026-11-16)

숨은 파일 표(LBA 24~35, u32: 하위 23비트 LBA · 비트23 빈 항목 · 상위 8비트 = 마지막 섹터 빈 바이트/8)
게임의 크기 계산(실행 파일 0x80044734): 크기 = (다음 항목 LBA − 이 항목 LBA)·2048 − 상위·8, 빈 항목 = 0
→ 규칙: 번호 순서대로 연속 배치, 빈 항목·끝 표지 = 다음 파일 시작 LBA

사용(모듈): rebuild(src_bin, out_bin, repl={파일번호: bytes}, raw_repl={파일번호: raw 2352 섹터 bytes})
  repl     = 내용(2048B 섹터, Form 1)으로 바꿀 파일 — 서브헤더는 원본 첫·마지막 섹터 것을 씀
  raw_repl = raw 섹터째 바꿀 파일(동영상 등) — 섹터 수가 같아야 함(STR 내부 구조 보존)
옮긴 섹터는 헤더 MSF 만 새 위치로(EDC 는 헤더 제외, Form 1 ECC 는 헤더 0 으로 계산 → 그대로 유효),
내용이 바뀐 Form 1 섹터만 EDC/ECC 재계산. 시스템 영역·실행 파일(LBA 38, ISO9660 에서 가리킴)은 제자리.
"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdecc

S = 2352
TABLE_LBA, TABLE_SECS = 24, 12

def read_table(f):
    f.seek(TABLE_LBA * S)
    raw = b''.join(f.read(S)[24:24 + 2048] for _ in range(TABLE_SECS))
    ent = list(struct.unpack('<%dI' % (len(raw) // 4), raw))
    n = len(ent)
    while n and ent[n - 1] == 0:
        n -= 1
    return ent, n

def rebuild(src, out, repl=None, raw_repl=None, log=print):
    repl = repl or {}; raw_repl = raw_repl or {}
    nsec_src = os.path.getsize(src) // S
    f = open(src, 'rb')
    ent, n = read_table(f)
    L = [e & 0x7FFFFF for e in ent[:n]]
    dm = [bool(e & 0x800000) for e in ent[:n]]
    hi = [e >> 24 for e in ent[:n]]
    first = L[0]                       # 실행 파일(0번) 시작 = 38
    end_src = L[n - 1]                 # 끝 표지 = 마지막 파일 끝
    def rawsecs(lba, cnt):
        f.seek(lba * S); return f.read(cnt * S)
    o = open(out, 'wb')
    o.write(rawsecs(0, first))         # 시스템 영역 (표·PVD 는 나중에 덮어씀)
    cur = first
    new_ent = list(ent)
    for i in range(n - 1):
        if dm[i]:
            new_ent[i] = (ent[i] & 0xFF800000) | cur      # 빈 항목: 다음 파일 시작
            continue
        nxt = L[i + 1]; cnt = nxt - L[i]
        size_old = cnt * 2048 - hi[i] * 8
        if i in repl:
            data = repl[i]
            if i == 0:
                assert len(data) == size_old, '실행 파일은 크기 고정(ISO9660 이 가리킴)'
            # 원본 그대로 + 0 만 덧붙인 경우만 막음(대사가 늘어 뒤 구간이 밀려 끝이 우연히 0 인 맵 515 는 통과 — 2026-11-17)
            raw_old = b''.join(rawsecs(L[i] + j, 1)[24:24 + 2048] for j in range(cnt))[:size_old] if len(data) > size_old and not any(data[size_old:]) else None
            if raw_old is not None and data[:size_old] == raw_old:
                raise SystemExit(f'⛔ 파일 {i}: 원래 크기 {size_old} 뒤가 전부 0 인 {len(data)} B — 섹터 채움을 넘긴 듯(get_exact 쓸 것)')
            cnt_new = (len(data) + 2047) // 2048
            h_new = (cnt_new * 2048 - len(data)) // 8
            src_first = rawsecs(L[i], 1); src_last = rawsecs(nxt - 1, 1)
            buf = bytearray()
            for k in range(cnt_new):
                sec = bytearray(src_first if k < cnt_new - 1 else src_last)
                if (sec[18] & 0x20):                      # 원본이 Form 2 면 Form 1 서브헤더로
                    sec[16:24] = bytes([sec[16], sec[17], 0x08, 0, sec[16], sec[17], 0x08, 0])
                chunk = data[k * 2048:(k + 1) * 2048]
                sec[24:24 + 2048] = chunk + b'\0' * (2048 - len(chunk))
                cdecc.set_header(sec, cur + k)
                cdecc.fix_sector(sec)
                buf += sec
            o.write(buf)
            new_ent[i] = (h_new << 24) | cur
            if cnt_new != cnt or True:
                pass
            cur += cnt_new
        elif i in raw_repl:
            rr = raw_repl[i]; assert len(rr) == cnt * S, '동영상 raw 교체는 섹터 수 동일'
            buf = bytearray(rr)
            for k in range(cnt):
                sec = bytearray(buf[k * S:(k + 1) * S]); cdecc.set_header(sec, cur + k); buf[k * S:(k + 1) * S] = sec
            o.write(buf)
            new_ent[i] = (hi[i] << 24) | cur
            cur += cnt
        else:
            buf = bytearray(rawsecs(L[i], cnt))
            if cur != L[i]:
                for k in range(cnt):
                    sec = bytearray(buf[k * S:(k + 1) * S]); cdecc.set_header(sec, cur + k); buf[k * S:(k + 1) * S] = sec
            o.write(buf)
            new_ent[i] = (hi[i] << 24) | cur
            cur += cnt
    # 끝 표지(남은 빈 항목들)
    for i in range(n - 1, n):
        new_ent[i] = (ent[i] & 0xFF800000) | cur
    tail = nsec_src - end_src           # 포스트갭
    buf = bytearray(rawsecs(end_src, tail))
    for k in range(tail):
        sec = bytearray(buf[k * S:(k + 1) * S]); cdecc.set_header(sec, cur + k); buf[k * S:(k + 1) * S] = sec
    o.write(buf)
    total = cur + tail
    o.close()
    # 표·PVD 갱신
    o = open(out, 'r+b')
    tbl = struct.pack('<%dI' % len(new_ent), *new_ent)
    for k in range(TABLE_SECS):
        o.seek((TABLE_LBA + k) * S); sec = bytearray(o.read(S))
        new = tbl[k * 2048:(k + 1) * 2048]
        if bytes(sec[24:24 + 2048]) != new:
            sec[24:24 + 2048] = new; cdecc.fix_sector(sec); o.seek((TABLE_LBA + k) * S); o.write(sec)
    o.seek(16 * S); pvd = bytearray(o.read(S))
    old_vs = struct.unpack_from('<I', pvd, 24 + 80)[0]
    if old_vs != total:
        struct.pack_into('<I', pvd, 24 + 80, total); struct.pack_into('>I', pvd, 24 + 84, total)
        cdecc.fix_sector(pvd); o.seek(16 * S); o.write(pvd)
    o.close()
    log(f'재구성: {nsec_src} → {total} 섹터 (바꾼 파일 {len(repl)} · raw {len(raw_repl)})')
    return new_ent[:n], total

if __name__ == '__main__':
    rebuild(sys.argv[1], sys.argv[2])
