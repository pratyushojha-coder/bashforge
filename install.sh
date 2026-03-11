#!/bin/bash

set -e

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo "  ██████╗  █████╗ ███████╗██╗  ██╗███████╗ ██████╗ ██████╗  ██████╗ ███████╗"
echo "  ██╔══██╗██╔══██╗██╔════╝██║  ██║██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝"
echo "  ██████╔╝███████║███████╗███████║█████╗  ██║   ██║██████╔╝██║  ███╗█████╗  "
echo "  ██╔══██╗██╔══██║╚════██║██╔══██║██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝  "
echo "  ██████╔╝██║  ██║███████║██║  ██║██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗"
echo "  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝"
echo ""
echo "  DevOps Bash IDE — Installer v2"
echo "you can contibute to https://github.com/pratyushojha-coder/bashforge"
echo ""
echo ""

# ── OS guard ──────────────────────────────────────────────────────────────────
if [[ "$(uname -s)" != "Linux" ]]; then
    echo "⚠  BashForge requires Linux (Ubuntu / WSL2)."
    echo "   On Windows, open WSL2 and run this installer inside it."
    exit 1
fi

# ── Dependencies ──────────────────────────────────────────────────────────────
echo "→ Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-tk curl unzip fontconfig

# ── JetBrains Mono font (optional, best UI experience) ───────────────────────
if ! fc-list 2>/dev/null | grep -qi "JetBrains Mono"; then
    echo "→ Installing JetBrains Mono font..."
    FONT_DIR="$HOME/.local/share/fonts/JetBrainsMono"
    mkdir -p "$FONT_DIR"
    TMP_ZIP=$(mktemp /tmp/jbmono_XXXXXX.zip)
    curl -fsSL \
        "https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip" \
        -o "$TMP_ZIP" 2>/dev/null \
    && unzip -qo "$TMP_ZIP" "fonts/ttf/*.ttf" -d "$FONT_DIR" 2>/dev/null \
    && fc-cache -f "$FONT_DIR" \
    && echo "  ✓ Font installed." \
    || echo "  ⚠ Font install skipped (non-critical — Consolas will be used)."
    rm -f "$TMP_ZIP"
else
    echo "  ✓ JetBrains Mono already installed."
fi

# ── Install BashForge ─────────────────────────────────────────────────────────
INSTALL_DIR="$HOME/.bashforge"
BIN_DIR="/usr/local/bin"

mkdir -p "$INSTALL_DIR"

echo "→ Downloading bashforge.py..."
curl -fsSL \
    "https://raw.githubusercontent.com/pratyushojha-coder/bashforge/main/bashforge.py" \
    -o "$INSTALL_DIR/bashforge.py"

chmod +x "$INSTALL_DIR/bashforge.py"

# ── Launcher script ───────────────────────────────────────────────────────────
echo "→ Creating launcher..."
sudo tee "$BIN_DIR/bashforge" > /dev/null << LAUNCHER
#!/bin/bash
exec python3 "$INSTALL_DIR/bashforge.py" "\$@"
LAUNCHER
sudo chmod +x "$BIN_DIR/bashforge"

# ── .desktop entry (app menu integration) ────────────────────────────────────
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/bashforge.desktop" << DESKTOP
[Desktop Entry]
Name=BashForge
Comment=DevOps Bash Script IDE
Exec=bashforge
Icon=utilities-terminal
Type=Application
Categories=Development;IDE;TextEditor;
Keywords=bash;shell;devops;script;kubernetes;docker;terraform;
StartupNotify=true
DESKTOP

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "  ✅  BashForge installed successfully!"
echo ""
echo "  Launch:   bashforge"
echo "  Direct:   python3 ~/.bashforge/bashforge.py"
echo ""
echo "  ── Layout ──────────────────────────────────────────────"
echo "   LEFT   │  Editor (code area + line numbers)"
echo "   RIGHT  │  Script Output  (top)  —  stdout / stderr"
echo "          │  Terminal       (bottom) — interactive shell"
echo "  ─────────────────────────────────────────────────────────"
echo ""
echo "  ── Keyboard shortcuts ──────────────────────────────────"
echo "   Ctrl+Enter   Run current script"
echo "   Ctrl+/       Toggle comment / uncomment"
echo "   Ctrl+S       Save"
echo "   Ctrl+O       Open file"
echo "   Ctrl+N       New file"
echo "   Ctrl+F / H   Find & Replace bar"
echo "   Ctrl+Z / Y   Undo / Redo"
echo "   Ctrl+D       Duplicate current line"
echo "   Ctrl+A       Select all"
echo "   Tab          Indent 4 spaces (or selected lines)"
echo "   Shift+Tab    Unindent"
echo "   ↑ / ↓        Terminal history navigation"
echo "   Tab          Terminal path auto-complete"
echo "  ─────────────────────────────────────────────────────────"
echo ""