#!/bin/bash
# Test if FFmpeg can stream to SRT at all

echo "=== Testing FFmpeg SRT Streaming ==="
echo ""

PORT=9001

echo "Test 1: Simple SRT test with test pattern..."
echo "This will stream a test pattern for 5 seconds"
echo ""

# Test with generated test pattern (no camera needed)
timeout 5 ffmpeg -hide_banner -loglevel info \
    -f lavfi -i testsrc=size=1280x720:rate=30 \
    -c:v libx264 -preset ultrafast -tune zerolatency \
    -b:v 2000k -g 60 \
    -f mpegts \
    "srt://0.0.0.0:$PORT?mode=listener&latency=120000" &

FFMPEG_PID=$!
echo "FFmpeg PID: $FFMPEG_PID"

# Wait for stream to start
sleep 2

# Try to connect
echo ""
echo "Trying to connect with ffplay..."
timeout 3 ffplay -autoexit -loglevel error \
    "srt://127.0.0.1:$PORT" 2>&1

PLAY_RESULT=$?

# Kill the ffmpeg process
kill $FFMPEG_PID 2>/dev/null
wait $FFMPEG_PID 2>/dev/null

echo ""
if [ $PLAY_RESULT -eq 0 ]; then
    echo "✓ FFmpeg SRT streaming works!"
    echo ""
    echo "Now try with your camera:"
    echo "  exostream send --use-ffmpeg"
else
    echo "✗ FFmpeg SRT test failed"
    echo ""
    echo "Try these alternatives:"
    echo "1. Use UDP instead: ffmpeg ... -f mpegts udp://127.0.0.1:9000"
    echo "2. Use GStreamer: exostream send -s"
    echo "3. Check FFmpeg SRT support: ffmpeg -protocols | grep srt"
fi

echo ""
echo "Test 2: Check SRT protocol support..."
if ffmpeg -protocols 2>&1 | grep -q "srt"; then
    echo "✓ SRT protocol is available in FFmpeg"
else
    echo "✗ SRT protocol NOT available"
    echo "  Your FFmpeg might not be compiled with SRT support"
fi

