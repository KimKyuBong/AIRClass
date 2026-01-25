@echo off
chcp 65001 >nul
echo ========================================
echo   AIRClass 서버 로그
echo ========================================
echo.
echo 종료하려면 Ctrl+C를 누르세요
echo.

docker-compose logs -f --tail=100
