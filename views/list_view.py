# views/list_view.py

import curses
import datetime
from .command_mode import command_mode

def display_list(stdscr, titles, datestring, initial_selection=0):
    """
    Returns:
      - None (if user ESC/q)
      - int (the selected index if user presses ENTER)
      - ("command", user_input, current_row) if user typed ':'.
    """
    current_row = initial_selection
    current_date = datetime.datetime.strptime(datestring, "%Y%m%d").strftime("%B %d, %Y")

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        header = f"Stories for {current_date}"
        stdscr.addstr(0, 2, header, curses.A_BOLD)

        for idx, title in enumerate(titles):
            x = 2
            y = idx + 2
            marker = "> " if idx == current_row else "  "
            line = f"{idx+1}:\t {marker}{title}"
            if idx == current_row:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(y, x, line)
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addstr(y, x, line)

        stdscr.addstr(
            h - 1,
            0,
            "Use UP/DOWN/j/k to navigate, ENTER to select, : for commands, ESC/q to exit."
        )
        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_UP, ord('k')):
            if current_row > 0:
                current_row -= 1
            else:
                current_row = len(titles) - 1 if len(titles) > 0 else 0
        elif key in (curses.KEY_DOWN, ord('j')):
            if current_row < len(titles) - 1:
                current_row += 1
            else:
                current_row = 0
        elif key in [curses.KEY_ENTER, 10, 13]:
            return current_row
        elif key == 27 or key in [ord('q'), ord('Q')]:
            return None
        elif key == ord(':'):
            command = command_mode(stdscr)
            if command is None:
                # user pressed ESC at the command prompt
                continue
            return ("command", command, current_row)
