"""오버레이 적재 주소 추정 — jal 대상과 함수 머리(addiu sp,-x) 위치 차이의 최빈값. 사용: ovlbase.py 파일bin"""
import struct,collections,sys
def guess(b):
    tg=set();P=[]
    for i in range(0,len(b)-4,4):
        w=struct.unpack_from('<I',b,i)[0]
        if w>>26==3: tg.add(((w&0x3ffffff)<<2)|0x80000000)
        if (w>>16)==0x27bd and (w&0x8000): P.append(i)
    c=collections.Counter()
    for t in tg:
        for p in P:
            base=t-p
            if 0x80010000<base<0x80200000: c[base]+=1
    return c.most_common(3)
if __name__=='__main__':
    for p in sys.argv[1:]: print(p,[(hex(a),n) for a,n in guess(open(p,'rb').read())])
