@echo off
set "src=log\*"
set "dst=D:\log_archive"

if not exist "%dst%" mkdir "%dst%" >nul 2>&1

robocopy "log" "%dst%" /E /NFL /NDL /NJH /NJS /NC /NS >nul 2>&1
