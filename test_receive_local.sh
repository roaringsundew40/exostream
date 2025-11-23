#!/bin/bash
# Test receiving the SRT stream locally

echo "=== Testing Local SRT Stream Reception ==="
echo ""
echo "Make sure exostream is running in another terminal!"
echo "This will attempt to receive and display the stream for 10 seconds..."
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Try to receive the stream
gst-launch-1.0 -v \
    srtsrc uri=srt://127.0.0.1:9000 ! \
    tsdemux ! \
    h264parse ! \
    avdec_h264 ! \
    videoconvert ! \
    fpsdisplaysink video-sink=fakesink text-overlay=true

echo ""
echo "If you saw 'Setting pipeline to PLAYING' and no errors, the stream is working!"

