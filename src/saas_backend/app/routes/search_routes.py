# DASHBOARD_BACKEND/app/routes/search_routes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

# --- Pydantic Models for Search Results ---

class Task(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    tags: str
    start_date: str = Field(alias="startDate")
    due_date: str = Field(alias="dueDate")
    project_id: int = Field(alias="projectId")
    author_user_id: int = Field(alias="authorUserId")
    assigned_user_id: int = Field(alias="assignedUserId")

    class Config:
        populate_by_name = True
        
class Project(BaseModel):
    id: int
    name: str
    description: str
    start_date: str = Field(alias="startDate")
    end_date: Optional[str] = Field(None, alias="endDate")
    
    class Config:
        populate_by_name = True

class User(BaseModel):
    user_id: int = Field(alias="userId")
    cognito_id: str = Field(alias="cognitoId")
    username: str
    profile_picture_url: str = Field(alias="profilePictureUrl")
    team_id: int = Field(alias="teamId")
    
    class Config:
        populate_by_name = True

class SearchResults(BaseModel):
    tasks: List[Task]
    projects: List[Project]
    users: List[User]

# --- STATIC DATA (Complete and Syntactically Valid) ---

# Replicating the full 40-task dataset
DUMMY_TASKS: List[Task] = [
    Task.model_validate({"id": 1, "title": "Task 1", "description": "Design the main module.", "status": "Work In Progress", "priority": "Urgent", "tags": "Design", "startDate": "2023-01-10T00:00:00Z", "dueDate": "2023-04-10T00:00:00Z", "projectId": 1, "authorUserId": 1, "assignedUserId": 2}),
    Task.model_validate({"id": 2, "title": "Task 2", "description": "Implement the navigation algorithm.", "status": "To Do", "priority": "High", "tags": "Coding", "startDate": "2023-01-15T00:00:00Z", "dueDate": "2023-05-15T00:00:00Z", "projectId": 2, "authorUserId": 3, "assignedUserId": 4}),
    Task.model_validate({"id": 3, "title": "Task 3", "description": "Develop renewable energy solutions.", "status": "Work In Progress", "priority": "Urgent", "tags": "Development", "startDate": "2023-03-20T00:00:00Z", "dueDate": "2023-09-20T00:00:00Z", "projectId": 3, "authorUserId": 5, "assignedUserId": 6}),
    Task.model_validate({"id": 4, "title": "Task 4", "description": "Outline new software development workflows.", "status": "To Do", "priority": "High", "tags": "Planning", "startDate": "2023-01-25T00:00:00Z", "dueDate": "2023-06-25T00:00:00Z", "projectId": 4, "authorUserId": 7, "assignedUserId": 8}),
    Task.model_validate({"id": 5, "title": "Task 5", "description": "Research AI models for prediction.", "status": "Work In Progress", "priority": "Urgent", "tags": "Research", "startDate": "2023-04-20T00:00:00Z", "dueDate": "2023-10-20T00:00:00Z", "projectId": 5, "authorUserId": 9, "assignedUserId": 10}),
    Task.model_validate({"id": 6, "title": "Task 6", "description": "Biotech product testing.", "status": "To Do", "priority": "Backlog", "tags": "Testing", "startDate": "2023-03-01T00:00:00Z", "dueDate": "2023-08-01T00:00:00Z", "projectId": 6, "authorUserId": 11, "assignedUserId": 12}),
    Task.model_validate({"id": 7, "title": "Task 7", "description": "AI optimization for golf equipment.", "status": "Work In Progress", "priority": "Urgent", "tags": "Optimization", "startDate": "2023-05-15T00:00:00Z", "dueDate": "2023-11-15T00:00:00Z", "projectId": 7, "authorUserId": 13, "assignedUserId": 14}),
    Task.model_validate({"id": 8, "title": "Task 8", "description": "Overhaul of the database for Hockey management.", "status": "To Do", "priority": "High", "tags": "Database", "startDate": "2023-04-01T00:00:00Z", "dueDate": "2023-10-01T00:00:00Z", "projectId": 8, "authorUserId": 15, "assignedUserId": 16}),
    Task.model_validate({"id": 9, "title": "Task 9", "description": "Upgrade telecom infrastructure.", "status": "Work In Progress", "priority": "Urgent", "tags": "Infrastructure", "startDate": "2023-06-10T00:00:00Z", "dueDate": "2023-12-10T00:00:00Z", "projectId": 9, "authorUserId": 17, "assignedUserId": 18}),
    Task.model_validate({"id": 10, "title": "Task 10", "description": "Enhance security protocols.", "status": "To Do", "priority": "Urgent", "tags": "Security", "startDate": "2023-07-05T00:00:00Z", "dueDate": "2024-01-05T00:00:00Z", "projectId": 10, "authorUserId": 19, "assignedUserId": 20}),
    Task.model_validate({"id": 11, "title": "Task 11", "description": "Finalize AI training parameters.", "status": "Work In Progress", "priority": "Urgent", "tags": "AI, Training", "startDate": "2023-01-20T00:00:00Z", "dueDate": "2023-05-20T00:00:00Z", "projectId": 5, "authorUserId": 1, "assignedUserId": 3}),
    Task.model_validate({"id": 12, "title": "Task 12", "description": "Update server security protocols.", "status": "To Do", "priority": "High", "tags": "Security", "startDate": "2023-02-10T00:00:00Z", "dueDate": "2023-06-10T00:00:00Z", "projectId": 1, "authorUserId": 2, "assignedUserId": 4}),
    Task.model_validate({"id": 13, "title": "Task 13", "description": "Redesign user interface for better UX.", "status": "Work In Progress", "priority": "Urgent", "tags": "Design, UX", "startDate": "2023-03-15T00:00:00Z", "dueDate": "2023-07-15T00:00:00Z", "projectId": 2, "authorUserId": 5, "assignedUserId": 6}),
    Task.model_validate({"id": 14, "title": "Task 14", "description": "Implement real-time data analytics.", "status": "To Do", "priority": "High", "tags": "Analytics", "startDate": "2023-04-05T00:00:00Z", "dueDate": "2023-08-05T00:00:00Z", "projectId": 3, "authorUserId": 7, "assignedUserId": 8}),
    Task.model_validate({"id": 15, "title": "Task 15", "description": "Develop end-to-end encryption solution.", "status": "Work In Progress", "priority": "Urgent", "tags": "Encryption", "startDate": "2023-05-01T00:00:00Z", "dueDate": "2023-09-01T00:00:00Z", "projectId": 4, "authorUserId": 9, "assignedUserId": 10}),
    Task.model_validate({"id": 16, "title": "Task 16", "description": "Optimize cloud storage usage.", "status": "To Do", "priority": "Backlog", "tags": "Cloud, Storage", "startDate": "2023-06-15T00:00:00Z", "dueDate": "2023-10-15T00:00:00Z", "projectId": 5, "authorUserId": 11, "assignedUserId": 12}),
    Task.model_validate({"id": 17, "title": "Task 17", "description": "Test software for hardware compatibility.", "status": "Work In Progress", "priority": "Urgent", "tags": "Testing, Hardware", "startDate": "2023-07-10T00:00:00Z", "dueDate": "2023-11-10T00:00:00Z", "projectId": 6, "authorUserId": 13, "assignedUserId": 14}),
    Task.model_validate({"id": 18, "title": "Task 18", "description": "Create new data visualization tools.", "status": "To Do", "priority": "High", "tags": "Visualization", "startDate": "2023-08-05T00:00:00Z", "dueDate": "2023-12-05T00:00:00Z", "projectId": 7, "authorUserId": 15, "assignedUserId": 16}),
    Task.model_validate({"id": 19, "title": "Task 19", "description": "Build prototype for new IoT devices.", "status": "Work In Progress", "priority": "Urgent", "tags": "IoT", "startDate": "2023-09-01T00:00:00Z", "dueDate": "2024-01-01T00:00:00Z", "projectId": 8, "authorUserId": 17, "assignedUserId": 18}),
    Task.model_validate({"id": 20, "title": "Task 20", "description": "Update legacy systems to new tech standards.", "status": "To Do", "priority": "Urgent", "tags": "Legacy, Upgrade", "startDate": "2023-10-10T00:00:00Z", "dueDate": "2024-02-10T00:00:00Z", "projectId": 9, "authorUserId": 19, "assignedUserId": 20}),
    Task.model_validate({"id": 21, "title": "Task 21", "description": "Establish new network security framework.", "status": "Work In Progress", "priority": "Urgent", "tags": "Security", "startDate": "2023-01-30T00:00:00Z", "dueDate": "2023-05-30T00:00:00Z", "projectId": 10, "authorUserId": 1, "assignedUserId": 3}),
    Task.model_validate({"id": 22, "title": "Task 22", "description": "Revise application deployment strategies.", "status": "To Do", "priority": "High", "tags": "Deployment", "startDate": "2023-02-20T00:00:00Z", "dueDate": "2023-06-20T00:00:00Z", "projectId": 1, "authorUserId": 2, "assignedUserId": 4}),
    Task.model_validate({"id": 23, "title": "Task 23", "description": "Conduct market analysis for product fit.", "status": "Work In Progress", "priority": "Urgent", "tags": "Market Analysis", "startDate": "2023-03-25T00:00:00Z", "dueDate": "2023-07-25T00:00:00Z", "projectId": 2, "authorUserId": 5, "assignedUserId": 6}),
    Task.model_validate({"id": 24, "title": "Task 24", "description": "Optimize user feedback collection mechanism.", "status": "To Do", "priority": "High", "tags": "Feedback", "startDate": "2023-04-15T00:00:00Z", "dueDate": "2023-08-15T00:00:00Z", "projectId": 3, "authorUserId": 7, "assignedUserId": 8}),
    Task.model_validate({"id": 25, "title": "Task 25", "description": "Integrate new API for third-party services.", "status": "Work In Progress", "priority": "Urgent", "tags": "API Integration", "startDate": "2023-05-05T00:00:00Z", "dueDate": "2023-09-05T00:00:00Z", "projectId": 4, "authorUserId": 9, "assignedUserId": 10}),
    Task.model_validate({"id": 26, "title": "Task 26", "description": "Update internal tooling for development teams.", "status": "To Do", "priority": "Backlog", "tags": "Tooling", "startDate": "2023-06-25T00:00:00Z", "dueDate": "2023-10-25T00:00:00Z", "projectId": 5, "authorUserId": 11, "assignedUserId": 12}),
    Task.model_validate({"id": 27, "title": "Task 27", "description": "Prepare cloud migration strategy document.", "status": "Work In Progress", "priority": "Urgent", "tags": "Cloud Migration", "startDate": "2023-07-20T00:00:00Z", "dueDate": "2023-11-20T00:00:00Z", "projectId": 6, "authorUserId": 13, "assignedUserId": 14}),
    Task.model_validate({"id": 28, "title": "Task 28", "description": "Design scalable database architecture.", "status": "To Do", "priority": "Medium", "tags": "Database Design", "startDate": "2023-08-15T00:00:00Z", "dueDate": "2023-12-15T00:00:00Z", "projectId": 7, "authorUserId": 15, "assignedUserId": 16}),
    Task.model_validate({"id": 29, "title": "Task 29", "description": "Prototype new mobile technology.", "status": "Work In Progress", "priority": "Urgent", "tags": "Mobile Tech", "startDate": "2023-09-10T00:00:00Z", "dueDate": "2024-01-10T00:00:00Z", "projectId": 8, "authorUserId": 17, "assignedUserId": 18}),
    Task.model_validate({"id": 30, "title": "Task 30", "description": "Enhance data encryption levels.", "status": "To Do", "priority": "High", "tags": "Encryption", "startDate": "2023-10-15T00:00:00Z", "dueDate": "2024-02-15T00:00:00Z", "projectId": 9, "authorUserId": 19, "assignedUserId": 20}),
    Task.model_validate({"id": 31, "title": "Task 31", "description": "Refactor backend code for better maintainability.", "status": "Work In Progress", "priority": "Urgent", "tags": "Refactoring, Backend", "startDate": "2023-11-01T00:00:00Z", "dueDate": "2024-03-01T00:00:00Z", "projectId": 10, "authorUserId": 20, "assignedUserId": 1}),
    Task.model_validate({"id": 32, "title": "Task 32", "description": "Expand the network infrastructure to support increased traffic.", "status": "To Do", "priority": "Medium", "tags": "Networking, Infrastructure", "startDate": "2023-11-05T00:00:00Z", "dueDate": "2024-01-05T00:00:00Z", "projectId": 1, "authorUserId": 2, "assignedUserId": 3}),
    Task.model_validate({"id": 33, "title": "Task 33", "description": "Create a new client dashboard interface.", "status": "Work In Progress", "priority": "Urgent", "tags": "UI, Dashboard", "startDate": "2023-11-10T00:00:00Z", "dueDate": "2024-02-10T00:00:00Z", "projectId": 2, "authorUserId": 4, "assignedUserId": 5}),
    Task.model_validate({"id": 34, "title": "Task 34", "description": "Develop an automated testing framework for new software releases.", "status": "To Do", "priority": "Medium", "tags": "Testing, Automation", "startDate": "2023-11-15T00:00:00Z", "dueDate": "2024-03-15T00:00:00Z", "projectId": 3, "authorUserId": 6, "assignedUserId": 7}),
    Task.model_validate({"id": 35, "title": "Task 35", "description": "Optimize database queries to improve application performance.", "status": "Work In Progress", "priority": "Urgent", "tags": "Database, Optimization", "startDate": "2023-11-20T00:00:00Z", "dueDate": "2024-01-20T00:00:00Z", "projectId": 4, "authorUserId": 8, "assignedUserId": 9}),
    Task.model_validate({"id": 36, "title": "Task 36", "description": "Implement end-user training for new system features.", "status": "To Do", "priority": "Backlog", "tags": "Training, User Experience", "startDate": "2023-11-25T00:00:00Z", "dueDate": "2024-01-25T00:00:00Z", "projectId": 5, "authorUserId": 10, "assignedUserId": 11}),
    Task.model_validate({"id": 37, "title": "Task 37", "description": "Conduct a comprehensive security audit of the existing infrastructure.", "status": "Work In Progress", "priority": "Urgent", "tags": "Security, Audit", "startDate": "2023-12-01T00:00:00Z", "dueDate": "2024-02-01T00:00:00Z", "projectId": 6, "authorUserId": 12, "assignedUserId": 13}),
    Task.model_validate({"id": 38, "title": "Task 38", "description": "Revise mobile app to incorporate new payment integrations.", "status": "To Do", "priority": "Medium", "tags": "Mobile, Payments", "startDate": "2023-12-05T00:00:00Z", "dueDate": "2024-02-05T00:00:00Z", "projectId": 7, "authorUserId": 14, "assignedUserId": 15}),
    Task.model_validate({"id": 39, "title": "Task 39", "description": "Update cloud configuration to optimize costs.", "status": "Work In Progress", "priority": "Urgent", "tags": "Cloud, Cost Saving", "startDate": "2023-12-10T00:00:00Z", "dueDate": "2024-02-10T00:00:00Z", "projectId": 8, "authorUserId": 16, "assignedUserId": 17}),
    Task.model_validate({"id": 40, "title": "Task 40", "description": "Implement automated backup procedures for critical data.", "status": "To Do", "priority": "High", "tags": "Backup, Automation", "startDate": "2023-12-15T00:00:00Z", "dueDate": "2024-02-15T00:00:00Z", "projectId": 9, "authorUserId": 18, "assignedUserId": 19}),
]

# Replicating the full 10-project dataset
DUMMY_PROJECTS: List[Project] = [
    Project.model_validate({"id": 1, "name": "Formula 1", "description": "A space exploration project.", "startDate": "2023-01-01T00:00:00Z", "endDate": "2023-12-31T00:00:00Z"}),
    Project.model_validate({"id": 3, "name": "Cricket", "description": "A project to boost renewable energy use.", "startDate": "2023-03-05T00:00:00Z", "endDate": "2024-03-05T00:00:00Z"}),
    Project.model_validate({"id": 4, "name": "Tennis", "description": "Tennis project for new software development techniques.", "startDate": "2023-01-20T00:00:00Z", "endDate": "2023-09-20T00:00:00Z"}),
    Project.model_validate({"id": 5, "name": "Echo", "description": "Echo project focused on AI advancements.", "startDate": "2023-04-15T00:00:00Z", "endDate": "2023-11-30T00:00:00Z"}),
    Project.model_validate({"id": 6, "name": "Foot Ball", "description": "Exploring cutting-edge biotechnology.", "startDate": "2023-02-25T00:00:00Z", "endDate": "2023-08-25T00:00:00Z"}),
    Project.model_validate({"id": 7, "name": "Golf", "description": "Development of new golf equipment using AI.", "startDate": "2023-05-10T00:00:00Z", "endDate": "2023-12-10T00:00:00Z"}),
    Project.model_validate({"id": 8, "name": "Hockey", "description": "Hockey management system overhaul.", "startDate": "2023-03-01T00:00:00Z", "endDate": "2024-01-01T00:00:00Z"}),
    Project.model_validate({"id": 9, "name": "India", "description": "Telecommunication infrastructure upgrade.", "startDate": "2023-06-01T00:00:00Z", "endDate": "2023-12-01T00:00:00Z"}),
    Project.model_validate({"id": 10, "name": "Judo", "description": "Initiative to enhance cyber-security measures.", "startDate": "2023-07-01T00:00:00Z", "endDate": "2024-02-01T00:00:00Z"}),
    # Note: Project ID 2 is skipped in your provided data, consistent with your Node.js mock.
]

# Replicating the user lookup data (only the users relevant to the task/project data you gave)
DUMMY_USERS: List[User] = [
    User.model_validate({"userId": 1, "cognitoId": "user-a1b2c3d4", "username": "Bharath Raj", "profilePictureUrl": "p1.jpeg", "teamId": 1}),
    User.model_validate({"userId": 2, "cognitoId": "123e4567-e89b-12d3-a456-426614174002", "username": "Priya", "profilePictureUrl": "p2.jpeg", "teamId": 2}),
    User.model_validate({"userId": 3, "cognitoId": "123e4567-e89b-12d3-a456-426614174003", "username": "Hitesh", "profilePictureUrl": "p3.jpeg", "teamId": 3}),
    User.model_validate({"userId": 4, "cognitoId": "213b7530-1031-70e0-67e9-fe0805e18fb3", "username": "Naveen", "profilePictureUrl": "p4.jpeg", "teamId": 4}),
    User.model_validate({"userId": 5, "cognitoId": "123e4567-e89b-12d3-a456-426614174005", "username": "EveClark", "profilePictureUrl": "p5.jpeg", "teamId": 5}),
    User.model_validate({"userId": 6, "cognitoId": "123e4567-e89b-12d3-a456-426614174006", "username": "FrankWright", "profilePictureUrl": "p6.jpeg", "teamId": 1}),
    User.model_validate({"userId": 7, "cognitoId": "123e4567-e89b-12d3-a456-426614174007", "username": "GraceHall", "profilePictureUrl": "p7.jpeg", "teamId": 2}),
    User.model_validate({"userId": 8, "cognitoId": "123e4567-e89b-12d3-a456-426614174008", "username": "HenryAllen", "profilePictureUrl": "p8.jpeg", "teamId": 3}),
    User.model_validate({"userId": 9, "cognitoId": "123e4567-e89b-12d3-a456-426614174009", "username": "IdaMartin", "profilePictureUrl": "p9.jpeg", "teamId": 4}),
    User.model_validate({"userId": 10, "cognitoId": "123e4567-e89b-12d3-a456-426614174010", "username": "bharath", "profilePictureUrl": "p10.jpeg", "teamId": 5}),
    User.model_validate({"userId": 11, "cognitoId": "123e4567-e89b-12d3-a456-426614174011", "username": "Vivek", "profilePictureUrl": "p11.jpeg", "teamId": 1}),
    User.model_validate({"userId": 12, "cognitoId": "123e4567-e89b-12d3-a456-426614174012", "username": "NormanBates", "profilePictureUrl": "p12.jpeg", "teamId": 2}),
    User.model_validate({"userId": 13, "cognitoId": "123e4567-e89b-12d3-a456-426614174013", "username": "OliviaPace", "profilePictureUrl": "p13.jpeg", "teamId": 3}),
    User.model_validate({"userId": 14, "cognitoId": "123e4567-e89b-12d3-a456-426614174014", "username": "PeterQuill", "profilePictureUrl": "p1.jpeg", "teamId": 4}),
    User.model_validate({"userId": 15, "cognitoId": "123e4567-e89b-12d3-a456-426614174015", "username": "QuincyAdams", "profilePictureUrl": "p2.jpeg", "teamId": 5}),
    User.model_validate({"userId": 16, "cognitoId": "123e4567-e89b-12d3-a456-426614174016", "username": "RachelGreen", "profilePictureUrl": "p3.jpeg", "teamId": 1}),
    User.model_validate({"userId": 17, "cognitoId": "123e4567-e89b-12d3-a456-426614174017", "username": "SteveJobs", "profilePictureUrl": "p4.jpeg", "teamId": 2}),
    User.model_validate({"userId": 18, "cognitoId": "123e4567-e89b-12d3-a456-426614174018", "username": "TinaFey", "profilePictureUrl": "p5.jpeg", "teamId": 3}),
    User.model_validate({"userId": 19, "cognitoId": "123e4567-e89b-12d3-a456-426614174019", "username": "UrsulaMonroe", "profilePictureUrl": "p6.jpeg", "teamId": 4}),
    User.model_validate({"userId": 20, "cognitoId": "123e4567-e89b-12d3-a456-426614174020", "username": "VictorHugo", "profilePictureUrl": "p7.jpeg", "teamId": 5}),
]


# --- APIRouter (Equivalent to Express Router) ---

router = APIRouter()

# --- Search Controller Function (Equivalent to searchController.search) ---

@router.get("/", response_model=SearchResults)
async def search(q: Optional[str] = None):
    """
    Performs a combined search across tasks, projects, and users based on a query string (q).
    """
    query = (q or "").lower()

    try:
        # --- 1. TASK SEARCH (title OR description) ---
        tasks = [
            task for task in DUMMY_TASKS
            if query in task.title.lower() or query in task.description.lower()
        ]

        # --- 2. PROJECT SEARCH (name OR description) ---
        projects = [
            project for project in DUMMY_PROJECTS
            if query in project.name.lower() or query in project.description.lower()
        ]

        # --- 3. USER SEARCH (username) ---
        users = [
            user for user in DUMMY_USERS
            if query in user.username.lower()
        ]

        return {"tasks": tasks, "projects": projects, "users": users}
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error performing search: {e}"
        )