@echo off
python subscribe_ss.py
timeout 10
taskkill /IM shadowsocks.exe /T
timeout 2
taskkill /IM shadowsocks.exe /T /F
timeout 1
start shadowsocks.exe

exit