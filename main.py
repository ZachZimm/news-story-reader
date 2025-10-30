# main.py
import sys
import curses
import datetime
import os
import argparse
import threading
from dotenv import load_dotenv

# Our own modules
from database import fetch_all_dates, fetch_story_titles, fetch_story_content, close_db_connection, fetch_all_story_embeddings
from copy_commands import copy_stories
from views.list_view import display_list
from views.story_view import display_story
from views.date_popup import display_dates_popup
from similarity import find_k_most_similar

all_dates = []  # We'll populate this once we know db_config

def wait_for_embeddings(stdscr, embeddings_ready, all_embeddings):
    """Wait for embeddings to be ready, showing a message if needed.
    
    Returns True if embeddings are available, False otherwise.
    """
    if embeddings_ready.is_set():
        return len(all_embeddings) > 0
    
    # Show loading message and wait
    stdscr.clear()
    stdscr.addstr(0, 2, "Waiting for embeddings to load...", curses.A_BOLD)
    stdscr.addstr(2, 2, "This may take a moment. Please wait...")
    stdscr.refresh()
    
    # Wait for embeddings to be ready (with timeout to avoid infinite wait)
    embeddings_ready.wait(timeout=300)  # 5 minute timeout
    
    if embeddings_ready.is_set() and len(all_embeddings) > 0:
        return True
    return False

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
    
    # Background loading of embeddings
    # Store all embeddings in memory: {story_id: [float, ...]}
    all_embeddings = {}
    embeddings_ready = threading.Event()
    embedding_thread = None
    
    def load_embeddings_background():
        """Background thread function to load embeddings."""
        try:
            loaded_embeddings = fetch_all_story_embeddings(db_config, use_sqlite)
            all_embeddings.update(loaded_embeddings)
        except Exception as e:
            # If loading fails, embeddings dict remains empty
            pass
        finally:
            embeddings_ready.set()
    
    if not use_sqlite:
        # Start background thread to fetch embeddings
        embedding_thread = threading.Thread(target=load_embeddings_background, daemon=True)
        embedding_thread.start()
    else:
        # In SQLite mode, embeddings are not available, so mark as ready immediately
        embeddings_ready.set()
    
    current_date = default_datestring
    selected_index = 0
    
    # Track KNN results: None means normal view, otherwise dict with 'story_ids', 'titles', 'source_story_id'
    knn_results = None

    while True:
        # Determine which list to display
        display_titles = knn_results['titles'] if knn_results else titles
        display_story_ids = knn_results['story_ids'] if knn_results else story_ids
        display_date = "KNN Results" if knn_results else current_date
        
        list_result = display_list(stdscr, display_titles, display_date, selected_index)
        if list_result is None:
            if knn_results:
                # Return to normal view from KNN results
                knn_results = None
                story_list = fetch_story_titles(db_config, current_date, use_sqlite)
                titles = [title for _, title in story_list]
                story_ids = [story_id for story_id, _ in story_list]
                selected_index = 0
                continue
            else:
                break  # user pressed ESC/q in the list

        if isinstance(list_result, tuple):
            # Possibly ("command", cmd_string, current_row)
            if list_result[0] == "command":
                cmd = list_result[1].strip()
                selected_index = list_result[2]
                if cmd.startswith("k") or cmd.startswith("K"):
                    # KNN search command: k <number> or k<number>
                    if not use_sqlite:
                        # Wait for embeddings if they're not ready yet
                        if not wait_for_embeddings(stdscr, embeddings_ready, all_embeddings):
                            # Embeddings failed to load or timed out
                            stdscr.clear()
                            stdscr.addstr(0, 2, "Error: Could not load embeddings.", curses.A_BOLD)
                            stdscr.addstr(2, 2, "Press any key to continue...")
                            stdscr.refresh()
                            stdscr.getch()
                            continue
                        
                        # Parse the number
                        cmd_parts = cmd.split()
                        if len(cmd_parts) == 1:
                            # Try to extract number from command like "k5"
                            num_str = cmd[1:].strip()
                            if not num_str:
                                k = 5  # Default
                            else:
                                try:
                                    k = int(num_str)
                                except ValueError:
                                    k = 5
                        else:
                            try:
                                k = int(cmd_parts[1])
                            except (ValueError, IndexError):
                                k = 5
                        
                        # Get the selected story ID
                        query_story_id = display_story_ids[selected_index]
                        query_embedding = all_embeddings.get(query_story_id)
                        
                        if query_embedding:
                            # Show searching message
                            stdscr.clear()
                            stdscr.addstr(0, 2, f"Searching for {k} similar stories...", curses.A_BOLD)
                            stdscr.refresh()
                            
                            # Get all candidate story IDs (all stories with embeddings)
                            candidate_ids = list(all_embeddings.keys())
                            
                            # Perform KNN search
                            similar_stories = find_k_most_similar(
                                query_embedding,
                                all_embeddings,
                                candidate_ids,
                                k=k,
                                exclude_query_id=query_story_id
                            )
                            
                            if similar_stories:
                                # Build results list
                                knn_story_ids = [sid for sid, _ in similar_stories]
                                knn_titles = []
                                for sid in knn_story_ids:
                                    # Try to get title from cache or fetch it
                                    if sid in story_cache:
                                        knn_titles.append(story_cache[sid]['title'])
                                    else:
                                        story_data = fetch_story_content(db_config, sid, use_sqlite)
                                        if story_data:
                                            story_cache[sid] = story_data
                                            knn_titles.append(story_data['title'])
                                        else:
                                            knn_titles.append(f"Story {sid}")
                                
                                knn_results = {
                                    'story_ids': knn_story_ids,
                                    'titles': knn_titles,
                                    'source_story_id': query_story_id
                                }
                                selected_index = 0
                            else:
                                # No results found
                                stdscr.clear()
                                stdscr.addstr(0, 2, "No similar stories found.", curses.A_BOLD)
                                stdscr.addstr(2, 2, "Press any key to continue...")
                                stdscr.refresh()
                                stdscr.getch()
                        else:
                            # No embedding for this story
                            stdscr.clear()
                            stdscr.addstr(0, 2, "No embedding available for this story.", curses.A_BOLD)
                            stdscr.addstr(2, 2, "Press any key to continue...")
                            stdscr.refresh()
                            stdscr.getch()
                    else:
                        # SQLite mode or no embeddings
                        stdscr.clear()
                        stdscr.addstr(0, 2, "KNN search only available with PostgreSQL embeddings.", curses.A_BOLD)
                        stdscr.addstr(2, 2, "Press any key to continue...")
                        stdscr.refresh()
                        stdscr.getch()
                elif cmd.startswith("d"):
                    parts = cmd.split()
                    if len(parts) < 2 or parts[1] not in all_dates:
                        chosen = display_dates_popup(stdscr, all_dates, current_date)
                        if chosen is not None:
                            current_date = chosen
                            story_list = fetch_story_titles(db_config, chosen, use_sqlite)
                            titles = [title for _, title in story_list]
                            story_ids = [story_id for story_id, _ in story_list]
                            story_cache = {}  # Clear cache when changing dates
                            knn_results = None  # Clear KNN results
                            selected_index = 0
                    else:
                        new_date = parts[1]
                        current_date = new_date
                        story_list = fetch_story_titles(db_config, new_date, use_sqlite)
                        titles = [title for _, title in story_list]
                        story_ids = [story_id for story_id, _ in story_list]
                        story_cache = {}  # Clear cache when changing dates
                        knn_results = None  # Clear KNN results
                        selected_index = 0
                elif cmd.startswith("c"):
                    # If user typed just ":c"
                    if len(cmd.split()) == 1:
                        cmd = f"c {selected_index + 1}"
                    # For copy command, we need to load stories if not cached
                    stories = []
                    for story_id in display_story_ids:
                        if story_id in story_cache:
                            stories.append(story_cache[story_id]['content'])
                        else:
                            story_data = fetch_story_content(db_config, story_id, use_sqlite)
                            if story_data:
                                story_cache[story_id] = story_data
                                stories.append(story_data['content'])
                            else:
                                stories.append("")
                    copy_stories(stdscr, cmd, stories, display_titles)
                elif cmd.isdigit():
                    # If user typed just a number
                    selected_index = int(cmd) - 1
                    if selected_index >= len(display_titles):
                        selected_index = len(display_titles) - 1
                    elif selected_index < 0:
                        selected_index = 0
                    # Load story content if not cached
                    story_id = display_story_ids[selected_index]
                    if story_id not in story_cache:
                        story_data = fetch_story_content(db_config, story_id, use_sqlite)
                        if story_data:
                            story_cache[story_id] = story_data
                    if story_id in story_cache:
                        story_data = story_cache[story_id]
                        display_story(
                            stdscr,
                            story_data['title'],
                            story_data['content'],
                            selected_index,
                            story_data.get('issue_date', current_date),
                            knn_results=knn_results
                        )

            continue
        else:
            # user selected a story index
            selected_index = list_result
            story_offset = 0
            
            # Load story content if not cached
            story_id = display_story_ids[selected_index]
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
                    story_data.get('issue_date', current_date),
                    offset=story_offset,
                    knn_results=knn_results
                )

                if story_result == "exit":
                    # ESC from story => exit entire program
                    sys.exit(0)
                elif story_result == "back":
                    # 'q' => back to the list (KNN results if from KNN, otherwise normal list)
                    break
                elif isinstance(story_result, tuple) and story_result[0] == "command":
                    cmd = story_result[1].strip()
                    story_offset = story_result[2]  # preserve scroll
                    if cmd.startswith("k") or cmd.startswith("K"):
                        # KNN search command from story view
                        if not use_sqlite:
                            # Wait for embeddings if they're not ready yet
                            if not wait_for_embeddings(stdscr, embeddings_ready, all_embeddings):
                                # Embeddings failed to load or timed out
                                stdscr.clear()
                                stdscr.addstr(0, 2, "Error: Could not load embeddings.", curses.A_BOLD)
                                stdscr.addstr(2, 2, "Press any key to continue...")
                                stdscr.refresh()
                                stdscr.getch()
                                continue
                            
                            # Parse the number
                            cmd_parts = cmd.split()
                            if len(cmd_parts) == 1:
                                num_str = cmd[1:].strip()
                                if not num_str:
                                    k = 5
                                else:
                                    try:
                                        k = int(num_str)
                                    except ValueError:
                                        k = 5
                            else:
                                try:
                                    k = int(cmd_parts[1])
                                except (ValueError, IndexError):
                                    k = 5
                            
                            # Use current story as query
                            query_story_id = story_id
                            query_embedding = all_embeddings.get(query_story_id)
                            
                            if query_embedding:
                                # Show searching message
                                stdscr.clear()
                                stdscr.addstr(0, 2, f"Searching for {k} similar stories...", curses.A_BOLD)
                                stdscr.refresh()
                                
                                # Get all candidate story IDs
                                candidate_ids = list(all_embeddings.keys())
                                
                                # Perform KNN search
                                similar_stories = find_k_most_similar(
                                    query_embedding,
                                    all_embeddings,
                                    candidate_ids,
                                    k=k,
                                    exclude_query_id=query_story_id
                                )
                                
                                if similar_stories:
                                    # Build results list
                                    knn_story_ids = [sid for sid, _ in similar_stories]
                                    knn_titles = []
                                    for sid in knn_story_ids:
                                        if sid in story_cache:
                                            knn_titles.append(story_cache[sid]['title'])
                                        else:
                                            story_data_fetch = fetch_story_content(db_config, sid, use_sqlite)
                                            if story_data_fetch:
                                                story_cache[sid] = story_data_fetch
                                                knn_titles.append(story_data_fetch['title'])
                                            else:
                                                knn_titles.append(f"Story {sid}")
                                    
                                    knn_results = {
                                        'story_ids': knn_story_ids,
                                        'titles': knn_titles,
                                        'source_story_id': query_story_id
                                    }
                                    selected_index = 0
                                    break  # Exit story view to show KNN results
                                else:
                                    # No results found
                                    stdscr.clear()
                                    stdscr.addstr(0, 2, "No similar stories found.", curses.A_BOLD)
                                    stdscr.addstr(2, 2, "Press any key to continue...")
                                    stdscr.refresh()
                                    stdscr.getch()
                            else:
                                # No embedding for this story
                                stdscr.clear()
                                stdscr.addstr(0, 2, "No embedding available for this story.", curses.A_BOLD)
                                stdscr.addstr(2, 2, "Press any key to continue...")
                                stdscr.refresh()
                                stdscr.getch()
                        else:
                            # SQLite mode or no embeddings
                            stdscr.clear()
                            stdscr.addstr(0, 2, "KNN search only available with PostgreSQL embeddings.", curses.A_BOLD)
                            stdscr.addstr(2, 2, "Press any key to continue...")
                            stdscr.refresh()
                            stdscr.getch()
                    elif cmd.startswith("d"):
                        parts = cmd.split()
                        if len(parts) < 2 or parts[1] not in all_dates:
                            chosen = display_dates_popup(stdscr, all_dates, current_date)
                            if chosen is not None:
                                current_date = chosen
                                story_list = fetch_story_titles(db_config, chosen, use_sqlite)
                                titles = [title for _, title in story_list]
                                story_ids = [story_id for story_id, _ in story_list]
                                story_cache = {}  # Clear cache when changing dates
                                knn_results = None  # Clear KNN results
                                selected_index = 0
                            break
                        else:
                            new_date = parts[1]
                            current_date = new_date
                            story_list = fetch_story_titles(db_config, new_date, use_sqlite)
                            titles = [title for _, title in story_list]
                            story_ids = [story_id for story_id, _ in story_list]
                            story_cache = {}  # Clear cache when changing dates
                            knn_results = None  # Clear KNN results
                            selected_index = 0
                            break
                    elif cmd.startswith("c"):
                        if len(cmd.split()) == 1:
                            cmd = f"c {selected_index + 1}"
                        # For copy command, we need to load stories if not cached
                        stories = []
                        current_story_ids = knn_results['story_ids'] if knn_results else story_ids
                        current_titles = knn_results['titles'] if knn_results else titles
                        for sid in current_story_ids:
                            if sid in story_cache:
                                stories.append(story_cache[sid]['content'])
                            else:
                                story_data_fetch = fetch_story_content(db_config, sid, use_sqlite)
                                if story_data_fetch:
                                    story_cache[sid] = story_data_fetch
                                    stories.append(story_data_fetch['content'])
                                else:
                                    stories.append("")
                        copy_stories(stdscr, cmd, stories, current_titles)
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
