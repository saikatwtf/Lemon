import time
from telegram import Update, ChatPermissions
from telegram.ext import CommandHandler, CallbackContext, Filters as TgFilters, MessageHandler
from telegram.error import BadRequest

from lemon.utils.decorators import admin_only, bot_admin, send_typing
from lemon.database import db

# Purge messages
@send_typing
@bot_admin
@admin_only
async def purge(update: Update, context: CallbackContext) -> None:
    """Purge messages from the replied message to the current message"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if the bot has permission to delete messages
    bot_member = chat.get_member(context.bot.id)
    if not bot_member.can_delete_messages:
        message.reply_text("I don't have permission to delete messages!")
        return
    
    # Check if replying to a message
    if not message.reply_to_message:
        message.reply_text("Reply to a message to start purging from.")
        return
    
    # Get the message IDs to delete
    start_message_id = message.reply_to_message.message_id
    end_message_id = message.message_id
    
    # Count deleted messages
    deleted_count = 0
    
    try:
        # Delete messages in range
        for msg_id in range(start_message_id, end_message_id + 1):
            try:
                context.bot.delete_message(chat_id=chat.id, message_id=msg_id)
                deleted_count += 1
                
                # Add a small delay to avoid hitting rate limits
                if deleted_count % 5 == 0:
                    time.sleep(0.1)
            except BadRequest:
                # Skip messages that can't be deleted
                pass
        
        # Send confirmation message
        confirm_message = message.reply_text(f"Purged {deleted_count} messages.")
        
        # Delete confirmation message after 5 seconds
        context.job_queue.run_once(
            lambda ctx: delete_message(ctx, chat.id, confirm_message.message_id),
            5,
        )
        
        # Log the action
        log_channel = context.bot_data.get("log_channel")
        if log_channel:
            context.bot.send_message(
                chat_id=log_channel,
                text=f"#PURGE\n"
                     f"Admin: {user.first_name} (ID: {user.id})\n"
                     f"Chat: {chat.title} (ID: {chat.id})\n"
                     f"Messages deleted: {deleted_count}"
            )
    except Exception as e:
        message.reply_text(f"Error purging messages: {e}")

# Delete a specific message
@send_typing
@bot_admin
@admin_only
async def delete_message_cmd(update: Update, context: CallbackContext) -> None:
    """Delete the replied message"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if the bot has permission to delete messages
    bot_member = chat.get_member(context.bot.id)
    if not bot_member.can_delete_messages:
        message.reply_text("I don't have permission to delete messages!")
        return
    
    # Check if replying to a message
    if not message.reply_to_message:
        message.reply_text("Reply to a message to delete it.")
        return
    
    try:
        # Delete the replied message
        context.bot.delete_message(
            chat_id=chat.id,
            message_id=message.reply_to_message.message_id
        )
        
        # Delete the command message
        context.bot.delete_message(
            chat_id=chat.id,
            message_id=message.message_id
        )
    except BadRequest as e:
        message.reply_text(f"Error deleting message: {e.message}")

