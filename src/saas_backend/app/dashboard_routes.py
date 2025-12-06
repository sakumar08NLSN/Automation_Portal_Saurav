# DASHBOARD_BACKEND/app/dashboard_routes.py

from fastapi import APIRouter
import os

# Import your existing route files
from app.routes import project_routes
from app.routes import task_routes
from app.routes import search_routes
from app.routes import user_routes
from app.routes import team_routes
from app.routes import upload_routes

# Create the master router for the dashboard endpoints
dashboard_router = APIRouter(prefix="/dashboard") # Optional: Add a common prefix if needed

# --- ROUTES ---

@dashboard_router.get("/", tags=["Home"]) 
async def home_route():
    return {"message": "Welcome to the Dashboard API home route."}

# Include your existing specific routers
dashboard_router.include_router(project_routes.router, prefix="/projects", tags=["Projects"])
dashboard_router.include_router(task_routes.router, prefix="/tasks", tags=["Tasks"])
dashboard_router.include_router(search_routes.router, prefix="/search", tags=["Search"])
dashboard_router.include_router(user_routes.router, prefix="/users", tags=["Users"])
dashboard_router.include_router(team_routes.router, prefix="/teams", tags=["Teams"])
# 💡 NEW ROUTE: Include the generic upload router (for /api/dashboard/upload/data)
dashboard_router.include_router(upload_routes.router, prefix="/upload", tags=["Upload"])