#!/bin/bash

set -e

echo "Installing BashForge..."

# Install dependencies
sudo apt update
sudo apt install python3 python3-tk -y

INSTALL_DIR="$HOME/.bashforge"
BIN_DIR="/usr/local/bin"

mkdir -p $INSTALL_DIR

curl -L https://raw.githubusercontent.com/pratyushojha-coder/bashforge/main/bashforge.py \
-o $INSTALL_DIR/bashforge.py

chmod +x $INSTALL_DIR/bashforge.py

sudo tee $BIN_DIR/bashforge > /dev/null <<EOF
#!/bin/bash
python3 $INSTALL_DIR/bashforge.py
EOF

sudo chmod +x $BIN_DIR/bashforge

echo ""
echo "✅ BashForge installed successfully!"
echo "Run using:"
echo "bashforge"