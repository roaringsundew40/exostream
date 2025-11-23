#!/bin/bash
# Check what formats and resolutions your camera supports

DEVICE=${1:-/dev/video0}

echo "=== Camera Formats for $DEVICE ==="
echo ""

if ! command -v v4l2-ctl &> /dev/null; then
    echo "v4l2-ctl not found. Installing..."
    sudo apt-get install -y v4l2-utils
fi

echo "Supported formats and resolutions:"
echo "=================================="
v4l2-ctl --device=$DEVICE --list-formats-ext

echo ""
echo "=== Summary ==="
echo "MJPEG formats are marked as 'Motion-JPEG'"
echo "Raw formats are marked as 'YUYV' or similar"
echo ""
echo "The Logitech C930e typically supports:"
echo "  - MJPEG: up to 1920x1080 @ 30fps"
echo "  - Raw (YUYV): up to 640x480 or 800x600"

