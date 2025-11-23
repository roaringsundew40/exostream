# Quick Start: FFmpeg Hardware Encoding

## Step 1: Test if FFmpeg Hardware Encoder Works

```bash
bash test_ffmpeg_hw.sh
```

## If Test Passes ✓

**Congratulations!** You can use hardware encoding with FFmpeg!

### Start Streaming (1080p with hardware encoding):
```bash
exostream send --use-ffmpeg --resolution 1920x1080 --fps 30 --bitrate 6000
```

**Results:**
- ✅ **CPU Usage:** ~5-15% (very low!)
- ✅ **Quality:** Excellent  
- ✅ **Latency:** <500ms
- ✅ **Full 1080p @ 30fps** - No problem!

### Connect from Windows:
```cmd
ffplay srt://192.168.86.30:9000
```

Or VLC:
```cmd
"C:\Program Files\VideoLAN\VLC\vlc.exe" srt://192.168.86.30:9000 --network-caching=50
```

## If Test Fails ✗

Hardware encoder doesn't work. Use software encoding:

### Option 1: FFmpeg Software (Recommended)
```bash
exostream send --ffmpeg-software --resolution 1280x720 --fps 30 --bitrate 6000
```

### Option 2: GStreamer Software
```bash
exostream send -s --resolution 1280x720 --fps 30 --bitrate 6000
```

**Results:**
- CPU Usage: ~60-70%
- Quality: Good
- Latency: ~1 second
- Recommended: 720p @ 30fps

## Why FFmpeg Might Work Better

FFmpeg uses **h264_v4l2m2m** encoder which:
- Different driver implementation than GStreamer's v4l2h264enc
- Better memory management  
- More mature V4L2 M2M integration
- Often works when GStreamer doesn't

## All Options Summary

| Command | Backend | Encoder | CPU | Works? |
|---------|---------|---------|-----|--------|
| `exostream send --use-ffmpeg` | FFmpeg | h264_v4l2m2m (HW) | ~10% | Test first! |
| `exostream send --ffmpeg-software` | FFmpeg | libx264 (SW) | ~70% | Always |
| `exostream send` | GStreamer | v4l2h264enc (HW) | ~10% | Rarely on Pi 4 |
| `exostream send -s` | GStreamer | x264enc (SW) | ~70% | Always |

## Troubleshooting

### "FFmpeg not found"
```bash
sudo apt-get install ffmpeg
```

### Hardware encoding works but quality is poor
Increase bitrate:
```bash
exostream send --use-ffmpeg --bitrate 8000
```

### Still having issues?
See [FFMPEG_GUIDE.md](FFMPEG_GUIDE.md) for detailed troubleshooting.

## Bottom Line

**Try FFmpeg hardware encoding first!** It often works when GStreamer's doesn't, giving you full 1080p @ 30fps with minimal CPU usage.

Run the test:
```bash
bash test_ffmpeg_hw.sh
```

If it passes, you're golden! 🎉

