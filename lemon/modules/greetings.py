import os
import time
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler, Filters as TgFilters, MessageHandler
from telegram.error import BadRequest

from lemon.utils.decorators import admin_only, bot_admin, send_typing
from lemon.database import db
from lemon.languages import get_text

# Handle new chat members
async def welcome_new_members(update: Update, context: CallbackContext) -> None:
    """Welcome new members to the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    # Skip in private chats
    if chat.type == "private":
        return
    
    # Get chat settings
    chat_data = await db.get_chat(chat.id) or {}
    welcome_settings = chat_data.get("welcome", {})
    
    # Check if welcome messages are enabled
    welcome_enabled = welcome_settings.get("enabled", False)
    if not welcome_enabled:
        return
    
    # Process each new member
    for new_member in message.new_chat_members:
        # Skip if the new member is the bot itself
        if new_member.id == context.bot.id:
            continue
        
        # Get welcome message
        welcome_type = welcome_settings.get("type", "text")
        welcome_content = welcome_settings.get("content", "")
        welcome_buttons = welcome_settings.get("buttons", [])
        
        # Create reply markup if buttons exist
        reply_markup = None
        if welcome_buttons:
            keyboard = []
            for row in welcome_buttons:
                keyboard_row = []
                for button in row:
                    if button.get("url"):
                        keyboard_row.append(
                            InlineKeyboardButton(button.get("text", ""), url=button.get("url"))
                        )
                    elif button.get("callback_data"):
                        keyboard_row.append(
                            InlineKeyboardButton(button.get("text", ""), callback_data=button.get("callback_data"))
                        )
                if keyboard_row:
                    keyboard.append(keyboard_row)
            
            if keyboard:
                reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Add verification button if CAPTCHA is enabled
        captcha_enabled = welcome_settings.get("captcha_enabled", False)
        captcha_timeout = welcome_settings.get("captcha_timeout", 60)
        
        if captcha_enabled:
            # Create or update keyboard with verify button
            if not reply_markup:
                keyboard = [[InlineKeyboardButton("Verify ✅", callback_data=f"verify_{new_member.id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
            else:
                # Add verify button to existing keyboard
                keyboard = reply_markup.inline_keyboard
                keyboard.append([InlineKeyboardButton("Verify ✅", callback_data=f"verify_{new_member.id}")])
                reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Restrict user until verified
            try:
                chat.restrict_member(
                    new_member.id,
                    permissions={
                        "can_send_messages": False,
                        "can_send_media_messages": False,
                        "can_send_other_messages": False,
                        "can_add_web_page_previews": False
                    }
                )
            except BadRequest:
                pass
        
        # Format welcome message
        if welcome_content:
            welcome_content = welcome_content.format(
                user=new_member.first_name,
                id=new_member.id,
                username=new_member.username or new_member.first_name,
                chat=chat.title,
                count=chat.get_member_count()
            )
        else:
            welcome_content = f"Welcome {new_member.first_name} to {chat.title}!"
        
        # Add CAPTCHA message if enabled
        if captcha_enabled:
            welcome_content += f"\n\nPlease verify you're human by clicking the button below within {captcha_timeout} seconds."
        
        # Send welcome message based on type
        try:
            if welcome_type == "text":
                sent_msg = message.reply_text(
                    welcome_content,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            elif welcome_type == "photo":
                photo_id = welcome_settings.get("media_id")
                if photo_id:
                    sent_msg = message.reply_photo(
                        photo=photo_id,
                        caption=welcome_content,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    sent_msg = message.reply_text(
                        welcome_content,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
            elif welcome_type == "video":
                video_id = welcome_settings.get("media_id")
                if video_id:
                    sent_msg = message.reply_video(
                        video=video_id,
                        caption=welcome_content,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    sent_msg = message.reply_text(
                        welcome_content,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                sent_msg = message.reply_text(
                    welcome_content,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # Schedule job to check CAPTCHA timeout if enabled
            if captcha_enabled:
                context.job_queue.run_once(
                    check_verification_timeout,
                    captcha_timeout,
                    context={
                        "chat_id": chat.id,
                        "user_id": new_member.id,
                        "message_id": sent_msg.message_id
                    }
                )
        except Exception as e:
            print(f"Error sending welcome message: {e}")

# Handle members leaving chat
async def farewell_members(update: Update, context: CallbackContext) -> None:
    """Send farewell message when members leave the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    # Skip in private chats
    if chat.type == "private":
        return
    
    # Get chat settings
    chat_data = await db.get_chat(chat.id) or {}
    farewell_settings = chat_data.get("farewell", {})
    
    # Check if farewell messages are enabled
    farewell_enabled = farewell_settings.get("enabled", False)
    if not farewell_enabled:
        return
    
    # Get the user who left
    user = message.left_chat_member
    
    # Skip if the user is the bot itself
    if user.id == context.bot.id:
        return
    
    # Get farewell message
    farewell_content = farewell_settings.get("content", "")
    
    # Format farewell message
    if farewell_content:
        farewell_content = farewell_content.format(
            user=user.first_name,
            id=user.id,
            username=user.username or user.first_name,
            chat=chat.title,
            count=chat.get_member_count()
        )
    else:
        farewell_content = f"Goodbye {user.first_name}! We'll miss you."
    
    # Send farewell message
    try:
        message.reply_text(
            farewell_content,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"Error sending farewell message: {e}")

