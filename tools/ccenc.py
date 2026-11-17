"""글자 → 대사 인코딩 바이트 (원문 검색용·빌드용 기초)"""
import os,sys; sys.path.insert(0,os.path.dirname(__file__)); import cctable
REV={}
for i,c in cctable.table().items():
    if len(c)==1 and c not in REV: REV[c]=i
def code(i):
    if i<0xd8: return bytes([i+0x20])
    v=i+0x20; return bytes([0xf7+v//256, v%256])
def enc(s): return b''.join(code(REV[c]) for c in s)
