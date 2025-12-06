# DASHBOARD_BACKEND/app/routes/task_routes.py

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

# --- Pydantic Models for Linked Data ---

class TaskUser(BaseModel):
    user_id: int = Field(alias="userId")
    cognito_id: str = Field(alias="cognitoId")
    username: str
    profile_picture_url: str = Field(alias="profilePictureUrl")
    team_id: int = Field(alias="teamId")
    
    class Config:
        populate_by_name = True

class Comment(BaseModel):
    id: int
    text: str
    task_id: int = Field(alias="taskId")
    user_id: int = Field(alias="userId")
    
    class Config:
        populate_by_name = True

class Attachment(BaseModel):
    id: int
    file_url: str = Field(alias="fileURL")
    file_name: str = Field(alias="fileName")
    task_id: int = Field(alias="taskId")
    uploaded_by_id: int = Field(alias="uploadedById")
    
    class Config:
        populate_by_name = True


# --- Core Task Models ---

class TaskBase(BaseModel):
    title: str
    description: str
    status: str
    priority: str
    tags: str
    start_date: str = Field(alias="startDate")
    due_date: str = Field(alias="dueDate")
    points: Optional[int] = 0
    project_id: int = Field(alias="projectId")
    author_user_id: int = Field(alias="authorUserId")
    assigned_user_id: Optional[int] = Field(None, alias="assignedUserId")

    class Config:
        populate_by_name = True

class Task(TaskBase):
    id: int

class TaskWithRelations(Task):
    author: Optional[TaskUser] = None
    assignee: Optional[TaskUser] = None
    comments: List[Comment] = []
    attachments: List[Attachment] = []

class TaskStatusUpdate(BaseModel):
    status: str

# --- STATIC DATA (Complete and Syntactically Valid) ---

# --- DUMMY_USERS (20 records) ---
DUMMY_USERS: List[TaskUser] = [
    TaskUser.model_validate({"userId": 1, "cognitoId": "123e4567-e89b-12d3-a456-426614174001", "username": "Bharath Raj", "profilePictureUrl": "p1.jpeg", "teamId": 1}),
    TaskUser.model_validate({"userId": 2, "cognitoId": "123e4567-e89b-12d3-a456-426614174002", "username": "Priya", "profilePictureUrl": "p2.jpeg", "teamId": 2}),
    TaskUser.model_validate({"userId": 3, "cognitoId": "123e4567-e89b-12d3-a456-426614174003", "username": "Hitesh", "profilePictureUrl": "p3.jpeg", "teamId": 3}),
    TaskUser.model_validate({"userId": 4, "cognitoId": "213b7530-1031-70e0-67e9-fe0805e18fb3", "username": "Naveen", "profilePictureUrl": "p4.jpeg", "teamId": 4}),
    TaskUser.model_validate({"userId": 5, "cognitoId": "123e4567-e89b-12d3-a456-426614174005", "username": "EveClark", "profilePictureUrl": "p5.jpeg", "teamId": 5}),
    TaskUser.model_validate({"userId": 6, "cognitoId": "123e4567-e89b-12d3-a456-426614174006", "username": "FrankWright", "profilePictureUrl": "p6.jpeg", "teamId": 1}),
    TaskUser.model_validate({"userId": 7, "cognitoId": "123e4567-e89b-12d3-a456-426614174007", "username": "GraceHall", "profilePictureUrl": "p7.jpeg", "teamId": 2}),
    TaskUser.model_validate({"userId": 8, "cognitoId": "123e4567-e89b-12d3-a456-426614174008", "username": "HenryAllen", "profilePictureUrl": "p8.jpeg", "teamId": 3}),
    TaskUser.model_validate({"userId": 9, "cognitoId": "123e4567-e89b-12d3-a456-426614174009", "username": "IdaMartin", "profilePictureUrl": "p9.jpeg", "teamId": 4}),
    TaskUser.model_validate({"userId": 10, "cognitoId": "123e4567-e89b-12d3-a456-426614174010", "username": "bharath", "profilePictureUrl": "p10.jpeg", "teamId": 5}),
    TaskUser.model_validate({"userId": 11, "cognitoId": "123e4567-e89b-12d3-a456-426614174011", "username": "Vivek", "profilePictureUrl": "p11.jpeg", "teamId": 1}),
    TaskUser.model_validate({"userId": 12, "cognitoId": "123e4567-e89b-12d3-a456-426614174012", "username": "NormanBates", "profilePictureUrl": "p12.jpeg", "teamId": 2}),
    TaskUser.model_validate({"userId": 13, "cognitoId": "123e4567-e89b-12d3-a456-426614174013", "username": "OliviaPace", "profilePictureUrl": "p13.jpeg", "teamId": 3}),
    TaskUser.model_validate({"userId": 14, "cognitoId": "123e4567-e89b-12d3-a456-426614174014", "username": "PeterQuill", "profilePictureUrl": "p1.jpeg", "teamId": 4}),
    TaskUser.model_validate({"userId": 15, "cognitoId": "123e4567-e89b-12d3-a456-426614174015", "username": "QuincyAdams", "profilePictureUrl": "p2.jpeg", "teamId": 5}),
    TaskUser.model_validate({"userId": 16, "cognitoId": "123e4567-e89b-12d3-a456-426614174016", "username": "RachelGreen", "profilePictureUrl": "p3.jpeg", "teamId": 1}),
    TaskUser.model_validate({"userId": 17, "cognitoId": "123e4567-e89b-12d3-a456-426614174017", "username": "SteveJobs", "profilePictureUrl": "p4.jpeg", "teamId": 2}),
    TaskUser.model_validate({"userId": 18, "cognitoId": "123e4567-e89b-12d3-a456-426614174018", "username": "TinaFey", "profilePictureUrl": "p5.jpeg", "teamId": 3}),
    TaskUser.model_validate({"userId": 19, "cognitoId": "123e4567-e89b-12d3-a456-426614174019", "username": "UrsulaMonroe", "profilePictureUrl": "p6.jpeg", "teamId": 4}),
    TaskUser.model_validate({"userId": 20, "cognitoId": "123e4567-e89b-12d3-a456-426614174020", "username": "VictorHugo", "profilePictureUrl": "p7.jpeg", "teamId": 5}),
]

