"""말투 칸 대사 말투별 나란히 보기 (2026-11-17) → work/slot_review/_말투별_나란히.txt
문장마다 말투(반 키드 · 반2 알프 · 네 이시토 · 게 자코츠 · 요 리델 · 포 포슈르)별로 다르게 찍히는 문장만"""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import slot_check as SC, slot_register as SR, krenc
WHO = [('반', 1), ('반2', 2), ('네', 3), ('게', 5), ('요', 6), ('포', 12)]
def main():
    slots, names, lines = SC.load_real()
    seen = set(); out = []
    for lid, jp, ko in lines:
        if not re.match(r'\{1[58]:..\}|「|　', ko): continue          # 범용 화자 줄만(고정 화자 {08:XX} 줄은 그 인물 값으로만 찍힘)
        key = re.sub(r'\{1[58]:0.\}', '', ko)
        if key in seen: continue
        seen.add(key)
        rs = []
        for nm, w in WHO:
            t = krenc.normalize(SC.expand(ko, w, slots, names))
            body = t.split('\n', 1)[1] if t.startswith(('{', '「')) is False and '\n' in t else t
            rs.append(list(SR.sentences(body)))
        if len({len(r) for r in rs}) != 1: out.append(f'[{lid}] 문장 수 다름'); continue
        diff = [k for k in range(len(rs[0])) if len({r[k] for r in rs}) > 1]
        if not diff: continue
        out.append(f'[{lid}]')
        for k in diff:
            out.append('  ' + ' │ '.join(f'{WHO[j][0]}:{rs[j][k]}' for j in range(len(WHO))))
    p = os.path.join(SC.OUT, '_말투별_나란히.txt')
    open(p, 'w', encoding='utf8').write('\n'.join(out))
    print('묶음', len(seen), '· 말투로 달라지는 줄', sum(1 for o in out if o.startswith('[')), '→', p)
if __name__ == '__main__': main()
