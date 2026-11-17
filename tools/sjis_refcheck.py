"""SJIS 문자열 누락 검산 — 오버레이(적재 0x801D2800)의 코드 참조(lui+addiu/ori)·데이터 포인터가 가리키는 SJIS 시작점을
추출 목록(work/text/master.json sjis)과 대조. → 누락(참조O·추출X) / 참조 없음(추출O·참조X)"""
import sys,os,json,struct,collections
BASE=0x801D2800
def refs(b):
    out=collections.defaultdict(list); regs={}
    for i in range(0,len(b)-3,4):
        w=struct.unpack_from('<I',b,i)[0]; op=w>>26; rs=(w>>21)&31; rt=(w>>16)&31; imm=w&0xffff
        simm=imm-0x10000 if imm&0x8000 else imm
        if op==0xf: regs[rt]=(imm<<16,i)
        elif op in (9,0xd) and rs in regs and i-regs[rs][1]<=64:
            a=(regs[rs][0]+(imm if op==0xd else simm))&0xffffffff
            if BASE<=a<BASE+len(b): out[a-BASE].append(('code',i))
        if BASE<=w<BASE+len(b): out[w-BASE].append(('data',i))
    return out
def is_sjis_start(b,o):
    if o>=len(b)-1: return False
    c=b[o]
    if not (0x81<=c<=0x9f or 0xe0<=c<=0xef): return False
    try: b[o:o+2].decode('cp932'); return True
    except: return False
def read(b,o):
    j=o; s=''
    while j<len(b)-1 and b[j]:
        c=b[j]
        if 0x81<=c<=0x9f or 0xe0<=c<=0xef:
            try: s+=b[j:j+2].decode('cp932'); j+=2; continue
            except: break
        s+=chr(c) if 0x20<=c<0x7f else f'<{c:02X}>'; j+=1
    return s
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    M=json.load(open('work/text/master.json',encoding='utf8'))
    for fi in (38,40,226):
        b=open(f'work/files/1_{fi:04d}.bin','rb').read()
        have={int(m['locs'][0].split('@')[1],16) for m in M if m['kind']=='sjis' and m['locs'][0].startswith(f'sjis:{fi}@')}
        R=refs(b)
        miss=[(o,read(b,o)) for o in sorted(R) if is_sjis_start(b,o) and o not in have]
        # 문자열 중간을 가리키는 참조(추출 문자열 안쪽)
        unref=[o for o in sorted(have) if o not in R]
        print(f'== {fi}: 추출 {len(have)} · 참조된 SJIS 시작 {sum(1 for o in R if is_sjis_start(b,o))} · 누락 {len(miss)} · 참조 없는 추출 {len(unref)}')
        for o,s in miss[:60]: print('  누락',hex(o),R[o][:2],s[:40])
        for o in unref[:40]: print('  참조없음',hex(o),read(b,o)[:30])
