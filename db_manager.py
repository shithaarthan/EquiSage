import sqlite3
import json
from datetime import datetime
import os

# Get the directory of the current script to ensure the DB is in the project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "sessions.db")

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Makes rows accessible like dicts
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def setup_database():
    """Creates the necessary tables if they don't exist."""
    conn = get_db_connection()
    if conn:
        try:
            # Table to store user session data (the result of the last analysis)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    chat_id INTEGER PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    last_updated TIMESTAMP NOT NULL
                );
            """)
            # Table to track if we've sent a welcome message
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    first_seen TIMESTAMP NOT NULL
                );
            """)
            conn.commit()
            print("SQLite database setup complete.")
        except sqlite3.Error as e:
            print(f"Database setup error: {e}")
        finally:
            conn.close()

def save_session(chat_id: int, state_data: dict):
    """Saves or updates a user's session state in the database."""
    conn = get_db_connection()
    if conn:
        try:
            conn.execute("""
                INSERT INTO sessions (chat_id, state_json, last_updated)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    state_json=excluded.state_json,
                    last_updated=excluded.last_updated;
            """, (chat_id, json.dumps(state_data), datetime.now()))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error saving session for chat_id {chat_id}: {e}")
        finally:
            conn.close()

def load_session(chat_id: int) -> dict | None:
    """Loads a user's session state from the database."""
    conn = get_db_connection()
    if conn:
        try:
            session_row = conn.execute("SELECT state_json FROM sessions WHERE chat_id = ?", (chat_id,)).fetchone()
            if session_row:
                return json.loads(session_row['state_json'])
        except sqlite3.Error as e:
            print(f"Error loading session for chat_id {chat_id}: {e}")
        finally:
            conn.close()
    return None

def check_and_register_user(chat_id: int) -> bool:
    """
    Checks if a user is new. If so, registers them and returns True.
    If they are an existing user, returns False.
    """
    conn = get_db_connection()
    is_new_user = False
    if conn:
        try:
            user = conn.execute("SELECT 1 FROM users WHERE chat_id = ?", (chat_id,)).fetchone()
            if not user:
                # User not found, so they are new
                is_new_user = True
                conn.execute(
                    "INSERT INTO users (chat_id, first_seen) VALUES (?, ?)",
                    (chat_id, datetime.now())
                )
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error checking user {chat_id}: {e}")
        finally:
            conn.close()
    return is_new_user