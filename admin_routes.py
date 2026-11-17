import random
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database import get_db, init_db
from auth import get_current_instructor_id

router = APIRouter()
templates = Jinja2Templates(directory=".")

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    inst_id = get_current_instructor_id(request)
    if not inst_id:
        return RedirectResponse(url="/portal", status_code=303)
        
    init_db()
    conn = get_db()
    instructor = conn.execute("SELECT * FROM instructors WHERE id = ?", (inst_id,)).fetchone()
    students = conn.execute("SELECT * FROM students WHERE instructor_id = ? ORDER BY id DESC", (inst_id,)).fetchall()
    lessons = conn.execute("SELECT * FROM lessons WHERE instructor_id = ? ORDER BY id DESC", (inst_id,)).fetchall()
    quizzes = conn.execute("SELECT * FROM quizzes WHERE instructor_id = ? ORDER BY id DESC", (inst_id,)).fetchall()
    results = conn.execute("SELECT * FROM quiz_results WHERE instructor_id = ? ORDER BY id DESC", (inst_id,)).fetchall()
    conn.close()
    
    return templates.TemplateResponse(
        request=request, 
        name="dashboard.html", 
        context={
            "instructor": instructor,
            "students": students, 
            "lessons": lessons, 
            "quizzes": quizzes, 
            "results": results
        }
    )

@router.post("/add-student")
def add_student(request: Request, name: str = Form(...), email: str = Form(...), course: str = Form(...)):
    inst_id = get_current_instructor_id(request)
    if not inst_id:
        return RedirectResponse(url="/portal", status_code=303)
    access_code = str(random.randint(1000, 9999))
    conn = get_db()
    conn.execute(
        "INSERT INTO students (instructor_id, name, email, course, access_code) VALUES (?, ?, ?, ?, ?)",
        (inst_id, name.strip(), email.strip(), course.strip(), access_code)
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/edit-student/{student_id}")
def edit_student(request: Request, student_id: int, name: str = Form(...), email: str = Form(...), course: str = Form(...)):
    inst_id = get_current_instructor_id(request)
    if not inst_id:
        return RedirectResponse(url="/portal", status_code=303)
    conn = get_db()
    conn.execute(
        "UPDATE students SET name = ?, email = ?, course = ? WHERE id = ? AND instructor_id = ?",
        (name.strip(), email.strip(), course.strip(), student_id, inst_id)
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/delete-student/{student_id}")
def delete_student(request: Request, student_id: int):
    inst_id = get_current_instructor_id(request)
    if not inst_id:
        return RedirectResponse(url="/portal", status_code=303)
    conn = get_db()
    conn.execute("DELETE FROM students WHERE id = ? AND instructor_id = ?", (student_id, inst_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/add-lesson")
def add_lesson(
    request: Request,
    title: str = Form(...),
    course: str = Form(...),
    video_url: str = Form(""),
    description: str = Form("")
):
    inst_id = get_current_instructor_id(request)
    if not inst_id:
        return RedirectResponse(url="/portal", status_code=303)
    conn = get_db()
    conn.execute(
        "INSERT INTO lessons (instructor_id, title, course, video_url, description) VALUES (?, ?, ?, ?, ?)",
        (inst_id, title.strip(), course.strip(), video_url.strip(), description.strip())
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/delete-lesson/{lesson_id}")
def delete_lesson(request: Request, lesson_id: int):
    inst_id = get_current_instructor_id(request)
    if not inst_id:
        return RedirectResponse(url="/portal", status_code=303)
    conn = get_db()
    conn.execute("DELETE FROM lessons WHERE id = ? AND instructor_id = ?", (lesson_id, inst_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/rename-course")
def rename_course(request: Request, old_course: str = Form(...), new_course: str = Form(...)):
    inst_id = get_current_instructor_id(request)
    if not inst_id:
        return RedirectResponse(url="/portal", status_code=303)
    old_c, new_c = old_course.strip(), new_course.strip()
    conn = get_db()
    conn.execute("UPDATE students SET course = ? WHERE course = ? AND instructor_id = ?", (new_c, old_c, inst_id))
    conn.execute("UPDATE lessons SET course = ? WHERE course = ? AND instructor_id = ?", (new_c, old_c, inst_id))
    conn.execute("UPDATE quizzes SET course = ? WHERE course = ? AND instructor_id = ?", (new_c, old_c, inst_id))
    conn.execute("UPDATE quiz_results SET course = ? WHERE course = ? AND instructor_id = ?", (new_c, old_c, inst_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/add-bulk-quiz")
async def add_bulk_quiz(request: Request):
    inst_id = get_current_instructor_id(request)
    if not inst_id:
        return RedirectResponse(url="/portal", status_code=303)
    
    form_data = await request.form()
    course = form_data.get("course", "").strip()
    questions = form_data.getlist("question")
    opt1s = form_data.getlist("opt1")
    opt2s = form_data.getlist("opt2")
    opt3s = form_data.getlist("opt3")
    correct_opts = form_data.getlist("correct_opt")
    
    conn = get_db()
    for q, o1, o2, o3, corr in zip(questions, opt1s, opt2s, opt3s, correct_opts):
        if q.strip():
            conn.execute(
                "INSERT INTO quizzes (instructor_id, course, question, opt1, opt2, opt3, correct_opt) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (inst_id, course, q.strip(), o1.strip(), o2.strip(), o3.strip(), corr)
            )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/delete-quiz/{quiz_id}")
def delete_quiz(request: Request, quiz_id: int):
    inst_id = get_current_instructor_id(request)
    if not inst_id:
        return RedirectResponse(url="/portal", status_code=303)
    conn = get_db()
    conn.execute("DELETE FROM quizzes WHERE id = ? AND instructor_id = ?", (quiz_id, inst_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/delete-result/{result_id}")
def delete_result(request: Request, result_id: int):
    inst_id = get_current_instructor_id(request)
    if not inst_id:
        return RedirectResponse(url="/portal", status_code=303)
    conn = get_db()
    conn.execute("DELETE FROM quiz_results WHERE id = ? AND instructor_id = ?", (result_id, inst_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/dashboard", status_code=303)
