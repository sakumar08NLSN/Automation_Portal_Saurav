# DASHBOARD_BACKEND/app/routes/project_routes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# --- Pydantic Models ---

class ProjectBase(BaseModel):
    """Schema for data sent to create a new project (POST body)."""
    name: str
    description: str
    # Use Field(alias=...) to map snake_case (Python) to camelCase (JSON/JS)
    start_date: str = Field(alias="startDate")
    end_date: Optional[str] = Field(None, alias="endDate")

    class Config:
        # Crucial for allowing both field names in the Pydantic model
        populate_by_name = True

class Project(ProjectBase):
    """Full schema for a project object returned by the API."""
    id: int
    # You can add fields like status/progress later if needed
    # status: str = "To Do" 
    # progress: int = 0

# --- STATIC DATA (Complete and Syntactically Valid) ---

# This list now contains all 10 projects from your Node.js controller data.
DUMMY_PROJECTS: List[Project] = [
    Project.model_validate({ # Project ID 1
        "id": 1,
        "name": "Formula 1",
        "description": "A space exploration project.",
        "startDate": "2023-01-01T00:00:00Z",
        "endDate": "2023-12-31T00:00:00Z"
    }),
    Project.model_validate({ # Project ID 3
        "id": 3,
        "name": "Cricket",
        "description": "A project to boost renewable energy use.",
        "startDate": "2023-03-05T00:00:00Z",
        "endDate": "2024-03-05T00:00:00Z"
    }),
    Project.model_validate({ # Project ID 4
        "id": 4,
        "name": "Tennis",
        "description": "Tennis project for new software development techniques.",
        "startDate": "2023-01-20T00:00:00Z",
        "endDate": "2023-09-20T00:00:00Z"
    }),
    Project.model_validate({ # Project ID 5
        "id": 5, 
        "name": "Echo", 
        "description": "Echo project focused on AI advancements.", 
        "startDate": "2023-04-15T00:00:00Z", 
        "endDate": "2023-11-30T00:00:00Z" 
    }),
    Project.model_validate({ # Project ID 6
        "id": 6, 
        "name": "Foot Ball", 
        "description": "Exploring cutting-edge biotechnology.", 
        "startDate": "2023-02-25T00:00:00Z", 
        "endDate": "2023-08-25T00:00:00Z" 
    }),
    Project.model_validate({ # Project ID 7
        "id": 7, 
        "name": "Golf", 
        "description": "Development of new golf equipment using AI.", 
        "startDate": "2023-05-10T00:00:00Z", 
        "endDate": "2023-12-10T00:00:00Z" 
    }),
    Project.model_validate({ # Project ID 8
        "id": 8, 
        "name": "Hockey", 
        "description": "Hockey management system overhaul.", 
        "startDate": "2023-03-01T00:00:00Z", 
        "endDate": "2024-01-01T00:00:00Z" 
    }),
    Project.model_validate({ # Project ID 9
        "id": 9, 
        "name": "India", 
        "description": "Telecommunication infrastructure upgrade.", 
        "startDate": "2023-06-01T00:00:00Z", 
        "endDate": "2023-12-01T00:00:00Z" 
    }),
    Project.model_validate({ # Project ID 10
        "id": 10,
        "name": "Judo",
        "description": "Initiative to enhance cyber-security measures.",
        "startDate": "2023-07-01T00:00:00Z",
        "endDate": "2024-02-01T00:00:00Z"
    })
]

# Initialize the ID counter based on the existing data
current_max_project_id = max(p.id for p in DUMMY_PROJECTS) if DUMMY_PROJECTS else 0

# --- APIRouter (The entry point for this set of routes) ---

router = APIRouter()

# --- Controller Functions ---

# GET /projects (Equivalent to router.get("/", getProjects))
@router.get("/", response_model=List[Project])
async def get_projects():
    """
    Mocks Project.findMany() and returns the list of all static projects.
    """
    try:
        return DUMMY_PROJECTS
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving projects: {e}"
        )

# POST /projects (Equivalent to router.post("/", createProject))
@router.post("/", response_model=Project, status_code=201)
async def create_project(project_data: ProjectBase):
    """
    Mocks Project.create() and creates a new project.
    """
    global current_max_project_id

    try:
        current_max_project_id += 1 

        # Create the new project object
        new_project = Project(
            id=current_max_project_id,
            name=project_data.name,
            description=project_data.description,
            start_date=project_data.start_date,
            end_date=project_data.end_date,
        )

        # Simulate saving (add to array)
        DUMMY_PROJECTS.append(new_project)

        # Return the newly created object with a 201 status
        return new_project
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating a project: {e}"
        )