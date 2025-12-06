# DASHBOARD_BACKEND/app/routes/team_routes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Any

# --- Pydantic Models for Linked Data ---

class TeamUserLookup(BaseModel):
    user_id: int = Field(alias="userId")
    username: str
    cognito_id: str = Field(alias="cognitoId")
    profile_picture_url: str = Field(alias="profilePictureUrl")
    team_id: int = Field(alias="teamId")

    class Config:
        populate_by_name = True

class TeamBase(BaseModel):
    id: int
    team_name: str = Field(alias="teamName")
    product_owner_user_id: int = Field(alias="productOwnerUserId")
    project_manager_user_id: int = Field(alias="projectManagerUserId")

    class Config:
        populate_by_name = True

class TeamResponse(TeamBase):
    product_owner_username: Optional[str] = Field(None, alias="productOwnerUsername")
    project_manager_username: Optional[str] = Field(None, alias="projectManagerUsername")

    class Config:
        populate_by_name = True


# --- STATIC DATA (Complete and Syntactically Valid) ---

# --- DUMMY_TEAMS (5 records) ---
DUMMY_TEAMS: List[TeamBase] = [
    TeamBase.model_validate({"id": 1, "teamName": "BSR", "productOwnerUserId": 11, "projectManagerUserId": 2}),
    TeamBase.model_validate({"id": 2, "teamName": "GDT", "productOwnerUserId": 13, "projectManagerUserId": 4}),
    TeamBase.model_validate({"id": 3, "teamName": "Analytics", "productOwnerUserId": 15, "projectManagerUserId": 6}),
    TeamBase.model_validate({"id": 4, "teamName": "Devops", "productOwnerUserId": 17, "projectManagerUserId": 8}),
    TeamBase.model_validate({"id": 5, "teamName": "Automation", "productOwnerUserId": 19, "projectManagerUserId": 10}),
]