# --- DUMMY_COMMENTS (Minimal 25 records - You may need to verify these IDs/links) ---
DUMMY_COMMENTS: List[Comment] = [
    Comment.model_validate({"id": 1, "text": "We need to update this design...", "taskId": 1, "userId": 2}),
    Comment.model_validate({"id": 2, "text": "Can we move this to next sprint?", "taskId": 1, "userId": 1}),
    Comment.model_validate({"id": 3, "text": "Starting implementation today.", "taskId": 2, "userId": 4}),
    Comment.model_validate({"id": 4, "text": "Renewable energy research is underway.", "taskId": 3, "userId": 6}),
    Comment.model_validate({"id": 5, "text": "Workflow documents finalized.", "taskId": 4, "userId": 8}),
    Comment.model_validate({"id": 6, "text": "AI model training failed once.", "taskId": 5, "userId": 10}),
    Comment.model_validate({"id": 7, "text": "Product testing successful.", "taskId": 6, "userId": 12}),
    Comment.model_validate({"id": 8, "text": "Optimization results are promising.", "taskId": 7, "userId": 14}),
    Comment.model_validate({"id": 9, "text": "Database overhaul planned.", "taskId": 8, "userId": 16}),
    Comment.model_validate({"id": 10, "text": "Infrastructure upgrade ongoing.", "taskId": 9, "userId": 18}),
    Comment.model_validate({"id": 11, "text": "Security protocols reviewed.", "taskId": 10, "userId": 20}),
    Comment.model_validate({"id": 12, "text": "Server security update meeting...", "taskId": 12, "userId": 2}),
    Comment.model_validate({"id": 13, "text": "UX mockups approved.", "taskId": 13, "userId": 6}),
    Comment.model_validate({"id": 14, "text": "Data pipeline setup is complete.", "taskId": 14, "userId": 8}),
    Comment.model_validate({"id": 15, "text": "Encryption keys generated.", "taskId": 15, "userId": 10}),
    Comment.model_validate({"id": 16, "text": "Cloud storage usage is high.", "taskId": 16, "userId": 12}),
    Comment.model_validate({"id": 17, "text": "Hardware compatibility test passed.", "taskId": 17, "userId": 14}),
    Comment.model_validate({"id": 18, "text": "Visualization library chosen.", "taskId": 18, "userId": 16}),
    Comment.model_validate({"id": 19, "text": "IoT prototype assembly started.", "taskId": 19, "userId": 18}),
    Comment.model_validate({"id": 20, "text": "Legacy system analysis complete.", "taskId": 20, "userId": 20}),
    Comment.model_validate({"id": 21, "text": "New framework documentation is pending.", "taskId": 21, "userId": 3}),
    Comment.model_validate({"id": 22, "text": "Deployment strategy needs final review.", "taskId": 22, "userId": 4}),
    Comment.model_validate({"id": 23, "text": "Market analysis report sent to PO.", "taskId": 23, "userId": 6}),
    Comment.model_validate({"id": 24, "text": "Feedback mechanism needs testing.", "taskId": 24, "userId": 8}),
    Comment.model_validate({"id": 25, "text": "API keys are in the vault.", "taskId": 25, "userId": 10}),
]

