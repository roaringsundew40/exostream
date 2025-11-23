#!/bin/bash
# Diagnose where latency is coming from

echo "=== Latency Diagnostics ==="
echo ""
echo "Make sure exostream is running!"
echo ""

# Check CPU usage
echo "1. Checking CPU usage..."
ps aux | grep -E "(exostream|x264)" | grep -v grep
echo ""

# Monitor CPU in real-time for 3 seconds
echo "2. CPU usage over 3 seconds:"
top -b -n 3 -d 1 | grep -E "(Cpu|exostream|x264)" | head -20
echo ""

# Test latency by capturing with timestamps
echo "3. Testing pipeline latency (capturing 3 seconds)..."
echo "   Start time: $(date +%H:%M:%S.%3N)"

timeout 3 gst-launch-1.0 -v \
    srtsrc uri=srt://127.0.0.1:9000 ! \
    fakesink sync=false 2>&1 | grep -E "(pts|dts|Setting pipeline)"

echo "   End time: $(date +%H:%M:%S.%3N)"
echo ""

# Check if encoder is keeping up
echo "4. Frame statistics from sender..."
gst-launch-1.0 -v \
    srtsrc uri=srt://127.0.0.1:9000 ! \
    h264parse ! \
    avdec_h264 ! \
    fpsdisplaysink video-sink=fakesink text-overlay=false sync=false &

PID=$!
sleep 5
kill $PID 2>/dev/null

echo ""
echo "=== Recommendations ==="
echo "- If CPU is > 80%, try 720p: exostream send -s --resolution 1280x720"
echo "- If you see dropped frames, encoder can't keep up"
echo "- If timestamps show >1 second delay, it's GStreamer buffering"

