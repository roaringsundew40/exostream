#!/bin/bash
# Test playback locally on Raspberry Pi

echo "=== Testing Local Playback ==="
echo ""
echo "Make sure stream is running in another terminal!"
echo "This will try to play the stream locally for 5 seconds..."
echo ""

# Try with ffplay if available
if command -v ffplay &> /dev/null; then
    echo "Testing with ffplay..."
    timeout 5 ffplay -autoexit -loglevel info srt://127.0.0.1:9000
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✓ Stream works locally!"
        echo "If this works but Windows doesn't, check firewall/network"
    else
        echo ""
        echo "✗ Stream failed locally"
        echo "Check if exostream is actually running"
    fi
else
    echo "ffplay not available, trying with ffmpeg..."
    timeout 5 ffmpeg -i srt://127.0.0.1:9000 -f null - 2>&1 | tail -10
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✓ Stream data received"
    else
        echo ""
        echo "✗ Could not receive stream"
    fi
fi

echo ""
echo "If local test works, try from Windows with:"
echo "  ffplay -timeout 5000000 srt://$(hostname -I | awk '{print $1}'):9000"

