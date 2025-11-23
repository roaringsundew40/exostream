#!/bin/bash
# Test if encoder produces valid H.264

echo "=== Testing H.264 Encoder Output ==="
echo "This will encode 3 seconds and save to test.h264"
echo ""

# Encode a short clip
gst-launch-1.0 -e \
    v4l2src device=/dev/video0 num-buffers=90 ! \
    image/jpeg,width=1280,height=720,framerate=30/1 ! \
    jpegdec ! \
    videoconvert ! \
    video/x-raw,format=I420 ! \
    x264enc bitrate=2000 speed-preset=veryfast tune=zerolatency bframes=0 key-int-max=60 ! \
    "video/x-h264,stream-format=byte-stream,alignment=au,profile=baseline" ! \
    h264parse config-interval=-1 ! \
    filesink location=test.h264

echo ""
echo "Testing if the file is valid H.264..."
ffprobe -v error -show_streams test.h264 2>&1 | grep -E "(codec_name|width|height|r_frame_rate)"

echo ""
echo "If you see codec_name=h264 and dimensions above, encoding works!"
echo "You can play test.h264 with: ffplay test.h264"

