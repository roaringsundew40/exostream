#!/bin/bash
# Comprehensive SRT diagnosis

echo "=== SRT Support Diagnosis ==="
echo ""

# 1. Check FFmpeg protocols
echo "1. Checking FFmpeg SRT protocol support..."
if ffmpeg -protocols 2>&1 | grep -q "srt"; then
    echo "   ✓ SRT protocol available"
else
    echo "   ✗ SRT protocol NOT available"
    echo "   Your FFmpeg doesn't have SRT support!"
    echo "   Reinstall FFmpeg with SRT: sudo apt-get install --reinstall ffmpeg"
    exit 1
fi
echo ""

# 2. Check libsrt
echo "2. Checking for libsrt library..."
if ldconfig -p | grep -q libsrt; then
    echo "   ✓ libsrt found"
    ldconfig -p | grep libsrt
else
    echo "   ✗ libsrt NOT found"
    echo "   Install with: sudo apt-get install libsrt1.5-gnutls"
fi
echo ""

# 3. Test different SRT URL formats
echo "3. Testing SRT URL formats..."
echo ""

PORT=9999

# Format 1: mode=listener with full address
echo "   Test A: srt://0.0.0.0:$PORT?mode=listener"
timeout 2 ffmpeg -hide_banner -loglevel error \
    -f lavfi -i "testsrc=size=640x480:rate=10" \
    -c:v libx264 -preset ultrafast -t 1 \
    -f mpegts "srt://0.0.0.0:$PORT?mode=listener" 2>&1 &
FFMPEG_PID=$!
sleep 1
if ps -p $FFMPEG_PID > /dev/null 2>&1; then
    echo "      ✓ Format A works"
    kill $FFMPEG_PID 2>/dev/null
else
    echo "      ✗ Format A failed"
fi
wait $FFMPEG_PID 2>/dev/null
echo ""

# Format 2: mode=listener with :: (any interface)
echo "   Test B: srt://:$PORT?mode=listener"
timeout 2 ffmpeg -hide_banner -loglevel error \
    -f lavfi -i "testsrc=size=640x480:rate=10" \
    -c:v libx264 -preset ultrafast -t 1 \
    -f mpegts "srt://:$PORT?mode=listener" 2>&1 &
FFMPEG_PID=$!
sleep 1
if ps -p $FFMPEG_PID > /dev/null 2>&1; then
    echo "      ✓ Format B works (RECOMMENDED)"
    kill $FFMPEG_PID 2>/dev/null
else
    echo "      ✗ Format B failed"
fi
wait $FFMPEG_PID 2>/dev/null
echo ""

# Format 3: listen=1 (alternative syntax)
echo "   Test C: srt://0.0.0.0:$PORT?listen=1"
timeout 2 ffmpeg -hide_banner -loglevel error \
    -f lavfi -i "testsrc=size=640x480:rate=10" \
    -c:v libx264 -preset ultrafast -t 1 \
    -f mpegts "srt://0.0.0.0:$PORT?listen=1" 2>&1 &
FFMPEG_PID=$!
sleep 1
if ps -p $FFMPEG_PID > /dev/null 2>&1; then
    echo "      ✓ Format C works"
    kill $FFMPEG_PID 2>/dev/null
else
    echo "      ✗ Format C failed"
fi
wait $FFMPEG_PID 2>/dev/null
echo ""

# 4. Check FFmpeg version
echo "4. FFmpeg version:"
ffmpeg -version | head -1
echo ""

echo "=== Recommendation ==="
echo "If all tests failed, your FFmpeg might not have working SRT support."
echo "Try: sudo apt-get install --reinstall ffmpeg libsrt1.5-gnutls"

