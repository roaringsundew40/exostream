#!/bin/bash
# Check all video-related memory settings

echo "=== Video Memory Diagnostics ==="
echo ""

echo "1. GPU Memory:"
vcgencmd get_mem gpu
vcgencmd get_mem arm
echo ""

echo "2. CMA (Contiguous Memory Allocator):"
if [ -f /proc/device-tree/chosen/linux,cma-default-size ]; then
    CMA_SIZE=$(hexdump -e '4/1 "%02x"' /proc/device-tree/chosen/linux,cma-default-size | sed 's/^0*//')
    CMA_MB=$((0x$CMA_SIZE / 1024 / 1024))
    echo "CMA Size: ${CMA_MB}MB"
else
    echo "CMA info not available via device tree"
fi

# Check via dmesg
dmesg | grep -i cma | tail -5
echo ""

echo "3. Video4Linux devices:"
ls -l /dev/video* 2>/dev/null | grep -v "by-"
echo ""

echo "4. V4L2 encoder capabilities:"
v4l2-ctl --list-devices 2>/dev/null | grep -A 5 "bcm2835-codec-encode"
echo ""

echo "5. Kernel version:"
uname -r
echo ""

echo "=== Recommendations ==="
echo ""
echo "If CMA is less than 256MB, you may need to increase it:"
echo "  1. Edit /boot/firmware/cmdline.txt (or /boot/cmdline.txt)"
echo "  2. Add: cma=256M"
echo "  3. Reboot"
echo ""
echo "Current GPU memory should be at least 128MB (you have this already)"

