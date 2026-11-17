"""PS1 ISO9660 reader for MODE2/2352 raw images (Baroque 도구 복사)."""
import struct, os
SEC=2352
def _b32(b,o): return struct.unpack('<I',b[o:o+4])[0]
class Iso:
    def __init__(self, path):
        self.path=path; self.f=open(path,'rb')
        self.files=self._walk_root()
    def sector(self, lba):
        self.f.seek(lba*SEC+24); return self.f.read(2048)
    def _walk_root(self):
        pvd=self.sector(16)
        assert pvd[1:6]==b'CD001', 'not a PVD'
        root=pvd[156:156+34]
        out=[]
        self._walk(_b32(root,2), _b32(root,10), '', out)
        return out
    def _walk(self, lba, length, path, out):
        data=b''.join(self.sector(lba+i) for i in range((length+2047)//2048))
        off=0
        while off<len(data):
            rl=data[off]
            if rl==0:
                off=(off//2048+1)*2048; continue
            rec=data[off:off+rl]
            ext=_b32(rec,2); dl=_b32(rec,10); flags=rec[25]; nlen=rec[32]
            name=rec[33:33+nlen]
            if not (nlen==1 and name in (b'\x00',b'\x01')):
                nm=name.decode('latin1').split(';')[0]
                full=path+'/'+nm
                if flags&2: self._walk(ext,dl,full,out)
                else: out.append((full,ext,dl))
            off+=rl
    def read_file(self, full):
        for f,lba,size in self.files:
            if f==full:
                return b''.join(self.sector(lba+i) for i in range((size+2047)//2048))[:size]
        raise KeyError(full)
    def dump(self, outdir, skip_ext=('.XA','.STR','.RAW')):
        os.makedirs(outdir, exist_ok=True)
        n=0
        for full,lba,size in self.files:
            if full.upper().endswith(skip_ext): continue
            data=b''.join(self.sector(lba+i) for i in range((size+2047)//2048))[:size]
            open(os.path.join(outdir, full.strip('/').replace('/','_')),'wb').write(data)
            n+=1
        return n
