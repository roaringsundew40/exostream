#!/bin/bash
# Verify if hardware encoding is actually being used

echo "=== Hardware Encoding Verification ==="
echo ""

# Check if exostream/ffmpeg is running
if ! ps aux | grep -E "(exostream|ffmpeg)" | grep -v grep > /dev/null; then
    echo "✗ No stream is running!"
    echo "Start stream first: exostream send --use-ffmpeg"
    exit 1
fi

echo "✓ Stream process found"
echo ""

# Show the actual FFmpeg command being used
echo "1. Checking FFmpeg command line..."
FFMPEG_CMD=$(ps aux | grep ffmpeg | grep -v grep | head -1)
echo ""
echo "$FFMPEG_CMD"
echo ""

# Check if h264_v4l2m2m is in the command
if echo "$FFMPEG_CMD" | grep -q "h264_v4l2m2m"; then
    echo "✓ Hardware encoder (h264_v4l2m2m) IS being used!"
    USING_HARDWARE=1
elif echo "$FFMPEG_CMD" | grep -q "libx264"; then
    echo "✗ Software encoder (libx264) is being used"
    USING_HARDWARE=0
else
    echo "⚠ Could not determine encoder type"
    USING_HARDWARE=0
fi
echo ""

# Check CPU usage
echo "2. Checking CPU usage..."
FFMPEG_PID=$(pgrep -f "ffmpeg.*h264" | head -1)

if [ -n "$FFMPEG_PID" ]; then
    echo "   FFmpeg PID: $FFMPEG_PID"
    
    # Get CPU usage for a few seconds
    echo "   Measuring CPU for 3 seconds..."
    CPU_USAGE=$(top -b -n 3 -d 1 -p $FFMPEG_PID 2>/dev/null | grep $FFMPEG_PID | tail -1 | awk '{print $9}')
    
    if [ -z "$CPU_USAGE" ]; then
        # Try alternative method
        CPU_USAGE=$(ps -p $FFMPEG_PID -o %cpu | tail -1 | tr -d ' ')
    fi
    
    echo "   CPU Usage: ${CPU_USAGE}%"
    echo ""
    
    # Interpret results
    if [ $USING_HARDWARE -eq 1 ]; then
        CPU_FLOAT=$(echo "$CPU_USAGE" | awk '{print int($1)}')
        if [ "$CPU_FLOAT" -lt 30 ]; then
            echo "✓✓✓ CONFIRMED: Hardware encoding is working!"
            echo "    CPU usage is ${CPU_USAGE}% (expected: 5-20% for hardware)"
        else
            echo "⚠ WARNING: Using h264_v4l2m2m but CPU is high (${CPU_USAGE}%)"
            echo "    Hardware encoder might not be working properly"
        fi
    else
        echo "   Software encoding detected (CPU: ${CPU_USAGE}%)"
        echo "   Expected: 60-100% for software, 5-20% for hardware"
    fi
else
    echo "   ✗ Could not find FFmpeg process"
fi

echo ""
echo "3. Checking video encoder device..."
if lsof 2>/dev/null | grep -q "/dev/video11"; then
    echo "   ✓ /dev/video11 (bcm2835-codec-encode) is open"
    echo "   This confirms hardware encoder is active!"
elif ps aux | grep ffmpeg | grep -q "/dev/video11"; then
    echo "   ✓ Hardware encoder device (/dev/video11) detected in command"
else
    echo "   ✗ Hardware encoder device not detected"
fi

echo ""
echo "=== Summary ==="
if [ $USING_HARDWARE -eq 1 ]; then
    echo "Status: Hardware encoding with h264_v4l2m2m"
    echo "This means: 1080p @ 30fps with ~10% CPU!"
else
    echo "Status: Software encoding with libx264"
    echo "This means: Limited resolution or high CPU"
fi

