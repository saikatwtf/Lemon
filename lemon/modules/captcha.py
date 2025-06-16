import os
import time
import random
import string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from captcha.image import ImageCaptcha
from telegram import Update, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler, Filters as TgFilters, MessageHandler
from telegram.error import BadRequest

from lemon.utils.decorators import admin_only, bot_admin, send_typing
from lemon.database import db

# Store captcha data
captcha_data = {}

# Generate a random captcha code
def generate_captcha_code(length=6):
    """Generate a random captcha code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# Generate a captcha image
def generate_captcha_image(text):
    """Generate a captcha image"""
    image = ImageCaptcha(width=280, height=90)
    data = image.generate(text)
    return BytesIO(data.read())

# Handle new chat members
async def new_chat_member(update: Update, context: CallbackContext) -> None:
    """Handle new chat members and apply CAPTCHA if enabled"""
    chat = update.effective_chat
    message = update.effective_message
    
    # Skip in private chats
    if chat.type == "private":
        return
    
    # Get chat settings
    chat_data = await db.get_chat(chat.id) or {}
    captcha_settings = chat_data.get("captcha", {})
    
    # Check if CAPTCHA is enabled
    captcha_enabled = captcha_settings.get("enabled", False)
    if not captcha_enabled:
        return
    
    # Get CAPTCHA timeout
    captcha_timeout = captcha_settings.get("timeout", 300)  # Default 5 minutes
    
    # Process each new member
    for new_member in message.new_chat_members:
        # Skip if the new member is the bot itself
        if new_member.id == context.bot.id:
            continue
        
        # Restrict the user
        try:
            chat.restrict_member(
                new_member.id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False
                )
            )
        except BadRequest as e:
            # Log the error but continue
            print(f"Error restricting user: {e}")
            continue
        
        # Generate CAPTCHA code
        captcha_code = generate_captcha_code()
        
        # Store CAPTCHA data
        if chat.id not in captcha_data:
            captcha_data[chat.id] = {}
        
        captcha_data[chat.id][new_member.id] = {
            "code": captcha_code,
            "time": time.time(),
            "timeout": captcha_timeout
        }
        
        # Generate CAPTCHA image
        captcha_image = generate_captcha_image(captcha_code)
        
        # Create keyboard with verify button
        keyboard = [
            [InlineKeyboardButton("Verify", callback_data=f"captcha_{new_member.id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send CAPTCHA message
        try:
            sent_message = message.reply_photo(
                photo=captcha_image,
                caption=f"Welcome {new_member.first_name}! Please solve this CAPTCHA to verify you're human.\n"
                        f"You have {captcha_timeout // 60} minutes to complete this.",
                reply_markup=reply_markup
            )
            
            # Store message ID for later deletion
            captcha_data[chat.id][new_member.id]["message_id"] = sent_message.message_id
            
            # Schedule job to check CAPTCHA timeout
            context.job_queue.run_once(
                check_captcha_timeout,
                captcha_timeout,
                context={
                    "chat_id": chat.id,
                    "user_id": new_member.id,
                    "message_id": sent_message.message_id
                }
            )
        except Exception as e:
            print(f"Error sending CAPTCHA: {e}")

# Check CAPTCHA timeout
async def check_captcha_timeout(context: CallbackContext) -> None:
    """Check if CAPTCHA has timed out"""
    job = context.job
    data = job.context
    
    chat_id = data["chat_id"]
    user_id = data["user_id"]
    message_id = data["message_id"]
    
    # Check if user has completed CAPTCHA
    if chat_id in captcha_data and user_id in captcha_data[chat_id]:
        # User has not completed CAPTCHA, kick them
        try:
            # Kick the user
            context.bot.kick_chat_member(chat_id, user_id)
            context.bot.unban_chat_member(chat_id, user_id)  # Unban so they can rejoin
            
            # Delete CAPTCHA message
            context.bot.delete_message(chat_id, message_id)
            
            # Send notification
            context.bot.send_message(
                chat_id=chat_id,
                text=f"User was kicked for not completing CAPTCHA verification in time."
            )
            
            # Remove CAPTCHA data
            del captcha_data[chat_id][user_id]
        except Exception as e:
            print(f"Error handling CAPTCHA timeout: {e}")

# Handle CAPTCHA button click
async def captcha_button(update: Update, context: CallbackContext) -> None:
    """Handle CAPTCHA verification button click"""
    query = update.callback_query
    user = query.from_user
    chat = query.message.chat
    
    # Extract user ID from callback data
    data = query.data.split("_")
    if len(data) != 2:
        query.answer("Invalid CAPTCHA data.")
        return
    
    target_user_id = int(data[1])
    
    # Check if the user clicking is the one who needs to verify
    if user.id != target_user_id:
        query.answer("This CAPTCHA is not for you.")
        return
    
    # Check if CAPTCHA data exists
    if chat.id not in captcha_data or target_user_id not in captcha_data[chat.id]:
        query.answer("CAPTCHA session expired or not found.")
        return
    
    # Show CAPTCHA input dialog
    query.answer()
    query.edit_message_caption(
        caption=f"Please enter the CAPTCHA code shown in the image.\n"
                f"Reply to this message with the code."
    )
    
    # Update CAPTCHA data to indicate waiting for input
    captcha_data[chat.id][target_user_id]["waiting_input"] = True

# Handle CAPTCHA code input
async def captcha_input(update: Update, context: CallbackContext) -> None:
    """Handle CAPTCHA code input"""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    
    # Skip if not replying to a message
    if not message.reply_to_message:
        return
    
    # Check if the replied message is from the bot
    if message.reply_to_message.from_user.id != context.bot.id:
        return
    
    # Check if the caption contains CAPTCHA text
    caption = message.reply_to_message.caption
    if not caption or "CAPTCHA" not in caption:
        return
    
    # Check if user has a pending CAPTCHA
    if chat.id not in captcha_data or user.id not in captcha_data[chat.id]:
        return
    
    # Check if waiting for input
    if not captcha_data[chat.id][user.id].get("waiting_input", False):
        return
    
    # Get the entered code
    entered_code = message.text.strip().upper()
    
    # Get the correct code
    correct_code = captcha_data[chat.id][user.id]["code"]
    
    # Check if the code is correct
    if entered_code == correct_code:
        # Unrestrict the user
        try:
            chat.restrict_member(
                user.id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
            
            # Delete CAPTCHA messages
            message.reply_to_message.delete()
            message.delete()
            
            # Send welcome message
            context.bot.send_message(
                chat_id=chat.id,
                text=f"Welcome {user.first_name}! You have been verified."
            )
            
            # Remove CAPTCHA data
            del captcha_data[chat.id][user.id]
        except Exception as e:
            print(f"Error completing CAPTCHA: {e}")
    else:
        # Wrong code
        message.reply_text("Incorrect code. Please try again.")

# Enable/disable CAPTCHA
@send_typing
@bot_admin
@admin_only
async def set_captcha(update: Update, context: CallbackContext) -> None:
    """Enable or disable CAPTCHA for the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if command has arguments
    if not context.args:
        # Get current settings
        chat_data = await db.get_chat(chat.id) or {}
        captcha_settings = chat_data.get("captcha", {})
        
        captcha_enabled = captcha_settings.get("enabled", False)
        captcha_timeout = captcha_settings.get("timeout", 300)
        
        if captcha_enabled:
            message.reply_text(
                f"CAPTCHA is currently enabled in this chat.\n"
                f"Timeout: {captcha_timeout // 60} minutes\n\n"
                f"To disable, use: /setcaptcha off\n"
                f"To change timeout, use: /setcaptcha timeout [seconds]"
            )
        else:
            message.reply_text(
                f"CAPTCHA is currently disabled in this chat.\n\n"
                f"To enable, use: /setcaptcha on\n"
                f"To set timeout, use: /setcaptcha timeout [seconds]"
            )
        return
    
    # Parse arguments
    arg = context.args[0].lower()
    
    # Update chat settings
    chat_data = await db.get_chat(chat.id) or {}
    if "captcha" not in chat_data:
        chat_data["captcha"] = {}
    
    if arg == "on":
        chat_data["captcha"]["enabled"] = True
        await db.update_chat(chat.id, chat_data)
        message.reply_text("CAPTCHA has been enabled in this chat.")
    
    elif arg == "off":
        chat_data["captcha"]["enabled"] = False
        await db.update_chat(chat.id, chat_data)
        message.reply_text("CAPTCHA has been disabled in this chat.")
    
    elif arg == "timeout" and len(context.args) > 1:
        try:
            timeout = int(context.args[1])
            if timeout < 60:
                timeout = 60  # Minimum 60 seconds
            
            chat_data["captcha"]["timeout"] = timeout
            await db.update_chat(chat.id, chat_data)
            
            message.reply_text(f"CAPTCHA timeout has been set to {timeout // 60} minutes.")
        except ValueError:
            message.reply_text("Please provide a valid number for the timeout in seconds.")
    
    else:
        message.reply_text(
            "Invalid argument. Use:\n"
            "/setcaptcha on - Enable CAPTCHA\n"
            "/setcaptcha off - Disable CAPTCHA\n"
            "/setcaptcha timeout [seconds] - Set CAPTCHA timeout"
        )

# Define handlers
HANDLERS = [
    CommandHandler("setcaptcha", set_captcha, filters=~TgFilters.private),
    MessageHandler(TgFilters.status_update.new_chat_members, new_chat_member),
    CallbackQueryHandler(captcha_button, pattern=r"^captcha_"),
    MessageHandler(TgFilters.text & ~TgFilters.command, captcha_input)
]