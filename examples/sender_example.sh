#!/bin/bash
# Example script for starting the ExoStream sender

# Basic usage with defaults
# exostream send

# List available cameras
# exostream send --list-devices

# Medium quality preset (default)
exostream send --preset medium

# High quality with encryption
# exostream send --preset high --passphrase "mysecretpassword"

# Custom configuration
# exostream send \
#     --device /dev/video0 \
#     --port 9000 \
#     --resolution 1920x1080 \
#     --fps 30 \
#     --bitrate 4000 \
#     --verbose

# Low quality for poor network
# exostream send --preset low --port 9000

