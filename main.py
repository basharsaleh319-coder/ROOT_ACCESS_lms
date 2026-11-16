from fastapi import FastAPI
from database import init_db
import auth
import admin_routes
import student_routes

app = FastAPI(title="ROOT ACCESS LMS")

# تهيئة قاعدة البيانات عند التشغيل
init_db()

# ربط الأقسام الثلاثة بالتطبيق الرئيسي
app.include_router(auth.router)
app.include_router(admin_routes.router)
app.include_router(student_routes.router)
