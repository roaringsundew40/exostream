@echo off
REM Batch file to connect to ExoStream from Windows using VLC
REM 
REM Instructions:
REM 1. Copy this file to your Windows computer
REM 2. Edit the IP address below to match your Raspberry Pi
REM 3. Double-click to run

SET RPI_IP=192.168.86.30
SET PORT=9000

echo ===================================
echo ExoStream Windows VLC Connector
echo ===================================
echo.
echo Connecting to: srt://%RPI_IP%:%PORT%
echo.
echo Make sure:
echo  1. ExoStream is running on your Raspberry Pi
echo  2. Your Pi's IP address is %RPI_IP%
echo  3. VLC is installed in the default location
echo.
pause

echo Starting VLC with optimized settings for low latency...
echo.

"C:\Program Files\VideoLAN\VLC\vlc.exe" ^
    "srt://%RPI_IP%:%PORT%?latency=120" ^
    --network-caching=100 ^
    --live-caching=100 ^
    --srt-streamid="" ^
    --clock-jitter=0 ^
    --clock-synchro=0 ^
    --avcodec-hw=any

REM If VLC is in 32-bit Program Files, try this instead:
REM "C:\Program Files (x86)\VideoLAN\VLC\vlc.exe" ^

echo.
echo If VLC didn't open, it might be installed in a different location.
echo Edit this batch file and update the path to vlc.exe
pause

