# FFmpeg Hardware Encoding Guide

ExoStream now supports **FFmpeg** as an alternative to GStreamer! FFmpeg's h264_v4l2m2m encoder has better hardware support on some Raspberry Pi systems.

## Test FFmpeg Hardware Encoder

**First, test if it works:**
```bash
bash test_ffmpeg_hw.sh
```

If you see "SUCCESS! Hardware encoding works with FFmpeg!", you can use FFmpeg hardware encoding!

## Usage

### **FFmpeg with Hardware Encoder (Recommended if test passes)**
```bash
exostream send --use-ffmpeg
```

This uses:
- **Encoder:** h264_v4l2m2m (hardware)
- **CPU Usage:** ~5-15% (very low!)
- **Quality:** Excellent
- **Latency:** <500ms

### **FFmpeg with Software Encoder**
```bash
exostream send --ffmpeg-software
```

This uses:
- **Encoder:** libx264 (software)
- **CPU Usage:** ~60-80%
- **Quality:** Excellent
- **Latency:** ~1 second

### **GStreamer (Default)**
```bash
# Hardware (if available)
exostream send

# Software
exostream send -s
```

## Comparison

| Method | Encoder | CPU Usage | Quality | Latency |
|--------|---------|-----------|---------|---------|
| FFmpeg HW | h264_v4l2m2m | ~5-15% | Excellent | <500ms |
| FFmpeg SW | libx264 | ~60-80% | Excellent | ~1sec |
| GStreamer HW | v4l2h264enc | ~5-15% | Good | <500ms |
| GStreamer SW | x264enc | ~60-80% | Good | ~1sec |

## Why Try FFmpeg?

1. **Different driver** - h264_v4l2m2m vs v4l2h264enc
2. **Better hardware detection** - Sometimes works when GStreamer doesn't
3. **Simpler pipeline** - Fewer moving parts
4. **Industry standard** - Used by most video tools

## Examples

### **1080p Hardware Encoding (if HW works)**
```bash
exostream send --use-ffmpeg --resolution 1920x1080 --fps 30 --bitrate 6000
```

### **720p Hardware Encoding**
```bash
exostream send --use-ffmpeg --resolution 1280x720 --fps 30 --bitrate 4000
```

### **With Encryption**
```bash
exostream send --use-ffmpeg --passphrase "mysecret"
```

### **Custom Settings**
```bash
exostream send --use-ffmpeg \
    --resolution 1920x1080 \
    --fps 24 \
    --bitrate 6000 \
    --port 9000
```

## Troubleshooting

### "FFmpeg not found"
Install FFmpeg:
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

### "h264_v4l2m2m encoder NOT found"
Your FFmpeg doesn't have V4L2 M2M support. Use software encoding:
```bash
exostream send --ffmpeg-software
```

### Still not working?
Fall back to GStreamer software encoding:
```bash
exostream send -s --resolution 1280x720
```

## Performance Tips

### **If hardware encoding works:**
- ✅ Use 1080p @ 30fps - No problem!
- ✅ Low CPU, low latency
- ✅ Can run multiple streams

### **If using software encoding:**
- Use 720p @ 30fps for best balance
- Or 1080p @ 20-24fps for higher resolution
- Monitor CPU with `top`

## Debug FFmpeg Output

Run with verbose flag to see FFmpeg details:
```bash
exostream send --use-ffmpeg --verbose
```

You'll see FFmpeg's encoding statistics in real-time.

## Summary

1. **Test:** `bash test_ffmpeg_hw.sh`
2. **If SUCCESS:** `exostream send --use-ffmpeg` (hardware!)
3. **If FAILED:** `exostream send -s --resolution 1280x720` (software)

FFmpeg's h264_v4l2m2m often works when GStreamer's v4l2h264enc doesn't!

