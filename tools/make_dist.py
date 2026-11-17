# -*- coding: utf-8 -*-
r"""배포 묶음 — dist/ChronoCross_KR_v0.9/ (디스크별 xdelta + xdelta.exe + readme.txt + 패치적용.bat) + zip

  python tools/make_dist.py      # work/build/full_d1·d2.bin(build_full.py 결과)으로 xdelta → 원본에 되짚어 바이트 대조

규칙(초코보2 make_dist 형식): 해시 MD5 대문자 · 한국어 문서 CP949(CRLF) · 버전 v0.9 한 자리 · bat 의 if 블록 안 echo 에 괄호 금지
"""
import hashlib, os, shutil, subprocess, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from ccget import P

VER = 'v0.9'
PKG = 'ChronoCross_KR_' + VER
DIST = os.path.join(ROOT, 'dist', PKG)
XDELTA = r'C:\claude\utils\xdelta.exe'
DISCS = [
    dict(n=1, name='Chrono Cross (Japan, Asia) (Disc 1).bin', src=P['1'], out=os.path.join(ROOT, 'work', 'build', 'full_d1.bin'),
         src_md5='988a1af0'),
    dict(n=2, name='Chrono Cross (Japan, Asia) (Disc 2).bin', src=P['2'], out=os.path.join(ROOT, 'work', 'build', 'full_d2.bin'),
         src_md5='826a66fb'),
]


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


README = """크로노 크로스 (PS1 일본판, 2장) 한글 패치 {ver}
==============================================

1개의 트랙으로 이루어진 디스크 2장에 각각 패치하시면 됩니다.

[디스크 1] {name1}
원본md5 : {src1}
패치md5 : {dst1}

[디스크 2] {name2}
원본md5 : {src2}
패치md5 : {dst2}

입니다.


[ 적용 방법 ]

1. 원본 .bin 과 .cue 를 이 패치 묶음과 같은 폴더에 둡니다.
   디스크 1·2 중 있는 것만 패치합니다.
2. 「패치적용.bat」 을 실행합니다.
   배치가 원본 MD5 를 먼저 확인하고, 끝난 뒤 결과 MD5 까지 검사합니다.
   원본은 .bak 으로 남겨 둡니다.
3. .cue 는 고치지 않아도 됩니다.

  직접 적용:
    xdelta.exe -d -s "원본 디스크 1.bin" "{patch1}" "결과.bin"
  (Delta Patcher 같은 xdelta3 GUI 도구로 적용해도 됩니다. 원본이 다르면 xdelta 가 적용을 거부합니다.)


[ 바뀌는 것 ]

■ 대사 전체(맵·이벤트·전투·보스), 동료 말투(한국어용으로 다시 설계한 말투 칸)
■ 메뉴·설정·상점·대장간·메모리 카드 화면, 인물 프로필
■ 인물·아이템·엘리먼트·기술 이름과 설명, 전투 결과 화면
■ 그림 글자(메뉴 라벨·상태 이상·전투 설명서·타이틀 "진동 기능" 등)
■ 이름 입력판(한글), 오프닝 동영상의 시(한글 자막을 영상에 다시 그림)


[ 알려진 사항 ]

■ 시험판입니다. 전체 플레이 검증을 마치지 않았습니다.
■ 개발용 디버그 메뉴는 번역하지 않았습니다(일반 플레이에서는 나오지 않음).
■ 칸이 좁은 곳 몇 군데는 원문보다 짧게 줄였습니다(프로필·전투 결과·저장 목록 등).
■ 일본어판으로 저장한 세이브도 불러올 수 있습니다.
"""

