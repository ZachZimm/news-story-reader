# database.py

import sqlite3
import psycopg2
import datetime

# Connection caching for PostgreSQL (connection reuse)
_db_connection = None
_db_config = None
_use_sqlite = None

def _get_connection(use_sqlite, db_config):
    """Get a database connection (cached for PostgreSQL, new for SQLite).
    
    Args:
        use_sqlite: Boolean indicating whether to use SQLite (True) or PostgreSQL (False)
        db_config: If use_sqlite is True, this is the SQLite database file path.
                   If use_sqlite is False, this is a dict with PostgreSQL connection params.
    
    Returns:
        Database connection object
    """
    global _db_connection, _db_config, _use_sqlite
    
    if use_sqlite:
        # SQLite: create new connection each time (cheap, file-based)
        return sqlite3.connect(db_config)
    else:
        # PostgreSQL: reuse connection to avoid overhead
        config_key = str(sorted(db_config.items()))
        if _db_connection is None or _db_config != config_key or _use_sqlite != use_sqlite:
            if _db_connection:
                try:
                    _db_connection.close()
                except:
                    pass
            _db_connection = psycopg2.connect(**db_config)
            _db_config = config_key
            _use_sqlite = use_sqlite
        return _db_connection

def close_db_connection():
    """Close cached database connection (call on program exit)."""
    global _db_connection, _db_config, _use_sqlite
    if _db_connection:
        try:
            _db_connection.close()
        except:
            pass
        _db_connection = None
        _db_config = None
        _use_sqlite = None

def fetch_all_dates(db_config, use_sqlite=True):
    """Fetch all distinct dates from the database.
    
    Args:
        db_config: If use_sqlite is True, this is the SQLite database file path.
                   If use_sqlite is False, this is a dict with PostgreSQL connection params.
        use_sqlite: Boolean indicating whether to use SQLite (True) or PostgreSQL (False)
    
    Returns:
        List of date strings in YYYYMMDD format
    """
    conn = _get_connection(use_sqlite, db_config)
    try:
        c = conn.cursor()
        query = "SELECT DISTINCT issue_date FROM documents ORDER BY issue_date DESC"
        c.execute(query)
        rows = c.fetchall()
        dates = []
        for row in rows:
            date_val = row[0]
            # Convert date objects to string format YYYYMMDD
            if isinstance(date_val, (datetime.date, datetime.datetime)):
                dates.append(date_val.strftime("%Y%m%d"))
            elif isinstance(date_val, str):
                dates.append(date_val)
            else:
                # Fallback: try to convert to string
                dates.append(str(date_val))
        return dates
    finally:
        # Only close connection if SQLite (PostgreSQL connection is cached)
        if use_sqlite:
            conn.close()

def fetch_story_titles(db_config, date_str, use_sqlite=True):
    """Fetch only titles and IDs for a given date (fast, for list view).
    
    Args:
        db_config: If use_sqlite is True, this is the SQLite database file path.
                   If use_sqlite is False, this is a dict with PostgreSQL connection params.
        date_str: The date string to fetch stories for
        use_sqlite: Boolean indicating whether to use SQLite (True) or PostgreSQL (False)
    
    Returns:
        List of (story_id, title) tuples
    """
    conn = _get_connection(use_sqlite, db_config)
    try:
        c = conn.cursor()
        query = "SELECT id, title FROM stories WHERE issue_date=%s ORDER BY id" if not use_sqlite else "SELECT id, title FROM stories WHERE issue_date=? ORDER BY id"
        c.execute(query, (date_str,))
        rows = c.fetchall()
        return [(r[0], r[1]) for r in rows]  # (id, title) tuples
    finally:
        # Only close connection if SQLite (PostgreSQL connection is cached)
        if use_sqlite:
            conn.close()

def fetch_story_content(db_config, story_id, use_sqlite=True):
    """Fetch full content for a single story (lazy load).
    
    Args:
        db_config: If use_sqlite is True, this is the SQLite database file path.
                   If use_sqlite is False, this is a dict with PostgreSQL connection params.
        story_id: The story ID to fetch
        use_sqlite: Boolean indicating whether to use SQLite (True) or PostgreSQL (False)
    
    Returns:
        Dictionary with story data: {'id', 'title', 'author', 'issue_date', 'content'}
        Returns None if story not found
    """
    conn = _get_connection(use_sqlite, db_config)
    try:
        c = conn.cursor()
        query = "SELECT id, title, author, issue_date, content FROM stories WHERE id=%s" if not use_sqlite else "SELECT id, title, author, issue_date, content FROM stories WHERE id=?"
        c.execute(query, (story_id,))
        row = c.fetchone()
        if row:
            return {
                'id': row[0],
                'title': row[1],
                'author': row[2],
                'issue_date': row[3],
                'content': row[4]
            }
        return None
    finally:
        # Only close connection if SQLite (PostgreSQL connection is cached)
        if use_sqlite:
            conn.close()