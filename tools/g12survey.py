"""G12~14 전투 설명서(파일 2543 /help 스프라이트 7쪽) 조사 — 글 조각(CLUT 3FF8·3FF9·3FFA)을 쪽마다 번호 붙여 그림
→ work/g12/survey_pN.png (조각 테두리·번호) + work/g12/pieces.json"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sprtab
from ccget import get_exact
from PIL import Image, ImageDraw

TEXT_CLUT = {0x3FF8, 0x3FF9, 0x3FFA}


def load():
    b = get_exact('1', 2543)
    v = sprtab.vram_from_tims(get_exact('1', 11)); v = sprtab.vram_from_tims(b, v)
    return b, v, sprtab.read(b, 0x2c, 0x2c9c)


if __name__ == '__main__':
    b, v, T = load()
    out = {}
    for i, s in enumerate(T['spr']):
        if not s: continue
        ps = s['pieces']
        x0 = min(p['x'] for p in ps); y0 = min(p['y'] for p in ps)
        im = sprtab.render(v, s, pad=2); sc = 4
        I = Image.fromarray(im).resize((im.shape[1] * sc, im.shape[0] * sc), Image.NEAREST); d = ImageDraw.Draw(I)
        rows = []
        for k, p in enumerate(ps):
            if p['clut'] not in TEXT_CLUT: continue
            X = (p['x'] - x0 + 2) * sc; Y = (p['y'] - y0 + 2) * sc
            d.rectangle([X, Y, X + p['w'] * sc - 1, Y + p['h'] * sc - 1], outline=(255, 0, 0))
            d.text((X + 1, Y + 1), str(k), fill=(255, 255, 0))
            rows.append(dict(k=k, **{q: p[q] for q in ('x', 'y', 'u', 'v', 'w', 'h', 'tp', 'clut', 'fl')}))
        I.save('work/g12/survey_p%d.png' % (i + 1)); out[i + 1] = rows
        print(i + 1, '글 조각', len(rows), '/', len(ps))
    json.dump(out, open('work/g12/pieces.json', 'w'), indent=0)
