"""말투 칸 범용 대사 «말투 섞임» 검출 (2026-11-17) — 존댓말(요·포) 화자로 펼쳤을 때 반말로 끝나는 문장
  python tools/slot_register.py → work/slot_review/_말투섞임.tsv
범용 대사 = 화자가 {15/18:XX}(파티 슬롯) 인 줄. 고정 화자({08:XX})줄은 그 인물 말투로만 보면 되므로 제외"""
import os, sys, re, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import slot_check as SC, krenc
REP = {'반': 1, '반2': 2, '네': 3, '게': 5, '요': 6, '포': 12}
CASUAL = re.compile(r'(자|어|아|해|지|야|군|네|냐|니|마|라|래|걸|게|까|봐|줘|돼|와|가|나|구나|잖아|거든)$')
def sentences(t):
    """쪽(▼) 안의 줄을 이어 붙여 문장(. ! ? … 로 끝) 단위로 — 선택지 줄(　　　)은 뺌, 쪽 끝 미완 문장도 하나로"""
    for page in t.split('\n▼\n'):
        body = ' '.join(l.strip('　 ') for l in page.split('\n') if l.strip() and not l.startswith('　　　'))
        for s in re.findall(r'[^.!?…]+(?:[.!?…]+|$)', body):
            s2 = re.sub(r'[.!?…~～ー」』\s,]+$', '', s.strip())
            if s2: yield s2
def main():
    slots, names, lines = SC.load_real()
    out = []
    for lid, jp, ko in lines:
        if not re.match(r'(\{1[58]:..\})', ko) and not ko.startswith('「') and not ko.startswith('　'): continue
        t = SC.expand(ko, REP['요'], slots, names)
        body = t.split('\n', 1)[1] if '\n' in t else t
        bad = [s for s in sentences(body) if CASUAL.search(re.sub(r'[^가-힣]+$', '', s)) and not s.endswith('요')]
        g = set(re.findall(r'\{12:(01|02|04|05|07|08|0B)\}', jp))       # 원문에 문법 칸(종결)이 있던 줄만 — 원문도 칸 없이 반말인 줄은 원작 그대로
        if bad and g: out.append((lid, ' / '.join(bad)[:120], ko))
    p = os.path.join(SC.OUT, '_말투섞임.tsv')
    with open(p, 'w', encoding='utf8') as f:
        f.write('id\t요 말투로 반말 끝 문장\tKO\n')
        for o in out: f.write('\t'.join(o) + '\n')
    print('요 말투 섞임 줄', len(out), '→', p)
if __name__ == '__main__': main()
