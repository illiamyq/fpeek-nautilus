#!/bin/bash
set -e

echo "Installing fpeek Nautilus Extension..."

# Check dependencies
if ! rpm -qa | grep -q nautilus-python; then
    echo "Installing nautilus-python..."
    sudo dnf install -y nautilus-python python3-nautilus
fi

# Create extension directory
EXTENSION_DIR="$HOME/.local/share/nautilus-python/extensions"
mkdir -p "$EXTENSION_DIR"

# Copy extension
cp fpeek_nautilus.py "$EXTENSION_DIR/"

echo "✓ Extension installed!"
echo ""
echo "Restart Nautilus:"
echo "  killall nautilus && nautilus &"
echo ""
echo "Right-click any file → look for ' File Peek'"
