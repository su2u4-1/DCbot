@echo off
set REMOTE_USER=su2u4
set REMOTE_IP=192.168.0.97
set REMOTE_SCRIPT=~/bot.sh

if "%1"=="" (
    echo 使用方式: bot.bat {start|stop|restart|status|log}
    exit /b 1
)

:: 如果是觀看 Log，需要保留互動式 TTY
if "%1"=="log" (
    ssh -t su2u4@192.168.0.97 "/home/su2u4/bot.sh log"
    exit /b 0
)

:: 其他指令（start/stop/restart/status）：重定向 stdin，讓 SSH 完成後安全斷開，不咬住背景進程
ssh su2u4@192.168.0.97 "/home/su2u4/bot.sh %1 < /dev/null"
