# DASHBOARD_BACKEND/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.applications import Starlette
from starlette.routing import Mount
import uvicorn
import os

# Import the standalone QC API application instance
from qc_api import qc_router # Import the APIRouter object
# Import the Dashboard routes APIRouter
from app.dashboard_routes import dashboard_router 

# --- CONFIGURATIONS ---

# The master app doesn't need the lifespan context since qc_app handles it.
master_app = FastAPI(
    title="Master Data Processing & Dashboard API",
    version="2.0.0"
)

# 1. CORS Middleware (Applied to the master app)
origins = [
    "http://localhost:3000",                 
    "https://pm-aqt9.vercel.app",    
    "https://pm-aqt9-l1fdp88vu-bharath-raj-g-sources-projects.vercel.app", 
    "https://pm-aqt9-9dcu9ev9t-bharath-raj-g-sources-projects.vercel.app/",
    "https://pm-aqt9-lkr4v0ctz-bharath-raj-g-sources-projects.vercel.app/",
            
    # You can also add the pattern for all vercel subdomains if your deployment URL changes often:
    # "https://*.vercel.app", 
]
master_app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    # --- CHANGE MADE HERE: Explicitly list all methods, including OPTIONS ---
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"], 
    allow_headers=["*"],
)

# --- ROUTING/MOUNTING ---
    
# 1. Mount the QC API as a sub-application (Example path: /qc/api/run_qc)
# If you prefer the old path structure, you might need to adjust prefixes in qc_api.py
# master_app.mount("/qc", qc_app) # Option 1: Mount with a prefix
master_app.include_router(qc_router, prefix="/api/qc" , tags=["QC Automation"])

# 2. Include the Dashboard Router (Example path: /api/dashboard/projects)
master_app.include_router(dashboard_router, prefix="/api") 


# --- SERVER ---
PORT = int(os.getenv("PORT", 8000))

if __name__ == "__main__":
    # The Uvicorn server runs the master application
    uvicorn.run(master_app, host="0.0.0.0", port=PORT)