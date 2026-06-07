import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-flask-secret-change-me")

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/web_auth")

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

    RESET_API_KEY = os.getenv("RESET_API_KEY", "unisys-reset-secret-key-2024")

    WEBSITE_NAME = os.getenv("WEBSITE_NAME", "Web_Auth")