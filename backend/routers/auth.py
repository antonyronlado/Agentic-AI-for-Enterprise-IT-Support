import secrets
import time
import logging
import bcrypt
import random
import string
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, field_validator
from database import get_db
from typing import Optional

import re

logger = logging.getLogger("nexusdesk.auth")

router = APIRouter(prefix="/auth", tags=["Auth"])

_BCRYPT_ROUNDS = 12

otp_store: dict = {}

_login_attempts: dict[str, list[float]] = {}
_MAX_ATTEMPTS   = 10
_WINDOW_SECONDS = 60
_MAX_IPS_STORED = 5000   # prevent unbounded memory growth

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

def _valid_email(email: str) -> bool:
    return bool(email and len(email) <= 254 and _EMAIL_RE.match(email))


def _check_rate_limit(ip: str):
    now      = time.time()
    attempts = _login_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < _WINDOW_SECONDS]
    if len(attempts) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many login attempts. Please wait {_WINDOW_SECONDS} seconds.",
        )
    attempts.append(now)
    _login_attempts[ip] = attempts
    # Prune oldest IPs to prevent unbounded memory growth
    if len(_login_attempts) > _MAX_IPS_STORED:
        oldest_ip = next(iter(_login_attempts))
        del _login_attempts[oldest_ip]


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


def _generate_token() -> str:
    return secrets.token_hex(32)


def _hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(_BCRYPT_ROUNDS))


def _verify_password(password: str, hashed) -> bool:
    if isinstance(hashed, str):
        hashed = hashed.encode("utf-8")
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed)
    except Exception:
        return False


def _is_legacy_sha256(hashed) -> bool:
    h = hashed.decode("utf-8") if isinstance(hashed, bytes) else hashed
    return (
        len(h) == 64
        and all(c in "0123456789abcdef" for c in h)
        and not h.startswith("$2b$")
    )


def _verify_legacy_sha256(password: str, hashed) -> bool:
    import hashlib
    h = hashed.decode("utf-8") if isinstance(hashed, bytes) else hashed
    return hashlib.sha256(password.encode()).hexdigest() == h


@router.post("/register")
async def register(req: RegisterRequest, db=Depends(get_db)):
    existing = await db.users.find_one(
        {"$or": [{"username": req.username}, {"email": req.email}]}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    # Role is set to "user" by default.
    # Admin accounts must be promoted manually via the database — never via email.
    role = "user"

    token = _generate_token()
    user_doc = {
        "username":  req.username,
        "email":     req.email,
        "password":  _hash_password(req.password),
        "role":      role,
        "auth_token": token,
        "token_created_at": int(time.time() * 1000),
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
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    user = await db.users.find_one(
        {"$or": [{"username": req.username}, {"email": req.username}]}
    )

    password_ok = False
    needs_migration = False

    if user:
        stored = user["password"]
        if _is_legacy_sha256(stored):
            password_ok = _verify_legacy_sha256(req.password, stored)
            needs_migration = password_ok
        else:
            password_ok = _verify_password(req.password, stored)
    else:
        _verify_password(req.password, bcrypt.hashpw(b"dummy", bcrypt.gensalt(4)))

    if not password_ok or not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    new_token = _generate_token()
    update_fields: dict = {
        "auth_token": new_token,
        "token_created_at": int(time.time() * 1000),
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


def generate_otp(length: int = 6) -> str:
    return "".join(random.choice(string.digits) for _ in range(length))


def _send_email(to_email: str, subject: str, body: str) -> bool:
    try:
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        sender_email = os.getenv("SENDER_EMAIL")

        if not all([smtp_server, smtp_user, smtp_password, sender_email]):
            print("SMTP configuration incomplete — email not sent")
            return False

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(sender_email, to_email, msg.as_string())

        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _valid_email(v):
            raise ValueError("Invalid email address format")
        return v


class VerifyOTPRequest(BaseModel):
    email: str
    otp:   str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _valid_email(v):
            raise ValueError("Invalid email address format")
        return v

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError("OTP must be exactly 6 digits")
        return v


class ResetPasswordRequest(BaseModel):
    email:        str
    new_password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _valid_email(v):
            raise ValueError("Invalid email address format")
        return v

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db=Depends(get_db)):
    user = await db.users.find_one({"email": req.email})
    if not user:
        return {"message": "If the email exists, an OTP has been sent"}

    otp = generate_otp()
    expires = int(time.time() * 1000) + 5 * 60 * 1000

    otp_store[req.email] = {"otp": otp, "expires": expires}

    email_subject = "Password Reset OTP - NexusDesk"
    email_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #333;">Password Reset Request</h2>
        <p>You requested to reset your password. Use the following OTP:</p>
        <div style="background: #f0f0f0; padding: 15px; border-radius: 8px; font-size: 24px; font-weight: bold; text-align: center; letter-spacing: 5px;">
            {otp}
        </div>
        <p style="color: #666; font-size: 12px; margin-top: 20px;">
            This OTP will expire in 5 minutes.<br>
            If you didn't request this, please ignore this email.
        </p>
    </body>
    </html>
    """

    sent = _send_email(req.email, email_subject, email_body)

    if not sent:
        print("\n" + "="*50)
        print(f"  📧 OTP FOR: {req.email}")
        print(f"  🔑 OTP CODE: {otp}")
        print(f"  ⏰ Expires in 5 minutes")
        print("="*50 + "\n")
        logger.warning("EMAIL NOT SENT — OTP printed to console above")

    return {"message": "If the email exists, an OTP has been sent"}


@router.post("/verify-otp")
async def verify_otp(req: VerifyOTPRequest, db=Depends(get_db)):
    stored = otp_store.get(req.email)

    if not stored:
        raise HTTPException(status_code=400, detail="No OTP requested for this email")

    if int(time.time() * 1000) > stored["expires"]:
        del otp_store[req.email]
        raise HTTPException(status_code=400, detail="OTP has expired")

    if stored["otp"] != req.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    otp_store[req.email]["verified"] = True

    return {"message": "OTP verified successfully", "verified": True}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db=Depends(get_db)):
    stored = otp_store.get(req.email)

    if not stored:
        raise HTTPException(status_code=400, detail="No OTP verification found")

    if not stored.get("verified", False):
        raise HTTPException(status_code=400, detail="Please verify OTP first")

    if int(time.time() * 1000) > stored.get("expires", 0):
        del otp_store[req.email]
        raise HTTPException(status_code=400, detail="OTP has expired")

    # Use bcrypt — consistent with register/login endpoints
    hashed_password = _hash_password(req.new_password)

    result = await db.users.update_one(
        {"email": req.email},
        {"$set": {"password": hashed_password}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Failed to reset password")

    del otp_store[req.email]

    await db.admin_logs.insert_one({
        "action": "password_reset",
        "details": f"Password reset for email '{req.email}'.",
        "timestamp": int(time.time() * 1000)
    })

    return {"message": "Password reset successfully"}


@router.post("/logout")
async def logout(request: Request, db=Depends(get_db)):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token:
            await db.users.update_one(
                {"auth_token": token},
                {"$unset": {"auth_token": "", "token_created_at": ""}}
            )
    return {"message": "Logged out successfully"}