"""실행 파일 문자열 표(RAM 0x800600E0, 함수 0x80019768): u32 n, u32 묶음오프셋[n+1], 묶음 = u16 오프셋 표 + 문자열(대사 인코딩)"""
import sys,os,struct; sys.path.insert(0,os.path.dirname(__file__)); import ccmsg,ccdecode
BASE=0x800600E0
def groups(a):
    o=BASE-0x80010000+0x800; n=struct.unpack_from('<I',a,o)[0]
    offs=struct.unpack_from('<%dI'%(n+1),a,o+4)
    out=[]
    for gi in range(n):
        g0=o+offs[gi]; g1=o+offs[gi+1] if gi+1<=n else None
        first=struct.unpack_from('<H',a,g0)[0]; k=first//2
        so=[struct.unpack_from('<H',a,g0+2*i)[0] for i in range(k)]
        out.append((gi,g0,g1,so))
    return out
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    a=open(sys.argv[1] if len(sys.argv)>1 else 'work/files/1_0000.bin','rb').read()
    for gi,g0,g1,so in groups(a):
        print(f'== 묶음 {gi} 문자열 {len(so)}')
        for si,s in enumerate(so[:6]):
            try: t,_=ccmsg.parse(a,g0+s); print('  ',si,ccdecode.text(t).replace('\n','⏎')[:60])
            except Exception as e: print('  ',si,'ERR',e)
