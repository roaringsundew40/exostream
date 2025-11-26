# Exostream

Stream webcam from Raspberry Pi using GStreamer with hardware H.264 encoding and SRT (Secure Reliable Transport) protocol.

## Features

- **Dual Backend Support** - Choose between GStreamer or FFmpeg
- **Hardware H.264 Encoding** - Utilizes Raspberry Pi's hardware encoder for minimal CPU usage
- **FFmpeg Integration** - Alternative hardware encoder (h264_v4l2m2m) that may work better on some systems
- **SRT Streaming** - Reliable streaming with low latency over local network or internet
- **Listener Mode** - Raspberry Pi acts as a server, clients connect to it
- **Encryption Support** - Optional SRT passphrase encryption
- **Quality Presets** - Easy configuration with low/medium/high presets
- **Beautiful CLI** - Rich terminal interface with real-time information

## Requirements

### Hardware
- Raspberry Pi 3 or 4
- Logitech C920 or C930 webcam (or any USB webcam)
- Network connection

### Software
- Python 3.8 or higher
- GStreamer 1.x with SRT plugin
- System packages (install on Raspberry Pi):

```bash
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gstreamer-1.0 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav
```

## Installation

### On Raspberry Pi (Sender)

1. Clone the repository:
```bash
git clone <repository-url>
cd exostream
```

2. Install Python dependencies:
```bash
pip3 install -e .
```

**Note:** If you're using a virtual environment, create it with system site packages:
```bash
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -e .
```

3. Verify installation:
```bash
# Check all dependencies
python3 check_dependencies.py

# Verify Exostream command
exostream --version
```

## Usage

### Starting the Stream (Raspberry Pi)

#### Try FFmpeg Hardware Encoding First (NEW!)
```bash
# Test if FFmpeg hardware encoder works
bash test_ffmpeg_hw.sh

# If test passes, use FFmpeg with hardware encoding
exostream send --use-ffmpeg
```

FFmpeg's h264_v4l2m2m encoder often works when GStreamer's doesn't! See [FFMPEG_GUIDE.md](FFMPEG_GUIDE.md) for details.

#### Basic Usage (GStreamer)
```bash
exostream send
```

This will start streaming with default settings:
- Device: `/dev/video0`
- Resolution: 1920x1080
- FPS: 30
- Bitrate: 6000 kbps
- Port: 9000

#### List Available Cameras
```bash
exostream send --list-devices
```

#### Custom Configuration
```bash
exostream send \
    --device /dev/video0 \
    --port 9000 \
    --resolution 1920x1080 \
    --fps 30 \
    --bitrate 4000
```

#### Using Presets
```bash
# Low quality (720p, 2Mbps)
exostream send --preset low

# Medium quality (1080p, 4Mbps) - default
exostream send --preset medium

# High quality (1080p, 6Mbps)
exostream send --preset high
```

#### With Encryption
```bash
exostream send --passphrase "mysecretpassword"
```

#### Verbose Mode
```bash
exostream send --verbose
```

### Connecting to the Stream (Client Computer)

Once the Raspberry Pi is streaming, you can connect from any computer on the network using various tools:

#### Using VLC Media Player
```bash
vlc srt://<raspberry-pi-ip>:9000
```

#### Using FFplay (from FFmpeg)
```bash
ffplay srt://<raspberry-pi-ip>:9000
```

#### Using GStreamer (Linux)
```bash
gst-launch-1.0 \
    srcsrc uri=srt://<raspberry-pi-ip>:9000 ! \
    tsdemux ! \
    h264parse ! \
    avdec_h264 ! \
    videoconvert ! \
    autovideosink
```

#### Using OBS Studio
1. Add a new Media Source
2. Set URL to: `srt://<raspberry-pi-ip>:9000`
3. Uncheck "Local File"

### Finding Your Raspberry Pi's IP Address
```bash
hostname -I
```

## Configuration Options

### Command Line Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--device` | `-d` | `/dev/video0` | Video device path |
| `--port` | `-p` | `9000` | SRT port to listen on |
| `--resolution` | `-r` | `1920x1080` | Video resolution |
| `--fps` | `-f` | `30` | Frames per second |
| `--bitrate` | `-b` | `4000` | Video bitrate in kbps |
| `--preset` | | | Quality preset (low/medium/high) |
| `--passphrase` | | | SRT encryption passphrase |
| `--software-encoder` | `-s` | | Use GStreamer software encoder (x264enc) |
| `--use-ffmpeg` | | | Use FFmpeg with hardware encoder (h264_v4l2m2m) |
| `--ffmpeg-software` | | | Use FFmpeg with software encoder (libx264) |
| `--list-devices` | `-l` | | List available devices and exit |
| `--verbose` | `-v` | | Enable verbose logging |