BAT = r"""@echo off
setlocal
set PATCH1={patch1}
set PATCH2={patch2}

echo.
echo  ==============================================
echo    Chrono Cross ^(PS1 JP^) Korean Patch {ver}
echo  ==============================================
echo.

if not exist "%~dp0xdelta.exe" (
  echo  [!] xdelta.exe 가 없습니다. 패치 묶음을 그대로 풀고 실행하세요.
  goto END
)

set DONE=0
call :ONE "{name1}" "%PATCH1%" {src1} {dst1}
call :ONE "{name2}" "%PATCH2%" {src2} {dst2}
if "%DONE%"=="0" (
  echo  [!] 원본 .bin 을 찾지 못했습니다. 이 폴더에 원본 .bin 을 두고 실행하세요.
)
goto END

:ONE
set NAME=%~1
set P=%~2
set SRCMD5=%3
set DSTMD5=%4
if not exist "%NAME%" goto :EOF
set DONE=1
echo  ---- %NAME%
echo  [1/3] 원본 검사 중...
set HASH=
for /f "skip=1 tokens=* delims=" %%H in ('certutil -hashfile "%NAME%" MD5') do (
  if not defined HASH set HASH=%%H
)
set HASH=%HASH: =%
if /I "%HASH%"=="%DSTMD5%" (
  echo  [!] 이미 이 버전의 한글 패치가 적용된 파일입니다.
  echo.
  goto :EOF
)
if /I not "%HASH%"=="%SRCMD5%" (
  echo  [!] 원본 MD5 가 다릅니다. 이 디스크는 패치하지 않습니다.
  echo      필요 : %SRCMD5%
  echo      현재 : %HASH%
  echo.
  goto :EOF
)
echo  [2/3] 패치 적용 중... 1~3분 걸립니다
"%~dp0xdelta.exe" -d -f -s "%NAME%" "%~dp0%P%" "%NAME%.kr"
if errorlevel 1 (
  echo  [!] 패치에 실패했습니다.
  if exist "%NAME%.kr" del "%NAME%.kr"
  echo.
  goto :EOF
)
echo  [3/3] 결과 검사 중...
set HASH2=
for /f "skip=1 tokens=* delims=" %%H in ('certutil -hashfile "%NAME%.kr" MD5') do (
  if not defined HASH2 set HASH2=%%H
)
set HASH2=%HASH2: =%
if /I not "%HASH2%"=="%DSTMD5%" (
  echo  [!] 결과 MD5 가 다릅니다. 원본은 그대로 두고 중단합니다.
  del "%NAME%.kr"
  echo.
  goto :EOF
)
move /y "%NAME%" "%NAME%.bak" >nul
move /y "%NAME%.kr" "%NAME%" >nul
echo  [OK] 한글 패치 완료. 원본은 "%NAME%.bak" 으로 남겨 두었습니다.
echo.
goto :EOF

:END
echo.
pause
endlocal
"""


def write_cp949(path, text):
    data = text.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp949')
    with open(path, 'wb') as f:
        f.write(data)


def main():
    os.makedirs(DIST, exist_ok=True)
    v = dict(ver=VER)
    for d in DISCS:
        s, o = md5(d['src']), md5(d['out'])
        assert s.startswith(d['src_md5']), (d['n'], s)
        patch = '%s_Disc%d.xdelta' % (PKG, d['n'])
        pp = os.path.join(DIST, patch)
        subprocess.run([XDELTA, '-e', '-9', '-f', '-s', d['src'], d['out'], pp], check=True)
        chk = os.path.join(ROOT, 'work', 'build', 'dist_check.bin')
        subprocess.run([XDELTA, '-d', '-f', '-s', d['src'], pp, chk], check=True)
        ok = md5(chk) == o
        os.remove(chk)
        if not ok: raise SystemExit('⛔ 디스크 %d xdelta 되짚기 결과가 빌드와 다르다' % d['n'])
        v.update({'name%d' % d['n']: d['name'], 'patch%d' % d['n']: patch, 'src%d' % d['n']: s.upper(), 'dst%d' % d['n']: o.upper()})
        print('디스크 %d: xdelta %d B · 원본md5 %s · 패치md5 %s · 되짚기 일치' % (d['n'], os.path.getsize(pp), s.upper(), o.upper()))
    shutil.copyfile(XDELTA, os.path.join(DIST, 'xdelta.exe'))
    write_cp949(os.path.join(DIST, 'readme.txt'), README.format(**v))
    write_cp949(os.path.join(DIST, '패치적용.bat'), BAT.format(**v))
    z = os.path.join(ROOT, 'dist', PKG + '.zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fn in sorted(os.listdir(DIST)):
            zf.write(os.path.join(DIST, fn), PKG + '/' + fn)
    print('✅ %s · zip %s (%d B, md5 %s)' % (DIST, z, os.path.getsize(z), md5(z).upper()))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
