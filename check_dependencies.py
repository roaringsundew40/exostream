#!/usr/bin/env python3
"""Check if all required dependencies are installed"""

import sys
import subprocess

def check_import(module_name, package_name=None):
    """Check if a Python module can be imported"""
    try:
        __import__(module_name)
        print(f"✓ {package_name or module_name} is installed")
        return True
    except ImportError:
        print(f"✗ {package_name or module_name} is NOT installed")
        return False

def check_command(command):
    """Check if a command exists"""
    try:
        subprocess.run([command, "--version"], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        print(f"✓ {command} is installed")
        return True
    except FileNotFoundError:
        print(f"✗ {command} is NOT installed")
        return False

def check_gst_plugin(plugin_name):
    """Check if a GStreamer plugin exists"""
    try:
        result = subprocess.run(
            ["gst-inspect-1.0", plugin_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if result.returncode == 0:
            print(f"✓ GStreamer plugin '{plugin_name}' is available")
            return True
        else:
            print(f"✗ GStreamer plugin '{plugin_name}' is NOT available")
            return False
    except FileNotFoundError:
        print(f"✗ gst-inspect-1.0 not found")
        return False

def main():
    print("=== ExoStream Dependency Check ===\n")
    
    all_ok = True
    
    print("Python Modules:")
    all_ok &= check_import("gi", "PyGObject (python3-gi)")
    all_ok &= check_import("cairo", "pycairo (python3-gi-cairo)")
    all_ok &= check_import("rich")
    all_ok &= check_import("click")
    all_ok &= check_import("yaml", "pyyaml")
    all_ok &= check_import("psutil")
    
    print("\nGStreamer:")
    all_ok &= check_command("gst-launch-1.0")
    all_ok &= check_command("gst-inspect-1.0")
    
    print("\nGStreamer Plugins:")
    all_ok &= check_gst_plugin("v4l2src")
    all_ok &= check_gst_plugin("srtsink")
    all_ok &= check_gst_plugin("srtsrc")
    
    # Check for hardware encoders
    print("\nHardware Encoders:")
    has_v4l2 = check_gst_plugin("v4l2h264enc")  # Pi 4
    has_omx = check_gst_plugin("omxh264enc")     # Pi 3
    
    if not (has_v4l2 or has_omx):
        print("⚠ No hardware H.264 encoder found! Software encoding will be used.")
        all_ok = False
    
    print("\n" + "="*40)
    if all_ok:
        print("✓ All dependencies are installed!")
        print("\nYou can now run: exostream send")
        return 0
    else:
        print("✗ Some dependencies are missing!")
        print("\nPlease install missing dependencies:")
        print("\nSystem packages:")
        print("  sudo apt-get install python3-gi python3-gi-cairo gir1.2-gstreamer-1.0 \\")
        print("    gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good \\")
        print("    gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav")
        print("\nPython packages:")
        print("  pip3 install -e .")
        return 1

if __name__ == "__main__":
    sys.exit(main())

