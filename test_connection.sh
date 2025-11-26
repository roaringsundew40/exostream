#!/bin/bash
# Test SRT stream connection

PI_IP=${1:-127.0.0.1}
PORT=${2:-9000}

echo "=== Testing SRT Stream Connection ==="
echo ""
echo "Stream: srt://$PI_IP:$PORT"
echo ""

# Check if stream is running
echo "1. Checking if stream is running..."
if ps aux | grep -E "(exostream|ffmpeg)" | grep -v grep > /dev/null; then
    echo "✓ Stream process found"
    ps aux | grep -E "(exostream|ffmpeg)" | grep -v grep | head -2
else
    echo "✗ No stream process running!"
    echo "Start stream first: exostream send --use-ffmpeg"
    exit 1
fi
echo ""

# Check if port is listening
echo "2. Checking if SRT port is listening..."
if ss -uln | grep ":$PORT" > /dev/null 2>&1; then
    echo "✓ Port $PORT is listening (UDP)"
    ss -uln | grep ":$PORT"
elif netstat -uln 2>/dev/null | grep ":$PORT" > /dev/null; then
    echo "✓ Port $PORT is listening (UDP)"
    netstat -uln | grep ":$PORT"
else
    echo "✗ Port $PORT not listening!"
    echo "Stream might not be started properly"
    exit 1
fi
echo ""

# Try to probe the stream
echo "3. Testing connection with ffprobe..."
echo "   This will attempt to connect and read stream info..."
timeout 10 ffprobe -v error -show_format -show_streams \
    srt://$PI_IP:$PORT 2>&1 | head -20

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Stream is accessible!"
else
    echo ""
    echo "⚠ Could not probe stream"
fi

echo ""
echo "=== Connection Commands ==="
echo ""
echo "Try these commands to connect:"
echo ""
echo "1. FFplay (low latency):"
echo "   ffplay -fflags nobuffer -flags low_delay srt://$PI_IP:$PORT"
echo ""
echo "2. FFplay (with timeout):"
echo "   ffplay -timeout 5000000 srt://$PI_IP:$PORT"
echo ""
echo "3. VLC:"
echo "   vlc srt://$PI_IP:$PORT --network-caching=100"
echo ""
echo "4. MPV:"
echo "   mpv srt://$PI_IP:$PORT --cache=no"
echo ""

