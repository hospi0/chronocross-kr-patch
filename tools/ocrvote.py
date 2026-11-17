"""OCR 결과(.txt)를 칸 번호별 표로 모은다 → work/glyphs/ocr_votes.json ; 가나 정답률도 보고"""
import sys,os,json,collections,unicodedata; sys.path.insert(0,os.path.dirname(__file__)); import cctable
sys.stdout.reconfigure(encoding='utf-8')
L=json.load(open('work/ocr/layout.json')); P,X0,LH,GH=L['pitch'],L['x0'],L['lineh'],L['gh']
t=cctable.table(); nk=lambda c: unicodedata.normalize('NFKC',c)
votes=collections.defaultdict(collections.Counter); ok=tot=0
for im in L['images']:
    p='work/ocr/'+im['img'].replace('.png','.txt')
    for row in open(p,encoding='utf-8-sig'):
        f=row.rstrip('\n').split('\t')
        if len(f)<5: continue
        text=f[0].replace(' ',''); X,Y,W,H=map(float,f[1:5]); cy=Y+H/2
        li=min(range(len(im['lines'])),key=lambda i:abs(im['lines'][i]['y']+GH/2-cy)); line=im['lines'][li]
        if abs(line['y']+GH/2-cy)>LH/2: continue
        n=len(text)
        for i,ch in enumerate(text):
            j=int((X+(i+0.5)*W/n-X0)//P)
            if 0<=j<len(line['cells']) and line['cells'][j] is not None:
                c=line['cells'][j]; votes[c][ch]+=1
                if c<0x14c: tot+=1; ok+= nk(ch)==nk(t.get(c,'?'))
print('가나·기호 OCR 일치 %d/%d'%(ok,tot))
json.dump({k:dict(v) for k,v in votes.items()},open('work/glyphs/ocr_votes.json','w',encoding='utf8'),ensure_ascii=False)
kt=[l.split('\t') for l in open('work/glyphs/kanji.tsv',encoding='utf8').read().splitlines()]
agree=dis=nov=0; out=[]
for r in kt:
    i=int(r[0]); v=votes.get(i)
    top=v.most_common(1)[0] if v else None
    if r[2]=='exact':
        if top and top[0]!=r[1] and top[1]>=3: out.append(('EXACT≠OCR',i,r[1],v.most_common(3)))
        continue
    if not v: nov+=1; out.append(('noOCR',i,r[1],[])); continue
    if top[0]==r[1]: agree+=1
    else: dis+=1; out.append(('DIS',i,r[1],v.most_common(3)))
print('애매 칸: OCR=모양 %d · 불일치 %d · OCR 없음 %d'%(agree,dis,nov))
with open('work/glyphs/ocr_check.tsv','w',encoding='utf8') as f:
    for k,i,c,v in out: f.write(f'{k}\t{i:04X}\t{c}\t{" ".join(a+str(b) for a,b in v)}\n')
