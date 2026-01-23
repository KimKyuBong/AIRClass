@echo off
chcp 65001 >nul
echo ========================================
echo   AIRClass 서버 중지 중...
echo ========================================
echo.

docker-compose down

echo.
echo 서버가 중지되었습니다.
echo.
pause
