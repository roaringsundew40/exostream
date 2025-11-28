#!/bin/bash
#
# Exostream Uninstallation Script
# Comprehensive removal with multiple cleanup levels
#
# Usage:
#   ./uninstall.sh           # Interactive (asks what to remove)
#   ./uninstall.sh --basic   # Remove only Exostream
#   ./uninstall.sh --full    # Remove everything (Exostream + FFmpeg + deps)
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
    echo ""
}

# Parse arguments
CLEANUP_LEVEL="interactive"

for arg in "$@"; do
    case $arg in
        --basic)
            CLEANUP_LEVEL="basic"
            shift
            ;;
        --full)
            CLEANUP_LEVEL="full"
            shift
            ;;
        --help)
            echo "Exostream Uninstallation Script"
            echo ""
            echo "Usage:"
            echo "  ./uninstall.sh          Interactive mode (asks what to remove)"
            echo "  ./uninstall.sh --basic  Remove only Exostream (keep FFmpeg, deps)"
            echo "  ./uninstall.sh --full   Remove everything (Exostream + FFmpeg + deps)"
            echo "  ./uninstall.sh --help   Show this help"
            exit 0
            ;;
    esac
done

print_header "Exostream Uninstallation"

if [ "$CLEANUP_LEVEL" = "interactive" ]; then
    echo "Choose cleanup level:"
    echo ""
    echo "  1) Basic    - Remove only Exostream (keep FFmpeg, build tools)"
    echo "  2) Standard - Remove Exostream + state/logs (keep FFmpeg, build tools)"
    echo "  3) Full     - Remove EVERYTHING (Exostream + FFmpeg + build deps)"
    echo ""
    read -p "Enter choice [1-3] (default: 2): " CHOICE
    
    case $CHOICE in
        1)
            CLEANUP_LEVEL="basic"
            print_info "Selected: Basic cleanup"
            ;;
        3)
            CLEANUP_LEVEL="full"
            print_warning "Selected: Full cleanup (will remove FFmpeg and dependencies)"
            ;;
        *)
            CLEANUP_LEVEL="standard"
            print_info "Selected: Standard cleanup"
            ;;
    esac
    echo ""
fi

# ============================================================================
# STEP 1: Stop Exostream Services
# ============================================================================

print_header "Step 1: Stop Exostream Services"

print_step "Checking for running daemon..."
if command -v exostream &> /dev/null; then
    if exostream daemon ping &> /dev/null 2>&1; then
        print_info "Stopping daemon..."
        exostream daemon stop || true
        print_success "Daemon stopped"
    else
        print_info "Daemon not running"
    fi
else
    print_info "exostream command not found"
fi

print_step "Checking for exostream processes..."
if pgrep -f exostreamd > /dev/null 2>&1; then
    print_warning "Found running exostreamd processes"
    print_info "Stopping them..."
    pkill -f exostreamd || true
    sleep 1
    print_success "Processes stopped"
else
    print_info "No exostream processes running"
fi

# ============================================================================
# STEP 2: Uninstall Exostream Package
# ============================================================================

print_header "Step 2: Uninstall Exostream Package"

print_step "Uninstalling exostream package..."
pip3 uninstall -y exostream 2>/dev/null || print_warning "Package not found in pip"
print_success "Package uninstalled"

print_step "Removing installed commands..."
REMOVED=0
if [ -f "$HOME/.local/bin/exostream" ]; then
    rm "$HOME/.local/bin/exostream"
    print_success "Removed exostream command"
    REMOVED=1
fi

if [ -f "$HOME/.local/bin/exostreamd" ]; then
    rm "$HOME/.local/bin/exostreamd"
    print_success "Removed exostreamd command"
    REMOVED=1
fi

if [ $REMOVED -eq 0 ]; then
    print_info "No commands found to remove"
fi

# ============================================================================
# STEP 3: Clean Up Exostream Files
# ============================================================================

print_header "Step 3: Clean Up Exostream Files"

print_step "Removing socket files..."
if [ -f "/tmp/exostream.sock" ]; then
    rm "/tmp/exostream.sock"
    print_success "Removed socket file"
else
    print_info "No socket file found"
fi

if [ "$CLEANUP_LEVEL" != "basic" ]; then
    print_step "Removing state directory..."
    if [ -d "$HOME/.exostream" ]; then
        rm -rf "$HOME/.exostream"
        print_success "Removed state directory: $HOME/.exostream"
    else
        print_info "No state directory found"
    fi
else
    print_step "Checking state directory..."
    if [ -d "$HOME/.exostream" ]; then
        print_warning "State directory kept: $HOME/.exostream"
        print_info "Contains your configurations and logs"
    fi
fi

# ============================================================================
# STEP 4: Clean Up PATH Configuration
# ============================================================================

print_header "Step 4: Clean Up PATH Configuration"

if grep -q "# Added by Exostream installer" ~/.bashrc 2>/dev/null; then
    print_step "Removing PATH modifications from ~/.bashrc..."
    # Remove the comment line and the export line
    # Escape $ in sed pattern (in sed, $ means end of line, so we need \$)
    sed -i.bak '/# Added by Exostream installer/,/export PATH="\$HOME\/\.local\/bin:\$PATH"/d' ~/.bashrc
    print_success "Removed PATH modifications"
    print_info "Backup saved to ~/.bashrc.bak"
else
    print_info "No PATH modifications found"
fi

# ============================================================================
# STEP 5: Remove User from Video Group (Optional)
# ============================================================================

print_header "Step 5: Video Group Membership"

