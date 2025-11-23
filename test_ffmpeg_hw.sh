#!/bin/bash
# Test FFmpeg hardware encoding on Raspberry Pi

echo "=== Testing FFmpeg Hardware Encoder ==="
echo ""

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "✗ FFmpeg not installed!"
    echo "Install with: sudo apt-get install ffmpeg"
    exit 1
fi

echo "✓ FFmpeg found: $(ffmpeg -version | head -1)"
echo ""

# Check if h264_v4l2m2m encoder is available
echo "Checking for h264_v4l2m2m hardware encoder..."
if ffmpeg -hide_banner -encoders 2>/dev/null | grep -q h264_v4l2m2m; then
    echo "✓ h264_v4l2m2m encoder found!"
else
    echo "✗ h264_v4l2m2m encoder NOT found"
    echo "Your FFmpeg might not have V4L2 M2M support compiled in"
    exit 1
fi

echo ""
echo "Testing hardware encoding at 720p for 5 seconds..."
echo ""

# Test encode
timeout 5 ffmpeg -f v4l2 -input_format mjpeg \
    -video_size 1280x720 -framerate 30 \
    -i /dev/video0 \
    -c:v h264_v4l2m2m -b:v 4M -g 60 \
    -f h264 test_ffmpeg_hw.h264 \
    -y 2>&1 | tail -30

if [ $? -eq 0 ] && [ -f test_ffmpeg_hw.h264 ]; then
    SIZE=$(stat -f%z test_ffmpeg_hw.h264 2>/dev/null || stat -c%s test_ffmpeg_hw.h264 2>/dev/null)
    
    if [ $SIZE -gt 100000 ]; then
        echo ""
        echo "✓✓✓ SUCCESS! Hardware encoding works with FFmpeg!"
        echo ""
        echo "File size: $(($SIZE / 1024)) KB"
        echo ""
        echo "Testing if video is valid..."
        ffprobe test_ffmpeg_hw.h264 2>&1 | grep -E "(Stream|Video:|Duration)"
        echo ""
        echo "Try playing: ffplay test_ffmpeg_hw.h264"
        echo ""
        echo "Hardware encoding is available with FFmpeg!"
        echo "You can now use: exostream send --use-ffmpeg"
        exit 0
    fi
fi

echo ""
echo "✗ Hardware encoding test failed"
echo "Falling back to software encoding is recommended"
exit 1

