import sqlite3
from datetime import datetime, timedelta
from contextlib import contextmanager

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_requests INTEGER DEFAULT 0,
                    total_duration INTEGER DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    file_id TEXT,
                    duration INTEGER,
                    text TEXT,
                    language TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def get_or_create_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name))
                conn.commit()
            
            return user_id
    
    def save_transcription(self, user_id: int, file_id: str, duration: int, text: str, language: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transcriptions (user_id, file_id, duration, text, language)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, file_id, duration, text, language))
            conn.commit()
            return cursor.lastrowid
    
    def update_user_stats(self, user_id: int, duration: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET total_requests = total_requests + 1,
                    total_duration = total_duration + ?
                WHERE user_id = ?
            ''', (duration, user_id))
            conn.commit()
    
    def get_user_stats(self, user_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT total_requests, total_duration
                FROM users
                WHERE user_id = ?
            ''', (user_id,))
            row = cursor.fetchone()
            
            if not row:
                return {'total_requests': 0, 'total_duration': 0}
            
            return {
                'total_requests': row['total_requests'],
                'total_duration_minutes': round(row['total_duration'] / 60, 1)
            }
    
    def get_admin_stats(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(total_requests) FROM users')
            total_requests = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT SUM(total_duration) FROM users')
            total_duration = cursor.fetchone()[0] or 0
            
            return {
                'total_users': total_users,
                'total_requests': total_requests,
                'total_duration_minutes': round(total_duration / 60, 1)
            }