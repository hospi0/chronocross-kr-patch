"""SLPS_023.64 (원본/오라클) 역어셈. 사용: dis.py <1|ko1> 시작주소 개수"""
import capstone,sys
nm=sys.argv[1]; a=int(sys.argv[2],16); n=int(sys.argv[3])
b=open(f'work/files/{nm}_0000.bin','rb').read()
md=capstone.Cs(capstone.CS_ARCH_MIPS,capstone.CS_MODE_MIPS32+capstone.CS_MODE_LITTLE_ENDIAN)
o=a-0x80010000+0x800
for ins in md.disasm(b[o:o+n*4],a): print(hex(ins.address)[2:],ins.mnemonic,ins.op_str)
