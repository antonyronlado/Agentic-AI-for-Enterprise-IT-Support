from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import get_db
import hashlib
from typing import Optional

router = APIRouter(prefix="/auth", tags=["Auth"])

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class UserProfile(BaseModel):
    uid: str
    username: str
    email: str
    role: str

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@router.post("/register")
async def register(req: RegisterRequest, db=Depends(get_db)):
    existing = await db.users.find_one({"$or": [{"username": req.username}, {"email": req.email}]})
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    role = "user"
    if req.email.endswith("@admin.com") or req.email.endswith("@admin.it.com"):
        role = "admin"
        
    user_doc = {
        "username": req.username,
        "email": req.email,
        "password": hash_password(req.password),
        "role": role
    }
    
    result = await db.users.insert_one(user_doc)
    
    import time
    await db.admin_logs.insert_one({
        "action": "user_registered",
        "details": f"User '{req.username}' registered as '{role}'.",
        "timestamp": int(time.time() * 1000)
    })
    
    return {
        "uid": str(result.inserted_id),
        "username": req.username,
        "email": req.email,
        "role": role
    }

@router.post("/login")
async def login(req: LoginRequest, db=Depends(get_db)):
    login_id = req.username.strip()
    user = await db.users.find_one({"$or": [{"username": login_id}, {"email": login_id}]})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    if user["password"] != hash_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    import time
    await db.admin_logs.insert_one({
        "action": "user_logged_in",
        "details": f"User '{req.username}' logged in.",
        "timestamp": int(time.time() * 1000)
    })
        
    return {
        "uid": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "role": user["role"]
    }
