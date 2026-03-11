#!/usr/bin/env python3
"""
BashForge IDE - A DevOps-focused Bash Script Editor
Designed for Ubuntu DevOps workflows
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import tempfile
import os
import re
import threading

# ── Colour Palette ──────────────────────────────────────────────────────────
BG_MAIN      = "#0d1117"
BG_EDITOR    = "#0d1117"
BG_TERMINAL  = "#010409"
BG_TOOLBAR   = "#161b22"
BG_STATUSBAR = "#161b22"
BG_LINENO    = "#0d1117"

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
SELECTION_BG = "#1f3a5f"

FONT_EDITOR  = ("JetBrains Mono", 12)
FONT_FALLBACK= ("Consolas", 12)
FONT_UI      = ("Segoe UI", 9)
FONT_MONO_SM = ("Consolas", 10)

# ── Syntax Highlight Patterns ────────────────────────────────────────────────
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

# ── Snippet Library ──────────────────────────────────────────────────────────
SNIPPETS = {
    "shebang + strict":  '#!/bin/bash\n\nset -euo pipefail\nIFS=$\'\\n\\t\'\n',
    "if-else":           'if [[ "${1}" == "" ]]; then\n    echo "Usage: $0 <arg>"\n    exit 1\nfi\n',
    "for loop":          'for item in "${array[@]}"; do\n    echo "$item"\ndone\n',
    "while read":        'while IFS= read -r line; do\n    echo "$line"\ndone < "${input_file}"\n',
    "function":          'my_func() {\n    local arg1="${1}"\n    echo "Running: ${arg1}"\n}\n',
    "trap cleanup":      'cleanup() {\n    echo "Cleaning up..."\n    rm -f /tmp/tmpfile\n}\ntrap cleanup EXIT INT TERM\n',
    "check root":        'if [[ $EUID -ne 0 ]]; then\n    echo "This script must be run as root" >&2\n    exit 1\nfi\n',
    "log function":      'log() { echo "[$(date +"%Y-%m-%d %H:%M:%S")] $*" | tee -a "${LOGFILE:-/tmp/script.log}"; }\n',
    "check command":     'command -v docker &>/dev/null || { echo "docker not found"; exit 1; }\n',
    "read input":        'read -rp "Enter value: " USER_INPUT\necho "You entered: ${USER_INPUT}"\n',
    "case statement":    'case "${ENV}" in\n    prod)   ENDPOINT="https://prod.example.com" ;;\n    stage)  ENDPOINT="https://stage.example.com" ;;\n    *)      echo "Unknown env: ${ENV}"; exit 1 ;;\nesac\n',
    "docker run":        'docker run -d \\\n    --name myapp \\\n    --restart unless-stopped \\\n    -p 8080:80 \\\n    -e ENV_VAR=value \\\n    -v /data:/app/data \\\n    myimage:latest\n',
    "kubectl apply":     'kubectl apply -f deployment.yaml\nkubectl rollout status deployment/myapp\nkubectl get pods -l app=myapp\n',
    "ssh remote exec":   'ssh -i ~/.ssh/key.pem -o StrictHostKeyChecking=no user@host \\\n    "bash -s" << \'EOF\'\necho "Running on remote host"\nEOF\n',
    "parse args":        'while [[ "$#" -gt 0 ]]; do\n    case $1 in\n        -e|--env)      ENV="$2"; shift ;;\n        -v|--verbose)  VERBOSE=1 ;;\n        -h|--help)     usage; exit 0 ;;\n        *)             echo "Unknown: $1"; exit 1 ;;\n    esac\n    shift\ndone\n',
    "color output":      'RED="\\033[0;31m"; GREEN="\\033[0;32m"; YELLOW="\\033[1;33m"; NC="\\033[0m"\necho -e "${GREEN}Success${NC}"\necho -e "${RED}Error${NC}"\necho -e "${YELLOW}Warning${NC}"\n',
    "retry loop":        'MAX_RETRY=5; RETRY=0\nuntil some_command; do\n    RETRY=$((RETRY+1))\n    [[ $RETRY -eq $MAX_RETRY ]] && { echo "Max retries reached"; exit 1; }\n    echo "Retry $RETRY/$MAX_RETRY in 5s..."\n    sleep 5\ndone\n',
    "heredoc":           'cat <<\'EOF\' > /tmp/config.conf\n[section]\nkey=value\nEOF\n',
    "env var default":   '${MY_VAR:-"default_value"}\n',
    "array ops":         'arr=("a" "b" "c")\necho "${arr[@]}"\necho "${#arr[@]}"\nfor i in "${!arr[@]}"; do echo "$i: ${arr[$i]}"; done\n',
}


class LineNumbers(tk.Text):
    """Line-number gutter synced to the editor."""

    def __init__(self, master, editor, **kwargs):
        super().__init__(master, **kwargs)
        self.editor = editor
        self.config(
            state="disabled",
            width=5,
            padx=8,
            pady=4,
            bg=BG_LINENO,
            fg=FG_DIM,
            font=FONT_EDITOR,
            relief="flat",
            cursor="arrow",
            selectbackground=BG_LINENO,
            borderwidth=0,
            highlightthickness=0,
        )

    def update(self, event=None):
        self.config(state="normal")
        self.delete("1.0", "end")
        line_count = int(self.editor.index("end-1c").split(".")[0])
        numbers = "\n".join(str(i) for i in range(1, line_count + 1))
        self.insert("1.0", numbers)
        self.config(state="disabled")
        self.yview_moveto(self.editor.yview()[0])


class BashForge:

    def __init__(self, root):
        self.root = root
        self.root.title("BashForge  ·  DevOps Bash IDE")
        self.root.geometry("1200x820")
        self.root.configure(bg=BG_MAIN)
        self.root.minsize(800, 560)

        self.current_file = None
        self.modified = False
        self._search_idx = "1.0"
        self._snippet_window = None
        self._proc = None
        self._cwd = os.path.expanduser("~")
        self._term_history = []
        self._term_hist_idx = -1

        self._try_font()
        self._build_ui()
        self._bind_shortcuts()
        self._syntax_highlight()
        self._update_status()

    # ── Font probe ───────────────────────────────────────────────────────────
    def _try_font(self):
        import tkinter.font as tkfont
        families = tkfont.families()
        self.mono_font = FONT_EDITOR if "JetBrains Mono" in families else FONT_FALLBACK

    # ── UI Construction ──────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_toolbar()
        self._build_main_area()
        self._build_statusbar()

    def _build_toolbar(self):
        tb = tk.Frame(self.root, bg=BG_TOOLBAR, height=46)
        tb.pack(fill="x", side="top")
        tb.pack_propagate(False)

        sep_frame = tk.Frame(tb, bg=BORDER, height=1)
        sep_frame.place(relx=0, rely=1.0, anchor="sw", relwidth=1)

        left = tk.Frame(tb, bg=BG_TOOLBAR)
        left.pack(side="left", padx=6, pady=5)

        def btn(parent, text, cmd, fg=FG_DIM, icon=""):
            label = f"{icon}  {text}" if icon else text
            b = tk.Button(
                parent, text=label, command=cmd,
                bg=BG_TOOLBAR, fg=fg,
                activebackground=ACTIVE_BG, activeforeground=fg,
                relief="flat", padx=10, pady=3,
                font=FONT_UI, cursor="hand2", borderwidth=0
            )
            b.pack(side="left", padx=1)
            b.bind("<Enter>", lambda e: b.config(bg=HOVER_BG))
            b.bind("<Leave>", lambda e: b.config(bg=BG_TOOLBAR))
            return b

        btn(left, "New",      self.new_file,        FG_DIM,    "⊕")
        btn(left, "Open",     self.open_file,       FG_DIM,    "📂")
        btn(left, "Save",     self.save_file,       FG_DIM,    "💾")
        btn(left, "Save As",  self.save_as,         FG_DIM,    "📝")

        tk.Frame(left, bg=BORDER, width=1, height=22).pack(side="left", padx=8)

        self.run_btn = btn(left, "Run  Ctrl+↵", self.run_script,  FG_GREEN,  "▶")
        btn(left, "Stop",     self.stop_script,     FG_RED,    "■")

        tk.Frame(left, bg=BORDER, width=1, height=22).pack(side="left", padx=8)

        btn(left, "Comment  Ctrl+/", self.toggle_comment, FG_COMMENT, "#")
        btn(left, "Snippets",  self.show_snippets,   FG_PURPLE, "⋯")
        btn(left, "Find/Replace", self.open_find_bar, FG_YELLOW, "🔍")

        right = tk.Frame(tb, bg=BG_TOOLBAR)
        right.pack(side="right", padx=6, pady=5)

        btn(right, "Clear Editor",   self.clear_editor,   FG_DIM, "⊗")
        btn(right, "Clear Terminal", self.clear_terminal, FG_DIM, "⊘")
        tk.Frame(right, bg=BORDER, width=1, height=22).pack(side="left", padx=8)
        btn(right, "Exit", self.root.quit, FG_RED, "✕")

    def _build_main_area(self):
        pane = tk.PanedWindow(
            self.root, orient="vertical",
            bg=BG_MAIN, sashwidth=5,
            sashrelief="flat", sashpad=0
        )
        pane.pack(fill="both", expand=True)

        # ── Top: Editor ──────────────────────────────────────────────────────
        editor_outer = tk.Frame(pane, bg=BG_EDITOR)

        # Find bar (hidden by default)
        self.find_bar = tk.Frame(editor_outer, bg=BG_TOOLBAR, pady=4)
        fb_inner = tk.Frame(self.find_bar, bg=BG_TOOLBAR)
        fb_inner.pack(fill="x", padx=8)

        tk.Label(fb_inner, text="Find:", bg=BG_TOOLBAR, fg=FG_DIM,
                 font=FONT_UI).pack(side="left", padx=(0, 4))
        self.find_entry = tk.Entry(fb_inner, bg=ACTIVE_BG, fg=FG_DEFAULT,
                                   insertbackground=FG_DEFAULT, font=FONT_MONO_SM,
                                   relief="flat", width=28, highlightthickness=1,
                                   highlightcolor=FG_ACCENT, highlightbackground=BORDER)
        self.find_entry.pack(side="left", padx=2)
        self.find_entry.bind("<Return>",  lambda e: self.find_next())
        self.find_entry.bind("<Escape>",  lambda e: self.close_find_bar())

        tk.Label(fb_inner, text="Replace:", bg=BG_TOOLBAR, fg=FG_DIM,
                 font=FONT_UI).pack(side="left", padx=(10, 4))
        self.replace_entry = tk.Entry(fb_inner, bg=ACTIVE_BG, fg=FG_DEFAULT,
                                      insertbackground=FG_DEFAULT, font=FONT_MONO_SM,
                                      relief="flat", width=22, highlightthickness=1,
                                      highlightcolor=FG_ACCENT, highlightbackground=BORDER)
        self.replace_entry.pack(side="left", padx=2)

        for lbl, cmd in [("▶ Next", self.find_next), ("◀ Prev", self.find_prev),
                         ("Replace", self.replace_one), ("Replace All", self.replace_all),
                         ("✕ Close", self.close_find_bar)]:
            b = tk.Button(fb_inner, text=lbl, command=cmd,
                          bg=ACTIVE_BG, fg=FG_ACCENT, relief="flat",
                          font=FONT_UI, padx=6, pady=2, cursor="hand2",
                          borderwidth=0, activebackground=HOVER_BG,
                          activeforeground=FG_ACCENT)
            b.pack(side="left", padx=3)

        # Editor row: line numbers + text
        editor_row = tk.Frame(editor_outer, bg=BG_EDITOR)
        editor_row.pack(fill="both", expand=True)

        vscroll = tk.Scrollbar(editor_row, orient="vertical",
                               bg=BG_TOOLBAR, troughcolor=BG_EDITOR, width=10)
        vscroll.pack(side="right", fill="y")

        hscroll = tk.Scrollbar(editor_outer, orient="horizontal",
                               bg=BG_TOOLBAR, troughcolor=BG_EDITOR, width=10)
        hscroll.pack(side="bottom", fill="x")

        self.line_nums = LineNumbers(editor_row, None)  # editor set below
        self.line_nums.pack(side="left", fill="y")

        tk.Frame(editor_row, bg=BORDER, width=1).pack(side="left", fill="y")

        self.editor = tk.Text(
            editor_row,
            bg=BG_EDITOR, fg=FG_DEFAULT,
            insertbackground=FG_ACCENT,
            selectbackground=SELECTION_BG,
            selectforeground=FG_DEFAULT,
            font=self.mono_font,
            undo=True, maxundo=-1,
            relief="flat", padx=14, pady=6,
            wrap="none",
            yscrollcommand=vscroll.set,
            xscrollcommand=hscroll.set,
            borderwidth=0, highlightthickness=0,
            spacing1=2, spacing3=2,
            tabs=("4c",),
        )
        self.editor.pack(side="left", fill="both", expand=True)
        self.line_nums.editor = self.editor

        vscroll.config(command=self._editor_yview)
        hscroll.config(command=self.editor.xview)

        pane.add(editor_outer, minsize=180)

        # ── Bottom: Terminal ─────────────────────────────────────────────────
        term_outer = tk.Frame(pane, bg=BG_TERMINAL)

        term_header = tk.Frame(term_outer, bg=BG_TOOLBAR, height=28)
        term_header.pack(fill="x")
        term_header.pack_propagate(False)
        tk.Label(term_header, text="  ⬛ TERMINAL", bg=BG_TOOLBAR,
                 fg=FG_DIM, font=("Segoe UI", 8, "bold")).pack(side="left", padx=6)
        tk.Label(term_header, text="↑↓ history  Tab=complete  cd/clear supported",
                 bg=BG_TOOLBAR, fg=FG_COMMENT, font=("Segoe UI", 7)).pack(side="right", padx=10)

        t_vscroll = tk.Scrollbar(term_outer, orient="vertical",
                                  bg=BG_TOOLBAR, troughcolor=BG_TERMINAL, width=10)
        t_vscroll.pack(side="right", fill="y")

        self.terminal = tk.Text(
            term_outer,
            bg=BG_TERMINAL, fg=FG_DEFAULT,
            font=self.mono_font,
            state="disabled", relief="flat",
            padx=14, pady=6, wrap="word",
            yscrollcommand=t_vscroll.set,
            borderwidth=0, highlightthickness=0,
            spacing1=1, spacing3=1,
            selectbackground=SELECTION_BG,
        )
        t_vscroll.config(command=self.terminal.yview)
        self.terminal.pack(fill="both", expand=True)

        # Input row
        input_row = tk.Frame(term_outer, bg=BG_TERMINAL)
        input_row.pack(fill="x", side="bottom")
        tk.Frame(input_row, bg=BORDER, height=1).pack(fill="x")
        inner = tk.Frame(input_row, bg=BG_TERMINAL)
        inner.pack(fill="x", padx=6, pady=4)
        tk.Label(inner, text="$ ", bg=BG_TERMINAL, fg=FG_GREEN,
                 font=self.mono_font).pack(side="left")
        self.term_input = tk.Entry(inner, bg=BG_TERMINAL, fg=FG_DEFAULT,
                                   insertbackground=FG_ACCENT, font=self.mono_font,
                                   relief="flat", borderwidth=0, highlightthickness=0)
        self.term_input.pack(side="left", fill="x", expand=True)
        self.term_input.bind("<Return>", self._run_terminal_cmd)
        self.term_input.bind("<Up>",     self._term_history_prev)
        self.term_input.bind("<Down>",   self._term_history_next)
        self.term_input.bind("<Tab>",    self._term_tab_complete)

        pane.add(term_outer, minsize=100)
        pane.paneconfigure(editor_outer, height=560)

        # Terminal colour tags
        for tag, fg in [("stdout",  FG_DEFAULT), ("stderr",  FG_RED),
                        ("cmd",     FG_ACCENT),   ("info",    FG_CYAN),
                        ("success", FG_GREEN),    ("warn",    FG_YELLOW),
                        ("prompt",  FG_GREEN)]:
            self.terminal.tag_config(tag, foreground=fg)

        self._term_write("BashForge DevOps IDE  —  Terminal Ready\n", "info")
        self._term_write(f"cwd: {self._cwd}\n\n", "info")

    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg=BG_STATUSBAR, height=24)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)
        tk.Frame(sb, bg=BORDER, height=1).place(x=0, y=0, relwidth=1)

        self.status_file = tk.Label(sb, text="  Untitled.sh", bg=BG_STATUSBAR,
                                    fg=FG_ACCENT, font=("Segoe UI", 8))
        self.status_file.pack(side="left", padx=4)

        self.status_mod = tk.Label(sb, text="", bg=BG_STATUSBAR,
                                   fg=FG_YELLOW, font=("Segoe UI", 8))
        self.status_mod.pack(side="left")

        self.status_pos = tk.Label(sb, text="Ln 1, Col 1", bg=BG_STATUSBAR,
                                   fg=FG_DIM, font=("Segoe UI", 8))
        self.status_pos.pack(side="right", padx=10)

        self.status_cwd = tk.Label(sb, text=f"  {self._cwd}", bg=BG_STATUSBAR,
                                   fg=FG_DIM, font=("Segoe UI", 8))
        self.status_cwd.pack(side="right", padx=10)

    # ── Scrollbar sync ───────────────────────────────────────────────────────
    def _editor_yview(self, *args):
        self.editor.yview(*args)
        self.line_nums.yview_moveto(self.editor.yview()[0])

    # ── Keyboard shortcuts ───────────────────────────────────────────────────
    def _bind_shortcuts(self):
        e = self.editor
        e.bind("<KeyRelease>",      self._on_key_release)
        e.bind("<ButtonRelease>",   self._on_key_release)
        e.bind("<Control-s>",       lambda ev: (self.save_file(), "break")[1])
        e.bind("<Control-o>",       lambda ev: (self.open_file(), "break")[1])
        e.bind("<Control-n>",       lambda ev: (self.new_file(), "break")[1])
        e.bind("<Control-z>",       lambda ev: self.editor.edit_undo())
        e.bind("<Control-y>",       lambda ev: self.editor.edit_redo())
        e.bind("<Control-a>",       self._select_all)
        e.bind("<Control-slash>",   lambda ev: self.toggle_comment())
        e.bind("<Control-f>",       lambda ev: self.open_find_bar())
        e.bind("<Control-h>",       lambda ev: self.open_find_bar())
        e.bind("<Control-Return>",  lambda ev: self.run_script())
        e.bind("<Control-d>",       self._duplicate_line)
        e.bind("<Tab>",             self._handle_tab)
        e.bind("<Shift-Tab>",       self._handle_shift_tab)
        e.bind("<Return>",          self._handle_enter)
        e.bind("<BackSpace>",       self._handle_backspace)
        for ch, cl in [('(',')'),(  '[',']'),('{','}'),('"','"'),("'","'")]:
            e.bind(ch, lambda ev, c=cl: self._auto_close(ev, c))

    def _on_key_release(self, event=None):
        self._syntax_highlight()
        self.line_nums.update()
        self._update_status()
        self.modified = True
        self.status_mod.config(text=" ●")

    # ── Status bar ───────────────────────────────────────────────────────────
    def _update_status(self, event=None):
        idx = self.editor.index("insert")
        ln, col = idx.split(".")
        self.status_pos.config(text=f"Ln {ln}, Col {int(col)+1}")
        fname = os.path.basename(self.current_file) if self.current_file else "Untitled.sh"
        self.status_file.config(text=f"  {fname}")
        if hasattr(self, "status_cwd"):
            self.status_cwd.config(text=f"  {self._cwd}")

    # ── Syntax highlighting ──────────────────────────────────────────────────
    def _syntax_highlight(self, event=None):
        content = self.editor.get("1.0", "end-1c")

        tag_colors = {
            "kw":      FG_PURPLE,
            "builtin": FG_CYAN,
            "var":     FG_ORANGE,
            "string":  FG_STRING,
            "comment": FG_COMMENT,
            "flag":    FG_YELLOW,
            "number":  FG_GREEN,
            "shebang": FG_DIM,
            "op":      FG_RED,
        }
        for tag, color in tag_colors.items():
            self.editor.tag_config(tag, foreground=color)
            self.editor.tag_remove(tag, "1.0", "end")

        patterns = [
            ("shebang", r'^#!.*$'),
            ("string",  r'"(?:[^"\\]|\\.)*"'),
            ("string",  r"'(?:[^'\\]|\\.)*'"),
            ("string",  r'`[^`]*`'),
            ("kw",      BASH_KEYWORDS),
            ("builtin", BASH_BUILTINS),
            ("var",     r'\$\{?[A-Za-z_][A-Za-z_0-9]*\}?'),
            ("var",     r'\$[0-9@#\?\*\$!-]'),
            ("flag",    r'(?<= )-{1,2}[a-zA-Z][a-zA-Z0-9-]*'),
            ("number",  r'\b[0-9]+\b'),
            ("op",      r'(?<!\w)(&&|\|\||;;|>>|<<|>|<|\|)(?!\w)'),
        ]
        for tag, pattern in patterns:
            for m in re.finditer(pattern, content, re.MULTILINE):
                s = f"1.0 + {m.start()} chars"
                e = f"1.0 + {m.end()} chars"
                self.editor.tag_add(tag, s, e)

        # Comments override everything — apply last
        for m in re.finditer(r'(?m)(?<!\\)#(?!!)[^\n]*', content):
            self.editor.tag_add("comment",
                                f"1.0 + {m.start()} chars",
                                f"1.0 + {m.end()} chars")

    # ── File operations ──────────────────────────────────────────────────────
    def new_file(self):
        if self.modified:
            if not messagebox.askyesno("New File", "Discard unsaved changes?"):
                return
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", "#!/bin/bash\n\nset -euo pipefail\n\n")
        self.current_file = None
        self.modified = False
        self.status_mod.config(text="")
        self._on_key_release()

    def open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Shell scripts", "*.sh *.bash *.zsh"),
                       ("All files", "*.*")]
        )
        if path:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            self.editor.delete("1.0", tk.END)
            self.editor.insert(tk.END, content)
            self.current_file = path
            self.modified = False
            self.status_mod.config(text="")
            self._on_key_release()
            self._term_write(f"Opened: {path}\n", "info")

    def save_file(self, event=None):
        if self.current_file:
            self._write_file(self.current_file)
        else:
            self.save_as()

    def save_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".sh",
            filetypes=[("Shell scripts", "*.sh"), ("All files", "*.*")]
        )
        if path:
            self._write_file(path)
            self.current_file = path

    def _write_file(self, path):
        code = self.editor.get("1.0", tk.END)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        self.modified = False
        self.status_mod.config(text="")
        self._term_write(f"Saved: {path}\n", "success")

    # ── Script execution ─────────────────────────────────────────────────────
    def run_script(self, event=None):
        code = self.editor.get("1.0", tk.END)
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".sh", mode="w", encoding="utf-8"
        )
        tmp.write(code)
        tmp.close()
        try:
            os.chmod(tmp.name, 0o755)
        except Exception:
            pass

        self._term_write(f"\n▶  Running script...\n", "cmd")
        self.run_btn.config(fg=FG_YELLOW, text="▶  Running...")

        def _run():
            try:
                self._proc = subprocess.Popen(
                    ["bash", tmp.name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=self._cwd,
                    text=True,
                )
                stdout, stderr = self._proc.communicate()
                rc = self._proc.returncode
                if stdout:
                    self.root.after(0, lambda: self._term_write(stdout, "stdout"))
                if stderr:
                    self.root.after(0, lambda: self._term_write(stderr, "stderr"))
                msg = f"✓ Exited 0\n" if rc == 0 else f"✗ Exited {rc}\n"
                tag = "success" if rc == 0 else "stderr"
                self.root.after(0, lambda: self._term_write(msg, tag))
            except Exception as ex:
                self.root.after(0, lambda: self._term_write(f"Error: {ex}\n", "stderr"))
            finally:
                self._proc = None
                self.root.after(0, lambda: self.run_btn.config(
                    fg=FG_GREEN, text="▶  Run  Ctrl+↵"))
                try:
                    os.unlink(tmp.name)
                except Exception:
                    pass

        threading.Thread(target=_run, daemon=True).start()

    def stop_script(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            self._term_write("■  Script terminated.\n", "warn")
        else:
            self._term_write("No running script.\n", "warn")

    # ── Embedded terminal ────────────────────────────────────────────────────
    def _run_terminal_cmd(self, event=None):
        cmd = self.term_input.get().strip()
        if not cmd:
            return
        self.term_input.delete(0, tk.END)
        self._term_history.append(cmd)
        self._term_hist_idx = len(self._term_history)
        self._term_write(f"$ {cmd}\n", "prompt")

        if cmd.startswith("cd"):
            parts = cmd.split(maxsplit=1)
            target = parts[1] if len(parts) > 1 else os.path.expanduser("~")
            target = os.path.expandvars(os.path.expanduser(target))
            if not os.path.isabs(target):
                target = os.path.join(self._cwd, target)
            target = os.path.normpath(target)
            if os.path.isdir(target):
                self._cwd = target
                self._term_write(f"→ {self._cwd}\n", "info")
                self._update_status()
            else:
                self._term_write(f"cd: {target}: No such directory\n", "stderr")
            return

        if cmd in ("clear", "cls"):
            self.clear_terminal()
            return

        def _exec():
            try:
                proc = subprocess.Popen(
                    cmd, shell=True, cwd=self._cwd,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                out, err = proc.communicate(timeout=120)
                if out:
                    self.root.after(0, lambda: self._term_write(out, "stdout"))
                if err:
                    self.root.after(0, lambda: self._term_write(err, "stderr"))
            except subprocess.TimeoutExpired:
                self.root.after(0, lambda: self._term_write("Timed out.\n", "warn"))
            except Exception as ex:
                self.root.after(0, lambda: self._term_write(f"Error: {ex}\n", "stderr"))

        threading.Thread(target=_exec, daemon=True).start()

    def _term_history_prev(self, event):
        if self._term_hist_idx > 0:
            self._term_hist_idx -= 1
            self.term_input.delete(0, tk.END)
            self.term_input.insert(0, self._term_history[self._term_hist_idx])

    def _term_history_next(self, event):
        if self._term_hist_idx < len(self._term_history) - 1:
            self._term_hist_idx += 1
            self.term_input.delete(0, tk.END)
            self.term_input.insert(0, self._term_history[self._term_hist_idx])
        else:
            self._term_hist_idx = len(self._term_history)
            self.term_input.delete(0, tk.END)

    def _term_tab_complete(self, event):
        text = self.term_input.get()
        parts = text.split()
        if not parts:
            return "break"
        partial = parts[-1]
        base_dir = self._cwd
        if os.sep in partial:
            base_dir = os.path.join(base_dir, os.path.dirname(partial))
            partial = os.path.basename(partial)
        try:
            matches = [f for f in os.listdir(base_dir) if f.startswith(partial)]
            if len(matches) == 1:
                rest = matches[0][len(partial):]
                if os.path.isdir(os.path.join(base_dir, matches[0])):
                    rest += "/"
                self.term_input.insert(tk.END, rest)
            elif len(matches) > 1:
                self._term_write("  ".join(matches) + "\n", "info")
        except Exception:
            pass
        return "break"

    def _term_write(self, text, tag="stdout"):
        self.terminal.config(state="normal")
        self.terminal.insert(tk.END, text, tag)
        self.terminal.see(tk.END)
        self.terminal.config(state="disabled")

    def clear_terminal(self):
        self.terminal.config(state="normal")
        self.terminal.delete("1.0", tk.END)
        self.terminal.config(state="disabled")

    # ── Editor helpers ────────────────────────────────────────────────────────
    def clear_editor(self):
        if messagebox.askyesno("Clear Editor", "Clear all content?"):
            self.editor.delete("1.0", tk.END)
            self._on_key_release()

    def _select_all(self, event=None):
        self.editor.tag_add("sel", "1.0", "end")
        return "break"

    def _duplicate_line(self, event=None):
        ln = int(self.editor.index("insert").split(".")[0])
        line = self.editor.get(f"{ln}.0", f"{ln}.end")
        self.editor.insert(f"{ln}.end", "\n" + line)
        self._on_key_release()
        return "break"

    def _handle_tab(self, event=None):
        try:
            start_ln = int(self.editor.index("sel.first").split(".")[0])
            end_ln   = int(self.editor.index("sel.last").split(".")[0])
            for ln in range(start_ln, end_ln + 1):
                self.editor.insert(f"{ln}.0", "    ")
        except tk.TclError:
            self.editor.insert("insert", "    ")
        return "break"

    def _handle_shift_tab(self, event=None):
        try:
            start_ln = int(self.editor.index("sel.first").split(".")[0])
            end_ln   = int(self.editor.index("sel.last").split(".")[0])
        except tk.TclError:
            start_ln = end_ln = int(self.editor.index("insert").split(".")[0])
        for ln in range(start_ln, end_ln + 1):
            line = self.editor.get(f"{ln}.0", f"{ln}.end")
            spaces = len(line) - len(line.lstrip(" "))
            remove = min(spaces, 4)
            if remove:
                self.editor.delete(f"{ln}.0", f"{ln}.{remove}")
        return "break"

    def _handle_enter(self, event=None):
        idx    = self.editor.index("insert")
        ln     = int(idx.split(".")[0])
        line   = self.editor.get(f"{ln}.0", f"{ln}.end")
        indent = re.match(r'^(\s*)', line).group(1)
        if line.rstrip().endswith(('then', 'do', 'else', 'elif', '{', '(')):
            indent += "    "
        self.editor.insert("insert", "\n" + indent)
        return "break"

    def _handle_backspace(self, event=None):
        idx = self.editor.index("insert")
        col = int(idx.split(".")[1])
        ln  = int(idx.split(".")[0])
        line_to_cursor = self.editor.get(f"{ln}.0", "insert")
        if line_to_cursor and line_to_cursor == " " * col and col % 4 == 0 and col > 0:
            self.editor.delete(f"{ln}.{col-4}", "insert")
            return "break"

    def _auto_close(self, event, closing):
        try:
            sel = self.editor.get("sel.first", "sel.last")
            self.editor.delete("sel.first", "sel.last")
            self.editor.insert("insert", event.char + sel + closing)
            return "break"
        except tk.TclError:
            pass
        ch = event.char
        next_char = self.editor.get("insert", "insert+1c")
        if ch == closing and next_char == closing:
            self.editor.mark_set("insert", "insert+1c")
            return "break"
        self.editor.insert("insert", ch + closing)
        self.editor.mark_set("insert", "insert-1c")
        return "break"

    # ── Comment / Uncomment ───────────────────────────────────────────────────
    def toggle_comment(self, event=None):
        try:
            start_ln = int(self.editor.index("sel.first").split(".")[0])
            end_ln   = int(self.editor.index("sel.last").split(".")[0])
        except tk.TclError:
            start_ln = end_ln = int(self.editor.index("insert").split(".")[0])

        lines = [self.editor.get(f"{ln}.0", f"{ln}.end")
                 for ln in range(start_ln, end_ln + 1)]

        all_commented = all(
            l.lstrip().startswith("#") or l.strip() == ""
            for l in lines if l.strip()
        )
        for i, ln in enumerate(range(start_ln, end_ln + 1)):
            line = lines[i]
            new = (re.sub(r'^(\s*)# ?', r'\1', line, count=1)
                   if all_commented
                   else re.sub(r'^(\s*)', r'\1# ', line, count=1))
            self.editor.delete(f"{ln}.0", f"{ln}.end")
            self.editor.insert(f"{ln}.0", new)

        self._on_key_release()
        return "break"

    # ── Find / Replace ────────────────────────────────────────────────────────
    def open_find_bar(self, event=None):
        self.find_bar.pack(fill="x", before=self.find_bar.master.winfo_children()[0])
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

    def _highlight_all_found(self, query):
        self.editor.tag_remove("found", "1.0", "end")
        self.editor.tag_config("found", background="#264f78", foreground="white")
        if not query:
            return
        idx = "1.0"
        while True:
            idx = self.editor.search(query, idx, "end", nocase=True)
            if not idx:
                break
            end = f"{idx}+{len(query)}c"
            self.editor.tag_add("found", idx, end)
            idx = end

    def find_next(self, event=None):
        query = self.find_entry.get()
        if not query:
            return
        self._highlight_all_found(query)
        idx = self.editor.search(query, self._search_idx, "end", nocase=True)
        if not idx:
            idx = self.editor.search(query, "1.0", "end", nocase=True)
        if idx:
            end = f"{idx}+{len(query)}c"
            self.editor.tag_remove("sel", "1.0", "end")
            self.editor.tag_add("sel", idx, end)
            self.editor.mark_set("insert", idx)
            self.editor.see(idx)
            self._search_idx = end

    def find_prev(self):
        query = self.find_entry.get()
        if not query:
            return
        idx = self.editor.search(query, "1.0", self._search_idx,
                                  nocase=True, backwards=True)
        if not idx:
            idx = self.editor.search(query, "1.0", "end",
                                      nocase=True, backwards=True)
        if idx:
            end = f"{idx}+{len(query)}c"
            self.editor.tag_remove("sel", "1.0", "end")
            self.editor.tag_add("sel", idx, end)
            self.editor.mark_set("insert", idx)
            self.editor.see(idx)
            self._search_idx = idx

    def replace_one(self):
        query   = self.find_entry.get()
        replace = self.replace_entry.get()
        if not query:
            return
        try:
            start = self.editor.index("sel.first")
            end   = self.editor.index("sel.last")
            if self.editor.get(start, end).lower() == query.lower():
                self.editor.delete(start, end)
                self.editor.insert(start, replace)
        except tk.TclError:
            pass
        self.find_next()

    def replace_all(self):
        query   = self.find_entry.get()
        replace = self.replace_entry.get()
        if not query:
            return
        content = self.editor.get("1.0", "end-1c")
        new_content = re.sub(re.escape(query), replace, content, flags=re.IGNORECASE)
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", new_content)
        self._on_key_release()
        count = len(re.findall(re.escape(query), content, re.IGNORECASE))
        self._term_write(f"Replaced {count} occurrence(s)\n", "info")

    # ── Snippets panel ────────────────────────────────────────────────────────
    def show_snippets(self):
        if self._snippet_window and tk.Toplevel.winfo_exists(self._snippet_window):
            self._snippet_window.lift()
            return

        win = tk.Toplevel(self.root)
        win.title("Snippets")
        win.configure(bg=BG_MAIN)
        win.geometry("340x480")
        win.resizable(False, True)
        self._snippet_window = win

        tk.Label(win, text="  ⋯  DevOps Snippets", bg=BG_MAIN,
                 fg=FG_ACCENT, font=("Segoe UI", 10, "bold"),
                 anchor="w").pack(fill="x", padx=4, pady=(10, 4))
        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=4)

        canvas = tk.Canvas(win, bg=BG_MAIN, highlightthickness=0)
        sb = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True, padx=4, pady=4)

        frame = tk.Frame(canvas, bg=BG_MAIN)
        canvas.create_window((0, 0), window=frame, anchor="nw")

        def on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        frame.bind("<Configure>", on_frame_configure)

        for key, code in SNIPPETS.items():
            row = tk.Frame(frame, bg=BG_MAIN)
            row.pack(fill="x", pady=1, padx=2)
            b = tk.Button(
                row, text=f"  {key}",
                command=lambda c=code, w=win: self._insert_snippet(c, w),
                bg=ACTIVE_BG, fg=FG_DEFAULT,
                activebackground=HOVER_BG, activeforeground=FG_ACCENT,
                relief="flat", anchor="w", padx=10, pady=6,
                font=FONT_MONO_SM, cursor="hand2", borderwidth=0,
            )
            b.pack(fill="x")
            b.bind("<Enter>", lambda e, btn=b: btn.config(bg=HOVER_BG, fg=FG_ACCENT))
            b.bind("<Leave>", lambda e, btn=b: btn.config(bg=ACTIVE_BG, fg=FG_DEFAULT))

    def _insert_snippet(self, code, window=None):
        self.editor.insert("insert", code)
        self._on_key_release()
        self.editor.focus_set()
        if window:
            window.destroy()
            self._snippet_window = None


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = BashForge(root)
    root.mainloop()