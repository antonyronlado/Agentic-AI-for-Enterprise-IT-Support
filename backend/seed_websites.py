"""
seed_websites.py - Run this ONCE to auto-register Web_Auth in the Unisys registry.
No Postman needed.

Usage:
    Activate Unisys venv, then run:
    python seed_websites.py
"""

import sys
from datetime import datetime
from pymongo import MongoClient

MONGO_URI    = "mongodb://localhost:27017/agentic_ai"
WEBSITE_NAME = "Web_Auth"
RESET_URL    = "http://localhost:5000/api/reset-password"
API_KEY      = "unisys-reset-secret-key-2024"
DESCRIPTION  = "Main Web_Auth authentication portal"


def seed():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        client.server_info()
    except Exception as e:
        print("\n[ERROR] Cannot connect to MongoDB at " + MONGO_URI)
        print("   Make sure MongoDB is running first, then run this script again.")
        print("   Error: " + str(e)[:120])
        sys.exit(1)

    db  = client["agentic_ai"]
    col = db["websites"]

    existing = col.find_one({"name": {"$regex": f"^{WEBSITE_NAME}$", "$options": "i"}})
    if existing:
        print("\n[OK] '" + WEBSITE_NAME + "' is already registered in Unisys. Nothing to do.\n")
        return

    now = int(datetime.now().timestamp() * 1000)
    col.insert_one({
        "name":        WEBSITE_NAME,
        "reset_url":   RESET_URL,
        "api_key":     API_KEY,
        "description": DESCRIPTION,
        "created_at":  now,
    })

    print("\n[SUCCESS] '" + WEBSITE_NAME + "' registered in Unisys!")
    print("   Name      : " + WEBSITE_NAME)
    print("   Reset URL : " + RESET_URL)
    print("   Description: " + DESCRIPTION)
    print("\nYou can now raise a password reset ticket in Unisys.")
    print("The AI agent will automatically reset the password on " + WEBSITE_NAME + ".\n")


if __name__ == "__main__":
    seed()
