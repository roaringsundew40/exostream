#!/bin/bash
# Stream using UDP (simpler than SRT, always works)

DEVICE=${1:-/dev/video0}
WIDTH=${2:-1920}
HEIGHT=${3:-1080}
FPS=${4:-30}
BITRATE=${5:-6000}
HOST=${6:-0.0.0.0}
PORT=${7:-9000}

echo "=== Starting UDP Stream with Hardware Encoding ==="
echo ""
echo "Device: $DEVICE"
echo "Resolution: ${WIDTH}x${HEIGHT} @ ${FPS}fps"
echo "Bitrate: ${BITRATE}kbps"
echo "Streaming to: udp://$HOST:$PORT"
echo ""
echo "Connect with:"
echo "  ffplay udp://@:$PORT"
echo "  or from another computer:"
echo "  ffplay udp://<THIS_PI_IP>:$PORT"
echo ""
echo "Press Ctrl+C to stop"
echo ""

ffmpeg -hide_banner -loglevel info \
    -f v4l2 -input_format mjpeg \
    -video_size ${WIDTH}x${HEIGHT} -framerate $FPS \
    -i $DEVICE \
    -pix_fmt yuv420p \
    -c:v h264_v4l2m2m -b:v ${BITRATE}k -g $(($FPS * 2)) \
    -f mpegts udp://$HOST:$PORT

