#!/bin/bash

set -e

echo "Installing BashForge..."

INSTALL_DIR="$HOME/.bashforge"
BIN_DIR="/usr/local/bin"

mkdir -p $INSTALL_DIR

curl -L https://raw.githubusercontent.com/pratyushojha-coder/bashforge/main/bashforge.py \
-o $INSTALL_DIR/bashforge.py

chmod +x $INSTALL_DIR/bashforge.py

# Create launcher
sudo tee $BIN_DIR/bashforge > /dev/null <<EOF
#!/bin/bash
python3 $INSTALL_DIR/bashforge.py
EOF

sudo chmod +x $BIN_DIR/bashforge

echo ""
echo "✅ BashForge installed successfully!"
echo ""
echo "Run:"
echo "bashforge"