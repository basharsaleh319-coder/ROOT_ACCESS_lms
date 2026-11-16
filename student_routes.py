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
        return HTMLResponse("<h3>البريد الإلكتروني أو رمز الدخول غير صحيح! <a href='/'>حاول مرة أخرى</a></h3>")
    
    lessons = conn.execute("SELECT * FROM lessons WHERE course = ?", (student["course"],)).fetchall()
    quizzes = conn.execute("SELECT * FROM quizzes WHERE course = ?", (student["course"],)).fetchall()
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
        return RedirectResponse(url="/", status_code=303)
        
    quizzes = conn.execute("SELECT * FROM quizzes WHERE course = ?", (student["course"],)).fetchall()
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
    quizzes = conn.execute("SELECT * FROM quizzes WHERE course = ?", (student["course"],)).fetchall()
    
    score = 0
    total = len(quizzes)
    for q in quizzes:
        if form_data.get(f"q_{q['id']}") == q["correct_opt"]:
            score += 1
            
    cert_id = f"RA-{random.randint(100000, 999999)}"
    conn.execute(
        "INSERT INTO quiz_results (student_name, course, score, total, cert_id) VALUES (?, ?, ?, ?, ?)",
        (student["name"], student["course"], score, total, cert_id)
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
    record = conn.execute("SELECT * FROM quiz_results WHERE cert_id = ?", (cert_id,)).fetchone()
    conn.close()
    if not record:
        return HTMLResponse("<h3>رقم الشهادة غير صالح.</h3>")
        
    return templates.TemplateResponse(
        request=request, 
        name="certificate.html", 
        context={"record": record, "issue_date": date.today().strftime("%Y-%m-%d")}
    )
