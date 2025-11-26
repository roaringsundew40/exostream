# Exostream

Stream webcam from Raspberry Pi using **NDI (Network Device Interface)** protocol with FFmpeg.

## Features

- **NDI Streaming** - Industry-standard protocol for professional video over IP
- **Automatic Discovery** - NDI streams are automatically discoverable on your network
- **Raw Frame Streaming** - Option to send uncompressed frames; NDI handles compression internally
- **Flexible Input Formats** - Supports MJPEG (for high resolution) or YUYV (for lower CPU usage)
- **NDI Groups** - Organize streams into groups for better network management
- **Beautiful CLI** - Rich terminal interface with device detection
- **Cross-Platform Clients** - View streams with OBS, vMix, NDI Studio Monitor, VLC, and more

## What is NDI?

NDI (Network Device Interface) is a royalty-free protocol that allows video equipment to communicate over a local network. Unlike traditional streaming protocols:
- **Zero configuration** - Streams automatically appear on the network
- **Low latency** - Optimized for real-time video production
- **High quality** - Handles compression intelligently
- **Widely supported** - Works with OBS, vMix, Wirecast, and many other tools

## Requirements

### Hardware
- Raspberry Pi 3, 4, or 5
- USB webcam (e.g., Logitech C920, C930, or any V4L2-compatible camera)
- Network connection (Ethernet recommended for best quality)

### Software
- Python 3.8 or higher
- FFmpeg with NDI support
- System packages:

```bash
sudo apt-get update
sudo apt-get install -y python3-pip
```

## Installation

### 1. Install FFmpeg with NDI Support

FFmpeg needs to be compiled with NDI support. Here are your options:

#### Option A: Use a Pre-compiled Binary (Easiest)
Some distributions provide FFmpeg with NDI support. Check if yours does:
```bash
ffmpeg -formats 2>&1 | grep libndi_newtek
```

If you see `libndi_newtek`, you're good to go!

#### Option B: Build FFmpeg with NDI Support (Recommended)