# --- DUMMY_ATTACHMENTS (Minimal 10 records - You may need to verify these IDs/links) ---
DUMMY_ATTACHMENTS: List[Attachment] = [
    Attachment.model_validate({"id": 1, "fileURL": "i1.jpg", "fileName": "DesignDoc.pdf", "taskId": 1, "uploadedById": 1}),
    Attachment.model_validate({"id": 2, "fileURL": "i2.pdf", "fileName": "Algorithm.zip", "taskId": 2, "uploadedById": 3}),
    Attachment.model_validate({"id": 3, "fileURL": "i3.docx", "fileName": "RenewablePlan.docx", "taskId": 3, "uploadedById": 5}),
    Attachment.model_validate({"id": 4, "fileURL": "i4.png", "fileName": "Workflow_Mockup.png", "taskId": 4, "uploadedById": 7}),
    Attachment.model_validate({"id": 5, "fileURL": "i5.xlsx", "fileName": "AI_Research_Summary.xlsx", "taskId": 5, "uploadedById": 9}),
    Attachment.model_validate({"id": 6, "fileURL": "i6.jpeg", "fileName": "Test_Results.jpeg", "taskId": 6, "uploadedById": 11}),
    Attachment.model_validate({"id": 7, "fileURL": "i7.mp4", "fileName": "Optimization_Video.mp4", "taskId": 7, "uploadedById": 13}),
    Attachment.model_validate({"id": 8, "fileURL": "i8.json", "fileName": "DB_Schema.json", "taskId": 8, "uploadedById": 15}),
    Attachment.model_validate({"id": 9, "fileURL": "i9.pptx", "fileName": "Upgrade_Plan.pptx", "taskId": 9, "uploadedById": 17}),
    Attachment.model_validate({"id": 10, "fileURL": "i10.html", "fileName": "Security_Checklist.html", "taskId": 10, "uploadedById": 19}),
]

