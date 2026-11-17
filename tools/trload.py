"""받은 번역(my files/번역/*.tsv) 읽기 — 파일 이름 «_ko» 꼬리 무시, id 로 대조"""
import os, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'my files', '번역')
TSV = os.path.join(ROOT, 'my files', 'tsv')

def rows(d):
    out = {}
    for p in sorted(glob.glob(os.path.join(d, '*.tsv'))):
        b = os.path.basename(p).replace('_ko', '')
        for l in open(p, encoding='utf-8-sig').read().splitlines()[1:]:
            f = l.split('\t')
            while len(f) < 6: f.append('')
            out[f[0]] = dict(id=f[0], kind=f[1], loc=f[2], budget=f[3], jp=f[4], ko=f[5], file=b)
    return out
