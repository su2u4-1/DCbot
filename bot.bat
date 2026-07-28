@echo off
set REMOTE_USER=su2u4
set REMOTE_IP=192.168.0.97
set REMOTE_SCRIPT=~/bot.sh

if "%~1"=="" (
    echo 使用方式: bot.bat {start^|stop^|restart^|status^|log}
    echo   bot.bat start   - 遠端啟動 Bot
    echo   bot.bat stop    - 遠端關閉 Bot
    echo   bot.bat restart - 遠端重啟 Bot
    echo   bot.bat status  - 查看遠端運行狀態
    echo   bot.bat log     - 查看即時 Log
    exit /b 1
)

ssh -t %REMOTE_USER%@%REMOTE_IP% "%REMOTE_SCRIPT% %1"
