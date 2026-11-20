import os
import sqlite3
import hashlib

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

class UniversalCursor:
    def __init__(self, cursor, is_pg=False):
        self.cursor = cursor
        self.is_pg = is_pg

    def _adapt(self, sql):
        if not self.is_pg:
            return sql
        sql = sql.replace("?", "%s")
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        if "INSERT OR IGNORE INTO instructors" in sql:
            sql = sql.replace("INSERT OR IGNORE INTO", "INSERT INTO") + " ON CONFLICT (username) DO NOTHING"
        return sql

    def execute(self, sql, params=()):
        self.cursor.execute(self._adapt(sql), params)
        return self

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

class UniversalConnection:
    def __init__(self, conn, is_pg=False):
        self.conn = conn
        self.is_pg = is_pg

    def cursor(self):
        if self.is_pg:
            return UniversalCursor(self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor), True)
        return UniversalCursor(self.conn.cursor(), False)

    def execute(self, sql, params=()):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

def get_db():
    if DATABASE_URL and DATABASE_URL.startswith("postgres") and psycopg2:
        conn = psycopg2.connect(DATABASE_URL)
        return UniversalConnection(conn, is_pg=True)
    conn = sqlite3.connect("root_access.db")
    conn.row_factory = sqlite3.Row
    return UniversalConnection(conn, is_pg=False)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS instructors (
            id SERIAL PRIMARY KEY,
            center_name TEXT DEFAULT 'ROOT ACCESS',
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            plan TEXT DEFAULT 'Standard',
            status TEXT DEFAULT 'active',
            description TEXT DEFAULT ''
        )
    """)
    
    default_pass = hash_password("1234")
    cursor.execute("""
        INSERT OR IGNORE INTO instructors (center_name, username, password_hash, plan)
        VALUES ('أكاديمية التجربة', 'admin', ?, 'الباقة الشهرية')
    """, (default_pass,))

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            instructor_id INTEGER DEFAULT 1,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            course TEXT NOT NULL,
            access_code TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id SERIAL PRIMARY KEY,
            instructor_id INTEGER DEFAULT 1,
            title TEXT NOT NULL,
            course TEXT NOT NULL,
            video_url TEXT NOT NULL,
            description TEXT DEFAULT ''
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id SERIAL PRIMARY KEY,
            instructor_id INTEGER DEFAULT 1,
            course TEXT NOT NULL,
            question TEXT NOT NULL,
            opt1 TEXT NOT NULL,
            opt2 TEXT NOT NULL,
            opt3 TEXT NOT NULL,
            correct_opt TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id SERIAL PRIMARY KEY,
            instructor_id INTEGER DEFAULT 1,
            student_name TEXT NOT NULL,
            course TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            cert_id TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
