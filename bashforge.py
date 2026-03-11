#!/usr/bin/env python3

import tkinter as tk
from tkinter import filedialog
import subprocess
import threading

class BashForge:

    def __init__(self, root):

        self.root = root
        self.root.title("BashForge")
        self.root.geometry("1000x650")

        self.create_ui()

    def create_ui(self):

        toolbar = tk.Frame(self.root, bg="#2b2b2b")
        toolbar.pack(fill="x")

        tk.Button(toolbar, text="Run", command=self.run_code).pack(side="left", padx=5)
        tk.Button(toolbar, text="Reset", command=self.reset).pack(side="left", padx=5)
        tk.Button(toolbar, text="Open", command=self.open_file).pack(side="left", padx=5)
        tk.Button(toolbar, text="Save", command=self.save_file).pack(side="left", padx=5)
        tk.Button(toolbar, text="Exit", command=self.root.quit).pack(side="right", padx=5)

        editor_frame = tk.Frame(self.root)
        editor_frame.pack(fill="both", expand=True)

        self.editor = tk.Text(
            editor_frame,
            bg="#1e1e1e",
            fg="white",
            insertbackground="white",
            font=("Consolas",12)
        )

        scrollbar = tk.Scrollbar(editor_frame, command=self.editor.yview)
        self.editor.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.editor.pack(fill="both", expand=True)

        terminal_label = tk.Label(self.root, text="Terminal Output")
        terminal_label.pack(anchor="w")

        self.terminal = tk.Text(
            self.root,
            height=10,
            bg="black",
            fg="lime",
            font=("Consolas",11)
        )

        self.terminal.pack(fill="x")

    def run_code(self):

        code = self.editor.get("1.0", tk.END)

        self.terminal.delete("1.0", tk.END)

        thread = threading.Thread(target=self.execute_code, args=(code,))
        thread.start()

    def execute_code(self, code):

        process = subprocess.Popen(
            ["bash"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate(code)

        output = stdout + stderr

        self.terminal.insert(tk.END, output)

    def reset(self):

        self.editor.delete("1.0", tk.END)
        self.terminal.delete("1.0", tk.END)

    def open_file(self):

        file = filedialog.askopenfilename()

        if file:
            with open(file,"r") as f:
                content = f.read()

            self.editor.delete("1.0",tk.END)
            self.editor.insert(tk.END,content)

    def save_file(self):

        file = filedialog.asksaveasfilename(defaultextension=".sh")

        if file:
            code = self.editor.get("1.0",tk.END)

            with open(file,"w") as f:
                f.write(code)

if __name__ == "__main__":

    root = tk.Tk()
    app = BashForge(root)
    root.mainloop()