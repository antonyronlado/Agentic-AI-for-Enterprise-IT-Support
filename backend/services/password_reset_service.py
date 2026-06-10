import hashlib
import logging
import random
import re
import string

from bson import ObjectId

logger = logging.getLogger("nexusdesk.password_reset")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_temp_password(length: int = 10) -> str:
    chars = string.ascii_letters + string.digits + "!@#$"
    return "".join(random.choice(chars) for _ in range(length))

def is_password_reset_request(title: str, description: str) -> bool:
    text = f"{title} {description}".lower()
    triggers = (
        "password", "forgot pass", "reset pass", "change pass",
        "locked out", "cannot login", "can't login", "cannot log in",
        "forgot my login", "forgot credentials",
    )
    return any(t in text for t in triggers)

def validate_preferred_password(password: str | None) -> str | None:

    if not password or not password.strip():
        return "Please enter a new password (at least 6 characters)."
    if len(password.strip()) < 6:
        return "Password must be at least 6 characters."
    if len(password) > 128:
        return "Password must be 128 characters or fewer."
    return None

def build_reset_messages(new_password: str, user_chosen: bool = False) -> tuple[str, str]:
    if user_chosen:
        employee_response = (
            "Your password has been updated to the one you chose.\n\n"
            f"Your new password is:\n{new_password}\n\n"
            "You can log in with this password right away."
        )
    else:
        employee_response = (
            "Great news — your password has been reset automatically.\n\n"
            f"Your new password is:\n{new_password}\n\n"
            "Use this password to log in, then change it to something only you know."
        )
    admin_label = "User-chosen" if user_chosen else "Auto-generated"
    admin_response = (
        f"Automated password reset completed ({admin_label}). "
        f"Temporary password: {new_password}"
    )
    return employee_response, admin_response

AWAITING_CONFIRM_MESSAGE = (
    "We detected a password reset request for your account.\n\n"
    "Before AI can change your password, please confirm below:\n"
    "• Allow AI to reset your password\n"
    "• Choose auto-generate OR set your own new password\n\n"
    "Use the confirmation panel below to proceed."
)

def extract_requested_password(text: str) -> str | None:
    if not text:
        return None
    patterns = [
        r'(?i)(?:new|set|change)\s+password\s+(?:to|:)\s*["\'"]?(\S+)["\'"]?',
        r'(?i)password\s+(?:to|:)\s*["\'"]?(\S+)["\'"]?',
    ]
    skip = {"my", "a", "the", "account", "below", "please"}
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        pwd = match.group(1).strip('"\'.,;')
        if len(pwd) >= 6 and pwd.lower() not in skip:
            return pwd
    return None

async def apply_password_reset(
    db,
    user_id: str | None,
    user_email: str | None,
    requested_password: str | None = None,
    user_chosen: bool = False,
) -> dict:
    if user_chosen and requested_password:
        err = validate_preferred_password(requested_password)
        if err:
            return {"success": False, "error": err}
    new_password = requested_password or generate_temp_password()

    user = None
    if user_id:
        try:
            user = await db.users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            pass
    if not user and user_email:
        user = await db.users.find_one({"email": user_email})
    if not user and user_email:
        prefix = user_email.split("@")[0]
        user = await db.users.find_one(
            {"email": {"$regex": f"^{re.escape(prefix)}@", "$options": "i"}}
        )

    if not user:
        logger.warning("Password reset failed — no user for id=%s email=%s", user_id, user_email)
        return {"success": False, "error": "User account not found"}

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password": hash_password(new_password)}},
    )

    username = user.get("username") or user.get("email") or "your account"
    logger.info("Password reset applied for user=%s email=%s", username, user.get("email"))

    employee_response, admin_response = build_reset_messages(
        new_password, user_chosen=bool(user_chosen and requested_password)
    )

    return {
        "success": True,
        "new_password": new_password,
        "username": username,
        "email": user.get("email"),
        "employee_response": employee_response,
        "admin_response": (
            f"{admin_response} Account: '{username}' ({user.get('email')})."
        ),
    }