# Clean bot messages
@send_typing
@bot_admin
@admin_only
async def clean(update: Update, context: CallbackContext) -> None:
    """Clean bot messages or specific message types"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if the bot has permission to delete messages
    bot_member = chat.get_member(context.bot.id)
    if not bot_member.can_delete_messages:
        message.reply_text("I don't have permission to delete messages!")
        return
    
    # Default to cleaning bot messages
    clean_type = "bot"
    limit = 100  # Default limit
    
    # Parse arguments
    if context.args:
        if context.args[0].lower() in ["bot", "commands", "all"]:
            clean_type = context.args[0].lower()
            
            # Check for limit
            if len(context.args) > 1:
                try:
                    limit = int(context.args[1])
                    if limit > 1000:
                        limit = 1000  # Maximum limit
                    elif limit < 1:
                        limit = 1  # Minimum limit
                except ValueError:
                    pass
    
    try:
        # Get recent messages
        deleted_count = 0
        
        # We need to iterate through messages manually since there's no API to get messages by type
        async for msg in context.bot.get_chat_history(chat.id, limit=limit):
            delete_msg = False
            
            if clean_type == "bot" and msg.from_user and msg.from_user.id == context.bot.id:
                delete_msg = True
            elif clean_type == "commands" and msg.text and msg.text.startswith("/"):
                delete_msg = True
            elif clean_type == "all":
                delete_msg = True
            
            if delete_msg:
                try:
                    context.bot.delete_message(chat_id=chat.id, message_id=msg.message_id)
                    deleted_count += 1
                    
                    # Add a small delay to avoid hitting rate limits
                    if deleted_count % 5 == 0:
                        time.sleep(0.1)
                except BadRequest:
                    # Skip messages that can't be deleted
                    pass
        
        # Send confirmation message
        confirm_message = message.reply_text(f"Cleaned {deleted_count} messages.")
        
        # Delete confirmation message after 5 seconds
        context.job_queue.run_once(
            lambda ctx: delete_message(ctx, chat.id, confirm_message.message_id),
            5,
        )
        
        # Log the action
        log_channel = context.bot_data.get("log_channel")
        if log_channel:
            context.bot.send_message(
                chat_id=log_channel,
                text=f"#CLEAN\n"
                     f"Admin: {user.first_name} (ID: {user.id})\n"
                     f"Chat: {chat.title} (ID: {chat.id})\n"
                     f"Type: {clean_type}\n"
                     f"Messages deleted: {deleted_count}"
            )
    except Exception as e:
        message.reply_text(f"Error cleaning messages: {e}")

# Set clean service settings
@send_typing
@bot_admin
@admin_only
async def set_clean_service(update: Update, context: CallbackContext) -> None:
    """Configure clean service settings"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Get chat settings
    chat_data = await db.get_chat(chat.id) or {}
    if "clean_service" not in chat_data:
        chat_data["clean_service"] = {
            "enabled": False,
            "pin_silence": False
        }
    
    # Check command arguments
    if not context.args:
        # Show current settings
        clean_service = chat_data.get("clean_service", {})
        enabled = clean_service.get("enabled", False)
        pin_silence = clean_service.get("pin_silence", False)
        
        status = "enabled" if enabled else "disabled"
        pin_status = "enabled" if pin_silence else "disabled"
        
        message.reply_text(
            f"Clean service is currently {status}.\n"
            f"Silent pin notifications: {pin_status}\n\n"
            f"To enable/disable: /cleanservice on/off\n"
            f"To enable/disable silent pins: /cleanservice pin on/off"
        )
        return
    
    # Handle subcommands
    if context.args[0].lower() == "on":
        chat_data["clean_service"]["enabled"] = True
        await db.update_chat(chat.id, chat_data)
        message.reply_text("Clean service has been enabled. Service messages will be automatically removed.")
    
    elif context.args[0].lower() == "off":
        chat_data["clean_service"]["enabled"] = False
        await db.update_chat(chat.id, chat_data)
        message.reply_text("Clean service has been disabled.")
    
    elif context.args[0].lower() == "pin" and len(context.args) > 1:
        if context.args[1].lower() == "on":
            chat_data["clean_service"]["pin_silence"] = True
            await db.update_chat(chat.id, chat_data)
            message.reply_text("Pin notifications will now be silenced.")
        
        elif context.args[1].lower() == "off":
            chat_data["clean_service"]["pin_silence"] = False
            await db.update_chat(chat.id, chat_data)
            message.reply_text("Pin notifications will now be shown.")
        
        else:
            message.reply_text("Invalid option. Use 'on' or 'off'.")
    
    else:
        message.reply_text(
            "Invalid argument. Use:\n"
            "/cleanservice on - Enable clean service\n"
            "/cleanservice off - Disable clean service\n"
            "/cleanservice pin on - Enable silent pins\n"
            "/cleanservice pin off - Disable silent pins"
        )

# Handle service messages
async def clean_service_handler(update: Update, context: CallbackContext) -> None:
    """Clean service messages if enabled"""
    chat = update.effective_chat
    message = update.effective_message
    
    # Skip in private chats
    if chat.type == "private":
        return
    
    # Get chat settings
    chat_data = await db.get_chat(chat.id) or {}
    clean_service = chat_data.get("clean_service", {})
    
    # Check if clean service is enabled
    if not clean_service.get("enabled", False):
        return
    
    # Check if it's a service message
    is_service = (
        message.new_chat_members or
        message.left_chat_member or
        message.new_chat_title or
        message.new_chat_photo or
        message.delete_chat_photo or
        message.group_chat_created or
        message.supergroup_chat_created or
        message.channel_chat_created or
        message.migrate_to_chat_id or
        message.migrate_from_chat_id or
        message.pinned_message
    )
    
    # Handle pinned messages separately
    if message.pinned_message and clean_service.get("pin_silence", False):
        try:
            # Delete the service message but keep the pinned message
            context.bot.delete_message(chat_id=chat.id, message_id=message.message_id)
        except BadRequest:
            pass
        return
    
    # Delete service message
    if is_service:
        try:
            context.bot.delete_message(chat_id=chat.id, message_id=message.message_id)
        except BadRequest:
            pass

# Helper function to delete messages
def delete_message(context: CallbackContext, chat_id, message_id):
    """Delete a message after a delay"""
    try:
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except BadRequest:
        pass

# Define handlers
HANDLERS = [
    CommandHandler("purge", purge, filters=~TgFilters.private),
    CommandHandler("del", delete_message_cmd, filters=~TgFilters.private),
    CommandHandler("clean", clean, filters=~TgFilters.private),
    CommandHandler("cleanservice", set_clean_service, filters=~TgFilters.private),
    MessageHandler(TgFilters.status_update, clean_service_handler)
]