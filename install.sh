#!/bin/bash
set -e

echo "Installing fpeek Nautilus Extension..."

if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
else
    echo "Cannot detect distribution"
    exit 1
fi

echo "Detected distribution: $DISTRO"

case $DISTRO in
    fedora)
        echo "Installing dependencies for Fedora..."
        if ! rpm -qa | grep -q nautilus-python; then
            sudo dnf install -y nautilus-python python3-nautilus
        fi
        sudo dnf install -y --allowerasing ffmpeg file
        ;;
    
    ubuntu|debian|pop|linuxmint)
        echo "Installing dependencies for Debian/Ubuntu..."
        sudo apt update
        sudo apt install -y python3-nautilus ffmpeg python3-pip file
        ;;
    
    arch|manjaro)
        echo "Installing dependencies for Arch..."
        sudo pacman -S --needed --noconfirm python-nautilus ffmpeg python-pip file
        ;;
    
    opensuse*|suse)
        echo "Installing dependencies for openSUSE..."
        sudo zypper install -y python3-nautilus ffmpeg python3-pip file
        ;;
    
    *)
        echo "Unsupported distribution: $DISTRO"
        echo "Please install manually: nautilus-python, ffmpeg, file, python3-pip"
        exit 1
        ;;
esac

echo "Installing Python dependencies (numpy, pillow, matplotlib)..."
pip3 install --user numpy pillow matplotlib

EXTENSION_DIR="$HOME/.local/share/nautilus-python/extensions"
mkdir -p "$EXTENSION_DIR"

cp fpeek_common.py "$EXTENSION_DIR/"
cp fpeek_nautilus.py "$EXTENSION_DIR/"
cp fpeek_analysis.py "$EXTENSION_DIR/"

echo "✓ Extension installed!"
echo ""
echo "Restart Nautilus:"
echo "  killall nautilus && nautilus &"
echo ""
echo "Right-click any image file -> 'peek file metadata'"