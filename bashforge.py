import curses
import subprocess

code_buffer = []
output_buffer = []

def run_code():
    global code_buffer, output_buffer
    code = "\n".join(code_buffer)

    try:
        result = subprocess.run(
            ["bash", "-c", code],
            capture_output=True,
            text=True
        )

        output_buffer = (result.stdout + result.stderr).split("\n")

    except Exception as e:
        output_buffer = [str(e)]


def reset_code():
    global code_buffer, output_buffer
    code_buffer = []
    output_buffer = []


def draw_ui(stdscr):
    curses.curs_set(1)

    while True:

        stdscr.clear()
        height, width = stdscr.getmaxyx()

        # Title
        stdscr.addstr(0, 2, "BashForge - Terminal Bash Editor", curses.A_BOLD)

        # Buttons
        stdscr.addstr(2, 2, "[F5 RUN]", curses.A_REVERSE)
        stdscr.addstr(2, 12, "[F6 RESET]", curses.A_REVERSE)
        stdscr.addstr(2, 24, "[F10 EXIT]", curses.A_REVERSE)

        # Editor
        stdscr.addstr(4, 2, "Code:")

        for i, line in enumerate(code_buffer):
            stdscr.addstr(5 + i, 2, line)

        # Output
        stdscr.addstr(height // 2, 2, "Output:")

        for i, line in enumerate(output_buffer[:height//2 - 2]):
            stdscr.addstr(height//2 + 1 + i, 2, line)

        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_F5:
            run_code()

        elif key == curses.KEY_F6:
            reset_code()

        elif key == curses.KEY_F10:
            break

        elif key == 10:
            code_buffer.append("")

        elif key == curses.KEY_BACKSPACE or key == 127:
            if code_buffer:
                code_buffer[-1] = code_buffer[-1][:-1]

        else:
            if not code_buffer:
                code_buffer.append("")
            code_buffer[-1] += chr(key)


def main():
    curses.wrapper(draw_ui)


if __name__ == "__main__":
    main()