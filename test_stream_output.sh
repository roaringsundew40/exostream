#!/bin/bash
# Test what the stream is actually outputting

echo "=== Testing Stream Output ==="
echo "This will capture 5 seconds of the stream and analyze it"
echo ""

# Receive stream and analyze
timeout 5 gst-launch-1.0 -v \
    srtsrc uri=srt://127.0.0.1:9000 ! \
    fakesink dump=true 2>&1 | head -50

echo ""
echo "If you see data dumps above, the stream is working."
echo "If you see 'Setting pipeline to PLAYING', that's good."
echo "If you see errors, the stream format might be wrong."

