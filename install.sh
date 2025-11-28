#!/bin/bash
#
# Exostream Complete Installation Script for Raspberry Pi
# Handles everything from system dependencies to FFmpeg with NDI
#
# Usage:
#   ./install.sh              # Automatic mode (compiles FFmpeg without asking)
#   ./install.sh --interactive # Interactive mode (asks before compiling FFmpeg)
#   ./install.sh --skip-ffmpeg # Skip FFmpeg compilation
#

set -e  # Exit on error

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
AUTO_MODE=1  # Default to automatic mode
SKIP_FFMPEG_ARG=0

for arg in "$@"; do
    case $arg in
        --interactive)
            AUTO_MODE=0
            shift
            ;;
        --auto)
            AUTO_MODE=1
            shift
            ;;
        --skip-ffmpeg)
            SKIP_FFMPEG_ARG=1
            shift
            ;;
        --help)
            echo "Exostream Installation Script"
            echo ""
            echo "Usage:"
            echo "  ./install.sh              Automatic mode (default, compiles FFmpeg)"
            echo "  ./install.sh --interactive Interactive mode (asks before compiling FFmpeg)"
            echo "  ./install.sh --skip-ffmpeg Skip FFmpeg compilation"
            echo "  ./install.sh --help       Show this help"
            exit 0
            ;;
    esac
done

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

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should NOT be run as root/sudo"
   print_info "It will ask for sudo password when needed"
   exit 1
fi

# Check if sudo is available
if ! command -v sudo &> /dev/null; then
    print_error "sudo is required but not found"
    print_info "Please install sudo or run as appropriate user"
    exit 1
fi

# Verify sudo access
print_step "Verifying sudo access..."
if ! sudo -n true 2>/dev/null; then
    print_info "Sudo access required for system package installation"
    print_info "You may be prompted for your password"
    sudo -v || {
        print_error "Failed to obtain sudo access"
        exit 1
    }
else
    print_success "Sudo access verified"
fi

print_header "Exostream Complete Installation for Raspberry Pi"

# Detect Raspberry Pi
print_info "Detecting system..."
if [[ -f /proc/device-tree/model ]]; then
    MODEL=$(cat /proc/device-tree/model)
    print_success "Detected: $MODEL"
else
    print_warning "Not a Raspberry Pi, continuing anyway..."
    MODEL="Unknown"
fi

# Detect architecture
ARCH=$(uname -m)
print_info "Architecture: $ARCH"

# ============================================================================
# STEP 1: System Dependencies
# ============================================================================

print_header "Step 1: System Dependencies"

print_step "Updating package lists..."
sudo apt-get update -qq

# Install Git
print_step "Checking/installing Git..."
if ! command -v git &> /dev/null; then
    print_info "Installing Git..."
    sudo apt-get install -y git
    print_success "Git installed"
else
    print_success "Git already installed"
fi

# Install Python 3
print_step "Checking/installing Python 3..."
if ! command -v python3 &> /dev/null; then
    print_info "Installing Python 3..."
    sudo apt-get install -y python3 python3-pip python3-dev
    print_success "Python 3 installed"
else
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_success "Python $PYTHON_VERSION already installed"
fi

# Check Python version
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    print_error "Python 3.8 or higher is required"
    print_info "Your version: $(python3 --version)"
    exit 1
fi

# Install pip if needed
print_step "Checking/installing pip3..."
if ! command -v pip3 &> /dev/null; then
    print_info "Installing pip3..."
    sudo apt-get install -y python3-pip
    print_success "pip3 installed"
else
    print_success "pip3 already installed"
fi

# Install basic build tools
print_step "Installing build essentials..."
sudo apt-get install -y build-essential pkg-config

# Install tkinter for GUI (if available)
print_step "Installing tkinter for GUI..."
sudo apt-get install -y python3-tk || {
    print_warning "python3-tk not available (GUI may not work)"
}

print_success "System dependencies complete"

# ============================================================================
# STEP 2: FFmpeg with NDI Support
# ============================================================================

print_header "Step 2: FFmpeg with NDI Support"

