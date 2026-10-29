@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Howler 한글 패치 제거

if exist "Howler.swf.orig" goto :check_game
echo 백업된 원본이 없습니다. 한글 패치가 설치되지 않았거나 이미 제거되었습니다.
echo Steam에서 "게임 파일 무결성 확인"을 해도 원본으로 돌아갑니다.
goto :end

:check_game
tasklist /fi "imagename eq Howler.exe" 2>nul | find /i "Howler.exe" >nul || goto :check_write
echo 게임이 실행 중입니다. 게임을 종료한 뒤 아무 키나 누르세요.
pause >nul
goto :check_game

:check_write
copy /y nul "..\__kopatch_write_test.tmp" >nul 2>&1
if exist "..\__kopatch_write_test.tmp" (
  del "..\__kopatch_write_test.tmp"
  goto :restore
)
echo 게임 폴더에 쓰려면 관리자 권한이 필요합니다.
echo 권한 요청 창이 뜨면 "예"를 눌러 주세요.
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b

:restore
copy /y "Howler.swf.orig" "..\Howler.swf" >nul || goto :fail
if exist "orig" xcopy "orig" "..\media" /s /y /q >nul || goto :fail
echo 원래 영어판으로 되돌렸습니다.
goto :end

:fail
echo [오류] 원본 파일을 복사하지 못했습니다.

:end
echo.
if /i not "%~1"=="/nopause" pause
