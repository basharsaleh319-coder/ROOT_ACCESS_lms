import random
from datetime import date
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory=".")

@router.post("/student-login", response_class=HTMLResponse)
def student_login_action(request: Request, email: str = Form(...), access_code: str = Form(...)):
    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE email = ? AND access_code = ?",
        (email.strip(), access_code.strip())
    ).fetchone()
    
    if not student:
        conn.close()
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"error": "البريد الإلكتروني أو رمز الدخول (PIN) غير صحيح!", "active_tab": "student"}
        )
    
    inst_id = student["instructor_id"]
    lessons = conn.execute("SELECT * FROM lessons WHERE course = ? AND instructor_id = ?", (student["course"], inst_id)).fetchall()
    quizzes = conn.execute("SELECT * FROM quizzes WHERE course = ? AND instructor_id = ?", (student["course"], inst_id)).fetchall()
    conn.close()
    
    return templates.TemplateResponse(
        request=request, 
        name="student_portal.html", 
        context={"student": student, "lessons": lessons, "has_quiz": len(quizzes) > 0}
    )


@router.post("/student-exam", response_class=HTMLResponse)
def student_exam_page(request: Request, email: str = Form(...), access_code: str = Form(...)):
    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE email = ? AND access_code = ?",
        (email.strip(), access_code.strip())
    ).fetchone()
    if not student:
        conn.close()
        return RedirectResponse(url="/portal", status_code=303)
        
    quizzes = conn.execute(
        "SELECT * FROM quizzes WHERE course = ? AND instructor_id = ?",
        (student["course"], student["instructor_id"])
    ).fetchall()
    conn.close()
    
    return templates.TemplateResponse(
        request=request, 
        name="student_exam.html", 
        context={"student": student, "quizzes": quizzes, "score": None, "cert_id": None}
    )

@router.post("/submit-quiz", response_class=HTMLResponse)
async def submit_quiz(request: Request):
    form_data = await request.form()
    email = form_data.get("email")
    access_code = form_data.get("access_code")
    
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE email = ? AND access_code = ?", (email, access_code)).fetchone()
    inst_id = student["instructor_id"]
    quizzes = conn.execute("SELECT * FROM quizzes WHERE course = ? AND instructor_id = ?", (student["course"], inst_id)).fetchall()
    
    score = 0
    total = len(quizzes)
    for q in quizzes:
        user_ans = str(form_data.get(f"q_{q['id']}", "")).strip()
        corr_ans = str(q["correct_opt"]).strip()
        if user_ans and (user_ans == corr_ans or f"opt{user_ans}" == corr_ans):
            score += 1

            
    cert_id = f"RA-{random.randint(100000, 999999)}"
    conn.execute(
        "INSERT INTO quiz_results (instructor_id, student_name, course, score, total, cert_id) VALUES (?, ?, ?, ?, ?, ?)",
        (inst_id, student["name"], student["course"], score, total, cert_id)
    )
    conn.commit()
    conn.close()
    
    return templates.TemplateResponse(
        request=request, 
        name="student_exam.html", 
        context={"student": student, "quizzes": quizzes, "score": score, "total": total, "cert_id": cert_id}
    )

@router.get("/certificate/{cert_id}", response_class=HTMLResponse)
def view_certificate(request: Request, cert_id: str):
    conn = get_db()
    record = conn.execute("""
        SELECT quiz_results.*, instructors.center_name 
        FROM quiz_results 
        LEFT JOIN instructors ON quiz_results.instructor_id = instructors.id 
        WHERE cert_id = ?
    """, (cert_id,)).fetchone()
    conn.close()
    
    if not record:
        return HTMLResponse("<h3>رقم الشهادة غير صالح.</h3>")
        
    return templates.TemplateResponse(
        request=request, 
        name="certificate.html", 
        context={"record": record, "issue_date": date.today().strftime("%Y-%m-%d")}
    )

# صفحة التحقق العامة من الشهادات
@router.get("/verify", response_class=HTMLResponse)
def verify_page(request: Request):
    return templates.TemplateResponse(request=request, name="verify.html", context={"record": None, "searched": False})

@router.post("/verify", response_class=HTMLResponse)
def verify_action(request: Request, cert_id: str = Form(...)):
    conn = get_db()
    record = conn.execute("""
        SELECT quiz_results.*, instructors.center_name 
        FROM quiz_results 
        LEFT JOIN instructors ON quiz_results.instructor_id = instructors.id 
        WHERE cert_id = ?
    """, (cert_id.strip().upper(),)).fetchone()
    conn.close()
    
    return templates.TemplateResponse(request=request, name="verify.html", context={"record": record, "searched": True})