# --- DUMMY_TASKS (Complete 40 records) ---
DUMMY_TASKS: List[Task] = [
    Task.model_validate({"id": 1, "title": "Task 1", "description": "Design the main module.", "status": "Work In Progress", "priority": "Urgent", "tags": "Design", "startDate": "2023-01-10T00:00:00Z", "dueDate": "2023-04-10T00:00:00Z", "points": 5, "projectId": 1, "authorUserId": 1, "assignedUserId": 2}),
    Task.model_validate({"id": 2, "title": "Task 2", "description": "Implement the navigation algorithm.", "status": "To Do", "priority": "High", "tags": "Coding", "startDate": "2023-01-15T00:00:00Z", "dueDate": "2023-05-15T00:00:00Z", "points": 8, "projectId": 2, "authorUserId": 3, "assignedUserId": 4}),
    Task.model_validate({"id": 3, "title": "Task 3", "description": "Develop renewable energy solutions.", "status": "Work In Progress", "priority": "Urgent", "tags": "Development", "startDate": "2023-03-20T00:00:00Z", "dueDate": "2023-09-20T00:00:00Z", "points": 13, "projectId": 3, "authorUserId": 5, "assignedUserId": 6}),
    Task.model_validate({"id": 4, "title": "Task 4", "description": "Outline new software development workflows.", "status": "To Do", "priority": "High", "tags": "Planning", "startDate": "2023-01-25T00:00:00Z", "dueDate": "2023-06-25T00:00:00Z", "points": 2, "projectId": 4, "authorUserId": 7, "assignedUserId": 8}),
    Task.model_validate({"id": 5, "title": "Task 5", "description": "Research AI models for prediction.", "status": "Work In Progress", "priority": "Urgent", "tags": "Research", "startDate": "2023-04-20T00:00:00Z", "dueDate": "2023-10-20T00:00:00Z", "points": 5, "projectId": 5, "authorUserId": 9, "assignedUserId": 10}),
    Task.model_validate({"id": 6, "title": "Task 6", "description": "Biotech product testing.", "status": "To Do", "priority": "Backlog", "tags": "Testing", "startDate": "2023-03-01T00:00:00Z", "dueDate": "2023-08-01T00:00:00Z", "points": 3, "projectId": 6, "authorUserId": 11, "assignedUserId": 12}),
    Task.model_validate({"id": 7, "title": "Task 7", "description": "AI optimization for golf equipment.", "status": "Work In Progress", "priority": "Urgent", "tags": "Optimization", "startDate": "2023-05-15T00:00:00Z", "dueDate": "2023-11-15T00:00:00Z", "points": 8, "projectId": 7, "authorUserId": 13, "assignedUserId": 14}),
    Task.model_validate({"id": 8, "title": "Task 8", "description": "Overhaul of the database for Hockey management.", "status": "To Do", "priority": "High", "tags": "Database", "startDate": "2023-04-01T00:00:00Z", "dueDate": "2023-10-01T00:00:00Z", "points": 13, "projectId": 8, "authorUserId": 15, "assignedUserId": 16}),
    Task.model_validate({"id": 9, "title": "Task 9", "description": "Upgrade telecom infrastructure.", "status": "Work In Progress", "priority": "Urgent", "tags": "Infrastructure", "startDate": "2023-06-10T00:00:00Z", "dueDate": "2023-12-10T00:00:00Z", "points": 5, "projectId": 9, "authorUserId": 17, "assignedUserId": 18}),
    Task.model_validate({"id": 10, "title": "Task 10", "description": "Enhance security protocols.", "status": "To Do", "priority": "Urgent", "tags": "Security", "startDate": "2023-07-05T00:00:00Z", "dueDate": "2024-01-05T00:00:00Z", "points": 8, "projectId": 10, "authorUserId": 19, "assignedUserId": 20}),
    Task.model_validate({"id": 11, "title": "Task 11", "description": "Finalize AI training parameters.", "status": "Work In Progress", "priority": "Urgent", "tags": "AI, Training", "startDate": "2023-01-20T00:00:00Z", "dueDate": "2023-05-20T00:00:00Z", "points": 3, "projectId": 5, "authorUserId": 1, "assignedUserId": 3}),
    Task.model_validate({"id": 12, "title": "Task 12", "description": "Update server security protocols.", "status": "To Do", "priority": "High", "tags": "Security", "startDate": "2023-02-10T00:00:00Z", "dueDate": "2023-06-10T00:00:00Z", "points": 2, "projectId": 1, "authorUserId": 2, "assignedUserId": 4}),
    Task.model_validate({"id": 13, "title": "Task 13", "description": "Redesign user interface for better UX.", "status": "Work In Progress", "priority": "Urgent", "tags": "Design, UX", "startDate": "2023-03-15T00:00:00Z", "dueDate": "2023-07-15T00:00:00Z", "points": 5, "projectId": 2, "authorUserId": 5, "assignedUserId": 6}),
    Task.model_validate({"id": 14, "title": "Task 14", "description": "Implement real-time data analytics.", "status": "To Do", "priority": "High", "tags": "Analytics", "startDate": "2023-04-05T00:00:00Z", "dueDate": "2023-08-05T00:00:00Z", "points": 8, "projectId": 3, "authorUserId": 7, "assignedUserId": 8}),
    Task.model_validate({"id": 15, "title": "Task 15", "description": "Develop end-to-end encryption solution.", "status": "Work In Progress", "priority": "Urgent", "tags": "Encryption", "startDate": "2023-05-01T00:00:00Z", "dueDate": "2023-09-01T00:00:00Z", "points": 13, "projectId": 4, "authorUserId": 9, "assignedUserId": 10}),
    Task.model_validate({"id": 16, "title": "Task 16", "description": "Optimize cloud storage usage.", "status": "To Do", "priority": "Backlog", "tags": "Cloud, Storage", "startDate": "2023-06-15T00:00:00Z", "dueDate": "2023-10-15T00:00:00Z", "points": 3, "projectId": 5, "authorUserId": 11, "assignedUserId": 12}),
    Task.model_validate({"id": 17, "title": "Task 17", "description": "Test software for hardware compatibility.", "status": "Work In Progress", "priority": "Urgent", "tags": "Testing, Hardware", "startDate": "2023-07-10T00:00:00Z", "dueDate": "2023-11-10T00:00:00Z", "points": 5, "projectId": 6, "authorUserId": 13, "assignedUserId": 14}),
    Task.model_validate({"id": 18, "title": "Task 18", "description": "Create new data visualization tools.", "status": "To Do", "priority": "High", "tags": "Visualization", "startDate": "2023-08-05T00:00:00Z", "dueDate": "2023-12-05T00:00:00Z", "points": 8, "projectId": 7, "authorUserId": 15, "assignedUserId": 16}),
    Task.model_validate({"id": 19, "title": "Task 19", "description": "Build prototype for new IoT devices.", "status": "Work In Progress", "priority": "Urgent", "tags": "IoT", "startDate": "2023-09-01T00:00:00Z", "dueDate": "2024-01-01T00:00:00Z", "points": 13, "projectId": 8, "authorUserId": 17, "assignedUserId": 18}),
    Task.model_validate({"id": 20, "title": "Task 20", "description": "Update legacy systems to new tech standards.", "status": "To Do", "priority": "Urgent", "tags": "Legacy, Upgrade", "startDate": "2023-10-10T00:00:00Z", "dueDate": "2024-02-10T00:00:00Z", "points": 5, "projectId": 9, "authorUserId": 19, "assignedUserId": 20}),
    Task.model_validate({"id": 21, "title": "Task 21", "description": "Establish new network security framework.", "status": "Work In Progress", "priority": "Urgent", "tags": "Security", "startDate": "2023-01-30T00:00:00Z", "dueDate": "2023-05-30T00:00:00Z", "points": 8, "projectId": 10, "authorUserId": 1, "assignedUserId": 3}),
    Task.model_validate({"id": 22, "title": "Task 22", "description": "Revise application deployment strategies.", "status": "To Do", "priority": "High", "tags": "Deployment", "startDate": "2023-02-20T00:00:00Z", "dueDate": "2023-06-20T00:00:00Z", "points": 3, "projectId": 1, "authorUserId": 2, "assignedUserId": 4}),
    Task.model_validate({"id": 23, "title": "Task 23", "description": "Conduct market analysis for product fit.", "status": "Work In Progress", "priority": "Urgent", "tags": "Market Analysis", "startDate": "2023-03-25T00:00:00Z", "dueDate": "2023-07-25T00:00:00Z", "points": 5, "projectId": 2, "authorUserId": 5, "assignedUserId": 6}),
    Task.model_validate({"id": 24, "title": "Task 24", "description": "Optimize user feedback collection mechanism.", "status": "To Do", "priority": "High", "tags": "Feedback", "startDate": "2023-04-15T00:00:00Z", "dueDate": "2023-08-15T00:00:00Z", "points": 8, "projectId": 3, "authorUserId": 7, "assignedUserId": 8}),
    Task.model_validate({"id": 25, "title": "Task 25", "description": "Integrate new API for third-party services.", "status": "Work In Progress", "priority": "Urgent", "tags": "API Integration", "startDate": "2023-05-05T00:00:00Z", "dueDate": "2023-09-05T00:00:00Z", "points": 13, "projectId": 4, "authorUserId": 9, "assignedUserId": 10}),
    Task.model_validate({"id": 26, "title": "Task 26", "description": "Update internal tooling for development teams.", "status": "To Do", "priority": "Backlog", "tags": "Tooling", "startDate": "2023-06-25T00:00:00Z", "dueDate": "2023-10-25T00:00:00Z", "points": 2, "projectId": 5, "authorUserId": 11, "assignedUserId": 12}),
    Task.model_validate({"id": 27, "title": "Task 27", "description": "Prepare cloud migration strategy document.", "status": "Work In Progress", "priority": "Urgent", "tags": "Cloud Migration", "startDate": "2023-07-20T00:00:00Z", "dueDate": "2023-11-20T00:00:00Z", "points": 5, "projectId": 6, "authorUserId": 13, "assignedUserId": 14}),
    Task.model_validate({"id": 28, "title": "Task 28", "description": "Design scalable database architecture.", "status": "To Do", "priority": "Medium", "tags": "Database Design", "startDate": "2023-08-15T00:00:00Z", "dueDate": "2023-12-15T00:00:00Z", "points": 8, "projectId": 7, "authorUserId": 15, "assignedUserId": 16}),
    Task.model_validate({"id": 29, "title": "Task 29", "description": "Prototype new mobile technology.", "status": "Work In Progress", "priority": "Urgent", "tags": "Mobile Tech", "startDate": "2023-09-10T00:00:00Z", "dueDate": "2024-01-10T00:00:00Z", "points": 13, "projectId": 8, "authorUserId": 17, "assignedUserId": 18}),
    Task.model_validate({"id": 30, "title": "Task 30", "description": "Enhance data encryption levels.", "status": "To Do", "priority": "High", "tags": "Encryption", "startDate": "2023-10-15T00:00:00Z", "dueDate": "2024-02-15T00:00:00Z", "points": 5, "projectId": 9, "authorUserId": 19, "assignedUserId": 20}),
    Task.model_validate({"id": 31, "title": "Task 31", "description": "Refactor backend code for better maintainability.", "status": "Work In Progress", "priority": "Urgent", "tags": "Refactoring, Backend", "startDate": "2023-11-01T00:00:00Z", "dueDate": "2024-03-01T00:00:00Z", "points": 8, "projectId": 10, "authorUserId": 20, "assignedUserId": 1}),
    Task.model_validate({"id": 32, "title": "Task 32", "description": "Expand the network infrastructure to support increased traffic.", "status": "To Do", "priority": "Medium", "tags": "Networking, Infrastructure", "startDate": "2023-11-05T00:00:00Z", "dueDate": "2024-01-05T00:00:00Z", "points": 3, "projectId": 1, "authorUserId": 2, "assignedUserId": 3}),
    Task.model_validate({"id": 33, "title": "Task 33", "description": "Create a new client dashboard interface.", "status": "Work In Progress", "priority": "Urgent", "tags": "UI, Dashboard", "startDate": "2023-11-10T00:00:00Z", "dueDate": "2024-02-10T00:00:00Z", "points": 5, "projectId": 2, "authorUserId": 4, "assignedUserId": 5}),
    Task.model_validate({"id": 34, "title": "Task 34", "description": "Develop an automated testing framework for new software releases.", "status": "To Do", "priority": "Medium", "tags": "Testing, Automation", "startDate": "2023-11-15T00:00:00Z", "dueDate": "2024-03-15T00:00:00Z", "points": 8, "projectId": 3, "authorUserId": 6, "assignedUserId": 7}),
    Task.model_validate({"id": 35, "title": "Task 35", "description": "Optimize database queries to improve application performance.", "status": "Work In Progress", "priority": "Urgent", "tags": "Database, Optimization", "startDate": "2023-11-20T00:00:00Z", "dueDate": "2024-01-20T00:00:00Z", "points": 13, "projectId": 4, "authorUserId": 8, "assignedUserId": 9}),
    Task.model_validate({"id": 36, "title": "Task 36", "description": "Implement end-user training for new system features.", "status": "To Do", "priority": "Backlog", "tags": "Training, User Experience", "startDate": "2023-11-25T00:00:00Z", "dueDate": "2024-01-25T00:00:00Z", "points": 2, "projectId": 5, "authorUserId": 10, "assignedUserId": 11}),
    Task.model_validate({"id": 37, "title": "Task 37", "description": "Conduct a comprehensive security audit of the existing infrastructure.", "status": "Work In Progress", "priority": "Urgent", "tags": "Security, Audit", "startDate": "2023-12-01T00:00:00Z", "dueDate": "2024-02-01T00:00:00Z", "points": 5, "projectId": 6, "authorUserId": 12, "assignedUserId": 13}),
    Task.model_validate({"id": 38, "title": "Task 38", "description": "Revise mobile app to incorporate new payment integrations.", "status": "To Do", "priority": "Medium", "tags": "Mobile, Payments", "startDate": "2023-12-05T00:00:00Z", "dueDate": "2024-02-05T00:00:00Z", "points": 8, "projectId": 7, "authorUserId": 14, "assignedUserId": 15}),
    Task.model_validate({"id": 39, "title": "Task 39", "description": "Update cloud configuration to optimize costs.", "status": "Work In Progress", "priority": "Urgent", "tags": "Cloud, Cost Saving", "startDate": "2023-12-10T00:00:00Z", "dueDate": "2024-02-10T00:00:00Z", "points": 13, "projectId": 8, "authorUserId": 16, "assignedUserId": 17}),
    Task.model_validate({"id": 40, "title": "Task 40", "description": "Implement automated backup procedures for critical data.", "status": "To Do", "priority": "High", "tags": "Backup, Automation", "startDate": "2023-12-15T00:00:00Z", "dueDate": "2024-02-15T00:00:00Z", "points": 5, "projectId": 9, "authorUserId": 18, "assignedUserId": 19}),
]

