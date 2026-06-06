from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime
from bson import ObjectId

from database import get_db
from auth_deps import require_admin

router = APIRouter(prefix="/websites", tags=["Website Registry"])


class WebsiteCreate(BaseModel):
    name: str
    reset_url: str
    api_key: str
    description: Optional[str] = ""


class WebsiteOut(BaseModel):
    id: str
    name: str
    reset_url: str
    description: str
    created_at: int


@router.get("", response_model=List[WebsiteOut])
async def list_websites(db=Depends(get_db), _user=Depends(require_admin)):
    cursor = db.websites.find({})
    sites = await cursor.to_list(length=100)
    return [
        {
            "id": str(s["_id"]),
            "name": s["name"],
            "reset_url": s["reset_url"],
            "description": s.get("description", ""),
            "created_at": s.get("created_at", 0),
        }
        for s in sites
    ]


@router.get("/public", response_model=List[dict])
async def list_websites_public(db=Depends(get_db)):
    cursor = db.websites.find({}, {"name": 1, "_id": 0})
    sites = await cursor.to_list(length=100)
    return [{"name": s["name"]} for s in sites]


@router.post("", response_model=WebsiteOut)
async def register_website(
    payload: WebsiteCreate,
    db=Depends(get_db),
    _user=Depends(require_admin),
):
    existing = await db.websites.find_one({"name": {"$regex": f"^{payload.name}$", "$options": "i"}})
    if existing:
        raise HTTPException(status_code=409, detail=f"Website '{payload.name}' is already registered.")

    now = int(datetime.now().timestamp() * 1000)
    doc = {
        "name": payload.name.strip(),
        "reset_url": payload.reset_url.strip(),
        "api_key": payload.api_key.strip(),
        "description": (payload.description or "").strip(),
        "created_at": now,
    }
    result = await db.websites.insert_one(doc)
    return {
        "id": str(result.inserted_id),
        "name": doc["name"],
        "reset_url": doc["reset_url"],
        "description": doc["description"],
        "created_at": doc["created_at"],
    }


@router.delete("/{website_id}")
async def delete_website(
    website_id: str,
    db=Depends(get_db),
    _user=Depends(require_admin),
):
    try:
        oid = ObjectId(website_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid website ID")
    result = await db.websites.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Website not found")
    return {"message": "Website removed from registry successfully"}