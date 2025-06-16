import uuid
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext, Filters as TgFilters
from telegram.error import BadRequest

from lemon.utils.decorators import admin_only, bot_admin, send_typing
from lemon.database import db

# Create a new federation
@send_typing
async def new_federation(update: Update, context: CallbackContext) -> None:
    """Create a new federation"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    # Only allow in private chat
    if chat.type != "private":
        message.reply_text("This command can only be used in private chat with the bot.")
        return
    
    # Check if command has arguments
    if not context.args:
        message.reply_text("Please provide a name for the federation.")
        return
    
    # Get federation name
    fed_name = " ".join(context.args)
    
    # Generate federation ID
    fed_id = str(uuid.uuid4())
    
    try:
        # Create federation in database
        await db.create_federation(fed_id, user.id, fed_name)
        
        message.reply_text(
            f"Federation created successfully!\n\n"
            f"Name: {fed_name}\n"
            f"ID: `{fed_id}`\n"
            f"Creator: {user.first_name}\n\n"
            f"Use this ID to join the federation with /joinfed command.",
            parse_mode="Markdown"
        )
        
        # Log the action
        if context.bot.log_channel:
            context.bot.send_message(
                chat_id=context.bot.log_channel,
                text=f"#NEW_FEDERATION\n"
                     f"User: {user.first_name} (ID: {user.id})\n"
                     f"Federation: {fed_name} (ID: {fed_id})"
            )
    except Exception as e:
        message.reply_text(f"An error occurred: {e}")

# Join a federation
@send_typing
@bot_admin
@admin_only
async def join_federation(update: Update, context: CallbackContext) -> None:
    """Join a federation"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if command has arguments
    if not context.args:
        message.reply_text("Please provide a federation ID to join.")
        return
    
    # Get federation ID
    fed_id = context.args[0]
    
    try:
        # Check if federation exists
        federation = await db.get_federation(fed_id)
        
        if not federation:
            message.reply_text("Federation not found. Please check the ID and try again.")
            return
        
        # Check if user is federation owner or admin
        if user.id != federation.get("owner_id") and user.id not in federation.get("admins", []):
            message.reply_text("Only federation owner or admins can add groups to the federation.")
            return
        
        # Check if chat is already in a federation
        existing_feds = await db.async_federations.find({"chats": chat.id}).to_list(length=100)
        
        if existing_feds:
            message.reply_text(
                f"This chat is already in federation: {existing_feds[0].get('name')}\n"
                f"Leave it first with /leavefed command."
            )
            return
        
        # Add chat to federation
        await db.add_fed_chat(fed_id, chat.id)
        
        message.reply_text(
            f"This chat has joined the federation: {federation.get('name')}"
        )
        
        # Log the action
        if context.bot.log_channel:
            context.bot.send_message(
                chat_id=context.bot.log_channel,
                text=f"#JOIN_FEDERATION\n"
                     f"Admin: {user.first_name} (ID: {user.id})\n"
                     f"Chat: {chat.title} (ID: {chat.id})\n"
                     f"Federation: {federation.get('name')} (ID: {fed_id})"
            )
    except Exception as e:
        message.reply_text(f"An error occurred: {e}")