# Simple state to simulate data creation
current_max_task_id = max(t.id for t in DUMMY_TASKS) if DUMMY_TASKS else 0

# --- Helper Function for Joins (Simulating 'include') ---

def include_task_relations(task: Task) -> TaskWithRelations:
    """Simulates Prisma's 'include' by attaching related data."""
    
    # Convert base Task to dictionary to add new fields
    task_data = task.model_dump(by_alias=True)
    task_with_relations: Any = TaskWithRelations(**task_data)

    # Attach Author and Assignee User objects
    task_with_relations.author = next((u for u in DUMMY_USERS if u.user_id == task.author_user_id), None)
    task_with_relations.assignee = next((u for u in DUMMY_USERS if u.user_id == task.assigned_user_id), None)

    # Attach related Comments and Attachments
    task_with_relations.comments = [c for c in DUMMY_COMMENTS if c.task_id == task.id]
    task_with_relations.attachments = [a for a in DUMMY_ATTACHMENTS if a.task_id == task.id]

    return task_with_relations

# --- APIRouter Setup ---

router = APIRouter()

# --- Controller Functions ---

# 1. GET /tasks?projectId=N (Equivalent to getTasks)
@router.get("/", response_model=List[TaskWithRelations])
async def get_tasks(project_id: Optional[int] = None):
    """
    Retrieves all tasks, optionally filtered by project ID, with full relations.
    """
    try:
        if project_id is None:
            filtered_tasks = DUMMY_TASKS
        else:
            filtered_tasks = [task for task in DUMMY_TASKS if task.project_id == project_id]
            
            if not filtered_tasks:
                 raise HTTPException(status_code=404, detail=f"No tasks found for projectId {project_id}.")

        tasks_with_relations = [include_task_relations(task) for task in filtered_tasks]

        return tasks_with_relations
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tasks: {e}")


