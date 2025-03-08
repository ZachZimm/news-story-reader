# views/command_mode.py

import curses

def command_mode(stdscr):
    """
    Displays a prompt on the bottom line for command input.
    Returns the typed command or None if canceled with ESC.
    """
    curses.echo()
    h, w = stdscr.getmaxyx()
    prompt = ":"
    stdscr.addstr(h - 1, 0, prompt)
    stdscr.clrtoeol()
    stdscr.refresh()

    curses.cbreak()
    stdscr.keypad(True)
    user_input = ""
    cursor_pos = 0

    while True:
        stdscr.move(h - 1, 0)
        stdscr.clrtoeol()
        stdscr.addstr(h - 1, 0, prompt + user_input)
        stdscr.move(h - 1, 1 + cursor_pos)
        stdscr.refresh()

        ch = stdscr.getch()

        if ch == 27:  # ESC
            curses.noecho()
            return None
        elif ch in [curses.KEY_ENTER, 10, 13]:
            curses.noecho()
            return user_input
        elif ch in [curses.KEY_BACKSPACE, 127, 8]:
            if cursor_pos > 0:
                user_input = user_input[:cursor_pos - 1] + user_input[cursor_pos:]
                cursor_pos -= 1
        elif 32 <= ch <= 126:  # printable ASCII
            user_input = user_input[:cursor_pos] + chr(ch) + user_input[cursor_pos:]
            cursor_pos += 1
        elif ch == curses.KEY_LEFT and cursor_pos > 0:
            cursor_pos -= 1
        elif ch == curses.KEY_RIGHT and cursor_pos < len(user_input):
            cursor_pos += 1
