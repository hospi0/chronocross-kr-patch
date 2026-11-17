"""오버레이 역어셈. 사용: ovldis.py <파일bin> <적재주소hex> <시작주소hex> <개수>"""
import capstone,sys
b=open(sys.argv[1],'rb').read(); base=int(sys.argv[2],16); a=int(sys.argv[3],16); n=int(sys.argv[4])
md=capstone.Cs(capstone.CS_ARCH_MIPS,capstone.CS_MODE_MIPS32+capstone.CS_MODE_LITTLE_ENDIAN)
o=a-base
for ins in md.disasm(b[o:o+n*4],a): print(hex(ins.address)[2:],ins.mnemonic,ins.op_str)
