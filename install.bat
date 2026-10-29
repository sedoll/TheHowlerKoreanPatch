@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Howler 한글 패치 설치

echo ============================================
echo   Howler 한글 패치 설치
echo ============================================
echo.

rem --- 게임 폴더 안에 있는지 확인 ---
if exist "..\Howler.swf" goto :check_game
echo [오류] 게임 폴더를 찾지 못했습니다.
echo 이 패치 폴더를 Howler 게임 폴더 안에 넣고 다시 실행하세요.
echo 예: C:\Program Files ^(x86^)\Steam\steamapps\common\Howler\이 폴더
goto :end

rem --- 게임이 켜져 있으면 파일을 바꿀 수 없다 ---
:check_game
tasklist /fi "imagename eq Howler.exe" 2>nul | find /i "Howler.exe" >nul || goto :check_write
echo 게임이 실행 중입니다. 게임을 종료한 뒤 아무 키나 누르세요.
pause >nul
goto :check_game

rem --- Program Files 아래라 쓰기 권한이 없으면 관리자로 다시 실행 ---
:check_write
copy /y nul "..\__kopatch_write_test.tmp" >nul 2>&1
if exist "..\__kopatch_write_test.tmp" (
  del "..\__kopatch_write_test.tmp"
  goto :find_python
)
echo 게임 폴더에 쓰려면 관리자 권한이 필요합니다.
echo 권한 요청 창이 뜨면 "예"를 눌러 주세요.
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b

rem --- Python 찾기 ---
:find_python
set "PY="
py -3 -c "import sys; sys.exit(sys.version_info < (3, 8))" >nul 2>&1 && set "PY=py -3"
if defined PY goto :deps
python -c "import sys; sys.exit(sys.version_info < (3, 8))" >nul 2>&1 && set "PY=python"
if defined PY goto :deps

echo [안내] Python 3.8 이상이 필요합니다.
where winget >nul 2>&1 || goto :no_python
choice /c YN /m "지금 winget으로 Python을 설치할까요"
if errorlevel 2 goto :no_python
winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
echo.
echo Python 설치가 끝나면 이 창을 닫고 install.bat을 다시 실행하세요.
goto :end

:no_python
echo https://www.python.org/downloads/ 에서 Python을 설치한 뒤 다시 실행하세요.
echo 설치할 때 "Add python.exe to PATH"를 꼭 체크하세요.
goto :end

rem --- 라이브러리 (이미 있으면 건너뜀) ---
:deps
%PY% -c "import PIL, numpy" >nul 2>&1 && goto :patch
echo [1/2] 필요한 라이브러리를 설치하는 중...
%PY% -m pip install --disable-pip-version-check -q --user -r requirements.txt
if errorlevel 1 (
  echo [오류] 라이브러리 설치에 실패했습니다. 인터넷 연결을 확인하세요.
  goto :end
)

rem --- 패치 만들기 ---
:patch
echo [2/2] 한글 패치를 만드는 중... 잠시만 기다려 주세요.
set "PYTHONIOENCODING=utf-8"
%PY% make_patch.py
if errorlevel 1 (
  echo.
  echo [오류] 패치를 만들지 못했습니다. 위 메시지를 확인하세요.
  goto :end
)
echo.
echo 설치 완료! 게임을 실행하세요.
echo 되돌리려면 uninstall.bat을 실행하세요.

:end
echo.
if /i not "%~1"=="/nopause" pause
