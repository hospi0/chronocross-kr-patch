"""파일 안 대사 인코딩 문자열 후보(0 종결, 글자 4+, 상용자 85%+) 찾기. 사용: cctext_scan.py 파일..."""
import sys,os,json; sys.path.insert(0,os.path.dirname(__file__)); import ccmsg,ccdecode
common=set(json.load(open('work/common_chars.json',encoding='utf8')))
def scan(b):
    i=0;n=len(b);res=[]
    while i<n:
        if i and b[i-1]!=0: i+=1; continue
        try: t,e=ccmsg.parse(b,i)
        except Exception: i+=1; continue
        gl=[ccdecode.T.get(x[1],'?') for x in t if x[0]=='g']
        if len(gl)>=3 and sum(c in common for c in gl)>=0.85*len(gl) and e-i<600:
            res.append((i,ccdecode.text(t).replace('\n','⏎'))); i=e
        else: i+=1
    return res
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    for p in sys.argv[1:]:
        r=scan(open(p,'rb').read()); print('==',p,len(r))
        for o,s in r[:12]: print('  ',hex(o),s[:60])
