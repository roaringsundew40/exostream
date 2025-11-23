#!/bin/bash
# Example commands for receiving the ExoStream

# Replace <RASPBERRY_PI_IP> with your Raspberry Pi's actual IP address
RASPBERRY_PI_IP="192.168.1.100"
PORT="9000"

echo "=== ExoStream Receiver Examples ==="
echo ""
echo "Note: The sender application (Phase 1) only supports streaming."
echo "These are example commands for receiving the stream on a client computer."
echo ""

# VLC Media Player
echo "1. Using VLC Media Player:"
echo "   vlc srt://$RASPBERRY_PI_IP:$PORT"
echo ""

# FFplay
echo "2. Using FFplay (from FFmpeg):"
echo "   ffplay srt://$RASPBERRY_PI_IP:$PORT"
echo ""

# GStreamer
echo "3. Using GStreamer:"
echo "   gst-launch-1.0 srcsrc uri=srt://$RASPBERRY_PI_IP:$PORT ! tsdemux ! h264parse ! avdec_h264 ! videoconvert ! autovideosink"
echo ""

# With passphrase
echo "4. With encryption (if passphrase is set):"
echo "   vlc srt://$RASPBERRY_PI_IP:$PORT?passphrase=mysecretpassword"
echo ""

# MPV
echo "5. Using MPV:"
echo "   mpv srt://$RASPBERRY_PI_IP:$PORT"
echo ""

echo "=== Quick Test ==="
echo "To quickly test, run this command (replace IP):"
echo "ffplay -fflags nobuffer -flags low_delay -probesize 32 -analyzeduration 0 srt://$RASPBERRY_PI_IP:$PORT"