# Check if FFmpeg already has NDI
print_step "Checking existing FFmpeg installation..."
HAS_NDI=0
if command -v ffmpeg &> /dev/null; then
    print_info "FFmpeg found, checking for NDI support..."
    if ffmpeg -formats 2>&1 | grep -q libndi_newtek; then
        print_success "FFmpeg already has NDI support! Skipping compilation."
        HAS_NDI=1
    else
        print_warning "FFmpeg found but lacks NDI support"
        print_info "Will compile FFmpeg with NDI support"
    fi
else
    print_info "FFmpeg not found, will compile with NDI support"
fi

if [ $HAS_NDI -eq 0 ]; then
    if [ $SKIP_FFMPEG_ARG -eq 1 ]; then
        print_warning "Skipping FFmpeg compilation (--skip-ffmpeg flag)"
        print_warning "Streaming will NOT work without FFmpeg with NDI support"
        SKIP_FFMPEG=1
    elif [ $AUTO_MODE -eq 1 ]; then
        print_info "Automatic mode: Will compile FFmpeg with NDI support"
        print_warning "This will take 30-60 minutes on Raspberry Pi"
        SKIP_FFMPEG=0
    else
        print_step "This will take 30-60 minutes on Raspberry Pi"
        read -p "Compile FFmpeg with NDI support now? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_warning "Skipping FFmpeg compilation"
            print_warning "Streaming will NOT work without FFmpeg with NDI support"
            print_info "You can run this script again later or compile manually"
            SKIP_FFMPEG=1
        else
            SKIP_FFMPEG=0
        fi
    fi
    
    if [ $SKIP_FFMPEG -eq 0 ]; then
        
        print_step "Installing FFmpeg dependencies..."
        sudo apt-get install -y \
            autoconf automake build-essential cmake \
            libass-dev libfreetype6-dev libgnutls28-dev libmp3lame-dev \
            libsdl2-dev libtool libva-dev libvdpau-dev libvorbis-dev \
            libxcb1-dev libxcb-shm0-dev libxcb-xfixes0-dev meson ninja-build \
            pkg-config texinfo wget yasm zlib1g-dev nasm git-core
        
        print_success "FFmpeg dependencies installed"
        
        # Create build directory
        BUILD_DIR="$HOME/ffmpeg_build"
        mkdir -p "$BUILD_DIR"
        cd "$BUILD_DIR"
        
        print_step "Cloning FFMPEG-NDI repository..."
        if [ ! -d "FFMPEG-NDI" ]; then
            git clone https://github.com/lplassman/FFMPEG-NDI.git
            print_success "FFMPEG-NDI cloned"
        else
            print_info "FFMPEG-NDI already exists"
        fi
        
        print_step "Cloning FFmpeg repository..."
        if [ ! -d "ffmpeg" ]; then
            git clone https://git.ffmpeg.org/ffmpeg.git
            cd ffmpeg
            git checkout n5.1
            print_success "FFmpeg cloned (version 5.1)"
        else
            print_info "FFmpeg already exists"
            cd ffmpeg
        fi
        
        # Configure git for patching
        print_step "Configuring git for patches..."
        git config user.email "installer@exostream.local" || true
        git config user.name "Exostream Installer" || true
        
        # Apply NDI patch
        print_step "Applying NDI patch..."
        if [ ! -f "libavdevice/libndi_newtek_common.h" ]; then
            git am ../FFMPEG-NDI/libndi.patch || {
                print_warning "Patch may already be applied or failed"
                git am --abort 2>/dev/null || true
            }
            cp ../FFMPEG-NDI/libavdevice/libndi_newtek_* libavdevice/ 2>/dev/null || true
            print_success "NDI patch applied"
        else
            print_info "NDI patch already applied"
        fi
        
        # Install prerequisites
        print_step "Installing FFmpeg build prerequisites..."
        sudo bash ../FFMPEG-NDI/preinstall.sh
        print_success "Prerequisites installed"
        
        # Install NDI SDK based on architecture
        print_step "Installing NDI SDK for $ARCH..."
        
        if [[ "$ARCH" == "aarch64" ]]; then
            # 64-bit ARM (Raspberry Pi 4/5 with 64-bit OS)
            print_info "Installing NDI for ARM64 (Raspberry Pi 4/5 64-bit)"
            sudo bash ../FFMPEG-NDI/install-ndi-rpi4-aarch64.sh
        elif [[ "$ARCH" == "armv7l" ]] || [[ "$ARCH" == "armhf" ]]; then
            # 32-bit ARM
            if [[ "$MODEL" == *"Raspberry Pi 4"* ]] || [[ "$MODEL" == *"Raspberry Pi 5"* ]]; then
                print_info "Installing NDI for ARM32 (Raspberry Pi 4/5 32-bit)"
                sudo bash ../FFMPEG-NDI/install-ndi-rpi4-armhf.sh
            else
                print_info "Installing NDI for ARM32 (Raspberry Pi 3)"
                sudo bash ../FFMPEG-NDI/install-ndi-rpi3-armhf.sh
            fi
        elif [[ "$ARCH" == "x86_64" ]]; then
            print_info "Installing NDI for x86_64"
            sudo bash ../FFMPEG-NDI/install-ndi-x86_64.sh
        else
            print_error "Unsupported architecture: $ARCH"
            print_info "You may need to install NDI SDK manually"
            exit 1
        fi
        
        print_success "NDI SDK installed"
        
        # Configure FFmpeg
        print_step "Configuring FFmpeg (this may take a few minutes)..."
        ./configure --enable-nonfree --enable-libndi_newtek || {
            print_error "FFmpeg configuration failed"
            print_info "Check the output above for errors"
            exit 1
        }
        print_success "FFmpeg configured"
        
        # Build FFmpeg
        print_step "Building FFmpeg (this will take 30-60 minutes on Raspberry Pi)..."
        print_info "Be patient, this is the longest step..."
        NPROC=$(nproc)
        print_info "Using $NPROC CPU cores for compilation"
        
        make -j$NPROC || {
            print_error "FFmpeg compilation failed"
            print_info "This can happen due to low memory. Try:"
            print_info "  1. Close other applications"
            print_info "  2. Increase swap space"
            print_info "  3. Run: make -j1 (slower but uses less memory)"
            exit 1
        }
        
        print_success "FFmpeg compiled successfully!"
        
        # Install FFmpeg
        print_step "Installing FFmpeg..."
        sudo make install
        
        # Update library cache
        sudo ldconfig
        
        print_success "FFmpeg installed"
        
        # Verify NDI support
        print_step "Verifying NDI support..."
        if ffmpeg -formats 2>&1 | grep -q libndi_newtek; then
            print_success "FFmpeg has NDI support! ✓"
        else
            print_error "FFmpeg installed but NDI support not detected"
            exit 1
        fi
        
        # Return to original directory
        cd - > /dev/null
    fi
