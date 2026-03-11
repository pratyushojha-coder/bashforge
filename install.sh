#!/bin/bash

set -e

echo "Installing BashForge..."

INSTALL_DIR="$HOME/.bashforge"
BIN_DIR="/usr/local/bin"

# Create directory
mkdir -p $INSTALL_DIR

# Download latest script
curl -L https://raw.githubusercontent.com/pratyushojha-coder/bashforge/main/bashforge.py -o $INSTALL_DIR/bashforge.py

# Make executable
chmod +x $INSTALL_DIR/bashforge.py

# Create global command
sudo ln -sf $INSTALL_DIR/bashforge.py $BIN_DIR/bashforge

echo ""
echo "✅ BashForge installed successfully!"
echo "Run it using:"
echo ""
echo "bashforge"