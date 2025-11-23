#!/bin/bash
# Capture 5 seconds of the SRT stream to a file for analysis

echo "=== Capturing Stream to File ==="
echo "Make sure exostream is running!"
echo "Capturing 5 seconds to stream_capture.h264..."
echo ""

timeout 5 gst-launch-1.0 \
    srtsrc uri=srt://127.0.0.1:9000 ! \
    filesink location=stream_capture.h264

echo ""
echo "Analyzing captured stream..."
echo ""

if [ -f stream_capture.h264 ]; then
    SIZE=$(stat -f%z stream_capture.h264 2>/dev/null || stat -c%s stream_capture.h264 2>/dev/null)
    echo "File size: $SIZE bytes"
    
    if [ $SIZE -gt 1000 ]; then
        echo "Stream data captured successfully!"
        echo ""
        echo "Testing with ffprobe..."
        ffprobe -v error -show_streams stream_capture.h264 2>&1 | head -20
        
        echo ""
        echo "Try playing it: ffplay stream_capture.h264"
    else
        echo "ERROR: File is too small, stream might not be working"
    fi
else
    echo "ERROR: No file created, stream not receiving data"
fi

