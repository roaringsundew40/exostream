#!/bin/bash
# Debug script to check if stream is working

echo "=== ExoStream Debug Info ==="
echo ""

# Check if exostream is running
echo "1. Checking if exostream process is running..."
ps aux | grep -i exostream | grep -v grep
echo ""

# Check if port 9000 is listening
echo "2. Checking if SRT port 9000 is listening..."
if command -v ss &> /dev/null; then
    ss -tuln | grep 9000
else
    netstat -tuln | grep 9000
fi
echo ""

# Check active connections
echo "3. Checking active connections on port 9000..."
if command -v ss &> /dev/null; then
    ss -tn | grep 9000
else
    netstat -tn | grep 9000
fi
echo ""

# Test if we can receive the stream locally
echo "4. Testing local stream reception (5 seconds)..."
echo "   This will try to receive the stream using gst-launch..."
timeout 5 gst-launch-1.0 \
    srcsrc uri=srt://127.0.0.1:9000 ! \
    tsdemux ! \
    h264parse ! \
    fakesink 2>&1 | grep -E "(Setting pipeline|ERROR|WARNING)" || echo "No errors detected"

echo ""
echo "=== Debug Complete ==="

