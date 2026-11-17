"""크로노 크로스 숨은 파일 표(LBA 24~35, u32 항목: 하위 24비트=LBA, 상위 8비트=?) 읽기."""
import struct, sys
S=2352
class Disc:
    def __init__(s,path):
        s.f=open(path,'rb')
        import os; s.nsec=os.path.getsize(path)//S
        raw=b''.join(s.sec(24+i) for i in range(12))
        s.ent=[struct.unpack_from('<I',raw,i*4)[0] for i in range(len(raw)//4)]
    def sec(s,l):
        s.f.seek(l*S+24); return s.f.read(2048)
    def raw(s,l):
        s.f.seek(l*S); return s.f.read(S)
    def lba(s,i): return s.ent[i]&0x7FFFFF
    def dummy(s,i): return bool(s.ent[i]&0x800000)
    def hi(s,i): return s.ent[i]>>24
