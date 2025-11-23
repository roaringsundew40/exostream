#!/bin/bash
# Test the v4l2h264enc encoder directly

DEVICE=${1:-/dev/video0}

echo "=== Testing v4l2h264enc with camera ==="
echo ""
echo "Device: $DEVICE"
echo "Testing 1280x720 @ 30fps for 5 seconds..."
echo ""

# Simple pipeline: camera -> MJPEG -> decode -> convert -> I420 -> encode -> display stats
gst-launch-1.0 -v \
    v4l2src device=$DEVICE num-buffers=150 ! \
    image/jpeg,width=1280,height=720,framerate=30/1 ! \
    jpegdec ! \
    videoconvert ! \
    video/x-raw,format=I420 ! \
    v4l2h264enc ! \
    h264parse ! \
    fakesink sync=true

echo ""
echo "If that worked, let's try 1080p..."
echo ""

gst-launch-1.0 -v \
    v4l2src device=$DEVICE num-buffers=150 ! \
    image/jpeg,width=1920,height=1080,framerate=30/1 ! \
    jpegdec ! \
    videoconvert ! \
    video/x-raw,format=I420 ! \
    v4l2h264enc ! \
    h264parse ! \
    fakesink sync=true

