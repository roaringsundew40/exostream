#!/usr/bin/env python3
"""Test camera capabilities and GStreamer pipeline"""

import sys
import argparse
from exostream.sender.webcam import WebcamManager

def test_camera_with_gst(device_path, width=1920, height=1080, fps=30):
    """Test camera with a simple GStreamer pipeline"""
    try:
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst, GLib
        Gst.init(None)
        
        print(f"\n=== Testing {device_path} with GStreamer ===\n")
        
        # Create a simple test pipeline: v4l2src ! videoconvert ! autovideosink
        pipeline_str = (
            f"v4l2src device={device_path} ! "
            f"video/x-raw,width={width},height={height},framerate={fps}/1 ! "
            f"videoconvert ! "
            f"fpsdisplaysink video-sink=fakesink text-overlay=false"
        )
        
        print(f"Pipeline: {pipeline_str}\n")
        
        pipeline = Gst.parse_launch(pipeline_str)
        
        # Set up bus
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        
        # Start pipeline
        print("Starting pipeline for 5 seconds...")
        ret = pipeline.set_state(Gst.State.PLAYING)
        
        if ret == Gst.StateChangeReturn.FAILURE:
            print("✗ Failed to start pipeline!")
            return False
        
        # Run for 5 seconds
        loop = GLib.MainLoop()
        
        def on_message(bus, message):
            t = message.type
            if t == Gst.MessageType.ERROR:
                err, debug = message.parse_error()
                print(f"✗ Error: {err.message}")
                if debug:
                    print(f"  Debug: {debug}")
                loop.quit()
                return False
            elif t == Gst.MessageType.WARNING:
                warn, debug = message.parse_warning()
                print(f"⚠ Warning: {warn.message}")
            elif t == Gst.MessageType.STATE_CHANGED:
                if message.src == pipeline:
                    old, new, pending = message.parse_state_changed()
                    print(f"State: {old.value_nick} -> {new.value_nick}")
        
        bus.connect("message", on_message)
        
        # Stop after 5 seconds
        GLib.timeout_add_seconds(5, lambda: loop.quit())
        
        try:
            loop.run()
        except KeyboardInterrupt:
            pass
        
        # Stop pipeline
        pipeline.set_state(Gst.State.NULL)
        print("\n✓ Pipeline test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error testing camera: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description='Test camera with GStreamer')
    parser.add_argument('--device', '-d', default='/dev/video0', 
                       help='Video device path')
    parser.add_argument('--width', type=int, default=1920,
                       help='Video width')
    parser.add_argument('--height', type=int, default=1080,
                       help='Video height')
    parser.add_argument('--fps', '-f', type=int, default=30,
                       help='Frames per second')
    parser.add_argument('--list', '-l', action='store_true',
                       help='List available devices')
    
    args = parser.parse_args()
    
    print("=== ExoStream Camera Test ===\n")
    
    # Detect cameras
    print("Detecting video devices...")
    manager = WebcamManager()
    devices = manager.detect_devices()
    
    if not devices:
        print("✗ No video devices found!")
        return 1
    
    print(f"✓ Found {len(devices)} device(s):\n")
    for i, device in enumerate(devices):
        print(f"  [{i}] {device.path} - {device.name}")
    
    if args.list:
        return 0
    
    # Test the specified device
    device = manager.get_device_by_path(args.device)
    if not device:
        print(f"\n✗ Device {args.device} not found!")
        return 1
    
    print(f"\nTesting: {device.name} ({device.path})")
    print(f"Format: {args.width}x{args.height} @ {args.fps}fps")
    
    success = test_camera_with_gst(args.device, args.width, args.height, args.fps)
    
    if success:
        print("\n✓ Camera test passed! You can try 'exostream send' now.")
        return 0
    else:
        print("\n✗ Camera test failed!")
        print("\nTroubleshooting:")
        print("  1. Try a lower resolution: --width 1280 --height 720")
        print("  2. Try a lower framerate: --fps 15")
        print("  3. Check camera with: v4l2-ctl --device=/dev/video0 --list-formats-ext")
        return 1

if __name__ == '__main__':
    sys.exit(main())

