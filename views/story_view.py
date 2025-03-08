# views/story_view.py

import curses
import textwrap
import datetime
from .command_mode import command_mode

def display_story(stdscr, title, story, story_index, datestring, offset=0):
    """
    Returns one of:
      - "back" if user pressed q
      - "exit" if user pressed ESC
      - ("command", command_string, offset) if user typed a command
        (including current scroll offset).
    """
    curses.curs_set(0)
    h, w = stdscr.getmaxyx()
    margin = 4
    even_landmark = "♦︎"
    odd_landmark = "♢"
    current_date = datetime.datetime.strptime(datestring, "%Y%m%d").strftime("%B %d, %Y")

    col_width = (w - margin * 2 - 4) // 2
    wrapper = textwrap.TextWrapper(width=col_width)
    paragraphs = story.split('\n')
    wrapped_lines = []
    for paragraph in paragraphs:
        wrapped_lines.extend(wrapper.wrap(paragraph))
        wrapped_lines.append("")
    if wrapped_lines and wrapped_lines[-1] == "":
        wrapped_lines.pop()

    total_rows = (len(wrapped_lines) + 1) // 2

    while True:
        stdscr.clear()
        stdscr.addstr(0, margin, f"{story_index+1}: {title} - {current_date}", curses.A_BOLD)

        for i in range(2, h - 2):
            row_idx = i - 2 + offset
            if row_idx < total_rows:
                # Landmarks
                if row_idx % 2 == 0:
                    left_landmark, middle_landmark, right_landmark = even_landmark, odd_landmark, even_landmark
                else:
                    left_landmark, middle_landmark, right_landmark = odd_landmark, even_landmark, odd_landmark

                # First column
                if row_idx < len(wrapped_lines):
                    first_col = wrapped_lines[row_idx].ljust(col_width)
                else:
                    first_col = "".ljust(col_width)

                # Second column
                second_col_idx = row_idx + total_rows
                if second_col_idx < len(wrapped_lines):
                    second_col = wrapped_lines[second_col_idx].ljust(col_width)
                else:
                    second_col = "".ljust(col_width)

                if not first_col.strip() and not second_col.strip():
                    formatted_line = " " * (col_width * 2 + 4)
                else:
                    formatted_line = (
                        f"{left_landmark}  {first_col}"
                        f"{middle_landmark}  {second_col}"
                        f"{right_landmark}"
                    )
                stdscr.addstr(i, margin, formatted_line)

        stdscr.addstr(
            h - 1,
            0,
            "Use UP/DOWN/j/k to scroll, 'q' to go back, ESC to exit, : for commands."
        )
        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_UP, ord('k')) and offset > 0:
            offset -= 1
        elif key in (curses.KEY_DOWN, ord('j')) and offset < total_rows - (h - 2):
            offset += 1
        elif key in [ord('q'), ord('Q')]:
            return "back"
        elif key == 27:  # ESC
            return "exit"
        elif key == ord(':'):
            command = command_mode(stdscr)
            if command is None:
                continue
            # Return the command with current offset so we can re-display
            return ("command", command, offset)
