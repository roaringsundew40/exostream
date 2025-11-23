@echo off
REM ExoStream VLC Connector for Windows
REM Edit RPI_IP below to match your Raspberry Pi's IP address

SET RPI_IP=192.168.86.30
SET PORT=9000

echo ===================================
echo ExoStream Windows VLC Connector
echo ===================================
echo.
echo Connecting to: srt://%RPI_IP%:%PORT%
echo.

REM Try to find VLC in common locations
SET VLC_PATH=

IF EXIST "C:\Program Files\VideoLAN\VLC\vlc.exe" (
    SET VLC_PATH=C:\Program Files\VideoLAN\VLC\vlc.exe
)

IF EXIST "C:\Program Files (x86)\VideoLAN\VLC\vlc.exe" (
    SET VLC_PATH=C:\Program Files ^(x86^)\VideoLAN\VLC\vlc.exe
)

IF "%VLC_PATH%"=="" (
    echo ERROR: VLC not found in default locations!
    echo Please install VLC from https://www.videolan.org/
    echo Or edit this file and set VLC_PATH manually
    pause
    exit /b 1
)

echo Found VLC at: %VLC_PATH%
echo Starting stream...
echo.

REM Start VLC with simple settings
start "" "%VLC_PATH%" srt://%RPI_IP%:%PORT% --network-caching=100

echo.
echo VLC should open in a moment.
echo If you see a black screen, wait 2-3 seconds for the stream to start.
echo.
pause

