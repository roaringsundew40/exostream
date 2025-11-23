# ExoStream Performance Guide

## Current Situation

Your Raspberry Pi 4's hardware H.264 encoder (v4l2h264enc) isn't working due to driver issues. This is a **known problem** on many Pi 4 systems.

You're using **software encoding (x264enc)** which uses the CPU instead of dedicated hardware.

## Optimized Settings for Software Encoding

### **Best Quality at 720p (Recommended)**
```bash
exostream send -s --resolution 1280x720 --fps 30 --bitrate 6000
```
- **CPU Usage:** ~60-70%
- **Latency:** <1 second
- **Quality:** Excellent for most uses
- **Network:** ~6 Mbps

### **Good Quality at 1080p with Lower FPS**
```bash
exostream send -s --resolution 1920x1080 --fps 24 --bitrate 6000
```
- **CPU Usage:** ~70-80%
- **Latency:** ~1-2 seconds
- **Quality:** Cinematic feel (24fps like movies)
- **Network:** ~6 Mbps

### **Lighter Load - 720p at 24fps**
```bash
exostream send -s --resolution 1280x720 --fps 24 --bitrate 4000
```
- **CPU Usage:** ~40-50%
- **Latency:** <500ms
- **Quality:** Good
- **Network:** ~4 Mbps

### **Maximum Quality (High CPU)**
```bash
exostream send -s --resolution 1920x1080 --fps 20 --bitrate 8000
```
- **CPU Usage:** ~80-90%
- **Latency:** ~2 seconds
- **Quality:** Best possible with software encoding
- **Network:** ~8 Mbps

## Why 720p is Actually Great

- **1280x720 = 921,600 pixels** - Still HD quality
- **Common use cases:** Video calls, streaming, surveillance
- **Most displays:** 720p looks great on laptop/phone screens
- **Performance:** Smooth 30fps with low latency

## CPU Usage Tips

Monitor CPU while streaming:
```bash
top -p $(pgrep -f exostream)
```

If CPU hits 100%, the encoder can't keep up → frames queue → latency increases

## Network Bandwidth

Test your network speed between Pi and PC:
```bash
# On Pi
iperf3 -s

# On PC  
iperf3 -c <pi-ip-address>
```

You need at least **8-10 Mbps** for comfortable 1080p streaming.

## Future Options

### **1. Pi 5**
The Raspberry Pi 5 has a much better hardware encoder that actually works.

### **2. External Hardware Encoder**
USB devices like Elgato Cam Link do hardware encoding.

### **3. Different Board**
Boards like NVIDIA Jetson have reliable hardware encoding.

### **4. Optimize Your Pi**
- **Overclock:** Can give 10-20% more performance
- **Cooling:** Better cooling = sustained performance
- **Disable GUI:** Run headless for more CPU

## Bottom Line

**720p @ 30fps with 6000kbps bitrate** is the sweet spot for:
- ✅ Great quality
- ✅ Low latency (<1 sec)
- ✅ Reliable performance
- ✅ Doesn't stress the Pi

This is actually how most professional webcams work!

