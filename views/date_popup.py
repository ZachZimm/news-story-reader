# views/date_popup.py

import curses
import datetime

def display_dates_popup(stdscr, date_list, current_date):
    """
    Displays a vertical list of dates in the center of the screen so the user
    can pick one with ENTER or cancel with ESC/q.
    Returns the chosen date as 'YYYYMMDD', or None if cancelled.
    """
    formatted_dates = []
    for raw_date in date_list:
        dt = datetime.datetime.strptime(raw_date, "%Y%m%d")
        display_str = dt.strftime("%B %d, %Y")
        formatted_dates.append((raw_date, display_str))

    try:
        current_row = date_list.index(current_date)
    except ValueError:
        current_row = 0

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        box_width = max(min(w - 4, 40), 20)
        visible_count = min(len(formatted_dates), 20)
        box_height = visible_count + 4

        start_y = (h - box_height) // 2
        start_x = (w - box_width) // 2

        # Draw border
        for y in range(box_height):
            for x in range(box_width):
                if (y == 0 or y == box_height - 1) or (x == 0 or x == box_width - 1):
                    stdscr.addch(start_y + y, start_x + x, curses.ACS_CKBOARD)
                else:
                    stdscr.addch(start_y + y, start_x + x, ord(' '))

        title = " Select a Date "
        stdscr.addstr(start_y, start_x + 2, title, curses.A_BOLD)

        max_offset = len(formatted_dates) - visible_count
        scroll_top = max(0, min(current_row - (visible_count // 2), max_offset))
        scroll_bottom = scroll_top + visible_count

        for i, (raw, disp) in enumerate(formatted_dates[scroll_top:scroll_bottom]):
            actual_idx = i + scroll_top
            y_offset = start_y + 1 + i
            x_offset = start_x + 2
            marker = "> " if actual_idx == current_row else "  "
            line = marker + disp
            if actual_idx == current_row:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(y_offset, x_offset, line[:box_width - 4])
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addstr(y_offset, x_offset, line[:box_width - 4])

        instr = "Up/Down/j/k to move, ENTER to select, ESC/q to cancel"
        stdscr.addstr(start_y + box_height - 1, start_x + 2, instr[:box_width - 4], curses.A_BOLD)
        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_UP, ord('k')):
            if current_row > 0:
                current_row -= 1
            else:
                current_row = len(formatted_dates) - 1
        elif key in (curses.KEY_DOWN, ord('j')):
            if current_row < len(formatted_dates) - 1:
                current_row += 1
            else:
                current_row = 0
        elif key in [curses.KEY_ENTER, 10, 13]:
            return formatted_dates[current_row][0]
        elif key == 27 or key in [ord('q'), ord('Q')]:
            return None
