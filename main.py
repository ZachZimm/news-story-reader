# main.py
import sys
import curses
import datetime
import os
from dotenv import load_dotenv

# Our own modules
from database import fetch_all_dates, fetch_stories
from copy_commands import copy_stories
from views.list_view import display_list
from views.story_view import display_story
from views.date_popup import display_dates_popup

all_dates = []  # We'll populate this once we know db_dir

def tui(stdscr, db_dir, default_datestring):
    curses.curs_set(0)
    global all_dates
    all_dates = fetch_all_dates(db_dir)
    if not default_datestring in all_dates:
        default_datestring = all_dates[0]

    titles, stories = fetch_stories(db_dir, default_datestring)
    current_date = default_datestring
    selected_index = 0

    while True:
        list_result = display_list(stdscr, titles, current_date, selected_index)
        if list_result is None:
            break  # user pressed ESC/q in the list

        if isinstance(list_result, tuple):
            # Possibly ("command", cmd_string, current_row)
            if list_result[0] == "command":
                cmd = list_result[1].strip()
                selected_index = list_result[2]
                if cmd.startswith("d"):
                    parts = cmd.split()
                    if len(parts) < 2 or parts[1] not in all_dates:
                        chosen = display_dates_popup(stdscr, all_dates, current_date)
                        if chosen is not None:
                            current_date = chosen
                            titles, stories = fetch_stories(db_dir, chosen)
                            selected_index = 0
                    else:
                        new_date = parts[1]
                        current_date = new_date
                        titles, stories = fetch_stories(db_dir, new_date)
                        selected_index = 0
                elif cmd.startswith("c"):
                    # If user typed just ":c"
                    if len(cmd.split()) == 1:
                        cmd = f"c {selected_index + 1}"
                    copy_stories(stdscr, cmd, stories, titles)
                elif cmd.isdigit():
                    # If user typed just a number
                    selected_index = int(cmd) - 1
                    if selected_index > len(stories):
                        selected_index = len(stories) - 1
                    elif selected_index < 1:
                        selected_index = 0
                    display_story(stdscr, titles[selected_index], stories[selected_index], selected_index, current_date)

            continue
        else:
            # user selected a story index
            selected_index = list_result
            story_offset = 0

            while True:
                story_result = display_story(
                    stdscr,
                    titles[selected_index],
                    stories[selected_index],
                    selected_index,
                    current_date,
                    offset=story_offset
                )

                if story_result == "exit":
                    # ESC from story => exit entire program
                    sys.exit(0)
                elif story_result == "back":
                    # 'q' => back to the list
                    break
                elif isinstance(story_result, tuple) and story_result[0] == "command":
                    cmd = story_result[1].strip()
                    story_offset = story_result[2]  # preserve scroll
                    if cmd.startswith("d"):
                        parts = cmd.split()
                        if len(parts) < 2 or parts[1] not in all_dates:
                            chosen = display_dates_popup(stdscr, all_dates, current_date)
                            if chosen is not None:
                                current_date = chosen
                                titles, stories = fetch_stories(db_dir, chosen)
                                selected_index = 0
                            break
                        else:
                            new_date = parts[1]
                            current_date = new_date
                            titles, stories = fetch_stories(db_dir, new_date)
                            selected_index = 0
                            break
                    elif cmd.startswith("c"):
                        if len(cmd.split()) == 1:
                            cmd = f"c {selected_index + 1}"
                        copy_stories(stdscr, cmd, stories, titles)
                        # do not reset offset - remain in story
                    else:
                        # unrecognized command
                        pass
                else:
                    # user pressed ESC or something else
                    break

def main(datestring, db_dir):
    curses.wrapper(lambda stdscr: tui(stdscr, db_dir, datestring))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        datestring = sys.argv[1]
    else:
        today = datetime.date.today()
        datestring = today.strftime("%Y%m%d")
    load_dotenv()
    db_dir = os.getenv("STORY_DB_DIR", "news.db")
    main(datestring, db_dir)
