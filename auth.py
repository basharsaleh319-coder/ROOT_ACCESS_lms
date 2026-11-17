from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database import get_db, hash_password

router = APIRouter()
templates = Jinja2Templates(directory=".")

# بيانات دخول مالك المنصة (Super Admin)
MASTER_USERNAME = "superadmin"
MASTER_PASSWORD_HASH = hash_password("Master@2026")
MASTER_SESSION_TOKEN = "ra_master_owner_secret_2026"

def is_master(request: Request) -> bool:
    return request.cookies.get("master_session") == MASTER_SESSION_TOKEN

def get_current_instructor_id(request: Request):
    val = request.cookies.get("instructor_id")
    return int(val) if val and val.isdigit() else None

# 1. الصفحة الرئيسية التسويقية
@router.get("/", response_class=HTMLResponse)
def landing_page(request: Request):
    return templates.TemplateResponse(request=request, name="landing.html")

# 2. بوابة دخول المدربين والطلاب
@router.get("/portal", response_class=HTMLResponse)
def login_page(request: Request):
    if get_current_instructor_id(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None, "active_tab": "student"})

@router.post("/login", response_class=HTMLResponse)
def instructor_login_action(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = get_db()
    instructor = conn.execute(
        "SELECT * FROM instructors WHERE username = ? AND password_hash = ?",
        (username.strip(), hash_password(password.strip()))
    ).fetchone()
    conn.close()
    
    if not instructor:
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"error": "اسم المستخدم أو كلمة المرور غير صحيحة!", "active_tab": "teacher"}
        )
    if instructor["status"] != "active":
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"error": "تم إيقاف هذا الحساب مؤقتًا. تواصل مع الإدارة.", "active_tab": "teacher"}
        )
        
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="instructor_id", value=str(instructor["id"]), httponly=True)
    return response


@router.get("/logout")
def logout_action():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("instructor_id")
    response.delete_cookie("master_session")
    return response

# 3. بوابة دخول المالك السرية (ROOT ACCESS MASTER)
@router.get("/master-login", response_class=HTMLResponse)
def master_login_page(request: Request):
    if is_master(request):
        return RedirectResponse(url="/master", status_code=303)
    return templates.TemplateResponse(request=request, name="master_login.html")

@router.post("/master-login")
def master_login_action(username: str = Form(...), password: str = Form(...)):
    if username.strip() == MASTER_USERNAME and hash_password(password.strip()) == MASTER_PASSWORD_HASH:
        response = RedirectResponse(url="/master", status_code=303)
        response.set_cookie(key="master_session", value=MASTER_SESSION_TOKEN, httponly=True)
        return response
    return HTMLResponse("<h3>بيانات المالك غير صحيحة! <a href='/master-login'>حاول مرة أخرى</a></h3>")

# 4. صفحة سياسة الخصوصية وشروط الاستخدام
@router.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    return templates.TemplateResponse(request=request, name="privacy.html")
