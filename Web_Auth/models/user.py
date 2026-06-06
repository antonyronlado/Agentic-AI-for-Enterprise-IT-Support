from datetime import datetime, timezone
import bcrypt


def hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password: str, hashed: str) -> bool:
    """Verify a plain-text password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


class UserModel:
    def __init__(self, db):
        self.collection = db.users

    def find_by_email(self, email: str):
        """Find a user by email (case-insensitive)."""
        return self.collection.find_one({"email": email.lower().strip()})

    def email_exists(self, email: str) -> bool:
        """Check if an email is already registered."""
        return self.find_by_email(email) is not None

    def create(self, name: str, email: str, password: str) -> str:
        """Create a new user and return their inserted ID."""
        user = {
            "name": name.strip(),
            "email": email.lower().strip(),
            "password_hash": hash_password(password),
            "created_at": datetime.now(timezone.utc),
            "last_reset_at": None,
            "must_change_password": False,
            "temp_password_hint": None,
        }
        result = self.collection.insert_one(user)
        return str(result.inserted_id)

    def update_password(self, email: str, new_password: str, temp: bool = False) -> bool:
        """
        Reset a user's password.
        If temp=True, flag the account so the user is prompted to change it on next login.
        """
        result = self.collection.update_one(
            {"email": email.lower().strip()},
            {
                "$set": {
                    "password_hash": hash_password(new_password),
                    "last_reset_at": datetime.now(timezone.utc),
                    "must_change_password": temp,
                    # Store only a masked hint — never store plain temp password
                    "temp_password_hint": f"{new_password[:2]}{'*' * (len(new_password) - 4)}{new_password[-2:]}" if temp else None,
                }
            },
        )
        return result.modified_count > 0
