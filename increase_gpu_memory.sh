#!/bin/bash
# Script to increase GPU memory allocation for hardware encoding

echo "=== Raspberry Pi GPU Memory Configuration ==="
echo ""

# Check current GPU memory
CURRENT_GPU_MEM=$(vcgencmd get_mem gpu | grep -oP '\d+')
echo "Current GPU memory: ${CURRENT_GPU_MEM}M"
echo ""

if [ "$CURRENT_GPU_MEM" -lt 128 ]; then
    echo "⚠ GPU memory is too low for hardware H.264 encoding!"
    echo "  Recommended: 128M or 256M"
    echo ""
    echo "To increase GPU memory:"
    echo ""
    echo "1. Edit the config file:"
    echo "   sudo nano /boot/firmware/config.txt"
    echo ""
    echo "   (On older Raspberry Pi OS, the file might be at /boot/config.txt)"
    echo ""
    echo "2. Find the line with 'gpu_mem' or add it if it doesn't exist:"
    echo "   gpu_mem=128"
    echo ""
    echo "   For better performance with 1080p, use:"
    echo "   gpu_mem=256"
    echo ""
    echo "3. Save the file (Ctrl+X, then Y, then Enter)"
    echo ""
    echo "4. Reboot your Raspberry Pi:"
    echo "   sudo reboot"
    echo ""
    echo "5. After reboot, verify the change:"
    echo "   vcgencmd get_mem gpu"
    echo ""
else
    echo "✓ GPU memory is sufficient (${CURRENT_GPU_MEM}M)"
fi

# Offer to do it automatically
echo ""
read -p "Would you like to automatically set gpu_mem=128? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Modifying /boot/firmware/config.txt..."
    
    # Try new location first
    if [ -f /boot/firmware/config.txt ]; then
        CONFIG_FILE="/boot/firmware/config.txt"
    elif [ -f /boot/config.txt ]; then
        CONFIG_FILE="/boot/config.txt"
    else
        echo "✗ Could not find config.txt"
        exit 1
    fi
    
    # Backup the config file
    sudo cp "$CONFIG_FILE" "${CONFIG_FILE}.backup"
    echo "✓ Backed up to ${CONFIG_FILE}.backup"
    
    # Check if gpu_mem already exists
    if grep -q "^gpu_mem=" "$CONFIG_FILE"; then
        # Update existing value
        sudo sed -i 's/^gpu_mem=.*/gpu_mem=128/' "$CONFIG_FILE"
        echo "✓ Updated gpu_mem to 128"
    else
        # Add new line
        echo "gpu_mem=128" | sudo tee -a "$CONFIG_FILE" > /dev/null
        echo "✓ Added gpu_mem=128"
    fi
    
    echo ""
    echo "✓ Configuration updated!"
    echo ""
    echo "Please reboot your Raspberry Pi for changes to take effect:"
    echo "  sudo reboot"
fi

