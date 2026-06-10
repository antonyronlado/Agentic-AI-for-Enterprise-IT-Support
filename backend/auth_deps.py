import time
from fastapi import Depends, HTTPException, Request
from database import get_db

async def _get_current_user(request: Request, db=Depends(get_db)) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")
    user = await db.users.find_one({"auth_token": token})
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check session expiration (24 hours)
    created_at = user.get("token_created_at")
    if not created_at or int(time.time() * 1000) - created_at > 24 * 60 * 60 * 1000:
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return user

async def require_auth(user: dict = Depends(_get_current_user)) -> dict:
    return user

async def require_admin(user: dict = Depends(_get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user