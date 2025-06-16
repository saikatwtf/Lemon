import functools
from typing import Callable, Any
from telegram import Update, ChatMember
from telegram.ext import CallbackContext

def send_typing(func: Callable) -> Callable:
    """Send typing action while processing command."""
    @functools.wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs) -> Any:
        if update.effective_chat.type != "private":
            context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="typing"
            )
        return func(update, context, *args, **kwargs)
    return wrapper

def admin_only(func: Callable) -> Callable:
    """Restrict command to admins only."""
    @functools.wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs) -> Any:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Check if user is a bot admin
        from lemon.core.bot import LemonBot
        bot_instance = context.bot._bot_instance if hasattr(context.bot, '_bot_instance') else None
        
        # If the user is in SUDO_USERS environment variable
        sudo_users = []
        import os
        owner_id = os.getenv("OWNER_ID")
        if owner_id and owner_id.isdigit():
            sudo_users.append(int(owner_id))
        
        sudo_users_env = os.getenv("SUDO_USERS", "")
        if sudo_users_env:
            sudo_users.extend([int(user_id) for user_id in sudo_users_env.split(",") if user_id.strip().isdigit()])
        
        if user_id in sudo_users:
            return func(update, context, *args, **kwargs)
        
        # Check if user is a chat admin
        try:
            member = context.bot.get_chat_member(chat_id, user_id)
            if member.status in ["administrator", "creator"]:
                return func(update, context, *args, **kwargs)
            else:
                update.message.reply_text("This command is restricted to admins only.")
                return None
        except Exception as e:
            update.message.reply_text(f"Error checking admin status: {e}")
            return None
    return wrapper

def bot_admin(func: Callable) -> Callable:
    """Check if bot is admin in the chat."""
    @functools.wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs) -> Any:
        chat_id = update.effective_chat.id
        
        # Skip check for private chats
        if update.effective_chat.type == "private":
            return func(update, context, *args, **kwargs)
        
        # Check if bot is admin
        try:
            bot_member = context.bot.get_chat_member(chat_id, context.bot.id)
            if bot_member.status != "administrator":
                update.message.reply_text("I need to be an administrator to use this command.")
                return None
            return func(update, context, *args, **kwargs)
        except Exception as e:
            update.message.reply_text(f"Error checking bot admin status: {e}")
            return None
    return wrapper

def restricted_mode(mode: str) -> Callable:
    """Restrict command to specific chat modes."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(update: Update, context: CallbackContext, *args, **kwargs) -> Any:
            chat_id = update.effective_chat.id
            
            # Skip check for private chats if mode is "private"
            if mode == "private" and update.effective_chat.type == "private":
                return func(update, context, *args, **kwargs)
            
            # Skip check for group chats if mode is "group"
            if mode == "group" and update.effective_chat.type != "private":
                return func(update, context, *args, **kwargs)
            
            # Otherwise, check chat settings
            chat_data = context.chat_data.get("settings", {})
            current_mode = chat_data.get("mode", "normal")
            
            if current_mode == mode:
                return func(update, context, *args, **kwargs)
            else:
                update.message.reply_text(f"This command is only available in {mode} mode.")
                return None
        return wrapper
    return decorator