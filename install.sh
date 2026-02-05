#!/bin/bash
set -e

echo "Installing fpeek Nautilus Extension..."

# Check dependencies
if ! rpm -qa | grep -q nautilus-python; then
    echo "Installing nautilus-python..."
    sudo dnf install -y nautilus-python python3-nautilus
fi

echo "image analysis dependencies are being installed;"
pip3 install --user numpy pillow --break-system-packages

EXTENSION_DIR="$HOME/.local/share/nautilus-python/extensions"
mkdir -p "$EXTENSION_DIR"

cp fpeek_nautilus.py "$EXTENSION_DIR/"

echo "✓ Extension installed!"
echo ""
echo "Restart Nautilus:"
echo "  killall nautilus && nautilus &"
echo ""
echo "Right-click any image file -> 'peek file metadata'"