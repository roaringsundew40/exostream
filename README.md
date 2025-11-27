# Exostream

**Professional NDI streaming from Raspberry Pi with a modern service-based architecture**

[![Version](https://img.shields.io/badge/version-0.3.0-blue.svg)](https://github.com/roaringsundew40/exostream)
[![Tests](https://img.shields.io/badge/tests-42%2F42%20passing-brightgreen.svg)](tests/)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Stream webcam video over **NDI (Network Device Interface)** using FFmpeg, with a beautiful CLI and background daemon service.

**✨ One-command installation • Background service • Beautiful CLI • Production ready**

## ✨ What's New in v0.3.0

**Complete architectural rewrite!** Exostream now features:

- 🚀 **Background Daemon** - Runs as a service, no terminal required
- 🎨 **Beautiful CLI** - Rich terminal UI with colors, tables, and panels
- 🔌 **IPC Communication** - Client-server architecture via Unix sockets
- 💾 **State Persistence** - Configuration and status survive restarts
- 🔄 **Multiple Clients** - Control from multiple terminals simultaneously
- 🧪 **Fully Tested** - 42 comprehensive tests, 100% passing
- 📚 **Complete Documentation** - Extensive guides and examples

## Features

### Core Features
- **NDI Streaming** - Industry-standard protocol for professional video over IP
- **Automatic Discovery** - NDI streams are automatically discoverable on your network
- **Service-Based** - Background daemon with beautiful CLI frontend
- **State Management** - Persistent configuration across restarts
- **Device Detection** - Automatic webcam discovery and management

### Streaming Features
- **Raw Frame Streaming** - Uncompressed frames; NDI handles compression internally
- **Flexible Input Formats** - MJPEG (high resolution) or YUYV (lower CPU)
- **NDI Groups** - Organize streams into groups for network management
- **Multiple Resolutions** - 720p, 1080p, and custom resolutions
- **Configurable FPS** - 15, 30, 60 fps support

### User Experience
- **Beautiful CLI** - Rich terminal interface with status tables
- **Real-time Status** - Watch mode for live monitoring
- **Clear Errors** - User-friendly error messages with solutions
- **Works Anywhere** - No need to be in project directory
- **Cross-Platform Clients** - View with OBS, vMix, NDI Studio Monitor, VLC

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

## 🎉 New in v0.3.0: Fully Automated Installation!

**Fresh Raspberry Pi to working NDI stream in ONE command!**

```bash
git clone https://github.com/roaringsundew40/exostream
cd exostream
./install.sh --auto
```

**That's it!** The script handles **everything automatically**:

✅ Installs Python, Git, and build tools  
✅ Compiles FFmpeg with NDI support (~30-60 min)  
✅ Installs NDI SDK for your Raspberry Pi  
✅ Installs Exostream package  
✅ Configures PATH in ~/.bashrc  
✅ Sets up camera permissions  
✅ Verifies complete installation  

**After installation, use from anywhere:**
```bash
exostream daemon start
exostream start --name "MyCamera"
```

**Total time**: ~60-90 minutes (mostly unattended FFmpeg compilation)  
**User interaction**: Zero (in --auto mode)  
**Result**: Complete working system ✨

See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for details, or continue below for manual installation.

---

## Installation

### Automated Installation (Recommended)

**Use the installation script** that handles everything:

```bash
git clone https://github.com/roaringsundew40/exostream
cd exostream
./install.sh           # Interactive (asks before compiling FFmpeg)
./install.sh --auto    # Fully automatic (for unattended install)
```

The script will:
1. Install system dependencies (Python, Git, build tools)
2. Compile and install FFmpeg with NDI support
3. Install NDI SDK for your architecture
4. Install Exostream and configure PATH
5. Set up permissions for camera access
6. Verify everything works

**After installation:**
```bash
source ~/.bashrc       # Refresh PATH
exostream --version    # Verify
exostream daemon start # Start using!
```

### Manual Installation

If you prefer manual control or already have dependencies:

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

3. **Apply generic git email and name (required for patching):**
   ```bash
   git config user.email "you@example.com"
   git config user.name "You"
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

**🚀 Automated Install (Recommended):**

The installation script handles **everything** automatically:
- ✅ Installs system dependencies (Python, Git, build tools)
- ✅ Compiles FFmpeg with NDI support (optional, ~30-60 min)
- ✅ Installs Exostream package
- ✅ Configures PATH automatically
- ✅ Sets up video group permissions
- ✅ Verifies complete installation

```bash
git clone https://github.com/roaringsundew40/exostream
cd exostream
./install.sh
```

**Script Options:**
```bash
./install.sh              # Interactive (asks before FFmpeg compilation)
./install.sh --auto       # Fully automatic (compiles FFmpeg)
./install.sh --skip-ffmpeg # Skip FFmpeg (if already installed)
./install.sh --help       # Show help
```

**Manual Install:**

If you prefer manual installation or already have FFmpeg with NDI:
```bash
git clone https://github.com/roaringsundew40/exostream
cd exostream
pip3 install -e . --user

# Ensure ~/.local/bin is in your PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 3. Verify Installation

```bash
# Check dependencies
python3 check_dependencies.py

# Verify commands are available
exostream --version
exostreamd --version

# Test daemon
exostream daemon start
exostream daemon status
exostream daemon stop
```

## Usage

### Quick Start

```bash
# 1. Start the daemon (runs in background)
exostream daemon start

# 2. List your cameras
exostream devices

# 3. Start streaming
exostream start --name "MyCamera"

# 4. Check status
exostream status

# 5. Stop streaming
exostream stop

# 6. Stop daemon (when done)
exostream daemon stop

# Test installation
exostream test
```

### Daemon Management

```bash
# Start daemon
exostream daemon start
exostream daemon start --verbose  # With detailed logging

# Check if daemon is running
exostream daemon status

# Health check
exostream daemon ping

# Stop daemon
exostream daemon stop
```

### Streaming Control

#### Start Streaming

**Basic:**
```bash
exostream start --name "MyCamera"
```

Default settings:
- Device: `/dev/video0`
- Resolution: 1920x1080
- FPS: 30
- Input Format: MJPEG (best for 1080p)

**Custom Configuration:**
```bash
exostream start --name "Studio Camera 1" --device /dev/video0 --resolution 1920x1080 --fps 30
```

**With NDI Groups:**
```bash
exostream start --name "Camera 1" --groups "Studio,Production"
```

**Lower CPU (720p with raw YUYV):**
```bash
exostream start --name "MyCamera" --resolution 1280x720 --raw-input
```

**Note:** Most cameras only support YUYV at 720p or lower due to USB bandwidth limitations. For 1080p, use MJPEG (default).

#### Stop Streaming
```bash
exostream stop
```

#### Check Status
```bash
exostream status

# Watch mode (refresh every 2 seconds)
exostream status --watch
```

### Device Management

#### List Available Cameras
```bash
exostream devices
```

Output shows:
- 🟢 FREE devices (available)
- 🔴 IN USE devices (currently streaming)
- Device path, name, and index

---

## Testing

### Run All Tests

Verify your installation with a single command:

```bash
exostream test
```

**Output:**
```
╭────────────────────────────╮
│ Running Exostream Tests    │
╰────────────────────────────╯

╭─────────────────┬───────╮
│ Category        │ Count │
├─────────────────┼───────┤
│ Total Tests     │    42 │
│ Passed          │    42 │
╰─────────────────┴───────╯

╭─ Success ──────────────────╮
│ ✓ All tests passed!        │
│ 42/42 tests successful     │
╰────────────────────────────╯
```

### Verbose Output

See detailed test results:

```bash
exostream test --verbose
```

Shows each test name, status, and error messages.

### When to Test

- ✅ **After installation** - Verify everything works
- ✅ **After updates** - Ensure nothing broke
- ✅ **Before deployment** - Final verification
- ✅ **When reporting bugs** - Attach test results

See [TESTING.md](TESTING.md) for complete testing guide.

---

## Architecture

Exostream v0.3.0 uses a modern service-based architecture:

```
┌─────────────────────────────────────────────┐
│              exostream CLI                  │
│  (User commands from any terminal)          │
└─────────────────┬───────────────────────────┘
                  │ Unix Socket (JSON-RPC)
┌─────────────────▼───────────────────────────┐
│           exostreamd Daemon                 │
│  (Runs in background)                       │
│                                             │
│  ├─ IPC Server (handles commands)           │
│  ├─ Streaming Service (manages FFmpeg)      │
│  ├─ State Manager (persists config)         │
│  └─ Webcam Manager (detects devices)        │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│          FFmpeg + NDI Streaming             │
│  (Captures from camera, streams via NDI)    │
└─────────────────────────────────────────────┘
```

**Benefits:**
- ✅ No terminal blocking - daemon runs in background
- ✅ Control from anywhere - multiple clients can connect
- ✅ State persistence - configuration survives restarts
- ✅ Clean separation - CLI, service, and encoding layers isolated
- ✅ Easy to automate - systemd-ready architecture

## Configuration Options

### Stream Start Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--device` | `-d` | `/dev/video0` | Video device path |
| `--name` | `-n` | Required | NDI stream name (visible to clients) |
| `--groups` | `-g` | None | NDI groups (comma-separated) |
| `--resolution` | `-r` | `1920x1080` | Video resolution |
| `--fps` | `-f` | `30` | Frames per second |
| `--raw-input` | | | Use raw YUYV input (best at 720p) |

### Global Options

| Option | Short | Description |
|--------|-------|-------------|
| `--socket` | | Custom daemon socket path |
| `--verbose` | `-v` | Enable verbose logging |
| `--version` | | Show version and exit |
| `--help` | | Show help message |

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

## Documentation

Exostream includes comprehensive documentation:

- **QUICKSTART.md** - Get started in 5 minutes
- **COMPLETE.md** - Complete project overview
- **PROGRESS.md** - Development status and roadmap
- **ARCHITECTURE.md** - Detailed architecture guide
- **PHASE1_SUMMARY.md** - IPC layer documentation
- **PHASE2_SUMMARY.md** - Daemon service documentation
- **PHASE3_SUMMARY.md** - CLI client documentation

## Development

### Running Tests

**All tests:**
```bash
python3 -m unittest discover tests -v
```

Expected: 42/42 tests passing ✅

**Individual test suites:**
```bash
python3 -m unittest tests.test_ipc -v      # IPC tests (14)
python3 -m unittest tests.test_daemon -v   # Daemon tests (19)
python3 -m unittest tests.test_cli -v      # CLI tests (9)
```

**Test your camera:**
```bash
python3 test_camera.py --device /dev/video0
```

**Check dependencies:**
```bash
python3 check_dependencies.py
```

### Project Structure

```
exostream/
├── exostream/
│   ├── cli/              # CLI client
│   │   ├── main.py       # Command implementation
│   │   └── ipc_client.py # IPC client
│   ├── daemon/           # Background service
│   │   ├── main.py       # Daemon entry point
│   │   ├── service.py    # Streaming service
│   │   ├── ipc_server.py # IPC server
│   │   └── state_manager.py # State persistence
│   ├── common/           # Shared code
│   │   ├── protocol.py   # IPC protocol
│   │   ├── config.py     # Configuration
│   │   └── logger.py     # Logging
│   └── sender/           # Streaming core
│       ├── ffmpeg_encoder.py # FFmpeg wrapper
│       └── webcam.py     # Camera detection
├── tests/                # Test suite
├── docs/                 # Documentation
└── examples/             # Example scripts
```

### Adding Features

**Key components:**
- `daemon/service.py` - Streaming service orchestration
- `sender/ffmpeg_encoder.py` - FFmpeg process management
- `cli/main.py` - CLI commands
- `common/protocol.py` - IPC method definitions

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

## Uninstallation

To remove Exostream from your system:

```bash
cd /path/to/exostream
./uninstall.sh
```

This will:
- Stop any running daemon
- Remove installed commands
- Optionally remove state directory and configurations
- Clean up PATH modifications

**Manual uninstall:**
```bash
# Stop daemon
exostream daemon stop

# Uninstall package
pip3 uninstall exostream

# Remove commands
rm ~/.local/bin/exostream ~/.local/bin/exostreamd

# Optionally remove state
rm -rf ~/.exostream
```

## Upgrading

To upgrade to a newer version:

```bash
cd /path/to/exostream
git pull
pip3 install -e . --user --force-reinstall --no-deps
```

Or run the install script again:
```bash
./install.sh
```

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
