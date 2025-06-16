from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext, Filters as TgFilters
from telegram.error import BadRequest

from lemon.utils.decorators import admin_only, bot_admin, send_typing
from lemon.database import db

# Approve a user
@send_typing
@bot_admin
@admin_only
async def approve_user(update: Update, context: CallbackContext) -> None:
    """Approve a user in the chat"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Get the user to approve
    if not message.reply_to_message and not context.args:
        message.reply_text("Reply to a user or provide a username to approve.")
        return
    
    try:
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            target_id = target_user.id
            target_name = target_user.first_name
        else:
            username = context.args[0]
            if username.startswith("@"):
                username = username[1:]
            
            # Try to get user by username
            chat_member = context.bot.get_chat_member(chat.id, username)
            target_id = chat_member.user.id
            target_name = chat_member.user.first_name
        
        # Check if user is already approved
        is_approved = await db.is_user_approved(chat.id, target_id)
        if is_approved:
            message.reply_text(f"{target_name} is already approved in this chat.")
            return
        
        # Approve user in database
        await db.approve_user(chat.id, target_id)
        
        message.reply_text(f"{target_name} has been approved in this chat!")
        
        # Log the action
        if context.bot.log_channel:
            context.bot.send_message(
                chat_id=context.bot.log_channel,
                text=f"#APPROVE\n"
                     f"Admin: {user.first_name} (ID: {user.id})\n"
                     f"User: {target_name} (ID: {target_id})\n"
                     f"Chat: {chat.title} (ID: {chat.id})"
            )
    except BadRequest as e:
        message.reply_text(f"Error: {e.message}")

# Disapprove a user
@send_typing
@bot_admin
@admin_only
async def disapprove_user(update: Update, context: CallbackContext) -> None:
    """Disapprove a user in the chat"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Get the user to disapprove
    if not message.reply_to_message and not context.args:
        message.reply_text("Reply to a user or provide a username to disapprove.")
        return
    
    try:
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            target_id = target_user.id
            target_name = target_user.first_name
        else:
            username = context.args[0]
            if username.startswith("@"):
                username = username[1:]
            
            # Try to get user by username
            chat_member = context.bot.get_chat_member(chat.id, username)
            target_id = chat_member.user.id
            target_name = chat_member.user.first_name
        
        # Check if user is approved
        is_approved = await db.is_user_approved(chat.id, target_id)
        if not is_approved:
            message.reply_text(f"{target_name} is not approved in this chat.")
            return
        
        # Disapprove user in database
        result = await db.disapprove_user(chat.id, target_id)
        
        if result:
            message.reply_text(f"{target_name} has been disapproved in this chat.")
            
            # Log the action
            if context.bot.log_channel:
                context.bot.send_message(
                    chat_id=context.bot.log_channel,
                    text=f"#DISAPPROVE\n"
                         f"Admin: {user.first_name} (ID: {user.id})\n"
                         f"User: {target_name} (ID: {target_id})\n"
                         f"Chat: {chat.title} (ID: {chat.id})"
                )
        else:
            message.reply_text(f"Failed to disapprove {target_name}.")
    except BadRequest as e:
        message.reply_text(f"Error: {e.message}")

# List approved users
@send_typing
@bot_admin
async def list_approved(update: Update, context: CallbackContext) -> None:
    """List all approved users in the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Get all approved users from database
    approved_users = await db.async_approvals.find({"chat_id": chat.id}).to_list(length=100)
    
    if not approved_users:
        message.reply_text("No approved users in this chat.")
        return
    
    # Format approved users list
    approved_list = f"Approved users in {chat.title}:\n\n"
    
    for i, user_data in enumerate(approved_users, 1):
        user_id = user_data.get("user_id")
        try:
            user = await context.bot.get_chat(user_id)
            name = user.first_name
            if user.username:
                name = f"@{user.username}"
            approved_list += f"{i}. {name} (ID: {user_id})\n"
        except BadRequest:
            approved_list += f"{i}. Unknown User (ID: {user_id})\n"
    
    # Send in chunks if too long
    if len(approved_list) > 4000:
        for i in range(0, len(approved_list), 4000):
            message.reply_text(approved_list[i:i+4000])
    else:
        message.reply_text(approved_list)

# Check if a user is approved
@send_typing
async def check_approval(update: Update, context: CallbackContext) -> None:
    """Check if a user is approved in the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Get the user to check
    if not message.reply_to_message and not context.args:
        # Check the user who sent the command
        target_id = update.effective_user.id
        target_name = update.effective_user.first_name
    else:
        try:
            if message.reply_to_message:
                target_user = message.reply_to_message.from_user
                target_id = target_user.id
                target_name = target_user.first_name
            else:
                username = context.args[0]
                if username.startswith("@"):
                    username = username[1:]
                
                # Try to get user by username
                chat_member = context.bot.get_chat_member(chat.id, username)
                target_id = chat_member.user.id
                target_name = chat_member.user.first_name
        except BadRequest as e:
            message.reply_text(f"Error: {e.message}")
            return
    
    # Check if user is approved
    is_approved = await db.is_user_approved(chat.id, target_id)
    
    if is_approved:
        message.reply_text(f"{target_name} is approved in this chat.")
    else:
        message.reply_text(f"{target_name} is not approved in this chat.")

# Define handlers
HANDLERS = [
    CommandHandler("approve", approve_user, filters=~TgFilters.private),
    CommandHandler("disapprove", disapprove_user, filters=~TgFilters.private),
    CommandHandler("approved", list_approved, filters=~TgFilters.private),
    CommandHandler("approval", check_approval, filters=~TgFilters.private)
]