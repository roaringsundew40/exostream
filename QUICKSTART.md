# ExoStream Quick Start Guide

This guide will help you get ExoStream up and running in minutes.

## Prerequisites

Make sure you have a Raspberry Pi 3 or 4 with:
- Logitech C920/C930 webcam (or any USB webcam)
- Network connection
- Fresh Raspbian/Raspberry Pi OS installation

## Installation Steps

### 1. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    python3-gst-1.0 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libgstreamer1.0-dev \
    libcairo2-dev \
    libgirepository1.0-dev
```

### 2. Install ExoStream

```bash
cd /path/to/exostream
pip3 install -e .
```

### 3. Verify Installation

```bash
exostream --version
```

### 4. Check Your Webcam

```bash
# List available cameras
exostream send --list-devices

# Or manually check
ls -l /dev/video*
```

## First Stream

### Start Streaming (on Raspberry Pi)

```bash
exostream send
```

You should see output like:
```
Stream is available at:
  srt://192.168.1.100:9000
```

### Connect to Stream (on another computer)

#### Option 1: VLC (Easiest)
```bash
vlc srt://192.168.1.100:9000
```

#### Option 2: FFplay
```bash
ffplay srt://192.168.1.100:9000
```

#### Option 3: MPV
```bash
mpv srt://192.168.1.100:9000
```

## Common Commands

### Use a Different Camera
```bash
exostream send --device /dev/video2
```

### Change Quality
```bash
# Lower quality for slow networks
exostream send --preset low

# High quality
exostream send --preset high
```

### Custom Settings
```bash
exostream send \
    --resolution 1280x720 \
    --fps 25 \
    --bitrate 2000 \
    --port 9000
```

### Enable Encryption
```bash
# On Pi
exostream send --passphrase "mysecret"

# On client
vlc srt://192.168.1.100:9000?passphrase=mysecret
```

## Troubleshooting

### Can't find webcam?
```bash
# Check if webcam is recognized
lsusb | grep Logitech

# Check video devices
v4l2-ctl --list-devices
```

### Port already in use?
```bash
# Use a different port
exostream send --port 9001
```

### Stream is laggy?
```bash
# Try lower quality
exostream send --preset low

# Or adjust manually
exostream send --resolution 1280x720 --fps 25 --bitrate 2000
```

### Hardware encoder not working?
```bash
# Check available encoders
gst-inspect-1.0 | grep h264enc

# Should show either v4l2h264enc (Pi 4) or omxh264enc (Pi 3)
```

## Next Steps

- Read the full [README.md](README.md) for more options
- Check [examples/](examples/) for more usage examples
- Configure quality settings for your network

## Getting Help

If you encounter issues:
1. Run with `--verbose` flag to see detailed logs
2. Check the Troubleshooting section in README.md
3. Verify GStreamer and SRT plugin installation

