from telegram import Update, ChatMember
from telegram.ext import CommandHandler, CallbackContext, Filters
from telegram.error import BadRequest

from lemon.utils.decorators import admin_only, bot_admin, send_typing
from lemon.database import db

# List all admins in the group
@send_typing
@bot_admin
def admin_list(update: Update, context: CallbackContext) -> None:
    """List all administrators in a group"""
    chat = update.effective_chat
    
    if chat.type == "private":
        update.message.reply_text("This command can only be used in groups.")
        return
    
    try:
        # Get admin list from Telegram
        administrators = chat.get_administrators()
        
        # Format admin list
        admin_list = []
        for admin in administrators:
            user = admin.user
            status = "Creator" if admin.status == "creator" else "Admin"
            name = user.first_name
            if user.username:
                name = f"@{user.username}"
            admin_list.append(f"• {name} - {status}")
        
        # Send the admin list
        update.message.reply_text(
            f"Admins in {chat.title}:\n\n" + "\n".join(admin_list)
        )
    except BadRequest as e:
        update.message.reply_text(f"Error: {e.message}")

# Promote a user to admin
@send_typing
@bot_admin
@admin_only
def promote(update: Update, context: CallbackContext) -> None:
    """Promote a user to admin"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if the bot has permission to promote members
    bot_member = chat.get_member(context.bot.id)
    if not bot_member.can_promote_members:
        message.reply_text("I don't have permission to promote users!")
        return
    
    # Get the user to promote
    if not message.reply_to_message and not context.args:
        message.reply_text("Reply to a user or provide a username to promote.")
        return
    
    try:
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            user_name = message.reply_to_message.from_user.first_name
        else:
            username = context.args[0]
            if username.startswith("@"):
                username = username[1:]
            
            # Try to get user by username
            chat_member = context.bot.get_chat_member(chat.id, username)
            user_id = chat_member.user.id
            user_name = chat_member.user.first_name
        
        # Check if user is already an admin
        member = chat.get_member(user_id)
        if member.status in ["administrator", "creator"]:
            message.reply_text("This user is already an admin!")
            return
        
        # Promote the user
        context.bot.promote_chat_member(
            chat_id=chat.id,
            user_id=user_id,
            can_change_info=True,
            can_delete_messages=True,
            can_invite_users=True,
            can_restrict_members=True,
            can_pin_messages=True
        )
        
        message.reply_text(f"Successfully promoted {user_name}!")
        
        # Log the action
        context.bot.send_message(
            chat_id=int(context.bot.log_channel),
            text=f"#PROMOTE\n"
                 f"Admin: {user.first_name} (ID: {user.id})\n"
                 f"User: {user_name} (ID: {user_id})\n"
                 f"Chat: {chat.title} (ID: {chat.id})"
        )
    except BadRequest as e:
        message.reply_text(f"Error: {e.message}")

# Demote an admin
@send_typing
@bot_admin
@admin_only
def demote(update: Update, context: CallbackContext) -> None:
    """Demote an admin to regular user"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if the bot has permission to promote/demote members
    bot_member = chat.get_member(context.bot.id)
    if not bot_member.can_promote_members:
        message.reply_text("I don't have permission to demote users!")
        return
    
    # Get the user to demote
    if not message.reply_to_message and not context.args:
        message.reply_text("Reply to a user or provide a username to demote.")
        return
    
    try:
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            user_name = message.reply_to_message.from_user.first_name
        else:
            username = context.args[0]
            if username.startswith("@"):
                username = username[1:]
            
            # Try to get user by username
            chat_member = context.bot.get_chat_member(chat.id, username)
            user_id = chat_member.user.id
            user_name = chat_member.user.first_name
        
        # Check if user is an admin
        member = chat.get_member(user_id)
        if member.status != "administrator":
            message.reply_text("This user is not an admin!")
            return
        
        # Check if user is the creator
        if member.status == "creator":
            message.reply_text("I can't demote the creator of the group!")
            return
        
        # Demote the user
        context.bot.promote_chat_member(
            chat_id=chat.id,
            user_id=user_id,
            can_change_info=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False
        )
        
        message.reply_text(f"Successfully demoted {user_name}!")
        
        # Log the action
        context.bot.send_message(
            chat_id=int(context.bot.log_channel),
            text=f"#DEMOTE\n"
                 f"Admin: {user.first_name} (ID: {user.id})\n"
                 f"User: {user_name} (ID: {user_id})\n"
                 f"Chat: {chat.title} (ID: {chat.id})"
        )
    except BadRequest as e:
        message.reply_text(f"Error: {e.message}")

# Pin a message
@send_typing
@bot_admin
@admin_only
def pin(update: Update, context: CallbackContext) -> None:
    """Pin a message in the group"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if the bot has permission to pin messages
    bot_member = chat.get_member(context.bot.id)
    if not bot_member.can_pin_messages:
        message.reply_text("I don't have permission to pin messages!")
        return
    
    # Check if replying to a message
    if not message.reply_to_message:
        message.reply_text("Reply to a message to pin it.")
        return
    
    # Check if the message is already pinned
    try:
        # Pin the message
        notify = not (context.args and context.args[0].lower() == "silent")
        context.bot.pin_chat_message(
            chat_id=chat.id,
            message_id=message.reply_to_message.message_id,
            disable_notification=not notify
        )
        
        if notify:
            message.reply_text("Message pinned successfully!")
    except BadRequest as e:
        message.reply_text(f"Error: {e.message}")

# Unpin a message
@send_typing
@bot_admin
@admin_only
def unpin(update: Update, context: CallbackContext) -> None:
    """Unpin a message in the group"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if the bot has permission to pin messages
    bot_member = chat.get_member(context.bot.id)
    if not bot_member.can_pin_messages:
        message.reply_text("I don't have permission to unpin messages!")
        return
    
    try:
        # If replying to a message, unpin that specific message
        if message.reply_to_message:
            context.bot.unpin_chat_message(
                chat_id=chat.id,
                message_id=message.reply_to_message.message_id
            )
        # Otherwise unpin the last pinned message
        else:
            context.bot.unpin_chat_message(chat_id=chat.id)
        
        message.reply_text("Message unpinned successfully!")
    except BadRequest as e:
        message.reply_text(f"Error: {e.message}")

# Unpin all messages
@send_typing
@bot_admin
@admin_only
def unpin_all(update: Update, context: CallbackContext) -> None:
    """Unpin all messages in the group"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if the bot has permission to pin messages
    bot_member = chat.get_member(context.bot.id)
    if not bot_member.can_pin_messages:
        message.reply_text("I don't have permission to unpin messages!")
        return
    
    try:
        # Unpin all messages
        context.bot.unpin_all_chat_messages(chat_id=chat.id)
        message.reply_text("All messages unpinned successfully!")
    except BadRequest as e:
        message.reply_text(f"Error: {e.message}")

# Define handlers
HANDLERS = [
    CommandHandler("adminlist", admin_list, filters=~Filters.private),
    CommandHandler("promote", promote, filters=~Filters.private),
    CommandHandler("demote", demote, filters=~Filters.private),
    CommandHandler("pin", pin, filters=~Filters.private),
    CommandHandler("unpin", unpin, filters=~Filters.private),
    CommandHandler("unpinall", unpin_all, filters=~Filters.private)
]