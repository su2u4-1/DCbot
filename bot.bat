@echo off
set REMOTE=su2u4@192.168.0.106
set REMOTE_SCRIPT=/home/su2u4/bot.sh

if "%1"=="" (
    echo 使用方式: bot.bat {start|stop|restart|status|log}
    exit /b 1
)

:: 如果是觀看 Log，需要保留互動式 TTY
if "%1"=="log" (
    ssh -t %REMOTE% "%REMOTE_SCRIPT% log"
    exit /b 0
)

if "%1"=="restart" (
    :: 單次 SSH 連線：將 .env 串流傳送至遠端，並依序執行 git pull 與 restart
    tar -cf - .env | ssh %REMOTE% "tar -xf - -C /home/su2u4/DCbot/ && cd /home/su2u4/DCbot && git pull"
    ssh %REMOTE% "%REMOTE_SCRIPT% restart < /dev/null"
    exit /b 0
)

:: 其他指令（start/stop/status）：重定向 stdin，讓 SSH 完成後安全斷開
ssh %REMOTE% "%REMOTE_SCRIPT% %1 < /dev/null"
