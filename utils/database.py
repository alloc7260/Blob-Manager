"""
MongoDB database connection and user management
"""

import os
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is required")

client = MongoClient(MONGO_URI)
db = client["blob-manager"]
users_collection = db["users"]

# Create unique index on username
users_collection.create_index([("username", ASCENDING)], unique=True)


class UserDB:
    """User database operations"""
    
    @staticmethod
    def create_user(username: str, totp_secret: str, blob_sas_url: str) -> Dict:
        """Create a new user"""
        try:
            user_data = {
                "username": username,
                "totp_secret": totp_secret,
                "blob_sas_url": blob_sas_url
            }
            result = users_collection.insert_one(user_data)
            user_data["_id"] = str(result.inserted_id)
            return user_data
        except DuplicateKeyError:
            raise ValueError("Username already exists")
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict]:
        """Get user by username"""
        user = users_collection.find_one({"username": username})
        if user:
            user["_id"] = str(user["_id"])
        return user
    
    @staticmethod
    def username_exists(username: str) -> bool:
        """Check if username exists"""
        return users_collection.count_documents({"username": username}) > 0
    
    @staticmethod
    def update_blob_sas_url(username: str, blob_sas_url: str) -> bool:
        """Update user's blob SAS URL"""
        result = users_collection.update_one(
            {"username": username},
            {"$set": {"blob_sas_url": blob_sas_url}}
        )
        return result.modified_count > 0
