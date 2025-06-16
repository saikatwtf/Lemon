import os
import logging
import motor.motor_asyncio
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class MongoDB:
    """MongoDB database connection and operations"""
    
    def __init__(self):
        """Initialize MongoDB connection"""
        self.uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        self.db_name = os.getenv("DB_NAME", "lemon_bot")
        
        try:
            # Synchronous client for initialization
            self.client = MongoClient(self.uri)
            self.db = self.client[self.db_name]
            
            # Async client for operations
            self.async_client = motor.motor_asyncio.AsyncIOMotorClient(self.uri)
            self.async_db = self.async_client[self.db_name]
            
            # Initialize collections
            self.chats = self.db.chats
            self.users = self.db.users
            self.warns = self.db.warns
            self.filters = self.db.filters
            self.notes = self.db.notes
            self.approvals = self.db.approvals
            self.federations = self.db.federations
            self.fed_bans = self.db.fed_bans
            
            # Async collections
            self.async_chats = self.async_db.chats
            self.async_users = self.async_db.users
            self.async_warns = self.async_db.warns
            self.async_filters = self.async_db.filters
            self.async_notes = self.async_db.notes
            self.async_approvals = self.async_db.approvals
            self.async_federations = self.async_db.federations
            self.async_fed_bans = self.async_db.fed_bans
            
            logger.info(f"Connected to MongoDB: {self.db_name}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    # User methods
    async def get_user(self, user_id):
        """Get user data from database"""
        return await self.async_users.find_one({"_id": user_id})
    
    async def update_user(self, user_id, user_data):
        """Update user data in database"""
        await self.async_users.update_one(
            {"_id": user_id},
            {"$set": user_data},
            upsert=True
        )
    
    # Chat methods
    async def get_chat(self, chat_id):
        """Get chat data from database"""
        return await self.async_chats.find_one({"_id": chat_id})
    
    async def update_chat(self, chat_id, chat_data):
        """Update chat data in database"""
        await self.async_chats.update_one(
            {"_id": chat_id},
            {"$set": chat_data},
            upsert=True
        )
    
    # Warning methods
    async def get_warns(self, chat_id, user_id):
        """Get warnings for a user in a chat"""
        return await self.async_warns.find_one({"chat_id": chat_id, "user_id": user_id})
    
    async def add_warn(self, chat_id, user_id, reason=None):
        """Add a warning for a user in a chat"""
        warn_data = await self.get_warns(chat_id, user_id) or {"chat_id": chat_id, "user_id": user_id, "warns": []}
        warn_data["warns"].append({"reason": reason, "count": len(warn_data["warns"]) + 1})
        
        await self.async_warns.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": warn_data},
            upsert=True
        )
        return len(warn_data["warns"])
    
    async def reset_warns(self, chat_id, user_id):
        """Reset warnings for a user in a chat"""
        await self.async_warns.delete_one({"chat_id": chat_id, "user_id": user_id})
    
    # Filter methods
    async def get_filters(self, chat_id):
        """Get all filters for a chat"""
        cursor = self.async_filters.find({"chat_id": chat_id})
        return await cursor.to_list(length=100)
    
    async def add_filter(self, chat_id, keyword, content, reply_markup=None):
        """Add a filter to a chat"""
        filter_data = {
            "chat_id": chat_id,
            "keyword": keyword.lower(),
            "content": content,
            "reply_markup": reply_markup
        }
        
        await self.async_filters.update_one(
            {"chat_id": chat_id, "keyword": keyword.lower()},
            {"$set": filter_data},
            upsert=True
        )
    
    async def remove_filter(self, chat_id, keyword):
        """Remove a filter from a chat"""
        result = await self.async_filters.delete_one({"chat_id": chat_id, "keyword": keyword.lower()})
        return result.deleted_count > 0
    
    # Note methods
    async def get_note(self, chat_id, note_name):
        """Get a note from a chat"""
        return await self.async_notes.find_one({"chat_id": chat_id, "name": note_name.lower()})
    
    async def get_all_notes(self, chat_id):
        """Get all notes for a chat"""
        cursor = self.async_notes.find({"chat_id": chat_id})
        return await cursor.to_list(length=100)
    
    async def save_note(self, chat_id, note_name, content, reply_markup=None):
        """Save a note to a chat"""
        note_data = {
            "chat_id": chat_id,
            "name": note_name.lower(),
            "content": content,
            "reply_markup": reply_markup
        }
        
        await self.async_notes.update_one(
            {"chat_id": chat_id, "name": note_name.lower()},
            {"$set": note_data},
            upsert=True
        )
    
    async def delete_note(self, chat_id, note_name):
        """Delete a note from a chat"""
        result = await self.async_notes.delete_one({"chat_id": chat_id, "name": note_name.lower()})
        return result.deleted_count > 0
    
    # Approval methods
    async def is_user_approved(self, chat_id, user_id):
        """Check if a user is approved in a chat"""
        approval = await self.async_approvals.find_one({"chat_id": chat_id, "user_id": user_id})
        return bool(approval)
    
    async def approve_user(self, chat_id, user_id):
        """Approve a user in a chat"""
        await self.async_approvals.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"chat_id": chat_id, "user_id": user_id}},
            upsert=True
        )
    
    async def disapprove_user(self, chat_id, user_id):
        """Disapprove a user in a chat"""
        result = await self.async_approvals.delete_one({"chat_id": chat_id, "user_id": user_id})
        return result.deleted_count > 0
    
    # Federation methods
    async def create_federation(self, fed_id, owner_id, fed_name):
        """Create a new federation"""
        fed_data = {
            "_id": fed_id,
            "owner_id": owner_id,
            "name": fed_name,
            "chats": [],
            "admins": []
        }
        
        await self.async_federations.insert_one(fed_data)
    
    async def get_federation(self, fed_id):
        """Get federation data"""
        return await self.async_federations.find_one({"_id": fed_id})
    
    async def add_fed_chat(self, fed_id, chat_id):
        """Add a chat to a federation"""
        await self.async_federations.update_one(
            {"_id": fed_id},
            {"$addToSet": {"chats": chat_id}}
        )
    
    async def remove_fed_chat(self, fed_id, chat_id):
        """Remove a chat from a federation"""
        await self.async_federations.update_one(
            {"_id": fed_id},
            {"$pull": {"chats": chat_id}}
        )
    
    async def fed_ban_user(self, fed_id, user_id, reason=None):
        """Ban a user from a federation"""
        ban_data = {
            "fed_id": fed_id,
            "user_id": user_id,
            "reason": reason
        }
        
        await self.async_fed_bans.update_one(
            {"fed_id": fed_id, "user_id": user_id},
            {"$set": ban_data},
            upsert=True
        )
    
    async def fed_unban_user(self, fed_id, user_id):
        """Unban a user from a federation"""
        result = await self.async_fed_bans.delete_one({"fed_id": fed_id, "user_id": user_id})
        return result.deleted_count > 0
    
    async def is_user_fed_banned(self, fed_id, user_id):
        """Check if a user is banned in a federation"""
        ban = await self.async_fed_bans.find_one({"fed_id": fed_id, "user_id": user_id})
        return bool(ban)