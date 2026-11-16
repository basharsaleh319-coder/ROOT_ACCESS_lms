import sqlite3
import hashlib

def get_db():
    conn = sqlite3.connect("root_access.db")
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. جدول المدربين والمراكز (العملاء)
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
    
    # إنشاء حساب مدرب تجريبي افتراضي (admin / 1234)
    default_pass = hash_password("1234")
    cursor.execute("""
        INSERT OR IGNORE INTO instructors (id, center_name, username, password_hash, plan)
        VALUES (1, 'أكاديمية التجربة', 'admin', ?, 'الباقة الشهرية')
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
    
    # ترقية الجداول القديمة تلقائيًا إذا كانت موجودة بدون عمود instructor_id
    for table in ["students", "lessons", "quizzes", "quiz_results"]:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN instructor_id INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # العمود موجود بالفعل

    conn.commit()
    conn.close()
