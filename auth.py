from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"
ADMIN_SESSION_TOKEN = "root_access_secure_token_2026"

def is_admin(request: Request) -> bool:
    return request.cookies.get("admin_session") == ADMIN_SESSION_TOKEN

# 1. الصفحة الرئيسية التسويقية (Landing Page)
@router.get("/", response_class=HTMLResponse)
def landing_page(request: Request):
    return templates.TemplateResponse(request=request, name="landing.html")

# 2. بوابة تسجيل الدخول الموحدة (طالب / معلم)
@router.get("/portal", response_class=HTMLResponse)
def login_page(request: Request):
    if is_admin(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html")

@router.post("/login")
def login_action(username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="admin_session", value=ADMIN_SESSION_TOKEN, httponly=True)
        return response
    return HTMLResponse("<h3>بيانات الدخول غير صحيحة! <a href='/portal'>حاول مرة أخرى</a></h3>")

@router.get("/logout")
def logout_action():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("admin_session")
    return response