# Leave a federation
@send_typing
@bot_admin
@admin_only
async def leave_federation(update: Update, context: CallbackContext) -> None:
    """Leave a federation"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    try:
        # Find federation that contains this chat
        federation = await db.async_federations.find_one({"chats": chat.id})
        
        if not federation:
            message.reply_text("This chat is not in any federation.")
            return
        
        # Remove chat from federation
        await db.remove_fed_chat(federation.get("_id"), chat.id)
        
        message.reply_text(
            f"This chat has left the federation: {federation.get('name')}"
        )
        
        # Log the action
        if context.bot.log_channel:
            context.bot.send_message(
                chat_id=context.bot.log_channel,
                text=f"#LEAVE_FEDERATION\n"
                     f"Admin: {user.first_name} (ID: {user.id})\n"
                     f"Chat: {chat.title} (ID: {chat.id})\n"
                     f"Federation: {federation.get('name')} (ID: {federation.get('_id')})"
            )
    except Exception as e:
        message.reply_text(f"An error occurred: {e}")

# Get federation info
@send_typing
async def federation_info(update: Update, context: CallbackContext) -> None:
    """Get information about a federation"""
    chat = update.effective_chat
    message = update.effective_message
    
    # Get federation ID
    if context.args:
        fed_id = context.args[0]
    else:
        # If no ID provided, try to get federation for current chat
        if chat.type == "private":
            message.reply_text("Please provide a federation ID.")
            return
        
        federation = await db.async_federations.find_one({"chats": chat.id})
        
        if not federation:
            message.reply_text("This chat is not in any federation. Please provide a federation ID.")
            return
        
        fed_id = federation.get("_id")
    
    try:
        # Get federation from database
        federation = await db.get_federation(fed_id)
        
        if not federation:
            message.reply_text("Federation not found. Please check the ID and try again.")
            return
        
        # Get federation owner
        try:
            owner = await context.bot.get_chat(federation.get("owner_id"))
            owner_name = owner.first_name
            if owner.username:
                owner_name = f"@{owner.username}"
        except BadRequest:
            owner_name = f"User {federation.get('owner_id')}"
        
        # Get federation chats
        chat_count = len(federation.get("chats", []))
        
        # Get federation admins
        admin_count = len(federation.get("admins", []))
        
        # Get federation banned users
        banned_count = await db.async_fed_bans.count_documents({"fed_id": fed_id})
        
        # Format federation info
        info_text = f"Federation Information:\n\n" \
                   f"Name: {federation.get('name')}\n" \
                   f"ID: `{fed_id}`\n" \
                   f"Owner: {owner_name}\n" \
                   f"Chats: {chat_count}\n" \
                   f"Admins: {admin_count}\n" \
                   f"Banned Users: {banned_count}"
        
        message.reply_text(info_text, parse_mode="Markdown")
    except Exception as e:
        message.reply_text(f"An error occurred: {e}")

# Ban a user from federation
@send_typing
async def federation_ban(update: Update, context: CallbackContext) -> None:
    """Ban a user from all chats in the federation"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    # Get federation for current chat
    if chat.type != "private":
        federation = await db.async_federations.find_one({"chats": chat.id})
        
        if not federation:
            message.reply_text("This chat is not in any federation.")
            return
        
        fed_id = federation.get("_id")
    else:
        # In private chat, require federation ID
        if not context.args or len(context.args) < 2:
            message.reply_text("Please provide a federation ID and a user to ban.")
            return
        
        fed_id = context.args[0]
        context.args = context.args[1:]  # Remove fed_id from args
        
        # Check if federation exists
        federation = await db.get_federation(fed_id)
        
        if not federation:
            message.reply_text("Federation not found. Please check the ID and try again.")
            return
    
    # Check if user is federation owner or admin
    if user.id != federation.get("owner_id") and user.id not in federation.get("admins", []):
        message.reply_text("Only federation owner or admins can ban users from the federation.")
        return
    
    # Get the user to ban
    if not message.reply_to_message and not context.args:
        message.reply_text("Reply to a user or provide a username to ban from the federation.")
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
            try:
                target_user = await context.bot.get_chat(username)
                target_id = target_user.id
                target_name = target_user.first_name
            except BadRequest:
                # Try to get user by ID
                try:
                    user_id = int(username)
                    target_user = await context.bot.get_chat(user_id)
                    target_id = target_user.id
                    target_name = target_user.first_name
                except (ValueError, BadRequest):
                    message.reply_text("User not found. Please check the username or ID.")
                    return
        
        # Get reason for ban
        reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "No reason provided"
        
        # Check if user is already banned
        is_banned = await db.is_user_fed_banned(fed_id, target_id)
        if is_banned:
            message.reply_text(f"{target_name} is already banned in this federation.")
            return
        
        # Ban user in federation
        await db.fed_ban_user(fed_id, target_id, reason)
        
        # Ban user from all chats in federation
        ban_count = 0
        for chat_id in federation.get("chats", []):
            try:
                await context.bot.kick_chat_member(chat_id, target_id)
                ban_count += 1
            except BadRequest:
                continue
        
        message.reply_text(
            f"{target_name} has been banned from the federation: {federation.get('name')}\n"
            f"Banned in {ban_count} chats.\n"
            f"Reason: {reason}"
        )
        
        # Log the action
        if context.bot.log_channel:
            context.bot.send_message(
                chat_id=context.bot.log_channel,
                text=f"#FEDBAN\n"
                     f"Admin: {user.first_name} (ID: {user.id})\n"
                     f"User: {target_name} (ID: {target_id})\n"
                     f"Federation: {federation.get('name')} (ID: {fed_id})\n"
                     f"Banned in: {ban_count} chats\n"
                     f"Reason: {reason}"
            )
    except Exception as e:
        message.reply_text(f"An error occurred: {e}")

