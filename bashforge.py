#!/usr/bin/env python3

import tkinter as tk
from tkinter import filedialog
import subprocess
import threading
import os
import pty
import sys

class BashForge:

    def __init__(self, root):

        self.root = root
        self.root.title("BashForge IDE")
        self.root.geometry("1000x700")

        self.process = None
        self.master_fd = None

        self.build_ui()

    def build_ui(self):

        toolbar = tk.Frame(self.root, bg="#2b2b2b")
        toolbar.pack(fill="x")

        tk.Button(toolbar, text="Run", command=self.run_code).pack(side="left", padx=5)
        tk.Button(toolbar, text="Stop", command=self.stop_process).pack(side="left", padx=5)
        tk.Button(toolbar, text="Open", command=self.open_file).pack(side="left", padx=5)
        tk.Button(toolbar, text="Save", command=self.save_file).pack(side="left", padx=5)
        tk.Button(toolbar, text="Clear", command=self.clear_terminal).pack(side="left", padx=5)

        editor_frame = tk.Frame(self.root)
        editor_frame.pack(fill="both", expand=True)

        self.editor = tk.Text(
            editor_frame,
            bg="#1e1e1e",
            fg="white",
            insertbackground="white",
            font=("Consolas", 12)
        )

        scroll = tk.Scrollbar(editor_frame, command=self.editor.yview)
        self.editor.configure(yscrollcommand=scroll.set)

        scroll.pack(side="right", fill="y")
        self.editor.pack(fill="both", expand=True)

        terminal_label = tk.Label(self.root, text="Terminal", bg="#222", fg="white")
        terminal_label.pack(fill="x")

        self.terminal = tk.Text(
            self.root,
            height=12,
            bg="black",
            fg="lime",
            insertbackground="white",
            font=("Consolas", 11)
        )

        self.terminal.pack(fill="x")

        self.terminal.bind("<Return>", self.send_input)

    def run_code(self):

        code = self.editor.get("1.0", tk.END)

        self.clear_terminal()

        thread = threading.Thread(target=self.start_shell, args=(code,))
        thread.daemon = True
        thread.start()

    def start_shell(self, code):

        self.master_fd, slave_fd = pty.openpty()

        self.process = subprocess.Popen(
            ["bash"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            text=True,
            close_fds=True
        )

        os.write(self.master_fd, code.encode())

        while True:
            try:
                data = os.read(self.master_fd, 1024).decode()
                self.terminal.insert(tk.END, data)
                self.terminal.see(tk.END)
            except OSError:
                break

    def send_input(self, event):

        if self.master_fd is None:
            return

        line = self.terminal.get("insert linestart", "insert lineend")

        os.write(self.master_fd, (line + "\n").encode())

        return "break"

    def stop_process(self):

        if self.process:
            self.process.terminate()
            self.process = None

    def clear_terminal(self):

        self.terminal.delete("1.0", tk.END)

    def open_file(self):

        file = filedialog.askopenfilename()

        if file:
            with open(file, "r") as f:
                content = f.read()

            self.editor.delete("1.0", tk.END)
            self.editor.insert(tk.END, content)

    def save_file(self):

        file = filedialog.asksaveasfilename(defaultextension=".sh")

        if file:
            code = self.editor.get("1.0", tk.END)

            with open(file, "w") as f:
                f.write(code)


if __name__ == "__main__":

    root = tk.Tk()
    app = BashForge(root)
    root.mainloop()