# 크로노 크로스 (PS1 일본판, 2장) 한글 패치

- 원본: `Chrono Cross (Japan, Asia) (Disc 1).bin` / `(Disc 2).bin` (각 1트랙, MODE2/2352)
- 배포 파일은 릴리즈의 zip(디스크별 xdelta + 적용 bat + readme)을 쓰세요.
- 빌드: `tools/build_full.py --disc 1|2`(번역 TSV → 대사·메뉴·전투·프로필·그림·글꼴·오프닝 동영상 → 디스크) → `tools/make_dist.py`(배포 묶음)
- 번역 표: `my files/tsv/cc_*.tsv`(KO 열), 받은 번역 병합·손질: `tools/trmerge.py` + `work/merge/override.tsv`·`slot_rewrite*.tsv`
- 말투 칸(동료별 말투) 설계: `docs/말투칸_설계안.md`, 검사: `tools/slot_check.py`·`tools/slot_register.py`·`tools/slot_side.py`
- 조사·결정 기록: `docs/00_초기조사.md`