fi

# ============================================================================
# STEP 3: Install Exostream
# ============================================================================

print_header "Step 3: Install Exostream"

print_step "Installing Python dependencies..."
cd "$SCRIPT_DIR"
pip3 install -e . --user --break-system-packages

print_success "Exostream package installed"

# Configure PATH
print_step "Configuring PATH..."
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    print_info "Adding ~/.local/bin to PATH in ~/.bashrc..."
    
    # Backup bashrc
    cp ~/.bashrc ~/.bashrc.backup.$(date +%Y%m%d_%H%M%S)
    
    echo '' >> ~/.bashrc
    echo '# Added by Exostream installer' >> ~/.bashrc
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    
    print_success "PATH configured in ~/.bashrc"
    
    # Add to current session
    export PATH="$HOME/.local/bin:$PATH"
else
    print_success "PATH already configured"
fi

# Add user to video group
print_step "Configuring video device permissions..."
if groups | grep -q video; then
    print_success "User already in 'video' group"
else
    print_info "Adding user to 'video' group..."
    sudo usermod -aG video $USER
    print_success "User added to 'video' group"
    print_warning "You may need to log out and back in for this to take effect"
fi

# ============================================================================
# STEP 4: Verify Installation
# ============================================================================

print_header "Step 4: Verifying Installation"

# Verify commands
print_step "Verifying commands..."
VERIFICATION_FAILED=0

