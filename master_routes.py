from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database import get_db, init_db, hash_password
from auth import is_master

router = APIRouter()
templates = Jinja2Templates(directory=".")

@router.get("/master", response_class=HTMLResponse)
def master_dashboard(request: Request):
    if not is_master(request):
        return RedirectResponse(url="/master-login", status_code=303)
        
    init_db()
    conn = get_db()
    instructors = conn.execute("SELECT * FROM instructors ORDER BY id DESC").fetchall()
    total_students = conn.execute("SELECT COUNT(*) as c FROM students").fetchone()["c"]
    total_lessons = conn.execute("SELECT COUNT(*) as c FROM lessons").fetchone()["c"]
    total_certs = conn.execute("SELECT COUNT(*) as c FROM quiz_results").fetchone()["c"]
    conn.close()
    
    # حساب الإيرادات التقديرية بناءً على الباقات النشطة
    monthly_revenue = 0
    for inst in instructors:
        if inst["status"] == "active" and "الشهرية" in inst["plan"]:
            monthly_revenue += 150
            
    return templates.TemplateResponse(
        request=request,
        name="master_dashboard.html",
        context={
            "instructors": instructors,
            "total_students": total_students,
            "total_lessons": total_lessons,
            "total_certs": total_certs,
            "monthly_revenue": monthly_revenue
        }
    )

@router.post("/master/add-instructor")
def add_instructor(
    request: Request,
    center_name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    plan: str = Form(...)
):
    if not is_master(request):
        return RedirectResponse(url="/master-login", status_code=303)
        
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO instructors (center_name, username, password_hash, plan) VALUES (?, ?, ?, ?)",
            (center_name.strip(), username.strip(), hash_password(password.strip()), plan)
        )
        conn.commit()
    except Exception:
        conn.close()
        return HTMLResponse("<h3>اسم المستخدم موجود مسبقًا! اختر اسمًا آخر. <a href='/master'>رجوع</a></h3>")
    conn.close()
    return RedirectResponse(url="/master", status_code=303)

@router.post("/master/toggle-status/{instructor_id}")
def toggle_instructor_status(request: Request, instructor_id: int):
    if not is_master(request):
        return RedirectResponse(url="/master-login", status_code=303)
    conn = get_db()
    inst = conn.execute("SELECT status FROM instructors WHERE id = ?", (instructor_id,)).fetchone()
    if inst:
        new_status = "suspended" if inst["status"] == "active" else "active"
        conn.execute("UPDATE instructors SET status = ? WHERE id = ?", (new_status, instructor_id))
        conn.commit()
    conn.close()
    return RedirectResponse(url="/master", status_code=303)

@router.post("/master/delete-instructor/{instructor_id}")
def delete_instructor(request: Request, instructor_id: int):
    if not is_master(request):
        return RedirectResponse(url="/master-login", status_code=303)
    if instructor_id == 1:
        return HTMLResponse("<h3>لا يمكن حذف حساب التجربة الافتراضي! <a href='/master'>رجوع</a></h3>")
    conn = get_db()
    conn.execute("DELETE FROM instructors WHERE id = ?", (instructor_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/master", status_code=303)