if groups | grep -q video; then
    print_warning "You are currently in the 'video' group"
    
    REMOVE_GROUP=0
    if [ "$CLEANUP_LEVEL" = "full" ]; then
        read -p "Remove yourself from 'video' group? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            REMOVE_GROUP=1
        fi
    else
        print_info "Keeping video group membership (may be needed for other apps)"
    fi
    
    if [ $REMOVE_GROUP -eq 1 ]; then
        sudo gpasswd -d $USER video
        print_success "Removed from video group"
        print_warning "Log out and back in for this to take effect"
    fi
else
    print_info "Not in video group"
fi

# ============================================================================
# STEP 6: Remove FFmpeg (Full cleanup only)
# ============================================================================

if [ "$CLEANUP_LEVEL" = "full" ]; then
    print_header "Step 6: Remove FFmpeg Installation"
    
    if command -v ffmpeg &> /dev/null; then
        print_warning "FFmpeg is installed"
        read -p "Remove FFmpeg? (y/N) " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_step "Removing FFmpeg..."
            
            # Check if it was installed via apt or compiled
            if dpkg -l | grep -q ffmpeg; then
                print_info "Removing FFmpeg via apt..."
                sudo apt-get remove -y ffmpeg libavcodec-dev libavformat-dev libavutil-dev || true
                print_success "FFmpeg removed"
            else
                print_info "FFmpeg appears to be compiled from source"
                
                # Try to remove from /usr/local
                if [ -f "/usr/local/bin/ffmpeg" ]; then
                    sudo rm -f /usr/local/bin/ffmpeg
                    sudo rm -f /usr/local/bin/ffprobe
                    sudo rm -rf /usr/local/lib/libav*
                    sudo rm -rf /usr/local/include/libav*
                    sudo ldconfig
                    print_success "Removed compiled FFmpeg"
                fi
            fi
        else
            print_info "FFmpeg kept"
        fi
    else
        print_info "FFmpeg not found"
    fi
    
    # Remove build directory
    print_step "Checking for FFmpeg build directory..."
    if [ -d "$HOME/ffmpeg_build" ]; then
        print_warning "Found build directory: $HOME/ffmpeg_build"
        read -p "Remove FFmpeg build directory? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$HOME/ffmpeg_build"
            print_success "Removed build directory"
        else
            print_info "Build directory kept"
        fi
    else
        print_info "No build directory found"
    fi
    
    # Remove NDI SDK
    print_step "Checking for NDI libraries..."
    if [ -d "/usr/local/include/ndi" ] || [ -f "/usr/local/lib/libndi.so" ]; then
        print_warning "Found NDI SDK installation"
        read -p "Remove NDI SDK? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo rm -rf /usr/local/include/ndi
            sudo rm -f /usr/local/lib/libndi*
            sudo ldconfig
            print_success "Removed NDI SDK"
        else
            print_info "NDI SDK kept"
        fi
    else
        print_info "No NDI SDK found"
    fi
fi

# ============================================================================
# STEP 7: Remove Build Dependencies (Full cleanup only)
# ============================================================================

if [ "$CLEANUP_LEVEL" = "full" ]; then
    print_header "Step 7: Remove Build Dependencies"
    
    print_warning "This will remove development packages used for building FFmpeg"
    print_info "These may be needed for other software development"
    echo ""
    read -p "Remove build dependencies? (y/N) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "Removing build dependencies..."
        
        sudo apt-get remove -y \
            autoconf automake cmake \
            libass-dev libfreetype6-dev libgnutls28-dev libmp3lame-dev \
            libsdl2-dev libtool libva-dev libvdpau-dev libvorbis-dev \
            libxcb1-dev libxcb-shm0-dev libxcb-xfixes0-dev meson ninja-build \
            texinfo yasm zlib1g-dev nasm git-core 2>/dev/null || true
        
        sudo apt-get autoremove -y
        
        print_success "Build dependencies removed"
    else
        print_info "Build dependencies kept"
    fi
fi

# ============================================================================
# Final Summary
# ============================================================================

print_header "Uninstallation Complete"

echo ""
echo -e "${GREEN}✓ Exostream has been uninstalled${NC}"
echo ""

echo "What was removed:"
case $CLEANUP_LEVEL in
    basic)
        echo "  ✓ Exostream package and commands"
        echo "  ✓ Socket file"
        echo "  - State directory kept"
        echo "  - FFmpeg kept"
        echo "  - Build dependencies kept"
        ;;
    standard)
        echo "  ✓ Exostream package and commands"
        echo "  ✓ Socket file"
        echo "  ✓ State directory and configurations"
        echo "  ✓ PATH modifications"
        echo "  - FFmpeg kept"
        echo "  - Build dependencies kept"
        ;;
    full)
        echo "  ✓ Exostream package and commands"
        echo "  ✓ Socket file"
        echo "  ✓ State directory and configurations"
        echo "  ✓ PATH modifications"
        echo "  ? FFmpeg (if you chose to remove)"
        echo "  ? Build dependencies (if you chose to remove)"
        ;;
esac

echo ""
echo "Remaining files:"
echo "  - Source directory: ${BLUE}$(pwd)${NC}"
echo "    (You can delete this manually: rm -rf $(pwd))"
echo ""

if [ -d "$HOME/.exostream" ]; then
    echo "  - State directory: ${BLUE}$HOME/.exostream${NC}"
    echo "    (Contains your configurations and logs)"
    echo ""
fi

if [ "$CLEANUP_LEVEL" != "full" ] && command -v ffmpeg &> /dev/null; then
    echo "  - FFmpeg: ${BLUE}$(which ffmpeg)${NC}"
    echo "    (Kept - may be useful for other applications)"
    echo ""
fi

print_success "Uninstallation completed!"

# Reminder about group membership
if groups | grep -q video && [ "$CLEANUP_LEVEL" = "full" ]; then
    echo ""
    print_warning "You are still in the 'video' group"
    print_info "Log out and back in if you removed yourself from it"
fi

echo ""
