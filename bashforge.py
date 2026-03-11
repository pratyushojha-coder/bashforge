#!/usr/bin/env python3

import tkinter as tk
from tkinter import filedialog
import subprocess

class BashForge:

    def __init__(self, root):
        self.root = root
        self.root.title("BashForge - Bash Editor")
        self.root.geometry("900x600")

        self.create_widgets()

    def create_widgets(self):

        # Toolbar
        toolbar = tk.Frame(self.root, bg="#222")
        toolbar.pack(side="top", fill="x")

        run_btn = tk.Button(toolbar, text="Run", command=self.run_code)
        run_btn.pack(side="left", padx=5, pady=5)

        reset_btn = tk.Button(toolbar, text="Reset", command=self.reset_code)
        reset_btn.pack(side="left", padx=5)

        open_btn = tk.Button(toolbar, text="Open", command=self.open_file)
        open_btn.pack(side="left", padx=5)

        save_btn = tk.Button(toolbar, text="Save", command=self.save_file)
        save_btn.pack(side="left", padx=5)

        exit_btn = tk.Button(toolbar, text="Exit", command=self.root.quit)
        exit_btn.pack(side="right", padx=5)

        # Code editor
        editor_frame = tk.Frame(self.root)
        editor_frame.pack(fill="both", expand=True)

        self.code_editor = tk.Text(
            editor_frame,
            bg="#1e1e1e",
            fg="white",
            insertbackground="white",
            font=("Consolas", 12)
        )

        scrollbar = tk.Scrollbar(editor_frame, command=self.code_editor.yview)
        self.code_editor.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.code_editor.pack(fill="both", expand=True)

        # Output terminal
        terminal_frame = tk.Frame(self.root, height=150)
        terminal_frame.pack(fill="x")

        terminal_label = tk.Label(terminal_frame, text="Terminal Output")
        terminal_label.pack(anchor="w")

        self.output_box = tk.Text(
            terminal_frame,
            bg="black",
            fg="lime",
            height=10,
            font=("Consolas", 11)
        )

        self.output_box.pack(fill="x")

    def run_code(self):

        code = self.code_editor.get("1.0", tk.END)

        try:
            result = subprocess.run(
                ["bash", "-c", code],
                capture_output=True,
                text=True
            )

            output = result.stdout + result.stderr

        except Exception as e:
            output = str(e)

        self.output_box.delete("1.0", tk.END)
        self.output_box.insert(tk.END, output)

    def reset_code(self):

        self.code_editor.delete("1.0", tk.END)
        self.output_box.delete("1.0", tk.END)

    def open_file(self):

        file_path = filedialog.askopenfilename()

        if file_path:
            with open(file_path, "r") as f:
                content = f.read()

            self.code_editor.delete("1.0", tk.END)
            self.code_editor.insert(tk.END, content)

    def save_file(self):

        file_path = filedialog.asksaveasfilename(defaultextension=".sh")

        if file_path:
            code = self.code_editor.get("1.0", tk.END)

            with open(file_path, "w") as f:
                f.write(code)


if __name__ == "__main__":

    root = tk.Tk()
    app = BashForge(root)
    root.mainloop()