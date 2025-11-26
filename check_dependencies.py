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

def check_ffmpeg_ndi():
    """Check if FFmpeg has NDI support"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-formats"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        if "libndi_newtek" in result.stdout:
            print("✓ FFmpeg has NDI support (libndi_newtek)")
            return True
        else:
            print("✗ FFmpeg does NOT have NDI support")
            print("  You need FFmpeg compiled with --enable-libndi_newtek")
            return False
    except FileNotFoundError:
        print("✗ FFmpeg not found")
        return False

def main():
    print("=== ExoStream NDI Dependency Check ===\n")
    
    all_ok = True
    
    print("Python Modules:")
    all_ok &= check_import("rich")
    all_ok &= check_import("click")
    all_ok &= check_import("yaml", "pyyaml")
    all_ok &= check_import("psutil")
    
    print("\nFFmpeg:")
    ffmpeg_ok = check_command("ffmpeg")
    all_ok &= ffmpeg_ok
    
    if ffmpeg_ok:
        print("\nNDI Support:")
        ndi_ok = check_ffmpeg_ndi()
        all_ok &= ndi_ok
    
    print("\n" + "="*40)
    if all_ok:
        print("✓ All dependencies are installed!")
        print("\nYou can now run: exostream send --stream-name 'MyStream'")
        return 0
    else:
        print("✗ Some dependencies are missing!")
        print("\nPlease install missing dependencies:")
        print("\nPython packages:")
        print("  pip3 install -e .")
        print("\nFFmpeg with NDI:")
        print("  1. Download NDI SDK from: https://www.ndi.tv/sdk/")
        print("  2. Install NDI SDK libraries")
        print("  3. Install or compile FFmpeg with --enable-libndi_newtek")
        print("     More info: https://trac.ffmpeg.org/wiki/CompilationGuide")
        return 1

if __name__ == "__main__":
    sys.exit(main())

