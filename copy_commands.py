# copy_commands.py

import curses

def copy_stories(stdscr, cmd, stories, titles):
    """
    Copies one or more stories (by index) to the clipboard.
    Accepts commands like ':c 1' or ':clip 2-4'.
    """
    h = stdscr.getmaxyx()[0]
    parts = cmd.split()

    if len(parts) > 1 and (parts[0] in ["c", "clip"]):
        try:
            story_indices = []
            # Skip the first part (the command itself), parse each argument
            for arg in parts[1:]:
                if "-" in arg:
                    # e.g. "3-5"
                    start, end = map(int, arg.split("-"))
                    story_indices.extend(range(start - 1, end))
                else:
                    # Single index
                    story_idx = int(arg) - 1
                    story_indices.append(story_idx)

            to_copy = []
            for idx in sorted(set(story_indices)):
                if 0 <= idx < len(stories) and idx < len(titles):
                    to_copy.append(f"{titles[idx]}\n\n{stories[idx]}\n")

            if to_copy:
                clipboard_content = "\n\n---\n\n".join(to_copy)
                try:
                    import pyperclip
                    pyperclip.copy(clipboard_content)
                    stdscr.addstr(h - 1, 0, f"Copied {len(to_copy)} stories to clipboard!")
                    stdscr.clrtoeol()
                    stdscr.refresh()
                    curses.napms(1500)
                except ImportError:
                    stdscr.addstr(h - 1, 0, "Error: pyperclip not installed. 'pip install pyperclip'")
                    stdscr.clrtoeol()
                    stdscr.refresh()
                    curses.napms(2000)
            else:
                stdscr.addstr(h - 1, 0, "No valid stories to copy.")
                stdscr.clrtoeol()
                stdscr.refresh()
                curses.napms(1500)
        except (ValueError, IndexError) as e:
            stdscr.addstr(h - 1, 0, f"Invalid clip format. Use ':c 1 3-5'. Error: {e}")
            stdscr.clrtoeol()
            stdscr.refresh()
            curses.napms(2000)
