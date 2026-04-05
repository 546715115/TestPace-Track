import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pace_track.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Document config table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id TEXT NOT NULL,
            name TEXT NOT NULL,
            bucket_id TEXT NOT NULL,
            doc_id TEXT NOT NULL,
            cache_path TEXT,
            last_sync TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Version plan table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS version_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id TEXT NOT NULL,
            version_name TEXT NOT NULL,
            stage_name TEXT NOT NULL,
            target_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Check field config table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS check_field_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            is_required INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()