if command -v exostream &> /dev/null; then
    VERSION=$(exostream --version 2>&1 | grep -oP '\d+\.\d+\.\d+' || echo "unknown")
    print_success "exostream command available (v$VERSION)"
else
    print_error "exostream command not found"
    VERIFICATION_FAILED=1
fi

if command -v exostreamd &> /dev/null; then
    VERSION=$(exostreamd --version 2>&1 | grep -oP '\d+\.\d+\.\d+' || echo "unknown")
    print_success "exostreamd command available (v$VERSION)"
else
    print_error "exostreamd command not found"
    VERIFICATION_FAILED=1
fi

# Verify Python dependencies
print_step "Verifying Python dependencies..."
MISSING_DEPS=0

# Check each dependency with correct import name
if ! python3 -c "import rich" 2>/dev/null; then
    print_error "Missing Python package: rich"
    MISSING_DEPS=1
fi

if ! python3 -c "import click" 2>/dev/null; then
    print_error "Missing Python package: click"
    MISSING_DEPS=1
fi

if ! python3 -c "import yaml" 2>/dev/null; then
    print_error "Missing Python package: pyyaml"
    MISSING_DEPS=1
fi

if ! python3 -c "import psutil" 2>/dev/null; then
    print_error "Missing Python package: psutil"
    MISSING_DEPS=1
fi

if [ $MISSING_DEPS -eq 0 ]; then
    print_success "All Python dependencies verified"
else
    print_warning "Some Python dependencies are missing"
    print_info "Try running: pip3 install -r requirements.txt --user --break-system-packages"
fi


# Check for cameras
print_step "Checking for video devices..."
if ls /dev/video* &> /dev/null; then
    NUM_DEVICES=$(ls /dev/video* 2>/dev/null | wc -l)
    print_success "Found $NUM_DEVICES video device(s)"
else
    print_warning "No video devices found"
    print_info "Connect a USB camera and check with: ls -l /dev/video*"
fi

# ============================================================================
# Installation Complete
# ============================================================================

print_header "Installation Complete!"

if [ $VERIFICATION_FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓✓✓ Exostream v0.3.0 installed successfully! ✓✓✓${NC}"
    echo ""
    echo -e "${CYAN}Quick Start:${NC}"
    echo ""
    echo "  1. Start daemon:"
    echo -e "     ${YELLOW}exostream daemon start${NC}"
    echo ""
    echo "  2. List cameras:"
    echo -e "     ${YELLOW}exostream devices${NC}"
    echo ""
    echo "  3. Start streaming:"
    echo -e "     ${YELLOW}exostream start --name \"MyCamera\"${NC}"
    echo ""
    echo "  4. Check status:"
    echo -e "     ${YELLOW}exostream status${NC}"
    echo ""
    echo "  5. Stop streaming:"
    echo -e "     ${YELLOW}exostream stop${NC}"
    echo ""
    echo "  6. Stop daemon:"
    echo -e "     ${YELLOW}exostream daemon stop${NC}"
    echo ""
    echo -e "${CYAN}Documentation:${NC}"
    echo "  - Quick start:  ${BLUE}cat QUICKSTART.md${NC}"
    echo "  - Full guide:   ${BLUE}cat README.md${NC}"
    echo "  - Architecture: ${BLUE}cat docs/ARCHITECTURE.md${NC}"
    echo ""
    
    # Check if PATH update is needed
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]] && ! command -v exostream &> /dev/null; then
        echo -e "${YELLOW}⚠ Important:${NC}"
        echo "  Commands not yet in PATH. Run one of:"
        echo -e "    ${YELLOW}source ~/.bashrc${NC}    (refresh current terminal)"
        echo -e "    ${YELLOW}bash${NC}                (start new shell)"
        echo "  Or simply close and reopen your terminal"
        echo ""
    fi
    
    # Note about group membership
    if ! groups | grep -q video; then
        echo -e "${YELLOW}⚠ Note:${NC}"
        echo "  You've been added to the 'video' group"
        echo "  Log out and back in for camera access to work"
        echo ""
    fi
    
    print_success "Ready to stream!"
    
else
    print_error "Installation completed but some verification checks failed"
    print_info "Check the messages above"
    exit 1
fi
