"""실행 파일 글꼴(RAM 0x8005670C, 22B/칸, u16 LE 행 11줄, bit15=왼쪽) 읽기"""
import struct, numpy as np
BASE=0x8005670C
def load(path='work/files/1_0000.bin', end=0x800600E0):
    a=open(path,'rb').read(); o=BASE-0x80010000+0x800; n=(end-BASE)//22
    g=np.zeros((n,11,16),np.uint8)
    for i in range(n):
        rows=struct.unpack_from('<11H',a,o+i*22)
        for y,v in enumerate(rows):
            for x in range(16): g[i,y,x]=(v>>(15-x))&1
    return g
