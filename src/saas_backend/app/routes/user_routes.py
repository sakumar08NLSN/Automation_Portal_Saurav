# DASHBOARD_BACKEND/app/routes/user_routes.py

from fastapi import APIRouter, HTTPException, Path,Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from sqlalchemy.orm import Session
from database import get_db
from core.users.models import User as DBUser

# --- Pydantic Models ---

class UserBase(BaseModel):
    """Schema for data that can be created (POST body)."""
    username: str
    cognito_id: str = Field(alias="cognitoId")
    profile_picture_url: str = Field("i1.jpg", alias="profilePictureUrl") # Default value
    team_id: int = Field(1, alias="teamId") # Default value

    class Config:
        populate_by_name = True

class User(UserBase):
    """Full user schema including the server-generated ID."""
    user_id: int = Field(alias="userId")

    class Config:
        populate_by_name = True

# --- STATIC DATA (Matching Your Node.js Controller Data) ---

DUMMY_USERS: List[User] = [
    User.model_validate({"userId": 1, "cognitoId": "123e4567-e89b-12d3-a456-426614174001", "username": "Bharath Raj", "profilePictureUrl": "p1.jpeg", "teamId": 1}),
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

# Simple state to simulate data creation
current_max_user_id = max(u.user_id for u in DUMMY_USERS) if DUMMY_USERS else 0

# --- APIRouter Setup ---

router = APIRouter()

# --- Controller Functions ---

# 1. GET /users (Equivalent to router.get("/", getUsers))
@router.get("/", response_model=List[User], tags=["Users"])
async def get_users():
    """
    Simulates User.findMany() and returns all users.
    """
    try:
        return DUMMY_USERS
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving users: {e}")

# 2. GET /users/{cognito_id} (Equivalent to router.get("/:cognitoId", getUser))
@router.get("/{okta_uid}", tags=["Users"])
async def get_user(okta_uid: str, db: Session = Depends(get_db)):
    """
    Fetches a user from PostgreSQL using their Okta ID. 
    If they don't exist, it automatically registers them!
    """
    try:
        # 1. Query the REAL PostgreSQL database using DBUser (SQLAlchemy)
        user = db.query(DBUser).filter(DBUser.okta_uid == okta_uid).first()
        
        # 2. If it's a brand new Okta user, insert them into the DB
        if not user:
            new_user = DBUser(
                okta_uid=okta_uid,
                email=f"{okta_uid}@placeholder.nielsen.com", 
                first_name="Nielsen",
                last_name="User",
                is_active=True
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            user = new_user

        # 3. Return the data in the exact JSON format your React frontend expects
        return {
            "userId": user.okta_uid,       
            "username": f"{user.first_name} {user.last_name}",
            "profilePictureUrl": "i1.jpg", 
            "teamId": 1                    
        }
        
    except Exception as e:
        # If anything crashes, it undoes the database transaction and tells you EXACTLY why
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")

# 3. POST /users (Equivalent to router.post("/", postUser))
@router.post("/", response_model=dict[str, Any], status_code=200, tags=["Users"])
async def post_user(user_data: UserBase):
    """
    Mocks User.create() and creates a new user.
    """
    global current_max_user_id

    try:
        current_max_user_id += 1 # Simulate database auto-increment

        # Create the new user object, using values from user_data and generated ID
        new_user = User(
            user_id=current_max_user_id,
            **user_data.model_dump(by_alias=False)
        )

        # Simulate saving (add to the array)
        DUMMY_USERS.append(new_user)

        # Your Node.js controller returns a custom response: { message, newUser }
        return {"message": "User Created Successfully", "newUser": new_user}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {e}")