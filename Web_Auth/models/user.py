from datetime import datetime, timezone
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

class UserModel:
    def __init__(self, db):
        self.collection = db.users

    def find_by_email(self, email: str):
        return self.collection.find_one({"email": email.lower().strip()})

    def email_exists(self, email: str) -> bool:
        return self.find_by_email(email) is not None

    def create(self, name: str, email: str, password: str) -> str:
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
        result = self.collection.update_one(
            {"email": email.lower().strip()},
            {
                "$set": {
                    "password_hash": hash_password(new_password),
                    "last_reset_at": datetime.now(timezone.utc),
                    "must_change_password": temp,
                    "temp_password_hint": f"{new_password[:2]}{'*' * (len(new_password) - 4)}{new_password[-2:]}" if temp else None,
                }
            },
        )
        return result.modified_count > 0