# --- DUMMY_USERS (20 records, used for lookups) ---
DUMMY_USERS: List[TeamUserLookup] = [
    TeamUserLookup.model_validate({"userId": 1, "cognitoId": "123e4567-e89b-12d3-a456-426614174001", "username": "Bharath Raj", "profilePictureUrl": "p1.jpeg", "teamId": 1}),
    TeamUserLookup.model_validate({"userId": 2, "cognitoId": "123e4567-e89b-12d3-a456-426614174002", "username": "Priya", "profilePictureUrl": "p2.jpeg", "teamId": 2}),
    TeamUserLookup.model_validate({"userId": 3, "cognitoId": "123e4567-e89b-12d3-a456-426614174003", "username": "Hitesh", "profilePictureUrl": "p3.jpeg", "teamId": 3}),
    TeamUserLookup.model_validate({"userId": 4, "cognitoId": "213b7530-1031-70e0-67e9-fe0805e18fb3", "username": "Naveen", "profilePictureUrl": "p4.jpeg", "teamId": 4}),
    TeamUserLookup.model_validate({"userId": 5, "cognitoId": "123e4567-e89b-12d3-a456-426614174005", "username": "EveClark", "profilePictureUrl": "p5.jpeg", "teamId": 5}),
    TeamUserLookup.model_validate({"userId": 6, "cognitoId": "123e4567-e89b-12d3-a456-426614174006", "username": "FrankWright", "profilePictureUrl": "p6.jpeg", "teamId": 1}),
    TeamUserLookup.model_validate({"userId": 7, "cognitoId": "123e4567-e89b-12d3-a456-426614174007", "username": "GraceHall", "profilePictureUrl": "p7.jpeg", "teamId": 2}),
    TeamUserLookup.model_validate({"userId": 8, "cognitoId": "123e4567-e89b-12d3-a456-426614174008", "username": "HenryAllen", "profilePictureUrl": "p8.jpeg", "teamId": 3}),
    TeamUserLookup.model_validate({"userId": 9, "cognitoId": "123e4567-e89b-12d3-a456-426614174009", "username": "IdaMartin", "profilePictureUrl": "p9.jpeg", "teamId": 4}),
    TeamUserLookup.model_validate({"userId": 10, "cognitoId": "123e4567-e89b-12d3-a456-426614174010", "username": "bharath", "profilePictureUrl": "p10.jpeg", "teamId": 5}),
    TeamUserLookup.model_validate({"userId": 11, "cognitoId": "123e4567-e89b-12d3-a456-426614174011", "username": "Vivek", "profilePictureUrl": "p11.jpeg", "teamId": 1}),
    TeamUserLookup.model_validate({"userId": 12, "cognitoId": "123e4567-e89b-12d3-a456-426614174012", "username": "NormanBates", "profilePictureUrl": "p12.jpeg", "teamId": 2}),
    TeamUserLookup.model_validate({"userId": 13, "cognitoId": "123e4567-e89b-12d3-a456-426614174013", "username": "OliviaPace", "profilePictureUrl": "p13.jpeg", "teamId": 3}),
    TeamUserLookup.model_validate({"userId": 14, "cognitoId": "123e4567-e89b-12d3-a456-426614174014", "username": "PeterQuill", "profilePictureUrl": "p1.jpeg", "teamId": 4}),
    TeamUserLookup.model_validate({"userId": 15, "cognitoId": "123e4567-e89b-12d3-a456-426614174015", "username": "QuincyAdams", "profilePictureUrl": "p2.jpeg", "teamId": 5}),
    TeamUserLookup.model_validate({"userId": 16, "cognitoId": "123e4567-e89b-12d3-a456-426614174016", "username": "RachelGreen", "profilePictureUrl": "p3.jpeg", "teamId": 1}),
    TeamUserLookup.model_validate({"userId": 17, "cognitoId": "123e4567-e89b-12d3-a456-426614174017", "username": "SteveJobs", "profilePictureUrl": "p4.jpeg", "teamId": 2}),
    TeamUserLookup.model_validate({"userId": 18, "cognitoId": "123e4567-e89b-12d3-a456-426614174018", "username": "TinaFey", "profilePictureUrl": "p5.jpeg", "teamId": 3}),
    TeamUserLookup.model_validate({"userId": 19, "cognitoId": "123e4567-e89b-12d3-a456-426614174019", "username": "UrsulaMonroe", "profilePictureUrl": "p6.jpeg", "teamId": 4}),
    TeamUserLookup.model_validate({"userId": 20, "cognitoId": "123e4567-e89b-12d3-a456-426614174020", "username": "VictorHugo", "profilePictureUrl": "p7.jpeg", "teamId": 5}),
]

# --- Helper Function for User Lookup ---

def find_username_by_id(user_id: Optional[int]) -> Optional[str]:
    """Simulates looking up a username by userId."""
    if user_id is None:
        return None
    
    # Use next() for efficient single item lookup
    user = next((u for u in DUMMY_USERS if u.user_id == user_id), None)
    return user.username if user else None


# --- APIRouter Setup ---

router = APIRouter()

# --- Controller Function (Equivalent to teamController.getTeams) ---

# GET /teams (Equivalent to router.get("/", getTeams))
@router.get("/", response_model=List[TeamResponse])
async def get_teams():
    """
    Retrieves all teams, augmenting them with Product Owner and Project Manager usernames.
    """
    try:
        teams = DUMMY_TEAMS

        teams_with_usernames = []
        for team in teams:
            product_owner_username = find_username_by_id(team.product_owner_user_id)
            project_manager_username = find_username_by_id(team.project_manager_user_id)

            response_data = team.model_dump(by_alias=True)
            
            teams_with_usernames.append(TeamResponse(
                **response_data,
                productOwnerUsername=product_owner_username,
                projectManagerUsername=project_manager_username
            ))
            
        return teams_with_usernames
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving teams: {e}")