"""대사 글꼴 칸 → 글자 표. 가나·기호 = 칸 순서로 손 확정(2026-11-16), 한자 = work/glyphs/kanji.tsv(판독 결과)."""
import os
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
HALF="()‐,+./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz=!\"$%&*:?-[]｡ｱｴ"
HIRA="あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
HIRA_D="がぎぐげござじずぜぞだぢづでどばびぶべぼ"+"ぱぴぷぺぽ"+"ぁぃぅぇぉっゃゅょ"
SYM="。「」＃ー～…？！・"
ZEN="０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ／、－‥"
KATA="アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
KATA_D="ガギグゲゴザジズゼゾダヂヅデドバビブベボ"+"パピプペポ"+"ァィゥェォッャュョヴヶ"
def base_table():
    t={0:' '}
    for i,c in enumerate(HALF): t[1+i]=c
    t[0x55]='　'
    s=HIRA+HIRA_D+SYM+ZEN
    for i,c in enumerate(s): t[0x56+i]=c
    assert 0x56+len(s)==0xD8, hex(0x56+len(s))
    for i,c in enumerate("ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ"+KATA+KATA_D): t[0xE0+i]=c
    assert 0xE0+26+len(KATA)+len(KATA_D)==0x14C
    return t
def table():
    t=base_table()
    p=os.path.join(ROOT,'work','glyphs','kanji.tsv')
    if os.path.exists(p):
        for l in open(p,encoding='utf8'):
            f=l.rstrip('\n').split('\t')
            if len(f)>=2 and f[1]: t[int(f[0])]=f[1]
    return t
