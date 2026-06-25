# Exostream

**Turn a Raspberry Pi and USB webcam into a controllable network video source**

[![Version](https://img.shields.io/badge/version-0.3.0-blue.svg)](https://github.com/roaringsundew40/exostream)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Exostream captures video from a USB webcam on a Raspberry Pi and makes it available on your local network for production tools to pick up. A background daemon handles the actual streaming; you control it from a CLI on the Pi or remotely over the network.

## What it does

Exostream is built for setups where you want a small, always-on camera node — a Pi on a shelf, in a studio, or at an event — that you can start, stop, and reconfigure without babysitting a terminal session.

**Capture** — Detects V4L2-compatible webcams and reads MJPEG or raw YUYV frames from them.

**Stream** — Runs FFmpeg in the background to capture, convert, and output video. Output is delivered over **NDI** (Network Device Interface), so receivers on the same LAN can discover and use the feed without extra wiring or URL configuration.

**Control** — A daemon (`exostreamd`) keeps streams running independently of your shell. The `exostream` CLI talks to it over a Unix socket. The daemon also exposes a TCP control port (default **9023**) for remote management and ships with an optional desktop GUI.

**Persist** — Stream configuration and daemon state survive restarts, so a Pi can reboot and resume with the same settings.

Receivers include OBS, vMix, NDI Studio Monitor, Wirecast, and other NDI-compatible software. Exostream is not a general-purpose internet streaming server — it is a local-network camera appliance.

## How NDI fits in

NDI is the transport layer. Exostream's job is camera capture and lifecycle management on the Pi; NDI is how the video leaves the device.

1. The daemon captures frames from `/dev/video*` via FFmpeg.
2. Frames are converted to the format NDI expects (UYVY422).
3. FFmpeg's `libndi_newtek` output publishes a named source on the LAN.
4. NDI clients on the same network discover that source automatically (mDNS).

This gives you low-latency, production-grade video on a local network without configuring RTMP URLs or managing encoders on the receiving side. NDI handles its own compression after Exostream hands off raw frames — Exostream does not pre-encode to H.264.

If you need internet streaming (YouTube, Twitch, etc.), NDI is the wrong tool; see [Alternatives](#alternatives) below.

## Features

- **Background daemon** — Streams keep running after you close the terminal
- **CLI with Rich UI** — Status tables, panels, and watch mode
- **Remote control** — TCP API on port 9023; optional tkinter GUI (`python -m exostream.remote.gui`)
- **Service discovery** — Remote clients can find Exostream instances on the network
- **Multiple streams** — Up to 3 concurrent cameras per daemon
- **Flexible capture** — MJPEG (best for 1080p) or raw YUYV (lower CPU at 720p)
- **Configurable output** — Resolution, FPS, stream name, and NDI groups
- **State persistence** — Settings stored under `~/.exostream`

## Requirements

### Hardware

- Raspberry Pi 3, 4, or 5
- USB webcam (Logitech C920/C930 or any V4L2-compatible camera)
- Network connection (Gigabit Ethernet recommended for 1080p)

### Software

- Python 3.8+
- FFmpeg compiled with NDI support (`libndi_newtek`)
- `python3-pip` and build tools (installed automatically by `install.sh`)

```bash
sudo apt-get update
sudo apt-get install -y python3-pip
```

## Installation

### Automated (recommended)

The install script handles system dependencies, FFmpeg compilation, NDI SDK setup, and PATH configuration:

```bash
git clone https://github.com/roaringsundew40/exostream
cd exostream
./install.sh           # Interactive (asks before compiling FFmpeg)
./install.sh --auto    # Fully automatic (for unattended install)
./install.sh --skip-ffmpeg  # Skip FFmpeg if already installed
```

Compilation takes roughly 30–60 minutes on a Pi, mostly unattended. After it finishes:

```bash
source ~/.bashrc
exostream --version
exostream daemon start
exostream start --name "MyCamera"
```

### Manual

If you already have FFmpeg with NDI support:

```bash
git clone https://github.com/roaringsundew40/exostream
cd exostream
pip3 install -e . --user

echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Verify FFmpeg has NDI:

```bash
ffmpeg -formats 2>&1 | grep libndi_newtek
```

If that returns nothing, see [Building FFmpeg with NDI](#building-ffmpeg-with-ndi) below.

### Building FFmpeg with NDI

FFmpeg must be built with `--enable-libndi_newtek`. The [lplassman/FFMPEG-NDI](https://github.com/lplassman/FFMPEG-NDI/) repository provides patches and install scripts for Raspberry Pi and x86_64.

Quick check for a pre-built binary:

```bash
ffmpeg -formats 2>&1 | grep libndi_newtek
```

If not available, follow the FFMPEG-NDI README to patch FFmpeg 5.1+, install the NDI SDK for your architecture, and build:

```bash
./configure --enable-nonfree --enable-libndi_newtek
make -j$(nproc)
sudo make install
```

Architecture-specific NDI install scripts are included in the FFMPEG-NDI repo (`install-ndi-rpi4-aarch64.sh`, `install-ndi-rpi3-armhf.sh`, etc.).

## Usage

### Quick start

```bash
# Start the daemon
exostream daemon start

# List cameras
exostream devices

# Start streaming (appears as an NDI source named "MyCamera")
exostream start --name "MyCamera"

# Check status
exostream status

# Stop streaming
exostream stop

# Stop daemon when done
exostream daemon stop
```

### Daemon management

```bash
exostream daemon start
exostream daemon start --verbose
exostream daemon status
exostream daemon ping
exostream daemon stop
exostream daemon shutdown   # Graceful shutdown
```

### Streaming

**Defaults:** `/dev/video0`, 1920×1080, 30 fps, MJPEG input.

```bash
# Basic
exostream start --name "MyCamera"

# Custom device and resolution
exostream start --name "Studio Cam" --device /dev/video2 --resolution 1280x720 --fps 30

# NDI groups (clients filter by group)
exostream start --name "Camera 1" --groups "Studio,Production"

# Lower CPU at 720p (raw YUYV — not recommended for 1080p)
exostream start --name "MyCamera" --resolution 1280x720 --raw-input

# Stop one device or all streams
exostream stop --device /dev/video0
exostream stop --all

# Live status refresh
exostream status --watch
```

### Remote control

The daemon listens on **TCP port 9023** by default for JSON-RPC commands (same protocol as the local Unix socket). This enables control from another machine on the network.

**Desktop GUI:**

```bash
python -m exostream.remote.gui
```

The GUI supports service discovery, connection to a remote Pi, stream start/stop, and settings updates.

**Programmatic access:** See `exostream/cli/network_client.py` for a Python client (`NetworkClientManager`).

### CLI reference

| Command | Description |
|---------|-------------|
| `exostream start` | Start streaming from a camera |
| `exostream stop` | Stop one or all streams |
| `exostream status` | Show daemon and stream status |
| `exostream devices` | List available cameras |
| `exostream daemon start\|stop\|status\|ping\|shutdown` | Manage the daemon |

**Start options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--device` | `-d` | `/dev/video0` | Video device path |
| `--name` | `-n` | *(required)* | Stream name (visible to NDI clients) |
| `--resolution` | `-r` | `1920x1080` | Output resolution |
| `--fps` | `-f` | `30` | Frames per second |
| `--raw-input` | | off | Use YUYV instead of MJPEG |
| `--groups` | `-g` | none | NDI groups (comma-separated) |

**Global options:** `--socket`, `--verbose`, `--version`, `--help`

## Architecture

```
┌──────────────────┐     ┌──────────────────┐
│  exostream CLI   │     │  Remote GUI /    │
│  (local shell)   │     │  network client  │
└────────┬─────────┘     └────────┬─────────┘
         │ Unix socket             │ TCP :9023
         │ (JSON-RPC)              │ (JSON-RPC)
         └────────────┬────────────┘
                      ▼
         ┌────────────────────────┐
         │      exostreamd        │
         │  ├─ IPC + TCP servers  │
         │  ├─ Streaming service  │
         │  ├─ Settings manager   │
         │  └─ State manager      │
         └────────────┬───────────┘
                      ▼
         ┌────────────────────────┐
         │  FFmpeg (libndi_newtek)│
         │  V4L2 → NDI output     │
         └────────────┬───────────┘
                      ▼
              LAN (NDI discovery)
                      ▼
         OBS / vMix / NDI Monitor …
```

**Video pipeline:**

```
v4l2 input → decode (if MJPEG) → pixel format conversion → libndi_newtek output
```

## Capture and encoding notes

Exostream sends raw frames to NDI rather than pre-encoding to H.264. NDI applies its own compression on the wire.

**MJPEG (default)** — Supports 1080p30 on most cameras. Moderate CPU for JPEG decode. Recommended for high resolution.

**YUYV (`--raw-input`)** — Lower CPU, no decode step. USB bandwidth limits this to 720p on most cameras; 1080p YUYV often fails or stutters.

## Performance

### Bandwidth (NDI, approximate)

| Resolution | Bitrate |
|------------|---------|
| 720p30 | 30–50 Mbps |
| 1080p30 | 70–125 Mbps |

Use Ethernet for 1080p. WiFi may work for 720p.

### CPU (Raspberry Pi 4, approximate)

| Mode | CPU |
|------|-----|
| 720p30 YUYV | 15–25% |
| 720p30 MJPEG | 25–35% |
| 1080p30 MJPEG | 40–60% |

Higher resolutions need adequate cooling for sustained use.

## Troubleshooting

### FFmpeg missing NDI support

```bash
ffmpeg -formats 2>&1 | grep libndi_newtek
```

If empty, rebuild FFmpeg with `--enable-libndi_newtek` or run `./install.sh`.

### No video devices found

```bash
ls -l /dev/video*
exostream devices
```

Ensure the user is in the `video` group and the camera is connected.

### Stream not appearing on the network

1. Confirm the stream is running: `exostream status`
2. Pi and receiver must be on the same LAN; NDI uses mDNS (allow multicast through firewalls)
3. If you set `--groups`, the receiver must look in those groups
4. Check FFmpeg didn't exit: run with `exostream daemon start --verbose`

### Stuttering or high CPU

```bash
exostream start --name "MyCamera" --resolution 1280x720
exostream start --name "MyCamera" --resolution 1280x720 --raw-input  # if camera supports YUYV at 720p
```

Prefer Ethernet over WiFi. Monitor with `top`.

### `--raw-input` fails at 1080p

Expected — most USB cameras cannot deliver YUYV at 1080p30. Drop to 720p or remove `--raw-input` to use MJPEG.

## Project structure

```
exostream/
├── exostream/
│   ├── cli/                 # CLI client (exostream command)
│   │   ├── main.py
│   │   ├── ipc_client.py
│   │   └── network_client.py
│   ├── daemon/              # Background service (exostreamd)
│   │   ├── main.py
│   │   ├── service.py
│   │   ├── ipc_server.py
│   │   ├── tcp_server.py
│   │   ├── state_manager.py
│   │   └── settings_manager.py
│   ├── sender/              # FFmpeg capture and NDI output
│   │   ├── ffmpeg_encoder.py
│   │   └── webcam.py
│   ├── remote/              # Remote control GUI
│   │   └── gui.py
│   └── common/              # Config, protocol, discovery, logging
├── install.sh
├── uninstall.sh
├── setup.py
└── requirements.txt
```

## Known limitations

1. **NDI SDK required** — FFmpeg must be built with NDI support
2. **Local network only** — NDI is not designed for internet delivery
3. **High bandwidth** — Raw-frame NDI uses substantial LAN bandwidth
4. **No audio yet** — Video only
5. **Pi thermals** — Sustained 1080p needs adequate cooling

## Alternatives

| Need | Consider |
|------|----------|
| Internet streaming | SRT, RTMP, WebRTC |
| Recording to file | FFmpeg H.264 direct to disk |
| Lower LAN bandwidth | NDI HX (not yet supported here) |

## FAQ

**Why NDI instead of RTMP?**  
NDI targets local production workflows — switchers, OBS, and studio monitors on the same LAN — with low latency and zero URL setup. Use RTMP for platform streaming.

**Can I stream to the internet?**  
Not with NDI. Use SRT, RTMP, or WebRTC for that.

**Does this work on Raspberry Pi 3?**  
Yes, but prefer 720p for stable performance.

**Can I use multiple cameras?**  
Yes. The daemon supports up to 3 concurrent streams — start each with a different `--device` and `--name`:

```bash
exostream start --device /dev/video0 --name "Cam A"
exostream start --device /dev/video2 --name "Cam B"
```

**Why is bandwidth so high?**  
NDI prioritizes quality and latency. It compresses on the wire, but raw-frame input still demands more bandwidth than H.264-based protocols.

## Uninstallation

```bash
cd /path/to/exostream
./uninstall.sh           # Interactive
./uninstall.sh --basic   # Remove Exostream only
./uninstall.sh --full    # Remove Exostream, FFmpeg, and dependencies
```

Manual:

```bash
exostream daemon stop
pip3 uninstall exostream
rm -f ~/.local/bin/exostream ~/.local/bin/exostreamd
rm -rf ~/.exostream      # optional: remove saved state
```

## Upgrading

```bash
cd /path/to/exostream
git pull
pip3 install -e . --user --force-reinstall --no-deps
```

Or re-run `./install.sh`.

## Contributing

Pull requests are welcome. Key extension points:

- `exostream/daemon/service.py` — stream orchestration
- `exostream/sender/ffmpeg_encoder.py` — FFmpeg process management
- `exostream/cli/main.py` — CLI commands
- `exostream/common/protocol.py` — RPC method definitions

## License

MIT License

## Acknowledgments

- Vizrt/NewTek for the NDI protocol and SDK
- FFmpeg project
- Raspberry Pi Foundation
- [lplassman/FFMPEG-NDI](https://github.com/lplassman/FFMPEG-NDI/) for FFmpeg NDI build tooling