This uses the [lplassman/FFMPEG-NDI repository](https://github.com/lplassman/FFMPEG-NDI/) which provides scripts to build FFmpeg with NDI support.

1. **Clone the FFMPEG-NDI repository:**
   ```bash
   git clone https://github.com/lplassman/FFMPEG-NDI.git
   ```

2. **Clone the FFmpeg repository and checkout version 5.1 or later:**
   ```bash
   git clone https://git.ffmpeg.org/ffmpeg.git
   cd ffmpeg
   git checkout n5.1
   ```

3. **Apply generic git email (required for patching):**
   ```bash
   git config user.email "you@example.com"
   ```

4. **Apply the NDI patch to restore NDI support:**
   ```bash
   sudo git am ../FFMPEG-NDI/libndi.patch
   sudo cp ../FFMPEG-NDI/libavdevice/libndi_newtek_* libavdevice/
   ```

5. **Install build prerequisites:**
   ```bash
   sudo bash ../FFMPEG-NDI/preinstall.sh
   ```

6. **Install NDI libraries for your architecture:**

   **For Raspberry Pi 4 (64-bit):**
   ```bash
   sudo bash ../FFMPEG-NDI/install-ndi-rpi4-aarch64.sh
   ```

   **For Raspberry Pi 4 (32-bit):**
   ```bash
   sudo bash ../FFMPEG-NDI/install-ndi-rpi4-armhf.sh
   ```

   **For Raspberry Pi 3 (32-bit):**
   ```bash
   sudo bash ../FFMPEG-NDI/install-ndi-rpi3-armhf.sh
   ```

   **For x86_64 (Intel/AMD):**
   ```bash
   sudo bash ../FFMPEG-NDI/install-ndi-x86_64.sh
   ```

   **For generic ARM64 or ARM32:**
   These require the NDI Advanced SDK. Download it manually from [ndi.tv](https://ndi.tv), extract the tar file, and copy it to the ffmpeg directory, then run:
   ```bash
   # ARM64
   sudo bash ../FFMPEG-NDI/install-ndi-generic-aarch64.sh
   # OR ARM32
   sudo bash ../FFMPEG-NDI/install-ndi-generic-armhf.sh
   ```

7. **Build and install FFmpeg:**
   ```bash
   ./configure --enable-nonfree --enable-libndi_newtek
   make -j$(nproc)
   sudo make install
   ```

8. **Verify NDI support:**
   ```bash
   ffmpeg -formats 2>&1 | grep libndi_newtek
   ```
   
   You should see `libndi_newtek` in the output.

### 2. Install Exostream

Clone the repository:
```bash
git clone https://github.com/roaringsundew40/exostream
cd exostream
```

Install Python dependencies:
```bash
pip3 install -e .
```

### 3. Verify Installation

```bash
# Check dependencies
python3 check_dependencies.py

# Verify Exostream command
exostream --version
```

## Usage

### Starting the Stream (Raspberry Pi)

#### Basic Usage
```bash
exostream send --name "MyCamera"
```

This will start streaming with default settings:
- Device: `/dev/video0`
- Resolution: 1920x1080
- FPS: 30
- Stream Name: "MyCamera" (visible to NDI clients)
- Input Format: MJPEG (best for 1080p)

#### List Available Cameras
```bash
exostream send --list-devices
```

#### Custom Configuration
```bash
exostream send \
    --name "Studio Camera 1" \
    --device /dev/video0 \
    --resolution 1920x1080 \
    --fps 30
```

#### Using Raw YUYV Input (Lower CPU)
For 720p streaming, you can use raw YUYV input which reduces CPU usage but may cause more stuttering:
```bash
exostream send --name "MyCamera" --resolution 1280x720 --raw-input
```

**Note:** Most cameras only support YUYV at 720p or lower due to USB bandwidth limitations. For 1080p, use MJPEG (default).

#### NDI Groups
Organize your streams into groups:
```bash
exostream send --name "Camera 1" --groups "Studio,Production"
```

#### Verbose Mode
```bash
exostream send --name "MyCamera" --verbose
```
## Configuration Options

### Command Line Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--device` | `-d` | `/dev/video0` | Video device path |
| `--name` | `-n` | `exostream` | NDI stream name (visible to clients) |
| `--groups` | `-g` | None | NDI groups (comma-separated) |
| `--resolution` | `-r` | `1920x1080` | Video resolution |
| `--fps` | `-f` | `30` | Frames per second |
| `--raw-input` | | | Use raw YUYV input (works best at 720p) |
| `--list-devices` | `-l` | | List available devices and exit |
| `--verbose` | `-v` | | Enable verbose logging |

## Understanding Raw Frame Streaming

Unlike traditional streaming that pre-encodes video to H.264:
- **Exostream sends raw uncompressed frames** to the NDI library
- **NDI handles compression** using its proprietary codec
- This provides **better quality** and **lower latency** than pre-encoded streams
- The CPU does pixel format conversion (MJPEG→Raw or YUYV→Raw), not H.264 encoding

### Input Format Notes

**MJPEG Input (Default)**:
- ✅ Supports high resolutions (1080p30)
- ✅ Widely supported by cameras
- ⚠️  Requires JPEG decoding (moderate CPU usage)
- 📝 Recommended for 1080p streaming

**YUYV Raw Input (--raw-input flag)**:
- ✅ No decoding needed (lower CPU usage)
- ✅ Best performance at 720p
- ❌ USB bandwidth limited (1080p30 = ~120MB/s, exceeds USB 2.0)
- ❌ Many cameras don't support YUYV at 1080p30
- 📝 Recommended for 720p streaming only

## Performance & Bandwidth

### Network Bandwidth

NDI uses approximately:
- **720p30**: 30-50 Mbps
- **1080p30**: 70-125 Mbps

**Recommendation**: Use Gigabit Ethernet for best results. WiFi may work for 720p but is not recommended for 1080p.

### CPU Usage

On Raspberry Pi 4:
- **720p30 YUYV**: ~15-25% CPU (lowest)
- **720p30 MJPEG**: ~25-35% CPU
- **1080p30 MJPEG**: ~40-60% CPU

The CPU handles:
1. Camera input decoding (if MJPEG)
2. Pixel format conversion (to UYVY422 for NDI)
3. Frame buffering and network transmission

## Troubleshooting

### Installation: FFmpeg NDI support not found

```bash
# Verify FFmpeg has NDI
ffmpeg -formats 2>&1 | grep libndi_newtek
```

If not found, you need to compile FFmpeg with `--enable-libndi_newtek`. See Installation section.

### No video devices found

Make sure your webcam is connected and recognized:
```bash
ls -l /dev/video*
```

Test with:
```bash
exostream send --list-devices
```

### Stream not appearing on network

1. **Check NDI is broadcasting**:
   - Look for "NDI stream name: ..." in the output
   - Make sure FFmpeg didn't error out

2. **Check network connectivity**:
   - Ensure Pi and client are on same network
   - NDI uses mDNS - check firewall allows multicast

3. **Check NDI groups**:
   - If you specified `--groups`, make sure your client is looking in those groups

### Performance issues / Stuttering

1. **Lower resolution**:
   ```bash
   exostream send --name "MyCamera" --resolution 1280x720
   ```

2. **Use YUYV at 720p** (if camera supports it):
   ```bash
   exostream send --name "MyCamera" --resolution 1280x720 --raw-input
   ```

3. **Use Ethernet instead of WiFi**

4. **Check CPU usage**:
   ```bash
   top
   ```

### Camera errors with --raw-input at 1080p

This is expected! Most USB cameras can't provide YUYV at 1080p30 due to bandwidth limits:
- Remove `--raw-input` flag to use MJPEG
- Or use `--resolution 1280x720` with `--raw-input`

## Architecture

```
Raspberry Pi (Sender)                         Client Computer
     Webcam                                    OBS / vMix / NDI Monitor
       ↓                                              ↑
   V4L2 Capture                                  NDI Receiver
   (MJPEG/YUYV)                                       ↑
       ↓                                              ↑
   FFmpeg Decode                                 NDI Decode
       ↓                                              ↑
  Raw Frames (UYVY422)                               ↑
       ↓                                              ↑
   NDI Encoding  ←-------- Network (mDNS) -----------┘
   (libndi_newtek)
```

### Pipeline Structure

The FFmpeg pipeline:
```
v4l2 input → decode (if MJPEG) → pixel format conversion → 
wrapped_avframe codec → libndi_newtek output
```

## Project Structure

```
exostream/
├── exostream/
│   ├── __init__.py
│   ├── cli.py              # Main CLI entry point
│   ├── common/
│   │   ├── config.py       # Configuration management (NDI, Video)
│   │   ├── logger.py       # Logging setup with Rich
│   │   ├── network.py      # Network utilities
│   │   └── gst_utils.py    # GStreamer helpers (legacy)
│   └── sender/
│       ├── webcam.py       # V4L2 device detection
│       ├── ffmpeg_encoder.py # FFmpeg NDI encoder
│       └── cli.py          # Sender CLI commands
├── requirements.txt
├── setup.py
├── check_dependencies.py   # Dependency checker
├── test_camera.py         # Camera testing utility
└── README.md
```

## Known Limitations

1. **NDI SDK Required**: FFmpeg must be compiled with NDI support
2. **Local Network Only**: NDI is designed for local networks, not internet streaming
3. **High Bandwidth**: NDI uses substantial bandwidth (up to 125 Mbps for 1080p)
4. **Raspberry Pi Performance**: Higher resolutions require adequate cooling for sustained streaming

## Alternatives

If NDI doesn't fit your needs:
- **For Internet Streaming**: Consider SRT, RTMP, or WebRTC
- **For Recording**: Use H.264 encoding directly to file
- **For Lower Bandwidth**: Consider pre-encoding to H.264 instead of raw frames

## Development

### Running Tests

Test your camera:
```bash
python3 test_camera.py --device /dev/video0
```

Check dependencies:
```bash
python3 check_dependencies.py
```

### Adding Features

The main encoder is in `exostream/sender/ffmpeg_encoder.py`. Key components:
- `FFmpegEncoder`: Handles FFmpeg process and NDI streaming
- `VideoConfig`: Resolution, FPS configuration
- `NDIConfig`: NDI-specific settings (stream name, groups)
- `WebcamManager`: V4L2 device detection and enumeration

## Roadmap

### Near Term
- [ ] Audio support
- [ ] Configuration file support
- [ ] Real-time statistics display
- [ ] Automatic reconnection on network issues

### Future
- [ ] Multiple camera support
- [ ] NDI HX support (lower bandwidth)
- [ ] Web-based configuration interface
- [ ] Systemd service file for auto-start

## FAQ

**Q: Why NDI instead of RTMP/YouTube/Twitch?**  
A: NDI is designed for professional production workflows with ultra-low latency. Use RTMP for internet streaming to platforms like YouTube.

**Q: Can I stream to the internet with this?**  
A: NDI is for local networks. For internet streaming, consider SRT, RTMP, or WebRTC solutions.

**Q: Why is my stream using so much bandwidth?**  
A: NDI prioritizes quality and latency over bandwidth. For lower bandwidth, use NDI HX (not yet supported) or switch to H.264-based streaming.

**Q: Does this work with Raspberry Pi 3?**  
A: Yes, but 1080p may be challenging. Use 720p for best results on Pi 3.

**Q: Can I use multiple cameras?**  
A: Currently, one camera per instance. You can run multiple Exostream instances with different stream names.

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- NewTek/Vizrt for the NDI protocol and SDK
- FFmpeg team for the excellent multimedia framework
- Raspberry Pi Foundation for amazing hardware
- The open source community

## Support

For issues and questions:
1. Check the Troubleshooting section above
2. Run `python3 check_dependencies.py` to verify your setup
3. Run with `--verbose` flag for detailed logs
4. Open an issue on GitHub with your logs
