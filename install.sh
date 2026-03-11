#!/bin/bash

set -e

echo ""
echo "  ██████╗  █████╗ ███████╗██╗  ██╗███████╗ ██████╗ ██████╗  ██████╗ ███████╗"
echo "  ██╔══██╗██╔══██╗██╔════╝██║  ██║██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝"
echo "  ██████╔╝███████║███████╗███████║█████╗  ██║   ██║██████╔╝██║  ███╗█████╗  "
echo "  ██╔══██╗██╔══██║╚════██║██╔══██║██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝  "
echo "  ██████╔╝██║  ██║███████║██║  ██║██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗"
echo "  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝"
echo ""
echo "  DevOps Bash IDE Installer"
echo ""

# ── Check OS ─────────────────────────────────────────────────────────────────
if [[ "$(uname -s)" != "Linux" ]]; then
    echo "⚠  BashForge is designed for Linux/Ubuntu."
    echo "   On Windows, use WSL2 or run bashforge.py directly with Python."
    exit 1
fi

echo "Installing BashForge dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-tk

# Optional: JetBrains Mono font for best experience
if ! fc-list | grep -qi "JetBrains Mono"; then
    echo "Installing JetBrains Mono font (optional but recommended)..."
    FONT_DIR="$HOME/.local/share/fonts"
    mkdir -p "$FONT_DIR"
    TMPDIR=$(mktemp -d)
    curl -sL "https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip" \
        -o "$TMPDIR/jb.zip" 2>/dev/null \
        && unzip -q "$TMPDIR/jb.zip" "*.ttf" -d "$FONT_DIR" 2>/dev/null \
        && fc-cache -f "$FONT_DIR" \
        && echo "  Font installed." \
        || echo "  Font install skipped (non-critical)."
    rm -rf "$TMPDIR"
fi

# ── Install application ───────────────────────────────────────────────────────
INSTALL_DIR="$HOME/.bashforge"
BIN_DIR="/usr/local/bin"

mkdir -p "$INSTALL_DIR"

echo "Downloading BashForge..."
curl -fsSL \
    "https://raw.githubusercontent.com/pratyushojha-coder/bashforge/main/bashforge.py" \
    -o "$INSTALL_DIR/bashforge.py"

chmod +x "$INSTALL_DIR/bashforge.py"

echo "Creating launcher..."
sudo tee "$BIN_DIR/bashforge" > /dev/null << EOF
#!/bin/bash
python3 "$INSTALL_DIR/bashforge.py" "\$@"
EOF

sudo chmod +x "$BIN_DIR/bashforge"

# ── Desktop shortcut (optional) ───────────────────────────────────────────────
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/bashforge.desktop" << EOF
[Desktop Entry]
Name=BashForge
Comment=DevOps Bash Script IDE
Exec=bashforge
Icon=utilities-terminal
Type=Application
Categories=Development;IDE;
Keywords=bash;shell;devops;script;
EOF

echo ""
echo "✅  BashForge installed successfully!"
echo ""
echo "  Run with:   bashforge"
echo "  Or:         python3 ~/.bashforge/bashforge.py"
echo ""
echo "  Keyboard shortcuts:"
echo "    Ctrl+Enter   Run script"
echo "    Ctrl+/       Toggle comment/uncomment"
echo "    Ctrl+S       Save"
echo "    Ctrl+F/H     Find & Replace"
echo "    Ctrl+Z/Y     Undo / Redo"
echo "    Ctrl+D       Duplicate line"
echo "    Ctrl+A       Select all"
echo "    Tab          Indent (4 spaces)"
echo "    Shift+Tab    Unindent"
echo ""