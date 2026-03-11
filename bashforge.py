#!/usr/bin/env python3
"""
BashForge IDE  –  DevOps-focused Bash editor for Ubuntu
Layout : LEFT = editor  |  RIGHT-TOP = script output  |  RIGHT-BOTTOM = terminal
Stdin  : Output panel has a live  "stdin ❯"  input row that feeds the running
         script in real time – so every  `read`  prompt works naturally.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import tempfile
import os
import re
import threading
import queue
import signal
import sys

# ── try to import pty (Linux only) ──────────────────────────────────────────
try:
    import pty, select
    HAS_PTY = True
except ImportError:
    HAS_PTY = False          # Windows / no pty – fall back to pipe mode

# ────────────────────────────────────────────────────────────
#  Colour tokens  (GitHub-dark palette)
# ────────────────────────────────────────────────────────────
BG_MAIN      = "#0d1117"
BG_EDITOR    = "#0d1117"
BG_OUTPUT    = "#010409"
BG_TERMINAL  = "#0a0e14"
BG_TOOLBAR   = "#161b22"
BG_STATUSBAR = "#161b22"
BG_LINENO    = "#0d1117"
BG_PANEL_HDR = "#13171f"

FG_DEFAULT   = "#e6edf3"
FG_DIM       = "#8b949e"
FG_ACCENT    = "#58a6ff"
FG_GREEN     = "#3fb950"
FG_YELLOW    = "#d29922"
FG_RED       = "#f85149"
FG_PURPLE    = "#bc8cff"
FG_ORANGE    = "#ffa657"
FG_CYAN      = "#79c0ff"
FG_STRING    = "#a5d6ff"
FG_COMMENT   = "#6e7681"

BORDER       = "#30363d"
HOVER_BG     = "#1c2128"
ACTIVE_BG    = "#21262d"
SEL_BG       = "#1f3a5f"

FONT_UI      = ("Segoe UI", 9)
FONT_MONO_SM = ("Consolas", 10)

# ────────────────────────────────────────────────────────────
#  Syntax patterns
# ────────────────────────────────────────────────────────────
BASH_KEYWORDS = (
    r'\b(if|then|else|elif|fi|for|while|do|done|case|esac|in|'
    r'function|return|exit|break|continue|local|readonly|export|'
    r'declare|typeset|unset|shift|set|source|trap|wait|'
    r'echo|printf|read|exec|eval|alias|unalias)\b'
)
BASH_BUILTINS = (
    r'\b(cd|ls|pwd|mkdir|rmdir|rm|cp|mv|touch|cat|grep|sed|awk|'
    r'find|xargs|sort|uniq|wc|head|tail|cut|tr|tee|curl|wget|'
    r'ssh|scp|rsync|git|docker|kubectl|helm|terraform|ansible|'
    r'systemctl|service|apt|apt-get|yum|dnf|pip|pip3|python3|'
    r'chmod|chown|chgrp|mount|umount|df|du|ps|top|kill|killall|'
    r'tar|zip|unzip|gzip|gunzip|openssl|jq|yq|nc|nmap|ping|'
    r'iptables|ufw|nginx|apache2|mysql|psql|redis-cli)\b'
)

# ────────────────────────────────────────────────────────────
#  Snippets
# ────────────────────────────────────────────────────────────
SNIPPETS = {
    "shebang + strict":  "#!/bin/bash\n\nset -euo pipefail\nIFS=$'\\n\\t'\n",
    "if-else":           'if [[ "${1}" == "" ]]; then\n    echo "Usage: $0 <arg>"\n    exit 1\nfi\n',
    "for loop":          'for item in "${array[@]}"; do\n    echo "$item"\ndone\n',
    "while read":        'while IFS= read -r line; do\n    echo "$line"\ndone < "${input_file}"\n',
    "function":          'my_func() {\n    local arg1="${1}"\n    echo "Running: ${arg1}"\n}\n',
    "trap cleanup":      'cleanup() {\n    echo "Cleaning up..."\n    rm -f /tmp/tmpfile\n}\ntrap cleanup EXIT INT TERM\n',
    "check root":        'if [[ $EUID -ne 0 ]]; then\n    echo "This script must be run as root" >&2\n    exit 1\nfi\n',
    "log function":      'log() { echo "[$(date +"%Y-%m-%d %H:%M:%S")] $*" | tee -a "${LOGFILE:-/tmp/script.log}"; }\n',
    "check command":     'command -v docker &>/dev/null || { echo "docker not found"; exit 1; }\n',
    "read input":        'read -rp "Enter your name: " name\necho "Hello, $name!"\n',
    "case statement":    'case "${ENV}" in\n    prod)   ENDPOINT="https://prod.example.com" ;;\n    stage)  ENDPOINT="https://stage.example.com" ;;\n    *)      echo "Unknown env: ${ENV}"; exit 1 ;;\nesac\n',
    "docker run":        'docker run -d \\\n    --name myapp \\\n    --restart unless-stopped \\\n    -p 8080:80 \\\n    -e ENV_VAR=value \\\n    -v /data:/app/data \\\n    myimage:latest\n',
    "kubectl apply":     'kubectl apply -f deployment.yaml\nkubectl rollout status deployment/myapp\nkubectl get pods -l app=myapp\n',
    "ssh remote exec":   "ssh -i ~/.ssh/key.pem -o StrictHostKeyChecking=no user@host \\\n    \"bash -s\" << 'EOF'\necho \"Running on remote host\"\nEOF\n",
    "parse args":        'while [[ "$#" -gt 0 ]]; do\n    case $1 in\n        -e|--env)      ENV="$2"; shift ;;\n        -v|--verbose)  VERBOSE=1 ;;\n        -h|--help)     usage; exit 0 ;;\n        *)             echo "Unknown: $1"; exit 1 ;;\n    esac\n    shift\ndone\n',
    "color output":      'RED="\\033[0;31m"; GREEN="\\033[0;32m"; YELLOW="\\033[1;33m"; NC="\\033[0m"\necho -e "${GREEN}Success${NC}"\necho -e "${RED}Error${NC}"\necho -e "${YELLOW}Warning${NC}"\n',
    "retry loop":        'MAX_RETRY=5; RETRY=0\nuntil some_command; do\n    RETRY=$((RETRY+1))\n    [[ $RETRY -eq $MAX_RETRY ]] && { echo "Max retries reached"; exit 1; }\n    echo "Retry $RETRY/$MAX_RETRY in 5s..."\n    sleep 5\ndone\n',
    "heredoc":           "cat <<'EOF' > /tmp/config.conf\n[section]\nkey=value\nEOF\n",
    "array ops":         'arr=("a" "b" "c")\necho "${arr[@]}"\necho "${#arr[@]}"\nfor i in "${!arr[@]}"; do echo "$i: ${arr[$i]}"; done\n',
}


# ────────────────────────────────────────────────────────────
#  Line-number gutter
# ────────────────────────────────────────────────────────────
class LineNumbers(tk.Text):
    def __init__(self, master, editor, font, **kwargs):
        super().__init__(master, **kwargs)
        self.editor = editor
        self.config(
            state="disabled", width=5,
            padx=8, pady=4,
            bg=BG_LINENO, fg=FG_DIM,
            font=font,
            relief="flat", cursor="arrow",
            selectbackground=BG_LINENO,
            borderwidth=0, highlightthickness=0,
        )

    def refresh(self):
        self.config(state="normal")
        self.delete("1.0", "end")
        n = int(self.editor.index("end-1c").split(".")[0])
        self.insert("1.0", "\n".join(str(i) for i in range(1, n + 1)))
        self.config(state="disabled")
        self.yview_moveto(self.editor.yview()[0])


# ────────────────────────────────────────────────────────────
#  Main application
# ────────────────────────────────────────────────────────────
class BashForge:

    def __init__(self, root):
        self.root = root
        self.root.title("BashForge  ·  DevOps Bash IDE")
        self.root.geometry("1400x860")
        self.root.configure(bg=BG_MAIN)
        self.root.minsize(900, 580)

        self.current_file    = None
        self.modified        = False
        self._search_idx     = "1.0"
        self._snippet_win    = None
        self._run_proc       = None      # running script Popen object
        self._pty_master_fd  = None      # pty master fd (Linux)
        self._cwd            = os.path.expanduser("~")
        self._term_hist      = []
        self._term_hist_idx  = -1
        self._out_queue      = queue.Queue()   # thread → GUI output
        self._stdin_queue    = queue.Queue()   # GUI → script stdin

        self._pick_font()
        self._build_ui()
        self._bind_keys()
        self._syntax_highlight()
        self._update_status()
        self.root.after(40, self._poll_output_queue)

    # ── font ─────────────────────────────────────────────────
    def _pick_font(self):
        import tkinter.font as tkfont
        fams = tkfont.families()
        name = "JetBrains Mono" if "JetBrains Mono" in fams else "Consolas"
        self.mono_font    = (name, 12)
        self.mono_font_sm = (name, 10)

    # ── reusable helpers ──────────────────────────────────────
    def _mk_btn(self, parent, text, cmd, fg=FG_DIM, icon=""):
        lbl = f"{icon}  {text}" if icon else text
        b = tk.Button(parent, text=lbl, command=cmd,
                      bg=BG_TOOLBAR, fg=fg,
                      activebackground=ACTIVE_BG, activeforeground=fg,
                      relief="flat", padx=10, pady=3,
                      font=FONT_UI, cursor="hand2", borderwidth=0)
        b.pack(side="left", padx=1)
        b.bind("<Enter>", lambda e: b.config(bg=HOVER_BG))
        b.bind("<Leave>", lambda e: b.config(bg=BG_TOOLBAR))
        return b

    def _panel_header(self, parent, title, hint=""):
        hdr = tk.Frame(parent, bg=BG_PANEL_HDR, height=26)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text=f"  {title}", bg=BG_PANEL_HDR,
                 fg=FG_DIM, font=("Segoe UI", 8, "bold")).pack(side="left", padx=4)
        if hint:
            tk.Label(hdr, text=f"{hint}  ", bg=BG_PANEL_HDR,
                     fg=FG_COMMENT, font=("Segoe UI", 7)).pack(side="right")
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")

    # ────────────────────────────────────────────────────────
    #  Top-level UI assembly
    # ────────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_toolbar()
        self._build_find_bar()
        self._build_panes()
        self._build_statusbar()

    # ── toolbar ───────────────────────────────────────────────
    def _build_toolbar(self):
        tb = tk.Frame(self.root, bg=BG_TOOLBAR, height=46)
        tb.pack(fill="x", side="top")
        tb.pack_propagate(False)
        tk.Frame(tb, bg=BORDER, height=1).place(relx=0, rely=1.0,
                                                anchor="sw", relwidth=1)
        L = tk.Frame(tb, bg=BG_TOOLBAR)
        L.pack(side="left", padx=6, pady=5)

        self._mk_btn(L, "New",      self.new_file,    FG_DIM,  "⊕")
        self._mk_btn(L, "Open",     self.open_file,   FG_DIM,  "📂")
        self._mk_btn(L, "Save",     self.save_file,   FG_DIM,  "💾")
        self._mk_btn(L, "Save As",  self.save_as,     FG_DIM,  "📝")
        tk.Frame(L, bg=BORDER, width=1, height=22).pack(side="left", padx=6)

        self.run_btn = self._mk_btn(L, "Run  Ctrl+↵",  self.run_script,  FG_GREEN, "▶")
        self._mk_btn(L, "Stop",  self.stop_script, FG_RED,   "■")
        tk.Frame(L, bg=BORDER, width=1, height=22).pack(side="left", padx=6)

        self._mk_btn(L, "Comment  Ctrl+/",      self.toggle_comment, FG_COMMENT, "#")
        self._mk_btn(L, "Snippets",              self.show_snippets,  FG_PURPLE,  "⋯")
        self._mk_btn(L, "Find/Replace  Ctrl+F", self.open_find_bar,  FG_YELLOW,  "🔍")

        R = tk.Frame(tb, bg=BG_TOOLBAR)
        R.pack(side="right", padx=6, pady=5)
        self._mk_btn(R, "Clear Editor",   self.clear_editor,   FG_DIM, "⊗")
        self._mk_btn(R, "Clear Output",   self.clear_output,   FG_DIM, "⊘")
        self._mk_btn(R, "Clear Terminal", self.clear_terminal, FG_DIM, "⊘")
        tk.Frame(R, bg=BORDER, width=1, height=22).pack(side="left", padx=6)
        self._mk_btn(R, "Exit", self.root.quit, FG_RED, "✕")

    # ── find/replace bar (hidden until Ctrl+F) ───────────────
    def _build_find_bar(self):
        self.find_bar = tk.Frame(self.root, bg=BG_PANEL_HDR, pady=5)

        inner = tk.Frame(self.find_bar, bg=BG_PANEL_HDR)
        inner.pack(fill="x", padx=10)

        def lbl(t):
            tk.Label(inner, text=t, bg=BG_PANEL_HDR, fg=FG_DIM,
                     font=FONT_UI).pack(side="left", padx=(8, 3))

        def ent(w):
            e = tk.Entry(inner, bg=ACTIVE_BG, fg=FG_DEFAULT,
                         insertbackground=FG_DEFAULT, font=FONT_MONO_SM,
                         relief="flat", width=w,
                         highlightthickness=1,
                         highlightcolor=FG_ACCENT,
                         highlightbackground=BORDER)
            e.pack(side="left", padx=2)
            return e

        def act(t, cmd):
            b = tk.Button(inner, text=t, command=cmd,
                          bg=ACTIVE_BG, fg=FG_ACCENT, relief="flat",
                          font=FONT_UI, padx=7, pady=1, cursor="hand2",
                          borderwidth=0, activebackground=HOVER_BG,
                          activeforeground=FG_ACCENT)
            b.pack(side="left", padx=2)

        lbl("Find:")
        self.find_entry = ent(30)
        self.find_entry.bind("<Return>", lambda e: self.find_next())
        self.find_entry.bind("<Escape>", lambda e: self.close_find_bar())

        lbl("Replace:")
        self.replace_entry = ent(24)

        act("▶ Next",      self.find_next)
        act("◀ Prev",      self.find_prev)
        act("Replace",     self.replace_one)
        act("Replace All", self.replace_all)
        act("✕ Close",     self.close_find_bar)

        tk.Frame(self.find_bar, bg=BORDER, height=1).pack(fill="x", pady=(4, 0))

    # ── three-panel layout ────────────────────────────────────
    def _build_panes(self):
        self.h_pane = tk.PanedWindow(
            self.root, orient="horizontal",
            bg=BORDER, sashwidth=5, sashrelief="flat", sashpad=0)
        self.h_pane.pack(fill="both", expand=True)

        # LEFT – editor
        ed_panel = tk.Frame(self.h_pane, bg=BG_EDITOR)
        self._panel_header(ed_panel, "EDITOR",
                           "Ctrl+/ comment  |  Ctrl+D dup  |  Tab indent")
        self._build_editor(ed_panel)
        self.h_pane.add(ed_panel, minsize=350)

        # RIGHT – vertical split
        self.v_pane = tk.PanedWindow(
            self.h_pane, orient="vertical",
            bg=BORDER, sashwidth=5, sashrelief="flat", sashpad=0)
        self.h_pane.add(self.v_pane, minsize=320)

        out_panel = tk.Frame(self.v_pane, bg=BG_OUTPUT)
        self._panel_header(out_panel, "SCRIPT OUTPUT",
                           "type below ↓ to send stdin while script runs")
        self._build_output(out_panel)
        self.v_pane.add(out_panel, minsize=120)

        term_panel = tk.Frame(self.v_pane, bg=BG_TERMINAL)
        self._panel_header(term_panel, "TERMINAL",
                           "↑↓ history  |  Tab complete  |  cd / clear")
        self._build_terminal(term_panel)
        self.v_pane.add(term_panel, minsize=100)

        self.root.update_idletasks()
        self.h_pane.paneconfigure(ed_panel,   width=780)
        self.v_pane.paneconfigure(out_panel,  height=380)

    # ── editor ────────────────────────────────────────────────
    def _build_editor(self, parent):
        row = tk.Frame(parent, bg=BG_EDITOR)
        row.pack(fill="both", expand=True)

        vscr = tk.Scrollbar(row, orient="vertical",
                             bg=BG_TOOLBAR, troughcolor=BG_EDITOR, width=10)
        vscr.pack(side="right", fill="y")

        hscr = tk.Scrollbar(parent, orient="horizontal",
                             bg=BG_TOOLBAR, troughcolor=BG_EDITOR, width=10)
        hscr.pack(side="bottom", fill="x")

        self.line_nums = LineNumbers(row, None, self.mono_font)
        self.line_nums.pack(side="left", fill="y")
        tk.Frame(row, bg=BORDER, width=1).pack(side="left", fill="y")

        self.editor = tk.Text(
            row,
            bg=BG_EDITOR, fg=FG_DEFAULT,
            insertbackground=FG_ACCENT,
            selectbackground=SEL_BG,
            selectforeground=FG_DEFAULT,
            font=self.mono_font,
            undo=True, maxundo=-1,
            relief="flat", padx=14, pady=6,
            wrap="none",
            yscrollcommand=vscr.set,
            xscrollcommand=hscr.set,
            borderwidth=0, highlightthickness=0,
            spacing1=2, spacing3=2,
        )
        self.editor.pack(side="left", fill="both", expand=True)
        self.line_nums.editor = self.editor
        vscr.config(command=self._ed_yview)
        hscr.config(command=self.editor.xview)

    def _ed_yview(self, *a):
        self.editor.yview(*a)
        self.line_nums.yview_moveto(self.editor.yview()[0])

    # ── output panel  (with live stdin row) ──────────────────
    def _build_output(self, parent):
        # Build bottom-up: stdin row first, then text fills the rest
        tk.Frame(parent, bg=BORDER, height=1).pack(side="bottom", fill="x")
        stdin_row = tk.Frame(parent, bg=BG_OUTPUT, height=38)
        stdin_row.pack(side="bottom", fill="x")
        stdin_row.pack_propagate(False)

        self._stdin_lbl = tk.Label(
            stdin_row, text="stdin ❯",
            bg=BG_OUTPUT, fg=FG_COMMENT,
            font=self.mono_font)
        self._stdin_lbl.pack(side="left", padx=(10, 6))

        self._stdin_hint = tk.Label(
            stdin_row, text="idle",
            bg=BG_OUTPUT, fg=FG_COMMENT,
            font=("Segoe UI", 8))
        self._stdin_hint.pack(side="right", padx=10)

        self._stdin_entry = tk.Entry(
            stdin_row,
            bg=ACTIVE_BG, fg=FG_CYAN,
            insertbackground=FG_CYAN,
            disabledbackground=ACTIVE_BG,
            disabledforeground="#334455",
            font=self.mono_font,
            relief="flat", borderwidth=0,
            highlightthickness=1,
            highlightcolor=FG_CYAN,
            highlightbackground=BORDER,
            state="disabled",
        )
        self._stdin_entry.pack(side="left", fill="x", expand=True, padx=(0, 6), pady=6)
        self._stdin_entry.bind("<Return>", self._send_stdin)

        # Text output fills all remaining space above stdin row
        text_frame = tk.Frame(parent, bg=BG_OUTPUT)
        text_frame.pack(side="top", fill="both", expand=True)

        vscr = tk.Scrollbar(text_frame, orient="vertical",
                             bg=BG_TOOLBAR, troughcolor=BG_OUTPUT, width=10)
        vscr.pack(side="right", fill="y")

        self.output = tk.Text(
            text_frame,
            bg=BG_OUTPUT, fg=FG_DEFAULT,
            font=self.mono_font_sm,
            state="disabled", relief="flat",
            padx=14, pady=6, wrap="word",
            yscrollcommand=vscr.set,
            borderwidth=0, highlightthickness=0,
            selectbackground=SEL_BG,
        )
        vscr.config(command=self.output.yview)
        self.output.pack(side="left", fill="both", expand=True)

        for tag, fg in [("stdout",  FG_DEFAULT), ("stderr",  FG_RED),
                        ("info",    FG_CYAN),    ("success", FG_GREEN),
                        ("warn",    FG_YELLOW),  ("input",   FG_CYAN)]:
            self.output.tag_config(tag, foreground=fg)

        # ── live stdin input row ──────────────────────────────
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")
        stdin_row = tk.Frame(parent, bg=BG_OUTPUT)
        stdin_row.pack(fill="x", side="bottom")

        self._stdin_lbl = tk.Label(
            stdin_row, text="stdin ❯",
            bg=BG_OUTPUT, fg=FG_COMMENT,
            font=self.mono_font)
        self._stdin_lbl.pack(side="left", padx=(10, 6), pady=5)

        self._stdin_entry = tk.Entry(
            stdin_row,
            bg=BG_OUTPUT, fg=FG_CYAN,
            insertbackground=FG_CYAN,
            disabledbackground=BG_OUTPUT,
            disabledforeground="#2a3a4a",
            font=self.mono_font,
            relief="flat", borderwidth=0, highlightthickness=1,
            highlightcolor=FG_CYAN,
            highlightbackground=BORDER,
            state="disabled",
        )
        self._stdin_entry.pack(side="left", fill="x", expand=True, pady=4)
        self._stdin_entry.bind("<Return>", self._send_stdin)

        self._stdin_hint = tk.Label(
            stdin_row, text="idle",
            bg=BG_OUTPUT, fg=FG_COMMENT,
            font=("Segoe UI", 8))
        self._stdin_hint.pack(side="right", padx=10)

    def _stdin_set_active(self, active: bool):
        """Enable or disable the stdin entry row."""
        if active:
            self._stdin_entry.config(state="normal")
            self._stdin_lbl.config(fg=FG_CYAN)
            self._stdin_hint.config(text="type & press Enter to send")
            self._stdin_entry.focus_set()
        else:
            self._stdin_entry.config(state="disabled")
            self._stdin_entry.delete(0, tk.END)
            self._stdin_lbl.config(fg=FG_COMMENT)
            self._stdin_hint.config(text="idle")

    def _send_stdin(self, _=None):
        """Called when user presses Enter in the stdin row."""
        line = self._stdin_entry.get()
        self._stdin_entry.delete(0, tk.END)
        self._ow(f"❯ {line}\n", "input")   # echo to output panel

        # route to the correct backend
        if self._pty_master_fd is not None:
            # pty mode – write directly to the master fd
            try:
                os.write(self._pty_master_fd, (line + "\n").encode())
            except OSError:
                pass
        elif self._run_proc and self._run_proc.poll() is None:
            # pipe mode – push into the queue for the writer thread
            self._stdin_queue.put(line + "\n")

    # ── terminal panel ───────────────────────────────────────
    def _build_terminal(self, parent):
        vscr = tk.Scrollbar(parent, orient="vertical",
                             bg=BG_TOOLBAR, troughcolor=BG_TERMINAL, width=10)
        vscr.pack(side="right", fill="y")

        self.terminal = tk.Text(
            parent,
            bg=BG_TERMINAL, fg=FG_DEFAULT,
            font=self.mono_font_sm,
            state="disabled", relief="flat",
            padx=14, pady=6, wrap="word",
            yscrollcommand=vscr.set,
            borderwidth=0, highlightthickness=0,
            selectbackground=SEL_BG,
        )
        vscr.config(command=self.terminal.yview)
        self.terminal.pack(fill="both", expand=True)

        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")
        inp_row = tk.Frame(parent, bg=BG_TERMINAL)
        inp_row.pack(fill="x", side="bottom", padx=6, pady=4)
        tk.Label(inp_row, text="$  ", bg=BG_TERMINAL, fg=FG_GREEN,
                 font=self.mono_font).pack(side="left")
        self.term_input = tk.Entry(
            inp_row, bg=BG_TERMINAL, fg=FG_DEFAULT,
            insertbackground=FG_ACCENT, font=self.mono_font,
            relief="flat", borderwidth=0, highlightthickness=0)
        self.term_input.pack(side="left", fill="x", expand=True)
        self.term_input.bind("<Return>", self._term_exec)
        self.term_input.bind("<Up>",     self._term_hist_prev)
        self.term_input.bind("<Down>",   self._term_hist_next)
        self.term_input.bind("<Tab>",    self._term_tab_complete)

        for tag, fg in [("stdout", FG_DEFAULT), ("stderr", FG_RED),
                        ("cmd",    FG_ACCENT),  ("info",   FG_CYAN),
                        ("success",FG_GREEN),   ("warn",   FG_YELLOW),
                        ("prompt", FG_GREEN)]:
            self.terminal.tag_config(tag, foreground=fg)

        self._tw("BashForge terminal ready.\n", "info")
        self._tw(f"cwd: {self._cwd}\n\n", "info")

    # ── statusbar ─────────────────────────────────────────────
    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg=BG_STATUSBAR, height=24)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)
        tk.Frame(sb, bg=BORDER, height=1).place(x=0, y=0, relwidth=1)

        self.st_file = tk.Label(sb, text="  Untitled.sh",
                                bg=BG_STATUSBAR, fg=FG_ACCENT, font=("Segoe UI", 8))
        self.st_file.pack(side="left", padx=4)
        self.st_mod  = tk.Label(sb, text="",
                                bg=BG_STATUSBAR, fg=FG_YELLOW, font=("Segoe UI", 8))
        self.st_mod.pack(side="left")
        self.st_pos  = tk.Label(sb, text="Ln 1, Col 1",
                                bg=BG_STATUSBAR, fg=FG_DIM, font=("Segoe UI", 8))
        self.st_pos.pack(side="right", padx=10)
        self.st_cwd  = tk.Label(sb, text=f"  {self._cwd}",
                                bg=BG_STATUSBAR, fg=FG_DIM, font=("Segoe UI", 8))
        self.st_cwd.pack(side="right", padx=10)

    # ────────────────────────────────────────────────────────
    #  Key bindings
    # ────────────────────────────────────────────────────────
    def _bind_keys(self):
        e = self.editor
        e.bind("<KeyRelease>",     self._on_edit)
        e.bind("<ButtonRelease>",  self._on_edit)
        e.bind("<Control-s>",      lambda ev: (self.save_file(),  "break")[1])
        e.bind("<Control-o>",      lambda ev: (self.open_file(),  "break")[1])
        e.bind("<Control-n>",      lambda ev: (self.new_file(),   "break")[1])
        e.bind("<Control-z>",      lambda ev: e.edit_undo())
        e.bind("<Control-y>",      lambda ev: e.edit_redo())
        e.bind("<Control-a>",      self._sel_all)
        e.bind("<Control-slash>",  lambda ev: self.toggle_comment())
        e.bind("<Control-f>",      lambda ev: self.open_find_bar())
        e.bind("<Control-h>",      lambda ev: self.open_find_bar())
        e.bind("<Control-Return>", lambda ev: self.run_script())
        e.bind("<Control-d>",      self._dup_line)
        e.bind("<Tab>",            self._tab)
        e.bind("<Shift-Tab>",      self._shift_tab)
        e.bind("<Return>",         self._enter)
        e.bind("<BackSpace>",      self._backspace)
        for ch, cl in [('(', ')'), ('[', ']'), ('{', '}'),
                       ('"', '"'), ("'", "'")]:
            e.bind(ch, lambda ev, c=cl: self._auto_close(ev, c))

    def _on_edit(self, _=None):
        self._syntax_highlight()
        self.line_nums.refresh()
        self._update_status()
        self.modified = True
        self.st_mod.config(text=" ●")

    def _update_status(self):
        idx = self.editor.index("insert")
        ln, col = idx.split(".")
        self.st_pos.config(text=f"Ln {ln}, Col {int(col)+1}")
        fname = (os.path.basename(self.current_file)
                 if self.current_file else "Untitled.sh")
        self.st_file.config(text=f"  {fname}")
        self.st_cwd.config(text=f"  {self._cwd}")

    # ────────────────────────────────────────────────────────
    #  Syntax highlighting
    # ────────────────────────────────────────────────────────
    def _syntax_highlight(self, _=None):
        src = self.editor.get("1.0", "end-1c")
        tag_fg = {
            "kw":      FG_PURPLE,  "builtin": FG_CYAN,
            "var":     FG_ORANGE,  "string":  FG_STRING,
            "comment": FG_COMMENT, "flag":    FG_YELLOW,
            "number":  FG_GREEN,   "shebang": FG_DIM,
            "op":      FG_RED,
        }
        for t, fg in tag_fg.items():
            self.editor.tag_config(t, foreground=fg)
            self.editor.tag_remove(t, "1.0", "end")

        patterns = [
            ("shebang", r'^#!.*$'),
            ("string",  r'"(?:[^"\\]|\\.)*"'),
            ("string",  r"'(?:[^'\\]|\\.)*'"),
            ("string",  r'`[^`]*`'),
            ("kw",      BASH_KEYWORDS),
            ("builtin", BASH_BUILTINS),
            ("var",     r'\$\{?[A-Za-z_]\w*\}?'),
            ("var",     r'\$[0-9@#\?\*\$!-]'),
            ("flag",    r'(?<= )-{1,2}[a-zA-Z][a-zA-Z0-9_-]*'),
            ("number",  r'\b[0-9]+\b'),
            ("op",      r'(?<![<>|&])(&&|\|\||;;|>>|<<|>|<|\|)(?![<>|&])'),
        ]
        for tag, pat in patterns:
            for m in re.finditer(pat, src, re.MULTILINE):
                self.editor.tag_add(tag, f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        for m in re.finditer(r'(?m)(?<!\\)#(?!!)[^\n]*', src):
            self.editor.tag_add("comment", f"1.0+{m.start()}c", f"1.0+{m.end()}c")

    # ────────────────────────────────────────────────────────
    #  File operations
    # ────────────────────────────────────────────────────────
    def new_file(self):
        if self.modified and not messagebox.askyesno("New File", "Discard unsaved changes?"):
            return
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", "#!/bin/bash\n\nset -euo pipefail\n\n")
        self.current_file = None
        self.modified = False
        self.st_mod.config(text="")
        self._on_edit()

    def open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Shell scripts", "*.sh *.bash *.zsh"), ("All files", "*.*")])
        if not path:
            return
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        self.editor.delete("1.0", tk.END)
        self.editor.insert(tk.END, content)
        self.current_file = path
        self.modified = False
        self.st_mod.config(text="")
        self._on_edit()
        self._ow(f"Opened: {path}\n", "info")

    def save_file(self, _=None):
        if self.current_file:
            self._write(self.current_file)
        else:
            self.save_as()

    def save_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".sh",
            filetypes=[("Shell scripts", "*.sh"), ("All files", "*.*")])
        if path:
            self._write(path)
            self.current_file = path

    def _write(self, path):
        code = self.editor.get("1.0", tk.END)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        self.modified = False
        self.st_mod.config(text="")
        self._ow(f"Saved: {path}\n", "success")

    # ────────────────────────────────────────────────────────
    #  Script execution  –  pty on Linux, pipe fallback elsewhere
    # ────────────────────────────────────────────────────────
    def _write_temp_script(self):
        code = self.editor.get("1.0", tk.END)
        code = code.replace("\r\n", "\n").replace("\r", "\n")
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".sh", mode="w",
            encoding="utf-8", newline="\n")
        tmp.write(code)
        tmp.close()
        try:
            os.chmod(tmp.name, 0o755)
        except OSError:
            pass
        return tmp.name

    def run_script(self, _=None):
        if self._run_proc and self._run_proc.poll() is None:
            self._ow("⚠  A script is already running. Stop it first.\n", "warn")
            return

        tmp_path = self._write_temp_script()
        self.clear_output()
        self._ow("▶  Running script...\n", "info")
        if HAS_PTY:
            self._ow("   (interactive mode – type input below ↓)\n\n", "warn")
        else:
            self._ow("   (pipe mode – type input below ↓ then Enter)\n\n", "warn")
        self.run_btn.config(text="▶  Running…", fg=FG_YELLOW)
        self.root.after(0, lambda: self._stdin_set_active(True))

        if HAS_PTY:
            threading.Thread(target=self._run_pty,  args=(tmp_path,), daemon=True).start()
        else:
            threading.Thread(target=self._run_pipe, args=(tmp_path,), daemon=True).start()

    # ── PTY runner (Linux) ────────────────────────────────────
    def _run_pty(self, tmp_path):
        master_fd = slave_fd = None
        try:
            master_fd, slave_fd = pty.openpty()
            self._pty_master_fd = master_fd

            proc = subprocess.Popen(
                ["bash", tmp_path],
                stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
                cwd=self._cwd,
                preexec_fn=os.setsid,
                close_fds=True,
            )
            self._run_proc = proc
            os.close(slave_fd)
            slave_fd = None

            buf = b""
            while True:
                try:
                    r, _, _ = select.select([master_fd], [], [], 0.05)
                except (ValueError, OSError):
                    break
                if r:
                    try:
                        chunk = os.read(master_fd, 4096)
                    except OSError:
                        break
                    if not chunk:
                        break
                    buf += chunk
                    # decode what we can, hold incomplete sequences
                    text = buf.decode("utf-8", errors="replace")
                    buf = b""
                    # strip ANSI escape codes for clean display
                    clean = re.sub(r'\x1b\[[0-9;]*[mABCDEFGHJKSTfhilmnprsu]', '', text)
                    clean = re.sub(r'\x1b\][^\x07]*\x07', '', clean)
                    clean = clean.replace('\r\n', '\n').replace('\r', '\n')
                    if clean:
                        self._out_queue.put(("stdout", clean))
                else:
                    if proc.poll() is not None:
                        break

            rc = proc.wait()
            tag  = "success" if rc == 0 else "stderr"
            icon = "✓" if rc == 0 else "✗"
            self._out_queue.put((tag, f"\n{icon}  Exited with code {rc}\n"))

        except Exception as ex:
            self._out_queue.put(("stderr", f"Error: {ex}\n"))
        finally:
            self._run_proc       = None
            self._pty_master_fd  = None
            if slave_fd is not None:
                try: os.close(slave_fd)
                except OSError: pass
            if master_fd is not None:
                try: os.close(master_fd)
                except OSError: pass
            self._out_queue.put(("_done", ""))
            try: os.unlink(tmp_path)
            except OSError: pass

    # ── Pipe runner (Windows / no pty) ───────────────────────
    def _run_pipe(self, tmp_path):
        try:
            proc = subprocess.Popen(
                ["bash", tmp_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self._cwd,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None,
                text=True, bufsize=1,
            )
            self._run_proc = proc

            def _read_out():
                for line in proc.stdout:
                    self._out_queue.put(("stdout", line))
                proc.stdout.close()

            def _read_err():
                for line in proc.stderr:
                    self._out_queue.put(("stderr", line))
                proc.stderr.close()

            def _write_stdin():
                """Forward lines from _stdin_queue to process stdin."""
                while proc.poll() is None:
                    try:
                        line = self._stdin_queue.get(timeout=0.1)
                        try:
                            proc.stdin.write(line)
                            proc.stdin.flush()
                        except (BrokenPipeError, OSError):
                            break
                    except queue.Empty:
                        continue
                try: proc.stdin.close()
                except OSError: pass

            t1 = threading.Thread(target=_read_out,    daemon=True)
            t2 = threading.Thread(target=_read_err,    daemon=True)
            t3 = threading.Thread(target=_write_stdin, daemon=True)
            t1.start(); t2.start(); t3.start()
            t1.join(); t2.join()
            rc = proc.wait()
            tag  = "success" if rc == 0 else "stderr"
            icon = "✓" if rc == 0 else "✗"
            self._out_queue.put((tag, f"\n{icon}  Exited with code {rc}\n"))

        except FileNotFoundError:
            self._out_queue.put(("stderr",
                "bash not found – run this on Ubuntu / WSL2.\n"))
        except Exception as ex:
            self._out_queue.put(("stderr", f"Error: {ex}\n"))
        finally:
            self._run_proc = None
            self._out_queue.put(("_done", ""))
            try: os.unlink(tmp_path)
            except OSError: pass

    def stop_script(self):
        proc = self._run_proc
        if proc and proc.poll() is None:
            try:
                if hasattr(os, "killpg"):
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
            except Exception:
                try: proc.terminate()
                except Exception: pass
            self._ow("■  Script stopped by user.\n", "warn")
        else:
            self._ow("No script is currently running.\n", "warn")

    # ── output queue poll (runs on main thread every 40 ms) ──
    def _poll_output_queue(self):
        try:
            while True:
                tag, text = self._out_queue.get_nowait()
                if tag == "_done":
                    self.run_btn.config(text="▶  Run  Ctrl+↵", fg=FG_GREEN)
                    self._stdin_set_active(False)
                else:
                    self._ow(text, tag)
        except queue.Empty:
            pass
        self.root.after(40, self._poll_output_queue)

    # ── output panel helpers ──────────────────────────────────
    def _ow(self, text, tag="stdout"):
        self.output.config(state="normal")
        self.output.insert(tk.END, text, tag)
        self.output.see(tk.END)
        self.output.config(state="disabled")

    def clear_output(self):
        self.output.config(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.config(state="disabled")

    # ────────────────────────────────────────────────────────
    #  Interactive terminal (bottom-right)
    # ────────────────────────────────────────────────────────
    def _tw(self, text, tag="stdout"):
        self.terminal.config(state="normal")
        self.terminal.insert(tk.END, text, tag)
        self.terminal.see(tk.END)
        self.terminal.config(state="disabled")

    def clear_terminal(self):
        self.terminal.config(state="normal")
        self.terminal.delete("1.0", tk.END)
        self.terminal.config(state="disabled")

    def _term_exec(self, _=None):
        cmd = self.term_input.get().strip()
        if not cmd:
            return
        self.term_input.delete(0, tk.END)
        self._term_hist.append(cmd)
        self._term_hist_idx = len(self._term_hist)
        self._tw(f"$ {cmd}\n", "prompt")

        if cmd.startswith("cd"):
            parts = cmd.split(maxsplit=1)
            target = parts[1] if len(parts) > 1 else os.path.expanduser("~")
            target = os.path.expandvars(os.path.expanduser(target))
            if not os.path.isabs(target):
                target = os.path.join(self._cwd, target)
            target = os.path.normpath(target)
            if os.path.isdir(target):
                self._cwd = target
                self._tw(f"→ {self._cwd}\n", "info")
                self._update_status()
            else:
                self._tw(f"cd: {target}: No such directory\n", "stderr")
            return

        if cmd in ("clear", "cls"):
            self.clear_terminal()
            return

        def _run():
            try:
                proc = subprocess.Popen(
                    cmd, shell=True, cwd=self._cwd,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                out, err = proc.communicate(timeout=120)
                if out: self.root.after(0, lambda o=out: self._tw(o, "stdout"))
                if err: self.root.after(0, lambda e=err: self._tw(e, "stderr"))
            except subprocess.TimeoutExpired:
                self.root.after(0, lambda: self._tw("Timed out.\n", "warn"))
            except Exception as ex:
                self.root.after(0, lambda: self._tw(f"Error: {ex}\n", "stderr"))

        threading.Thread(target=_run, daemon=True).start()

    def _term_hist_prev(self, _):
        if self._term_hist_idx > 0:
            self._term_hist_idx -= 1
            self.term_input.delete(0, tk.END)
            self.term_input.insert(0, self._term_hist[self._term_hist_idx])

    def _term_hist_next(self, _):
        if self._term_hist_idx < len(self._term_hist) - 1:
            self._term_hist_idx += 1
            self.term_input.delete(0, tk.END)
            self.term_input.insert(0, self._term_hist[self._term_hist_idx])
        else:
            self._term_hist_idx = len(self._term_hist)
            self.term_input.delete(0, tk.END)

    def _term_tab_complete(self, _):
        text = self.term_input.get()
        parts = text.split()
        if not parts:
            return "break"
        partial  = parts[-1]
        base_dir = self._cwd
        if os.sep in partial:
            base_dir = os.path.join(base_dir, os.path.dirname(partial))
            partial  = os.path.basename(partial)
        try:
            matches = [f for f in os.listdir(base_dir) if f.startswith(partial)]
            if len(matches) == 1:
                rest = matches[0][len(partial):]
                if os.path.isdir(os.path.join(base_dir, matches[0])):
                    rest += "/"
                self.term_input.insert(tk.END, rest)
            elif matches:
                self._tw("  ".join(matches) + "\n", "info")
        except OSError:
            pass
        return "break"

    # ────────────────────────────────────────────────────────
    #  Editor smart-edit helpers
    # ────────────────────────────────────────────────────────
    def clear_editor(self):
        if messagebox.askyesno("Clear Editor", "Clear all content?"):
            self.editor.delete("1.0", tk.END)
            self._on_edit()

    def _sel_all(self, _=None):
        self.editor.tag_add("sel", "1.0", "end")
        return "break"

    def _dup_line(self, _=None):
        ln = int(self.editor.index("insert").split(".")[0])
        line = self.editor.get(f"{ln}.0", f"{ln}.end")
        self.editor.insert(f"{ln}.end", "\n" + line)
        self._on_edit()
        return "break"

    def _tab(self, _=None):
        try:
            s = int(self.editor.index("sel.first").split(".")[0])
            e = int(self.editor.index("sel.last").split(".")[0])
            for ln in range(s, e + 1):
                self.editor.insert(f"{ln}.0", "    ")
        except tk.TclError:
            self.editor.insert("insert", "    ")
        return "break"

    def _shift_tab(self, _=None):
        try:
            s = int(self.editor.index("sel.first").split(".")[0])
            e = int(self.editor.index("sel.last").split(".")[0])
        except tk.TclError:
            s = e = int(self.editor.index("insert").split(".")[0])
        for ln in range(s, e + 1):
            line = self.editor.get(f"{ln}.0", f"{ln}.end")
            sp = min(len(line) - len(line.lstrip(" ")), 4)
            if sp:
                self.editor.delete(f"{ln}.0", f"{ln}.{sp}")
        return "break"

    def _enter(self, _=None):
        ln   = int(self.editor.index("insert").split(".")[0])
        line = self.editor.get(f"{ln}.0", f"{ln}.end")
        indent = re.match(r'^(\s*)', line).group(1)
        if line.rstrip().endswith(('then', 'do', 'else', 'elif', '{', '(')):
            indent += "    "
        self.editor.insert("insert", "\n" + indent)
        return "break"

    def _backspace(self, _=None):
        idx = self.editor.index("insert")
        col = int(idx.split(".")[1])
        ln  = int(idx.split(".")[0])
        pre = self.editor.get(f"{ln}.0", "insert")
        if pre and pre == " " * col and col % 4 == 0 and col > 0:
            self.editor.delete(f"{ln}.{col-4}", "insert")
            return "break"

    def _auto_close(self, ev, closing):
        try:
            sel = self.editor.get("sel.first", "sel.last")
            self.editor.delete("sel.first", "sel.last")
            self.editor.insert("insert", ev.char + sel + closing)
            return "break"
        except tk.TclError:
            pass
        ch = ev.char
        if ch == closing and self.editor.get("insert", "insert+1c") == closing:
            self.editor.mark_set("insert", "insert+1c")
            return "break"
        self.editor.insert("insert", ch + closing)
        self.editor.mark_set("insert", "insert-1c")
        return "break"

    # ────────────────────────────────────────────────────────
    #  Comment / Uncomment
    # ────────────────────────────────────────────────────────
    def toggle_comment(self, _=None):
        try:
            s = int(self.editor.index("sel.first").split(".")[0])
            e = int(self.editor.index("sel.last").split(".")[0])
        except tk.TclError:
            s = e = int(self.editor.index("insert").split(".")[0])
        lines = [self.editor.get(f"{ln}.0", f"{ln}.end") for ln in range(s, e+1)]
        all_commented = all(
            l.lstrip().startswith("#") or not l.strip() for l in lines if l.strip())
        for i, ln in enumerate(range(s, e+1)):
            new = (re.sub(r'^(\s*)# ?', r'\1', lines[i], count=1)
                   if all_commented
                   else re.sub(r'^(\s*)', r'\1# ', lines[i], count=1))
            self.editor.delete(f"{ln}.0", f"{ln}.end")
            self.editor.insert(f"{ln}.0", new)
        self._on_edit()
        return "break"

    # ────────────────────────────────────────────────────────
    #  Find / Replace
    # ────────────────────────────────────────────────────────
    def open_find_bar(self, _=None):
        children = self.root.winfo_children()
        toolbar  = children[0]
        self.find_bar.pack(fill="x", after=toolbar)
        self.find_entry.focus_set()
        try:
            sel = self.editor.get("sel.first", "sel.last")
            if sel:
                self.find_entry.delete(0, tk.END)
                self.find_entry.insert(0, sel)
        except tk.TclError:
            pass

    def close_find_bar(self):
        self.find_bar.pack_forget()
        self.editor.tag_remove("found", "1.0", "end")
        self.editor.focus_set()

    def _hl_all(self, q):
        self.editor.tag_remove("found", "1.0", "end")
        self.editor.tag_config("found", background="#264f78", foreground="white")
        if not q:
            return
        idx = "1.0"
        while True:
            idx = self.editor.search(q, idx, "end", nocase=True)
            if not idx:
                break
            end = f"{idx}+{len(q)}c"
            self.editor.tag_add("found", idx, end)
            idx = end

    def find_next(self, _=None):
        q = self.find_entry.get()
        if not q: return
        self._hl_all(q)
        idx = self.editor.search(q, self._search_idx, "end", nocase=True)
        if not idx:
            idx = self.editor.search(q, "1.0", "end", nocase=True)
        if idx:
            end = f"{idx}+{len(q)}c"
            self.editor.tag_remove("sel", "1.0", "end")
            self.editor.tag_add("sel", idx, end)
            self.editor.mark_set("insert", idx)
            self.editor.see(idx)
            self._search_idx = end

    def find_prev(self):
        q = self.find_entry.get()
        if not q: return
        idx = self.editor.search(q, "1.0", self._search_idx, nocase=True, backwards=True)
        if not idx:
            idx = self.editor.search(q, "1.0", "end", nocase=True, backwards=True)
        if idx:
            self.editor.tag_remove("sel", "1.0", "end")
            self.editor.tag_add("sel", idx, f"{idx}+{len(q)}c")
            self.editor.mark_set("insert", idx)
            self.editor.see(idx)
            self._search_idx = idx

    def replace_one(self):
        q = self.find_entry.get();  r = self.replace_entry.get()
        if not q: return
        try:
            s = self.editor.index("sel.first");  e = self.editor.index("sel.last")
            if self.editor.get(s, e).lower() == q.lower():
                self.editor.delete(s, e);  self.editor.insert(s, r)
        except tk.TclError: pass
        self.find_next()

    def replace_all(self):
        q = self.find_entry.get();  r = self.replace_entry.get()
        if not q: return
        content = self.editor.get("1.0", "end-1c")
        new     = re.sub(re.escape(q), r, content, flags=re.IGNORECASE)
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", new)
        self._on_edit()
        cnt = len(re.findall(re.escape(q), content, re.IGNORECASE))
        self._ow(f"Replaced {cnt} occurrence(s) of '{q}'\n", "info")

    # ────────────────────────────────────────────────────────
    #  Snippets
    # ────────────────────────────────────────────────────────
    def show_snippets(self):
        if self._snippet_win and self._snippet_win.winfo_exists():
            self._snippet_win.lift()
            return
        win = tk.Toplevel(self.root)
        win.title("Snippets");  win.configure(bg=BG_MAIN)
        win.geometry("340x500");  win.resizable(False, True)
        self._snippet_win = win

        tk.Label(win, text="  ⋯  DevOps Snippets",
                 bg=BG_MAIN, fg=FG_ACCENT,
                 font=("Segoe UI", 10, "bold"), anchor="w"
                 ).pack(fill="x", padx=4, pady=(10, 2))
        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=4, pady=(0, 4))

        canvas = tk.Canvas(win, bg=BG_MAIN, highlightthickness=0)
        sb = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True, padx=4)

        frm = tk.Frame(canvas, bg=BG_MAIN)
        canvas.create_window((0, 0), window=frm, anchor="nw")
        frm.bind("<Configure>",
                 lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        for key, code in SNIPPETS.items():
            b = tk.Button(frm, text=f"  {key}",
                          command=lambda c=code, w=win: self._ins_snippet(c, w),
                          bg=ACTIVE_BG, fg=FG_DEFAULT,
                          activebackground=HOVER_BG, activeforeground=FG_ACCENT,
                          relief="flat", anchor="w", padx=10, pady=5,
                          font=self.mono_font_sm, cursor="hand2", borderwidth=0)
            b.pack(fill="x", pady=1)
            b.bind("<Enter>", lambda e, btn=b: btn.config(bg=HOVER_BG, fg=FG_ACCENT))
            b.bind("<Leave>", lambda e, btn=b: btn.config(bg=ACTIVE_BG, fg=FG_DEFAULT))

    def _ins_snippet(self, code, win=None):
        self.editor.insert("insert", code)
        self._on_edit()
        self.editor.focus_set()
        if win:
            win.destroy()
            self._snippet_win = None


# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = BashForge(root)
    root.mainloop()