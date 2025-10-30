# views/story_view.py

import curses
import textwrap
import datetime
import hashlib
from .command_mode import command_mode

# Cache for wrapped text lines: {cache_key: {'wrapped_lines': [...], 'col_width': int}}
_wrapped_cache = {}


def _format_issue_date(raw_date):
    """Format the provided issue_date into a human-readable string."""
    if isinstance(raw_date, datetime.datetime):
        date_obj = raw_date.date()
    elif isinstance(raw_date, datetime.date):
        date_obj = raw_date
    else:
        date_str = str(raw_date).strip() if raw_date is not None else ""
        if not date_str:
            return "Unknown date"

        for fmt in ("%Y%m%d", "%Y-%m-%d"):
            try:
                date_obj = datetime.datetime.strptime(date_str, fmt).date()
                break
            except ValueError:
                continue
        else:
            return date_str

    return date_obj.strftime("%B %d, %Y")

def _get_cache_key(story_content, col_width):
    """Generate a cache key for wrapped text."""
    # Include both content and column width in cache key
    content_hash = hashlib.md5(story_content.encode('utf-8')).hexdigest()
    return f"{content_hash}_{col_width}"

def _get_wrapped_lines(story, col_width):
    """Get wrapped lines for a story, using cache if available."""
    cache_key = _get_cache_key(story, col_width)
    
    if cache_key not in _wrapped_cache:
        # Compute wrapped lines
        wrapper = textwrap.TextWrapper(width=col_width)
        paragraphs = story.split('\n')
        wrapped_lines = []
        for paragraph in paragraphs:
            wrapped_lines.extend(wrapper.wrap(paragraph))
            wrapped_lines.append("")
        if wrapped_lines and wrapped_lines[-1] == "":
            wrapped_lines.pop()
        _wrapped_cache[cache_key] = wrapped_lines
    
    return _wrapped_cache[cache_key]

def display_story(stdscr, title, story, story_index, issue_date, offset=0, knn_results=None):
    """
    Returns one of:
      - "back" if user pressed q
      - "exit" if user pressed ESC
      - ("command", command_string, offset) if user typed a command
        (including current scroll offset).
    
    Args:
        issue_date: The story's issue date (YYYYMMDD string/int or date object) used for display.
        knn_results: If not None, indicates we're viewing a story from KNN results.
                    When Q is pressed, should return to KNN results list.
    """
    curses.curs_set(0)
    h, w = stdscr.getmaxyx()
    margin = 4
    even_landmark = "♦︎"
    odd_landmark = "♢"
    formatted_issue_date = _format_issue_date(issue_date)

    col_width = (w - margin * 2 - 4) // 2
    # Get wrapped lines from cache (or compute and cache)
    wrapped_lines = _get_wrapped_lines(story, col_width)
    
    total_rows = (len(wrapped_lines) + 1) // 2

    while True:
        stdscr.clear()
        stdscr.addstr(0, margin, f"{story_index+1}: {title} - {formatted_issue_date}", curses.A_BOLD)

        for i in range(1, h - 1):
            row_idx = i - 1 + offset
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
            "Use UP/DOWN/j/k to scroll, 'q' to go back, ESC to exit, : for commands (use :k<N> for similar stories)."
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
