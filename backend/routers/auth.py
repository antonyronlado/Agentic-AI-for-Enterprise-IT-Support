import secrets
import time
import logging
import bcrypt
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, field_validator
from database import get_db
from typing import Optional

logger = logging.getLogger("nexusdesk.auth")

router = APIRouter(prefix="/auth", tags=["Auth"])

_BCRYPT_ROUNDS = 12   # cost factor — increase for stronger hashing

# ── Simple in-process rate limiter for login (IP → [timestamps]) ──────────
_login_attempts: dict[str, list[float]] = {}
_MAX_ATTEMPTS = 10      # per window
_WINDOW_SECONDS = 60    # rolling window


def _check_rate_limit(ip: str):
    now = time.time()
    attempts = _login_attempts.get(ip, [])
    # Prune old timestamps outside the window
    attempts = [t for t in attempts if now - t < _WINDOW_SECONDS]
    if len(attempts) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many login attempts. Please wait {_WINDOW_SECONDS} seconds.",
        )
    attempts.append(now)
    _login_attempts[ip] = attempts


# ── Input models ───────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def username_length(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be 3–50 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def strip_username(cls, v: str) -> str:
        return v.strip()[:100]


# ── Token helper ───────────────────────────────────────────────────────────
def _generate_token() -> str:
    return secrets.token_hex(32)   # 256-bit cryptographically random token


# ── Password helpers (bcrypt — auto-salted, resistant to rainbow tables) ───
def _hash_password(password: str) -> bytes:
    """Hash password with bcrypt (auto-salted, cost factor 12)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(_BCRYPT_ROUNDS))


def _verify_password(password: str, hashed) -> bool:
    """Constant-time bcrypt verification."""
    if isinstance(hashed, str):
        hashed = hashed.encode("utf-8")
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed)
    except Exception:
        return False


def _is_legacy_sha256(hashed) -> bool:
    """Detect old SHA-256 hex strings (64 lowercase hex chars, no bcrypt prefix)."""
    h = hashed.decode("utf-8") if isinstance(hashed, bytes) else hashed
    return (
        len(h) == 64
        and all(c in "0123456789abcdef" for c in h)
        and not h.startswith("$2b$")
    )


def _verify_legacy_sha256(password: str, hashed) -> bool:
    """Verify against the old SHA-256 hash (migration only)."""
    import hashlib
    h = hashed.decode("utf-8") if isinstance(hashed, bytes) else hashed
    return hashlib.sha256(password.encode()).hexdigest() == h


# ── Endpoints ──────────────────────────────────────────────────────────────
@router.post("/register")
async def register(req: RegisterRequest, db=Depends(get_db)):
    existing = await db.users.find_one(
        {"$or": [{"username": req.username}, {"email": req.email}]}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    # All new users default to 'user'. Admin role must be set manually in DB.
    role = "user"

    token = _generate_token()
    user_doc = {
        "username":  req.username,
        "email":     req.email,
        "password":  _hash_password(req.password),   # bcrypt + auto-salt
        "role":      role,
        "auth_token": token,
        "created_at": int(time.time() * 1000),
    }

    result = await db.users.insert_one(user_doc)

    await db.admin_logs.insert_one({
        "action":    "user_registered",
        "details":   f"User '{req.username}' registered as '{role}'.",
        "timestamp": int(time.time() * 1000),
    })

    return {
        "uid":         str(result.inserted_id),
        "username":    req.username,
        "email":       req.email,
        "role":        role,
        "auth_token":  token,
    }


@router.post("/login")
async def login(req: LoginRequest, request: Request, db=Depends(get_db)):
    # Rate-limit by client IP
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    # Look up user — support login by username or email
    user = await db.users.find_one(
        {"$or": [{"username": req.username}, {"email": req.username}]}
    )

    # ── Password verification with silent SHA-256 → bcrypt migration ──────
    # If the stored hash is an old SHA-256 hex string (64 chars, no $2b$ prefix),
    # we verify it using SHA-256. On success we immediately re-hash with bcrypt
    # and save it. After this point the user is fully migrated — all their
    # existing tickets, history and data remain completely untouched.
    password_ok = False
    needs_migration = False

    if user:
        stored = user["password"]
        if _is_legacy_sha256(stored):
            # Old SHA-256 hash detected — try legacy verification
            password_ok = _verify_legacy_sha256(req.password, stored)
            needs_migration = password_ok   # only migrate if password was correct
        else:
            # Modern bcrypt hash — normal verification
            password_ok = _verify_password(req.password, stored)
    else:
        # User not found — still do a dummy bcrypt check to prevent timing attacks
        _verify_password(req.password, bcrypt.hashpw(b"dummy", bcrypt.gensalt(4)))

    if not password_ok or not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # ── Silent password upgrade (SHA-256 → bcrypt) ────────────────────────
    # Happens transparently on first login after the security update.
    # The user never notices — they just log in normally.
    new_token = _generate_token()
    update_fields: dict = {
        "auth_token": new_token,
        "last_login":  int(time.time() * 1000),
    }
    if needs_migration:
        update_fields["password"] = _hash_password(req.password)
        logger.info(
            "Password migrated SHA-256→bcrypt for user '%s' — all data preserved.",
            user["username"],
        )

    await db.users.update_one({"_id": user["_id"]}, {"$set": update_fields})

    await db.admin_logs.insert_one({
        "action":    "user_logged_in",
        "details":   (
            f"User '{user['username']}' logged in from {client_ip}."
            + (" [password upgraded SHA-256→bcrypt]" if needs_migration else "")
        ),
        "timestamp": int(time.time() * 1000),
    })

    return {
        "uid":        str(user["_id"]),
        "username":   user["username"],
        "email":      user["email"],
        "role":       user["role"],
        "auth_token": new_token,
    }


@router.get("/me")
async def get_me(request: Request, db=Depends(get_db)):
    """Validate session token and return fresh user profile from DB."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    user = await db.users.find_one({"auth_token": token})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    return {
        "uid":      str(user["_id"]),
        "username": user["username"],
        "email":    user["email"],
        "role":     user["role"],
    }
