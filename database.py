# database.py

import sqlite3

def fetch_all_dates(db_dir):
    conn = sqlite3.connect(db_dir)
    c = conn.cursor()
    c.execute("SELECT DISTINCT issue_date FROM documents ORDER BY issue_date DESC")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def fetch_stories(db_dir, date_str):
    conn = sqlite3.connect(db_dir)
    c = conn.cursor()
    c.execute("SELECT * FROM stories WHERE issue_date=?", (date_str,))
    rows = c.fetchall()
    conn.close()
    # rows: (id, title, author, issue_date, content)
    titles = [r[1] for r in rows]
    stories = [r[4] for r in rows]
    return titles, stories
