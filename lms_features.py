from fastapi import APIRouter, HTTPException, Form, Request
from fastapi.responses import FileResponse
from datetime import datetime
import os
import secrets
import requests
from database import get_db, hash_password

router = APIRouter(tags=["ROOT ACCESS Core System"])

def init_all_tables():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_name TEXT DEFAULT '',
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            activation_token TEXT UNIQUE,
            is_active INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            class_name TEXT NOT NULL,
            subject TEXT DEFAULT ''
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS class_enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            student_code TEXT NOT NULL,
            student_name TEXT NOT NULL,
            access_pin TEXT NOT NULL DEFAULT '1234',
            UNIQUE(class_id, student_code)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS class_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS class_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            record_date TEXT NOT NULL,
            student_code TEXT NOT NULL,
            status TEXT NOT NULL,
            late_minutes INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            is_exam INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS class_certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cert_serial TEXT UNIQUE NOT NULL,
            class_id INTEGER NOT NULL,
            student_code TEXT NOT NULL,
            student_name TEXT NOT NULL,
            cert_type TEXT NOT NULL,
            issue_date TEXT NOT NULL
        )
    """)
    conn.commit()
    try:
        cursor.execute("ALTER TABLE teacher_activations ADD COLUMN teacher_name TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    conn.close()

init_all_tables()

def get_teacher_id(request: Request) -> int:
    val = request.cookies.get("instructor_id")
    return int(val) if val and val.isdigit() else 1

def send_gmail_security_link(teacher_email: str, token: str, base_url: str, purpose: str = "تفعيل حسابك"):
    BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()
    sender_email = "rootaccess.cayber@gmail.com"
    setup_link = f"{base_url}setup-password?token={token}"
    
    host = "".join(["a", "p", "i", ".", "b", "r", "e", "v", "o", ".", "c", "o", "m"])
    url = f"https://{host}/v3/smtp/email"
    
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }
    payload = {
        "sender": {"name": "ROOT ACCESS", "email": sender_email},
        "to": [{"email": teacher_email}],
        "subject": f"ROOT ACCESS - {purpose}",
        "htmlContent": f"""
        <div dir="rtl" style="font-family:Arial; background:#050505; color:#f3f4f6; padding:30px; border:1px solid #00ff88; border-radius:10px;">
            <h2 style="color:#00ff88;">🛡️ ROOT ACCESS</h2>
            <p>تم طلب (<strong>{purpose}</strong>) لحسابك. اضغط على الزر التالي لتعيين كلمة المرور:</p>
            <a href="{setup_link}" style="display:inline-block; background:#00ff88; color:#050505; padding:12px 24px; text-decoration:none; font-weight:bold; border-radius:6px; margin:15px 0;">
                تعيين كلمة المرور الآن
            </a>
        </div>
        """
    }
    response = requests.post(url, json=payload, headers=headers, timeout=15)
    if response.status_code not in (200, 201, 202):
        raise Exception(f"Brevo Error {response.status_code}: {response.text}")
@router.get("/setup-password")
def serve_setup_page():
    return FileResponse("setup_password.html")

@router.get("/api/master/teachers")
def get_all_teachers():
    conn = get_db()
    rows = conn.execute("SELECT id, teacher_name, email, is_active FROM teacher_activations ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.post("/api/master/invite-teacher")
def invite_teacher(request: Request, teacher_name: str = Form(""), email: str = Form(...)):
    email = email.strip().lower()
    name = teacher_name.strip() or email.split("@")[0]
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="يرجى إدخال بريد Gmail صحيح")
    conn = get_db()
    token = secrets.token_urlsafe(32)
    base_url = str(request.base_url)
    try:
        existing = conn.execute("SELECT * FROM teacher_activations WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.execute("UPDATE teacher_activations SET teacher_name = ?, activation_token = ? WHERE email = ?", (name, token, email))
        else:
            conn.execute("INSERT INTO teacher_activations (teacher_name, email, activation_token, is_active) VALUES (?, ?, ?, 0)", (name, email, token))
        conn.commit()
        try:
            send_gmail_security_link(email, token, base_url, "تفعيل حساب المعلم وإنشاء كلمة المرور")
            return {"status": "success", "message": f"تم إرسال رابط التفعيل بنجاح إلى: {email}"}
        except Exception as mail_err:
            setup_link = f"{base_url}setup-password?token={token}"
            return {"status": "success", "message": f'تم الحفظ! تعذر الإرسال ({mail_err})<br><a href="{setup_link}" target="_blank" dir="ltr" style="color:#00ff88;">افتح رابط تعيين كلمة المرور مباشرة</a>'}
    finally:
        conn.close()

@router.post("/api/master/teachers/{teacher_id}/reset-password")
def send_teacher_password_reset(request: Request, teacher_id: int):
    conn = get_db()
    teacher = conn.execute("SELECT * FROM teacher_activations WHERE id = ?", (teacher_id,)).fetchone()
    if not teacher:
        conn.close()
        raise HTTPException(status_code=404, detail="المعلم غير موجود")
    token = secrets.token_urlsafe(32)
    conn.execute("UPDATE teacher_activations SET activation_token = ? WHERE id = ?", (token, teacher_id))
    conn.commit()
    email = teacher["email"]
    conn.close()
    base_url = str(request.base_url)
    try:
        send_gmail_security_link(email, token, base_url, "تغيير / إعادة تعيين كلمة المرور")
        return {"status": "success", "message": f"تم إرسال رابط تغيير كلمة المرور إلى {email}"}
    except Exception as mail_err:
        setup_link = f"{base_url}setup-password?token={token}"
        return {"status": "success", "message": f'تعذر الإرسال ({mail_err})<br><a href="{setup_link}" target="_blank" dir="ltr" style="color:#00ff88;">افتح رابط تغيير كلمة المرور مباشرة</a>'}

@router.post("/api/master/teachers/{teacher_id}/update")
def update_teacher_info(teacher_id: int, teacher_name: str = Form(...), email: str = Form(...)):
    conn = get_db()
    old = conn.execute("SELECT * FROM teacher_activations WHERE id = ?", (teacher_id,)).fetchone()
    if not old:
        conn.close()
        raise HTTPException(status_code=404, detail="المعلم غير موجود")
    new_email = email.strip().lower()
    new_name = teacher_name.strip()
    try:
        conn.execute("UPDATE teacher_activations SET teacher_name = ?, email = ? WHERE id = ?", (new_name, new_email, teacher_id))
        conn.execute("UPDATE instructors SET name = ?, username = ? WHERE username = ?", (new_name, new_email, old["email"]))
        conn.commit()
        return {"status": "success", "message": "تم تحديث بيانات المعلم بنجاح"}
    except Exception:
        raise HTTPException(status_code=400, detail="البريد الإلكتروني مستخدم لمعلم آخر!")
    finally:
        conn.close()

@router.delete("/api/master/teachers/{teacher_id}")
def delete_teacher(teacher_id: int):
    conn = get_db()
    teacher = conn.execute("SELECT * FROM teacher_activations WHERE id = ?", (teacher_id,)).fetchone()
    if teacher:
        conn.execute("DELETE FROM instructors WHERE username = ?", (teacher["email"],))
        conn.execute("DELETE FROM teacher_activations WHERE id = ?", (teacher_id,))
        conn.commit()
    conn.close()
    return {"status": "success", "message": "تم حذف حساب المعلم نهائياً"}
@router.post("/api/teacher/activate-account")
def activate_teacher_account(token: str = Form(...), new_password: str = Form(...)):
    conn = get_db()
    teacher = conn.execute("SELECT * FROM teacher_activations WHERE activation_token = ?", (token.strip(),)).fetchone()
    if not teacher:
        conn.close()
        raise HTTPException(status_code=400, detail="الرابط غير صالح أو تم استخدامه مسبقاً")
    email = teacher["email"]
    name = teacher["teacher_name"] or email.split("@")[0]
    hashed_pw = hash_password(new_password.strip())
    conn.execute("UPDATE teacher_activations SET password_hash = ?, is_active = 1, activation_token = NULL WHERE id = ?", (hashed_pw, teacher["id"]))
    existing_inst = conn.execute("SELECT * FROM instructors WHERE username = ?", (email,)).fetchone()
    if existing_inst:
        conn.execute("UPDATE instructors SET name = ?, password_hash = ?, status = 'active' WHERE username = ?", (name, hashed_pw, email))
    else:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(instructors)").fetchall()]
        if "plan" in cols and "name" in cols:
            conn.execute("INSERT INTO instructors (name, username, password_hash, plan, status) VALUES (?, ?, ?, ?, ?)", (name, email, hashed_pw, "Standard", "active"))
        elif "name" in cols:
            conn.execute("INSERT INTO instructors (name, username, password_hash, status) VALUES (?, ?, ?, ?)", (name, email, hashed_pw, "active"))
        else:
            conn.execute("INSERT INTO instructors (username, password_hash, status) VALUES (?, ?, ?)", (email, hashed_pw, "active"))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "تم حفظ كلمة المرور وتأمين الحساب بنجاح"}

@router.post("/api/teacher/classes/create")
def create_class(request: Request, class_name: str = Form(...), subject: str = Form("")):
    teacher_id = get_teacher_id(request)
    conn = get_db()
    conn.execute("INSERT INTO classes (teacher_id, class_name, subject) VALUES (?, ?, ?)", (teacher_id, class_name.strip(), subject.strip()))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"تم إنشاء صف ({class_name}) بنجاح"}

@router.get("/api/teacher/classes")
def list_teacher_classes(request: Request):
    teacher_id = get_teacher_id(request)
    conn = get_db()
    rows = conn.execute("SELECT * FROM classes WHERE teacher_id = ? ORDER BY id DESC", (teacher_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.delete("/api/teacher/classes/{class_id}")
def delete_class(class_id: int):
    conn = get_db()
    conn.execute("DELETE FROM class_enrollments WHERE class_id = ?", (class_id,))
    conn.execute("DELETE FROM class_materials WHERE class_id = ?", (class_id,))
    conn.execute("DELETE FROM class_attendance WHERE class_id = ?", (class_id,))
    conn.execute("DELETE FROM classes WHERE id = ?", (class_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "تم حذف الصف وجميع بياناته"}

@router.post("/api/teacher/classes/{class_id}/add-student")
def add_student_to_class(class_id: int, student_code: str = Form(...), student_name: str = Form(...)):
    conn = get_db()
    email = student_code.strip().lower()
    if "@" not in email:
        conn.close()
        raise HTTPException(status_code=400, detail="يرجى إدخال بريد Gmail صحيح للطالب!")
    existing = conn.execute("SELECT access_pin FROM class_enrollments WHERE student_code = ?", (email,)).fetchone()
    pin = existing["access_pin"] if (existing and existing["access_pin"]) else str(secrets.randbelow(9000) + 1000)
    try:
        conn.execute("INSERT INTO class_enrollments (class_id, student_code, student_name, access_pin) VALUES (?, ?, ?, ?)", (class_id, email, student_name.strip(), pin))
        conn.commit()
        return {"status": "success", "message": f"تمت إضافة {student_name} | رمز الدخول السري (PIN): {pin}", "pin": pin}
    except Exception:
        raise HTTPException(status_code=400, detail="هذا البريد مسجل مسبقاً في هذا الصف!")
    finally:
        conn.close()

@router.post("/api/teacher/students/{enrollment_id}/update")
def update_student_in_class(enrollment_id: int, student_name: str = Form(...), student_code: str = Form(...)):
    conn = get_db()
    email = student_code.strip().lower()
    try:
        conn.execute("UPDATE class_enrollments SET student_name = ?, student_code = ? WHERE id = ?", (student_name.strip(), email, enrollment_id))
        conn.commit()
        return {"status": "success", "message": "تم تعديل بيانات الطالب بنجاح"}
    except Exception:
        raise HTTPException(status_code=400, detail="البريد مسجل مسبقاً في هذا الصف!")
    finally:
        conn.close()

@router.delete("/api/teacher/students/{enrollment_id}")
def delete_student_from_class(enrollment_id: int):
    conn = get_db()
    conn.execute("DELETE FROM class_enrollments WHERE id = ?", (enrollment_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "تم حذف الطالب من الصف"}

@router.get("/api/teacher/classes/{class_id}/students")
def get_class_students(class_id: int):
    conn = get_db()
    rows = conn.execute("SELECT * FROM class_enrollments WHERE class_id = ? ORDER BY student_name ASC", (class_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
@router.post("/api/teacher/classes/{class_id}/material")
def add_class_material(class_id: int, item_type: str = Form(...), title: str = Form(...), content: str = Form(...)):
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute("INSERT INTO class_materials (class_id, item_type, title, content, created_at) VALUES (?, ?, ?, ?, ?)", (class_id, item_type, title.strip(), content.strip(), today))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "تم نشر المحتوى لطلاب الصف بنجاح"}

@router.get("/api/teacher/classes/{class_id}/materials")
def get_class_materials(class_id: int):
    conn = get_db()
    rows = conn.execute("SELECT * FROM class_materials WHERE class_id = ? ORDER BY id DESC", (class_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.delete("/api/teacher/materials/{material_id}")
def delete_class_material(material_id: int):
    conn = get_db()
    conn.execute("DELETE FROM class_materials WHERE id = ?", (material_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "تم حذف المحتوى"}

@router.post("/api/teacher/classes/{class_id}/attendance")
def record_class_attendance(class_id: int, record_date: str = Form(...), student_code: str = Form(...), status: str = Form(...), late_minutes: int = Form(0), notes: str = Form(""), is_exam: bool = Form(False)):
    conn = get_db()
    conn.execute("INSERT INTO class_attendance (class_id, record_date, student_code, status, late_minutes, notes, is_exam) VALUES (?, ?, ?, ?, ?, ?, ?)", (class_id, record_date, student_code.strip().lower(), status, late_minutes if status == "late" else 0, notes, int(is_exam)))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "تم حفظ سجل اليوم في الرزنامة"}

@router.post("/api/teacher/classes/{class_id}/certificate")
def issue_class_certificate(class_id: int, student_code: str = Form(...), student_name: str = Form(...), cert_type: str = Form(...)):
    conn = get_db()
    serial = f"RA-2026-{secrets.token_hex(3).upper()}"
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute("INSERT INTO class_certificates (cert_serial, class_id, student_code, student_name, cert_type, issue_date) VALUES (?, ?, ?, ?, ?, ?)", (serial, class_id, student_code.strip().lower(), student_name.strip(), cert_type, today))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "تم إصدار الشهادة بنجاح", "cert_serial": serial}

@router.get("/student-portal")
def serve_student_portal():
    return FileResponse("student_portal.html")

@router.get("/api/student/{student_code}/classes")
def get_student_enrolled_classes(student_code: str, pin: str = ""):
    conn = get_db()
    rows = conn.execute("SELECT c.id, c.class_name, c.subject, e.student_name FROM classes c JOIN class_enrollments e ON c.id = e.class_id WHERE e.student_code = ? AND e.access_pin = ?", (student_code.strip().lower(), pin.strip())).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/api/student/{student_code}/class/{class_id}/details")
def get_student_class_details(student_code: str, class_id: int):
    email = student_code.strip().lower()
    conn = get_db()
    materials = [dict(r) for r in conn.execute("SELECT * FROM class_materials WHERE class_id = ? ORDER BY id DESC", (class_id,)).fetchall()]
    attendance = [dict(r) for r in conn.execute("SELECT * FROM class_attendance WHERE class_id = ? AND student_code = ? ORDER BY record_date DESC", (class_id, email)).fetchall()]
    certificates = [dict(r) for r in conn.execute("SELECT * FROM class_certificates WHERE class_id = ? AND student_code = ? ORDER BY id DESC", (class_id, email)).fetchall()]
    cls_info = conn.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
    conn.close()
    return {"class_info": dict(cls_info) if cls_info else {}, "materials": materials, "attendance": attendance, "certificates": certificates}

@router.get("/verify")
def serve_verify_page():
    return FileResponse("verify.html")

@router.get("/api/verify-certificate/{cert_serial}")
def verify_classroom_cert(cert_serial: str):
    conn = get_db()
    cert = conn.execute("SELECT cert.*, c.class_name, c.subject FROM class_certificates cert LEFT JOIN classes c ON cert.class_id = c.id WHERE cert.cert_serial = ?", (cert_serial.strip().upper(),)).fetchone()
    conn.close()
    if not cert:
        raise HTTPException(status_code=404, detail="الشهادة غير صالحة أو غير مسجلة")
    course_display = f"{cert['class_name']} - {cert['subject']}" if cert['subject'] else cert['class_name']
    return {"valid": True, "cert_serial": cert["cert_serial"], "student_id": f"{cert['student_name']} ({cert['student_code']})", "course_name": course_display, "cert_type": cert["cert_type"], "issue_date": cert["issue_date"]}