### Quality Presets

| Preset | Resolution | FPS | Bitrate | Use Case |
|--------|-----------|-----|---------|----------|
| low | 1280x720 | 25 | 2 Mbps | Low bandwidth networks |
| medium | 1920x1080 | 30 | 4 Mbps | Balanced quality/bandwidth |
| high | 1920x1080 | 30 | 6 Mbps | High quality, good network |

## Known Issues

### Hardware Encoder (v4l2h264enc) May Not Work
The Raspberry Pi 4's v4l2h264enc driver is **buggy on many systems**. If hardware encoding fails:

**Use software encoding instead:**
```bash
exostream send -s --resolution 1280x720 --fps 30 --bitrate 6000
```

This uses CPU instead of GPU but works reliably. See [PERFORMANCE_GUIDE.md](PERFORMANCE_GUIDE.md) for optimization tips.

### Recommended Settings for Software Encoding
- **Best:** 720p @ 30fps, 6000kbps bitrate (smooth, low latency)
- **Alternative:** 1080p @ 20-24fps, 6000kbps (higher res, cinematic feel)

## Troubleshooting

### Installation: PyGObject/girepository-2.0 not found
If `pip install -e .` fails with an error about `girepository-2.0` or PyGObject:

1. Make sure you installed the system packages first:
```bash
sudo apt-get install python3-gi python3-gi-cairo gir1.2-gstreamer-1.0
```

2. If using a virtual environment, recreate it with system packages:
```bash
deactivate  # if already in venv
rm -rf venv
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -e .
```

3. Verify with the dependency checker:
```bash
python3 check_dependencies.py
```

### No video devices found
Make sure your webcam is connected and recognized:
```bash
ls -l /dev/video*
v4l2-ctl --list-devices
```

### Port already in use
Check if another process is using the port:
```bash
sudo netstat -tulpn | grep 9000
```

### Pipeline fails to start
Check GStreamer installation and SRT plugin:
```bash
gst-inspect-1.0 srtsink
gst-inspect-1.0 v4l2h264enc  # Pi 4
gst-inspect-1.0 omxh264enc   # Pi 3
```

### High CPU usage
- Make sure hardware encoder is being used (check logs)
- Try lowering resolution or bitrate
- Use a quality preset instead of custom settings

### Stream is choppy or has artifacts
- Increase SRT latency: The latency is currently hardcoded to 120ms in the config
- Reduce bitrate or resolution
- Check network stability
- Ensure good lighting for the camera

## Architecture

```
Raspberry Pi (Sender)                    Client Computer
     Webcam                                  Display
       ↓                                        ↑
   V4L2 Capture                            SRT Client
       ↓                                        ↑
Hardware H.264 Encoder                    H.264 Decoder
       ↓                                        ↑
   SRT Listener  ←------- Network -------  SRT Caller
   (Port 9000)
```

### Pipeline Structure

The GStreamer pipeline on the Raspberry Pi:
```
v4l2src → capsfilter → queue → v4l2h264enc/omxh264enc → 
h264parse → mpegtsmux → queue → srtsink
```

## Development

### Project Structure
```
exostream/
├── exostream/
│   ├── __init__.py
│   ├── cli.py              # Main CLI entry point
│   ├── common/
│   │   ├── config.py       # Configuration management
│   │   ├── logger.py       # Logging setup
│   │   ├── network.py      # Network utilities
│   │   └── gst_utils.py    # GStreamer helpers
│   └── sender/
│       ├── webcam.py       # V4L2 device detection
│       ├── encoder.py      # GStreamer encoding pipeline
│       └── cli.py          # Sender CLI commands
├── requirements.txt
├── setup.py
└── README.md
```

### Running Tests
```bash
# TODO: Add tests
pytest
```

## Roadmap

### Phase 2: Robustness (Coming Soon)
- [ ] Error handling and reconnection logic
- [ ] Graceful shutdown
- [ ] Configuration file support

### Phase 3: Advanced Features
- [ ] Multiple quality presets
- [ ] Real-time stats dashboard
- [ ] Recording while streaming
- [ ] Adaptive bitrate

### Phase 4: Polish
- [ ] Beautiful terminal UI with live stats
- [ ] Network bandwidth adaptive bitrate
- [ ] Automatic reconnection
- [ ] Web-based configuration interface

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- GStreamer team for the excellent multimedia framework
- SRT Alliance for the SRT protocol
- Raspberry Pi Foundation for the amazing hardware