# Unban a user from federation
@send_typing
async def federation_unban(update: Update, context: CallbackContext) -> None:
    """Unban a user from all chats in the federation"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    # Get federation for current chat
    if chat.type != "private":
        federation = await db.async_federations.find_one({"chats": chat.id})
        
        if not federation:
            message.reply_text("This chat is not in any federation.")
            return
        
        fed_id = federation.get("_id")
    else:
        # In private chat, require federation ID
        if not context.args or len(context.args) < 2:
            message.reply_text("Please provide a federation ID and a user to unban.")
            return
        
        fed_id = context.args[0]
        context.args = context.args[1:]  # Remove fed_id from args
        
        # Check if federation exists
        federation = await db.get_federation(fed_id)
        
        if not federation:
            message.reply_text("Federation not found. Please check the ID and try again.")
            return
    
    # Check if user is federation owner or admin
    if user.id != federation.get("owner_id") and user.id not in federation.get("admins", []):
        message.reply_text("Only federation owner or admins can unban users from the federation.")
        return
    
    # Get the user to unban
    if not message.reply_to_message and not context.args:
        message.reply_text("Reply to a user or provide a username to unban from the federation.")
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
            try:
                target_user = await context.bot.get_chat(username)
                target_id = target_user.id
                target_name = target_user.first_name
            except BadRequest:
                # Try to get user by ID
                try:
                    user_id = int(username)
                    target_user = await context.bot.get_chat(user_id)
                    target_id = target_user.id
                    target_name = target_user.first_name
                except (ValueError, BadRequest):
                    message.reply_text("User not found. Please check the username or ID.")
                    return
        
        # Check if user is banned
        is_banned = await db.is_user_fed_banned(fed_id, target_id)
        if not is_banned:
            message.reply_text(f"{target_name} is not banned in this federation.")
            return
        
        # Unban user in federation
        result = await db.fed_unban_user(fed_id, target_id)
        
        if result:
            message.reply_text(
                f"{target_name} has been unbanned from the federation: {federation.get('name')}"
            )
            
            # Log the action
            if context.bot.log_channel:
                context.bot.send_message(
                    chat_id=context.bot.log_channel,
                    text=f"#FEDUNBAN\n"
                         f"Admin: {user.first_name} (ID: {user.id})\n"
                         f"User: {target_name} (ID: {target_id})\n"
                         f"Federation: {federation.get('name')} (ID: {fed_id})"
                )
        else:
            message.reply_text(f"Failed to unban {target_name} from the federation.")
    except Exception as e:
        message.reply_text(f"An error occurred: {e}")

# Define handlers
HANDLERS = [
    CommandHandler("newfed", new_federation),
    CommandHandler("joinfed", join_federation, filters=~TgFilters.private),
    CommandHandler("leavefed", leave_federation, filters=~TgFilters.private),
    CommandHandler("fedinfo", federation_info),
    CommandHandler("fban", federation_ban),
    CommandHandler("unfban", federation_unban)
]