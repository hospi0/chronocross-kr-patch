"""파일 안 SJIS 2바이트 문자열(가나·한자 포함, 4자 이상) 찾기. 사용: sjis_scan.py 파일 [적재주소hex]"""
import sys,re
b=open(sys.argv[1],'rb').read(); base=int(sys.argv[2],16) if len(sys.argv)>2 else 0
sys.stdout.reconfigure(encoding='utf-8')
i=0
while i<len(b)-1:
    j=i; s=''
    while j<len(b)-1:
        c=b[j]
        if (0x81<=c<=0x9f or 0xe0<=c<=0xef) and 0x40<=b[j+1]<=0xfc and b[j+1]!=0x7f:
            try: s+=b[j:j+2].decode('cp932'); j+=2; continue
            except: break
        elif 0x20<=c<0x7f and s: s+=chr(c); j+=1; continue
        break
    if len(re.findall(r'[぀-ヿ一-鿿]',s))>=3:
        print(hex(base+i) if base else hex(i), s); i=j
    else: i+=1
