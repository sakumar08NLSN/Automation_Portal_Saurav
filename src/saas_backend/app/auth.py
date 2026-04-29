# from fastapi import Request, HTTPException, status
# from jose import jwt
# import requests

# ISSUER = "https://nielsen.okta.com/oauth2/default"
# JWKS_URL = f"{ISSUER}/v1/keys"

# async def verify_okta_token(request: Request):
#     # ⚠️ TEMPORARY LOCAL BYPASS ⚠️
#     if "localhost" in str(request.url):
#         return {"sub": "local-dev-user", "preferred_username": "Local Admin"}
#     auth_header = request.headers.get("Authorization")
#     if not auth_header or not auth_header.startswith("Bearer "):
#         raise HTTPException(status_code=401, detail="Missing or invalid token")

#     token = auth_header.split(" ")[1]
    
#     try:
#         jwks = requests.get(JWKS_URL).json()
#         payload = jwt.decode(
#             token, 
#             jwks, 
#             algorithms=['RS256'], 
#             audience="api://default", 
#             issuer=ISSUER
#         )
#         return payload
#     except Exception as e:
#         raise HTTPException(status_code=401, detail=f"Invalid Okta token: {str(e)}")


import os
from fastapi import Request, HTTPException, status
from jose import jwt
import requests

ISSUER = "https://nielsen.okta.com/oauth2/default"
JWKS_URL = f"{ISSUER}/v1/keys"

async def verify_okta_token(request: Request):
    # 🚨 TEMPORARY LOCAL BYPASS 🚨
    # If APP_MODE is dev (via start.sh), bypass Okta and inject your real Okta ID
    if os.getenv("APP_MODE") == "dev":
        return {
            "sub": "00u23vc7vi2VW8tBj0h8", # This ensures your DB looks up your actual data!
            "preferred_username": "Local Admin"
        }
    
    # --- NORMAL PRODUCTION OKTA VERIFICATION ---
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth_header.split(" ")[1]
    
    try:
        jwks = requests.get(JWKS_URL).json()
        payload = jwt.decode(
            token, 
            jwks, 
            algorithms=['RS256'], 
            audience="api://default", 
            issuer=ISSUER
        )
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Okta token: {str(e)}")