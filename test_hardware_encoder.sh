#!/bin/bash
# Test if hardware encoder works with our new simplified pipeline

echo "=== Testing Hardware Encoder (v4l2h264enc) ==="
echo ""
echo "Testing 720p for 5 seconds..."
echo ""

timeout 5 gst-launch-1.0 -v \
    v4l2src device=/dev/video0 num-buffers=150 ! \
    image/jpeg,width=1280,height=720,framerate=30/1 ! \
    jpegdec ! \
    videoconvert ! \
    video/x-raw,format=I420 ! \
    v4l2h264enc extra-controls="controls,video_bitrate=4000000" ! \
    "video/x-h264,profile=baseline,level=(string)4" ! \
    h264parse config-interval=-1 ! \
    filesink location=test_hw.h264

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Hardware encoder worked!"
    echo "Testing if output is valid..."
    ffprobe test_hw.h264 2>&1 | grep -E "(Stream|Video:)"
    
    echo ""
    echo "Hardware encoder is available! Use: exostream send --resolution 1280x720"
    echo "(without the -s flag to use hardware encoder)"
else
    echo ""
    echo "✗ Hardware encoder failed"
    echo "You'll need to use software encoder with -s flag"
fi

