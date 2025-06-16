import os
from telegram import Update, ChatPermissions
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, Filters as TgFilters
from telegram.error import BadRequest
import time

from lemon.utils.decorators import admin_only, bot_admin, send_typing
from lemon.database import db

# Default flood settings
DEFAULT_FLOOD_LIMIT = 5
DEFAULT_FLOOD_MODE = "mute"
DEFAULT_FLOOD_TIME = 300  # 5 minutes

# Store user message counts
flood_data = {}

# Check for flooding
async def check_flood(update: Update, context: CallbackContext) -> None:
    """Check if a user is flooding the chat"""
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    
    # Skip in private chats
    if chat.type == "private":
        return
    
    # Skip for admins
    try:
        member = chat.get_member(user.id)
        if member.status in ["administrator", "creator"]:
            return
    except BadRequest:
        return
    
    # Get chat settings
    chat_data = await db.get_chat(chat.id) or {}
    flood_settings = chat_data.get("flood", {})
    
    # Get flood limit
    flood_limit = flood_settings.get("limit", DEFAULT_FLOOD_LIMIT)
    
    # Skip if flood protection is disabled
    if flood_limit <= 0:
        return
    
    # Get flood mode
    flood_mode = flood_settings.get("mode", DEFAULT_FLOOD_MODE)
    flood_time = flood_settings.get("time", DEFAULT_FLOOD_TIME)
    
    # Initialize flood data for chat if not exists
    if chat.id not in flood_data:
        flood_data[chat.id] = {}
    
    # Initialize flood data for user if not exists
    if user.id not in flood_data[chat.id]:
        flood_data[chat.id][user.id] = {
            "count": 0,
            "last_msg_time": time.time()
        }
    
    # Reset count if more than 5 seconds since last message
    if time.time() - flood_data[chat.id][user.id]["last_msg_time"] > 5:
        flood_data[chat.id][user.id]["count"] = 0
    
    # Update flood data
    flood_data[chat.id][user.id]["count"] += 1
    flood_data[chat.id][user.id]["last_msg_time"] = time.time()
    
    # Check if user has exceeded flood limit
    if flood_data[chat.id][user.id]["count"] >= flood_limit:
        # Reset flood count
        flood_data[chat.id][user.id]["count"] = 0
        
        # Apply flood action
        try:
            if flood_mode == "ban":
                chat.kick_member(user.id)
                message.reply_text(f"{user.first_name} has been banned for flooding.")
            elif flood_mode == "kick":
                chat.kick_member(user.id)
                chat.unban_member(user.id)
                message.reply_text(f"{user.first_name} has been kicked for flooding.")
            elif flood_mode == "mute":
                chat.restrict_member(
                    user.id,
                    permissions=ChatPermissions(
                        can_send_messages=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False
                    ),
                    until_date=time.time() + flood_time
                )
                message.reply_text(
                    f"{user.first_name} has been muted for {flood_time // 60} minutes for flooding."
                )
            
            # Log the action
            if context.bot.log_channel:
                context.bot.send_message(
                    chat_id=context.bot.log_channel,
                    text=f"#FLOOD_CONTROL\n"
                         f"User: {user.first_name} (ID: {user.id})\n"
                         f"Chat: {chat.title} (ID: {chat.id})\n"
                         f"Action: {flood_mode.capitalize()}\n"
                         f"Flood limit: {flood_limit} messages"
                )
        except BadRequest as e:
            message.reply_text(f"Error applying flood action: {e.message}")

# Set flood limit
@send_typing
@bot_admin
@admin_only
async def set_flood(update: Update, context: CallbackContext) -> None:
    """Set flood limit for the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if command has arguments
    if not context.args:
        # Get current settings
        chat_data = await db.get_chat(chat.id) or {}
        flood_settings = chat_data.get("flood", {})
        
        flood_limit = flood_settings.get("limit", DEFAULT_FLOOD_LIMIT)
        flood_mode = flood_settings.get("mode", DEFAULT_FLOOD_MODE)
        flood_time = flood_settings.get("time", DEFAULT_FLOOD_TIME)
        
        if flood_limit <= 0:
            message.reply_text("Flood control is currently disabled in this chat.")
        else:
            message.reply_text(
                f"Current flood settings:\n"
                f"Limit: {flood_limit} messages\n"
                f"Mode: {flood_mode}\n"
                f"Time (for mute): {flood_time // 60} minutes\n\n"
                f"To change settings, use:\n"
                f"/setflood [limit] [mode] [time]\n"
                f"Example: /setflood 5 mute 300\n"
                f"Set limit to 0 to disable flood control."
            )
        return
    
    # Parse arguments
    try:
        flood_limit = int(context.args[0])
        
        # Check if limit is valid
        if flood_limit < 0:
            message.reply_text("Flood limit must be 0 or higher.")
            return
        
        # Get mode if provided
        flood_mode = DEFAULT_FLOOD_MODE
        if len(context.args) > 1:
            mode = context.args[1].lower()
            if mode in ["ban", "kick", "mute"]:
                flood_mode = mode
        
        # Get time if provided
        flood_time = DEFAULT_FLOOD_TIME
        if len(context.args) > 2:
            try:
                flood_time = int(context.args[2])
                if flood_time < 30:
                    flood_time = 30  # Minimum 30 seconds
            except ValueError:
                pass
        
        # Update chat settings
        chat_data = await db.get_chat(chat.id) or {}
        if "flood" not in chat_data:
            chat_data["flood"] = {}
        
        chat_data["flood"]["limit"] = flood_limit
        chat_data["flood"]["mode"] = flood_mode
        chat_data["flood"]["time"] = flood_time
        
        await db.update_chat(chat.id, chat_data)
        
        if flood_limit == 0:
            message.reply_text("Flood control has been disabled in this chat.")
        else:
            message.reply_text(
                f"Flood settings updated:\n"
                f"Limit: {flood_limit} messages\n"
                f"Mode: {flood_mode}\n"
                f"Time (for mute): {flood_time // 60} minutes"
            )
    except ValueError:
        message.reply_text("Please provide a valid number for the flood limit.")

# Get flood settings
@send_typing
async def get_flood(update: Update, context: CallbackContext) -> None:
    """Get flood settings for the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Get current settings
    chat_data = await db.get_chat(chat.id) or {}
    flood_settings = chat_data.get("flood", {})
    
    flood_limit = flood_settings.get("limit", DEFAULT_FLOOD_LIMIT)
    flood_mode = flood_settings.get("mode", DEFAULT_FLOOD_MODE)
    flood_time = flood_settings.get("time", DEFAULT_FLOOD_TIME)
    
    if flood_limit <= 0:
        message.reply_text("Flood control is currently disabled in this chat.")
    else:
        message.reply_text(
            f"Current flood settings:\n"
            f"Limit: {flood_limit} messages\n"
            f"Mode: {flood_mode}\n"
            f"Time (for mute): {flood_time // 60} minutes"
        )

# Define handlers
HANDLERS = [
    CommandHandler("setflood", set_flood, filters=~TgFilters.private),
    CommandHandler("flood", get_flood, filters=~TgFilters.private),
    MessageHandler(TgFilters.text & ~TgFilters.command & ~TgFilters.private, check_flood)
]