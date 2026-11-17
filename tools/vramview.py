"""VRAM(1024×512 u16) 보기: 16비트 색 그림 + 4bpp 색인 그림(회색). 사용: vramview.py vram.bin 출력접두"""
import sys,numpy as np
from PIL import Image
v=np.frombuffer(open(sys.argv[1],'rb').read(),'<u2').reshape(512,1024)
r=(v&31)<<3; g=((v>>5)&31)<<3; b=((v>>10)&31)<<3
Image.fromarray(np.dstack([r,g,b]).astype(np.uint8)).save(sys.argv[2]+'_16.png')
idx=np.zeros((512,4096),np.uint8)
for k in range(4): idx[:,k::4]=(v>>(4*k))&15
Image.fromarray((idx*17).astype(np.uint8)).save(sys.argv[2]+'_4bpp.png')