# Check verification timeout
async def check_verification_timeout(context: CallbackContext) -> None:
    """Check if user has verified within the time limit"""
    job = context.job
    data = job.context
    
    chat_id = data["chat_id"]
    user_id = data["user_id"]
    message_id = data["message_id"]
    
    # Get chat settings
    chat_data = await db.get_chat(chat_id) or {}
    welcome_settings = chat_data.get("welcome", {})
    
    # Check if user has been verified
    user_verified = welcome_settings.get(f"verified_{user_id}", False)
    
    if not user_verified:
        # User has not verified, kick them
        try:
            # Kick the user
            context.bot.kick_chat_member(chat_id, user_id)
            context.bot.unban_chat_member(chat_id, user_id)  # Unban so they can rejoin
            
            # Update the verification message
            context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="User was removed for not verifying in time."
            )
        except Exception as e:
            print(f"Error handling verification timeout: {e}")

# Handle verification button click
async def verify_button_callback(update: Update, context: CallbackContext) -> None:
    """Handle verification button click"""
    query = update.callback_query
    user = query.from_user
    chat = query.message.chat
    
    # Extract user ID from callback data
    data = query.data.split("_")
    if len(data) != 2:
        query.answer("Invalid verification data.")
        return
    
    target_user_id = int(data[1])
    
    # Check if the user clicking is the one who needs to verify
    if user.id != target_user_id:
        query.answer("This verification is not for you.")
        return
    
    # Mark user as verified
    chat_data = await db.get_chat(chat.id) or {}
    if "welcome" not in chat_data:
        chat_data["welcome"] = {}
    
    chat_data["welcome"][f"verified_{user.id}"] = True
    await db.update_chat(chat.id, chat_data)
    
    # Unrestrict the user
    try:
        chat.restrict_member(
            user.id,
            permissions={
                "can_send_messages": True,
                "can_send_media_messages": True,
                "can_send_other_messages": True,
                "can_add_web_page_previews": True
            }
        )
        
        # Update the message
        query.edit_message_text(
            text=f"{user.first_name} has been verified. Welcome to the group!"
        )
        
        query.answer("You have been verified!")
    except Exception as e:
        query.answer(f"Error: {e}")