# 2. POST /tasks (Equivalent to createTask)
@router.post("/", response_model=Task, status_code=201)
async def create_task(task_data: TaskBase):
    """
    Mocks Task.create() and creates a new task.
    """
    global current_max_task_id

    try:
        current_max_task_id += 1

        new_task = Task(
            id=current_max_task_id,
            **task_data.model_dump(by_alias=False)
        )

        DUMMY_TASKS.append(new_task)
        
        return new_task
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating a task: {e}")


# 3. PATCH /tasks/{task_id}/status (Equivalent to updateTaskStatus)
@router.patch("/{task_id}/status", response_model=Task)
async def update_task_status(
    task_id: int = Path(..., alias="taskId"), 
    status_update: TaskStatusUpdate = ...
):
    """
    Updates the status of a specific task.
    """
    try:
        task_index = next(i for i, task in enumerate(DUMMY_TASKS) if task.id == task_id)
    except StopIteration:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found.")

    current_task_data = DUMMY_TASKS[task_index].model_dump()
    current_task_data['status'] = status_update.status
    
    updated_task = Task(**current_task_data)
    DUMMY_TASKS[task_index] = updated_task
    
    return updated_task


# 4. GET /tasks/user/{user_id} (Equivalent to getUserTasks)
@router.get("/user/{user_id}", response_model=List[TaskWithRelations])
async def get_user_tasks(user_id: int):
    """
    Retrieves tasks where the user is either the author or the assigned user, with relations.
    """
    try:
        filtered_tasks = [
            task for task in DUMMY_TASKS 
            if task.author_user_id == user_id or task.assigned_user_id == user_id
        ]
        
        tasks_with_relations = [include_task_relations(task) for task in filtered_tasks]

        return tasks_with_relations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user's tasks: {e}")