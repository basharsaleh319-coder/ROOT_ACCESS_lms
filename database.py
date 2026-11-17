import os
import sqlite3
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# طبقة توافق ذكية تجعل PostgreSQL يعمل بنفس أوامر SQLite دون تعديل باقي الملفات
class PostgresWrapper:
    def __init__(self, conn):
        self.conn = conn
        self.cur = conn.cursor(cursor_factory=RealDictCursor)

    def execute(self, query, params=None):
        # تحويل علامات الاستفهام ? إلى %s الخاصة بـ PostgreSQL
        pg_query = query.replace("?", "%s")
        # تعديل صيغة المفتاح التلقائي عند إنشاء الجداول
        pg_query = pg_query.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        # تعديل صيغة تجاهل التكرار عند إدخال المدرب الافتراضي
        if "INSERT OR IGNORE INTO instructors" in pg_query:
            pg_query = pg_query.replace("INSERT OR IGNORE INTO", "INSERT INTO") + " ON CONFLICT (username) DO NOTHING"
        
        self.cur.execute(pg_query, params or ())
        return self.cur

    def cursor(self):
        return self

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cur.close()
        self.conn.close()

def get_db():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL)
        return PostgresWrapper(conn)
    else:
        conn = sqlite3.connect("root_access.db")
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. جدول المدربين والمراكز
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS instructors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            center_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            plan TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        )
    """)
    
    default_pass = hash_password("1234")
    cursor.execute("""
        INSERT OR IGNORE INTO instructors (center_name, username, password_hash, plan)
        VALUES ('أكاديمية التجربة', 'admin', ?, 'الباقة الشهرية')
    """, (default_pass,))

    # 2. جدول الطلاب
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instructor_id INTEGER DEFAULT 1,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            course TEXT NOT NULL,
            access_code TEXT NOT NULL
        )
    """)
    
    # 3. جدول الدروس
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instructor_id INTEGER DEFAULT 1,
            title TEXT NOT NULL,
            course TEXT NOT NULL,
            video_url TEXT NOT NULL
        )
    """)
    
    # 4. جدول الامتحانات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instructor_id INTEGER DEFAULT 1,
            course TEXT NOT NULL,
            question TEXT NOT NULL,
            opt1 TEXT NOT NULL,
            opt2 TEXT NOT NULL,
            opt3 TEXT NOT NULL,
            correct_opt TEXT NOT NULL
        )
    """)
    
    # 5. جدول النتائج والشهادات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