# Set welcome message
@send_typing
@bot_admin
@admin_only
async def set_welcome(update: Update, context: CallbackContext) -> None:
    """Set welcome message for the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Get chat settings
    chat_data = await db.get_chat(chat.id) or {}
    if "welcome" not in chat_data:
        chat_data["welcome"] = {}
    
    # Check command arguments
    if not context.args and not message.reply_to_message:
        # Show current settings
        welcome_settings = chat_data.get("welcome", {})
        welcome_enabled = welcome_settings.get("enabled", False)
        welcome_type = welcome_settings.get("type", "text")
        captcha_enabled = welcome_settings.get("captcha_enabled", False)
        
        status = "enabled" if welcome_enabled else "disabled"
        captcha = "enabled" if captcha_enabled else "disabled"
        
        message.reply_text(
            f"Welcome messages are currently {status}.\n"
            f"Type: {welcome_type}\n"
            f"CAPTCHA: {captcha}\n\n"
            f"To enable/disable: /setwelcome on/off\n"
            f"To set message: /setwelcome <message> or reply to media\n"
            f"To enable/disable CAPTCHA: /setwelcome captcha on/off\n\n"
            f"You can use these placeholders:\n"
            f"{{user}} - User's name\n"
            f"{{id}} - User's ID\n"
            f"{{username}} - User's username\n"
            f"{{chat}} - Chat name\n"
            f"{{count}} - Member count"
        )
        return
    
    # Handle subcommands
    if context.args:
        if context.args[0].lower() == "on":
            chat_data["welcome"]["enabled"] = True
            await db.update_chat(chat.id, chat_data)
            message.reply_text("Welcome messages have been enabled.")
            return
        
        elif context.args[0].lower() == "off":
            chat_data["welcome"]["enabled"] = False
            await db.update_chat(chat.id, chat_data)
            message.reply_text("Welcome messages have been disabled.")
            return
        
        elif context.args[0].lower() == "captcha":
            if len(context.args) > 1:
                if context.args[1].lower() == "on":
                    chat_data["welcome"]["captcha_enabled"] = True
                    # Set default timeout if not set
                    if "captcha_timeout" not in chat_data["welcome"]:
                        chat_data["welcome"]["captcha_timeout"] = 60
                    await db.update_chat(chat.id, chat_data)
                    message.reply_text("CAPTCHA verification has been enabled.")
                    return
                elif context.args[1].lower() == "off":
                    chat_data["welcome"]["captcha_enabled"] = False
                    await db.update_chat(chat.id, chat_data)
                    message.reply_text("CAPTCHA verification has been disabled.")
                    return
                elif context.args[1].lower() == "timeout" and len(context.args) > 2:
                    try:
                        timeout = int(context.args[2])
                        if timeout < 10:
                            timeout = 10  # Minimum 10 seconds
                        chat_data["welcome"]["captcha_timeout"] = timeout
                        await db.update_chat(chat.id, chat_data)
                        message.reply_text(f"CAPTCHA timeout set to {timeout} seconds.")
                        return
                    except ValueError:
                        message.reply_text("Please provide a valid number for timeout in seconds.")
                        return
    
    # Set welcome message content
    if message.reply_to_message:
        # Check for media
        if message.reply_to_message.photo:
            chat_data["welcome"]["type"] = "photo"
            chat_data["welcome"]["media_id"] = message.reply_to_message.photo[-1].file_id
            content = message.reply_to_message.caption or "Welcome {user} to {chat}!"
        elif message.reply_to_message.video:
            chat_data["welcome"]["type"] = "video"
            chat_data["welcome"]["media_id"] = message.reply_to_message.video.file_id
            content = message.reply_to_message.caption or "Welcome {user} to {chat}!"
        else:
            chat_data["welcome"]["type"] = "text"
            content = message.reply_to_message.text or "Welcome {user} to {chat}!"
    else:
        chat_data["welcome"]["type"] = "text"
        content = " ".join(context.args)
    
    # Save welcome message
    chat_data["welcome"]["content"] = content
    chat_data["welcome"]["enabled"] = True
    await db.update_chat(chat.id, chat_data)
    
    message.reply_text("Welcome message has been set!")

# Set farewell message
@send_typing
@bot_admin
@admin_only
async def set_farewell(update: Update, context: CallbackContext) -> None:
    """Set farewell message for the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Get chat settings
    chat_data = await db.get_chat(chat.id) or {}
    if "farewell" not in chat_data:
        chat_data["farewell"] = {}
    
    # Check command arguments
    if not context.args and not message.reply_to_message:
        # Show current settings
        farewell_settings = chat_data.get("farewell", {})
        farewell_enabled = farewell_settings.get("enabled", False)
        
        status = "enabled" if farewell_enabled else "disabled"
        
        message.reply_text(
            f"Farewell messages are currently {status}.\n\n"
            f"To enable/disable: /setfarewell on/off\n"
            f"To set message: /setfarewell <message>\n\n"
            f"You can use these placeholders:\n"
            f"{{user}} - User's name\n"
            f"{{id}} - User's ID\n"
            f"{{username}} - User's username\n"
            f"{{chat}} - Chat name\n"
            f"{{count}} - Member count"
        )
        return
    
    # Handle subcommands
    if context.args:
        if context.args[0].lower() == "on":
            chat_data["farewell"]["enabled"] = True
            await db.update_chat(chat.id, chat_data)
            message.reply_text("Farewell messages have been enabled.")
            return
        
        elif context.args[0].lower() == "off":
            chat_data["farewell"]["enabled"] = False
            await db.update_chat(chat.id, chat_data)
            message.reply_text("Farewell messages have been disabled.")
            return
    
    # Set farewell message content
    if message.reply_to_message:
        content = message.reply_to_message.text or "Goodbye {user}! We'll miss you."
    else:
        content = " ".join(context.args)
    
    # Save farewell message
    chat_data["farewell"]["content"] = content
    chat_data["farewell"]["enabled"] = True
    await db.update_chat(chat.id, chat_data)
    
    message.reply_text("Farewell message has been set!")

# Define handlers
HANDLERS = [
    CommandHandler("setwelcome", set_welcome, filters=~TgFilters.private),
    CommandHandler("setfarewell", set_farewell, filters=~TgFilters.private),
    MessageHandler(TgFilters.status_update.new_chat_members, welcome_new_members),
    MessageHandler(TgFilters.status_update.left_chat_member, farewell_members),
    CallbackQueryHandler(verify_button_callback, pattern=r"^verify_")
]