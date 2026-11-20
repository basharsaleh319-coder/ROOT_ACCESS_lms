from fastapi import FastAPI
from database import init_db
import auth
import master_routes
import admin_routes
import student_routes
import lms_features

app = FastAPI(title="ROOT ACCESS MASTER LMS")

init_db()

app.include_router(auth.router)
app.include_router(master_routes.router)
app.include_router(admin_routes.router)
app.include_router(student_routes.router)
app.include_router(lms_features.router)
