# main.py
import sys
import curses
import datetime
import os
import argparse
from dotenv import load_dotenv

# Our own modules
from database import fetch_all_dates, fetch_story_titles, fetch_story_content, close_db_connection
from copy_commands import copy_stories
from views.list_view import display_list
from views.story_view import display_story
from views.date_popup import display_dates_popup

all_dates = []  # We'll populate this once we know db_config

def tui(stdscr, db_config, default_datestring, use_sqlite=True):
    curses.curs_set(0)
    global all_dates
    all_dates = fetch_all_dates(db_config, use_sqlite)
    if not default_datestring in all_dates:
        default_datestring = all_dates[0]

    # Load only titles initially (lazy loading)
    story_list = fetch_story_titles(db_config, default_datestring, use_sqlite)
    titles = [title for _, title in story_list]  # Extract just titles for display
    story_ids = [story_id for story_id, _ in story_list]  # Keep IDs for lazy loading
    story_cache = {}  # Cache loaded story content: {story_id: {'title': ..., 'content': ...}}
    
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
                            story_list = fetch_story_titles(db_config, chosen, use_sqlite)
                            titles = [title for _, title in story_list]
                            story_ids = [story_id for story_id, _ in story_list]
                            story_cache = {}  # Clear cache when changing dates
                            selected_index = 0
                    else:
                        new_date = parts[1]
                        current_date = new_date
                        story_list = fetch_story_titles(db_config, new_date, use_sqlite)
                        titles = [title for _, title in story_list]
                        story_ids = [story_id for story_id, _ in story_list]
                        story_cache = {}  # Clear cache when changing dates
                        selected_index = 0
                elif cmd.startswith("c"):
                    # If user typed just ":c"
                    if len(cmd.split()) == 1:
                        cmd = f"c {selected_index + 1}"
                    # For copy command, we need to load stories if not cached
                    stories = []
                    for story_id in story_ids:
                        if story_id in story_cache:
                            stories.append(story_cache[story_id]['content'])
                        else:
                            story_data = fetch_story_content(db_config, story_id, use_sqlite)
                            if story_data:
                                story_cache[story_id] = story_data
                                stories.append(story_data['content'])
                            else:
                                stories.append("")
                    copy_stories(stdscr, cmd, stories, titles)
                elif cmd.isdigit():
                    # If user typed just a number
                    selected_index = int(cmd) - 1
                    if selected_index >= len(titles):
                        selected_index = len(titles) - 1
                    elif selected_index < 0:
                        selected_index = 0
                    # Load story content if not cached
                    story_id = story_ids[selected_index]
                    if story_id not in story_cache:
                        story_data = fetch_story_content(db_config, story_id, use_sqlite)
                        if story_data:
                            story_cache[story_id] = story_data
                    if story_id in story_cache:
                        story_data = story_cache[story_id]
                        display_story(stdscr, story_data['title'], story_data['content'], selected_index, current_date)

            continue
        else:
            # user selected a story index
            selected_index = list_result
            story_offset = 0
            
            # Load story content if not cached
            story_id = story_ids[selected_index]
            if story_id not in story_cache:
                story_data = fetch_story_content(db_config, story_id, use_sqlite)
                if story_data:
                    story_cache[story_id] = story_data
            
            if story_id not in story_cache:
                # Story not found, skip
                continue
            
            story_data = story_cache[story_id]

            while True:
                story_result = display_story(
                    stdscr,
                    story_data['title'],
                    story_data['content'],
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
                                story_list = fetch_story_titles(db_config, chosen, use_sqlite)
                                titles = [title for _, title in story_list]
                                story_ids = [story_id for story_id, _ in story_list]
                                story_cache = {}  # Clear cache when changing dates
                                selected_index = 0
                            break
                        else:
                            new_date = parts[1]
                            current_date = new_date
                            story_list = fetch_story_titles(db_config, new_date, use_sqlite)
                            titles = [title for _, title in story_list]
                            story_ids = [story_id for story_id, _ in story_list]
                            story_cache = {}  # Clear cache when changing dates
                            selected_index = 0
                            break
                    elif cmd.startswith("c"):
                        if len(cmd.split()) == 1:
                            cmd = f"c {selected_index + 1}"
                        # For copy command, we need to load stories if not cached
                        stories = []
                        for sid in story_ids:
                            if sid in story_cache:
                                stories.append(story_cache[sid]['content'])
                            else:
                                story_data = fetch_story_content(db_config, sid, use_sqlite)
                                if story_data:
                                    story_cache[sid] = story_data
                                    stories.append(story_data['content'])
                                else:
                                    stories.append("")
                        copy_stories(stdscr, cmd, stories, titles)
                        # do not reset offset - remain in story
                    else:
                        # unrecognized command
                        pass
                else:
                    # user pressed ESC or something else
                    break

def main(datestring, db_config, use_sqlite=True):
    try:
        curses.wrapper(lambda stdscr: tui(stdscr, db_config, datestring, use_sqlite))
    finally:
        # Clean up database connection on exit
        close_db_connection()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='News Story Reader')
    parser.add_argument('datestring', nargs='?', help='Date string in YYYYMMDD format')
    parser.add_argument('--sqlite', action='store_true', help='Use SQLite database instead of PostgreSQL')
    args = parser.parse_args()
    
    # Determine datestring
    if args.datestring:
        datestring = args.datestring
    else:
        today = datetime.date.today()
        datestring = today.strftime("%Y%m%d")
    
    load_dotenv()
    
    # Determine database configuration
    use_sqlite = args.sqlite
    
    if use_sqlite:
        # SQLite mode: use STORY_DB_DIR or default to news.db
        db_config = os.getenv("STORY_DB_DIR", "news.db")
    else:
        # PostgreSQL mode: read connection parameters from .env
        db_config = {}
        # Only include parameters that are set
        if os.getenv("POSTGRES_HOST"):
            db_config['host'] = os.getenv("POSTGRES_HOST")
        else:
            db_config['host'] = "localhost"
        
        if os.getenv("POSTGRES_PORT"):
            db_config['port'] = os.getenv("POSTGRES_PORT")
        else:
            db_config['port'] = "5432"
        
        db_config['database'] = os.getenv("POSTGRES_DB")
        db_config['user'] = os.getenv("POSTGRES_USER")
        
        password = os.getenv("POSTGRES_PASSWORD")
        if password:
            db_config['password'] = password
        
        # Validate required PostgreSQL parameters
        if not db_config['database'] or not db_config['user']:
            print("Error: POSTGRES_DB and POSTGRES_USER must be set in .env file for PostgreSQL mode")
            sys.exit(1)
    
    main(datestring, db_config, use_sqlite)
