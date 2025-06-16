import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext, Filters
from telegram.error import BadRequest

from lemon.utils.decorators import admin_only, bot_admin, send_typing
from lemon.database import db

# Maximum number of warnings before ban
MAX_WARNS = int(os.getenv("MAX_WARNS", 3))

# Warn a user
@send_typing
@bot_admin
@admin_only
async def warn_user(update: Update, context: CallbackContext) -> None:
    """Warn a user in the group"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if replying to a message
    if not message.reply_to_message:
        message.reply_text("Reply to a message to warn the user.")
        return
    
    # Get the user to warn
    warned_user = message.reply_to_message.from_user
    
    # Don't allow warning admins
    try:
        member = chat.get_member(warned_user.id)
        if member.status in ["administrator", "creator"]:
            message.reply_text("I can't warn administrators!")
            return
    except BadRequest as e:
        message.reply_text(f"Error: {e.message}")
        return
    
    # Get reason for warning
    reason = " ".join(context.args) if context.args else "No reason provided"
    
    try:
        # Add warning to database
        warn_count = await db.add_warn(chat.id, warned_user.id, reason)
        
        # Check if user has reached max warnings
        if warn_count >= MAX_WARNS:
            # Ban the user
            chat.kick_member(warned_user.id)
            
            message.reply_text(
                f"{warned_user.first_name} has been banned after receiving {warn_count} warnings."
            )
            
            # Reset warnings after ban
            await db.reset_warns(chat.id, warned_user.id)
            
            # Log the action
            if context.bot.log_channel:
                context.bot.send_message(
                    chat_id=context.bot.log_channel,
                    text=f"#BAN_AFTER_WARNINGS\n"
                         f"User: {warned_user.first_name} (ID: {warned_user.id})\n"
                         f"Chat: {chat.title} (ID: {chat.id})\n"
                         f"Warnings: {warn_count}/{MAX_WARNS}\n"
                         f"Reason for last warning: {reason}"
                )
        else:
            # Create warning message with inline keyboard
            keyboard = [
                [InlineKeyboardButton("Remove Warning", callback_data=f"rmwarn_{warned_user.id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message.reply_text(
                f"User {warned_user.first_name} has been warned.\n"
                f"Current warnings: {warn_count}/{MAX_WARNS}\n"
                f"Reason: {reason}",
                reply_markup=reply_markup
            )
            
            # Log the action
            if context.bot.log_channel:
                context.bot.send_message(
                    chat_id=context.bot.log_channel,
                    text=f"#WARN\n"
                         f"Admin: {user.first_name} (ID: {user.id})\n"
                         f"User: {warned_user.first_name} (ID: {warned_user.id})\n"
                         f"Chat: {chat.title} (ID: {chat.id})\n"
                         f"Warnings: {warn_count}/{MAX_WARNS}\n"
                         f"Reason: {reason}"
                )
    except Exception as e:
        message.reply_text(f"An error occurred: {e}")

# Reset warnings for a user
@send_typing
@bot_admin
@admin_only
async def reset_warns(update: Update, context: CallbackContext) -> None:
    """Reset warnings for a user"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Get the user to reset warnings for
    if not message.reply_to_message and not context.args:
        message.reply_text("Reply to a user or provide a username to reset warnings.")
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
        
        # Reset warnings in database
        await db.reset_warns(chat.id, target_id)
        
        message.reply_text(f"Warnings have been reset for {target_name}.")
        
        # Log the action
        if context.bot.log_channel:
            context.bot.send_message(
                chat_id=context.bot.log_channel,
                text=f"#RESETWARNS\n"
                     f"Admin: {user.first_name} (ID: {user.id})\n"
                     f"User: {target_name} (ID: {target_id})\n"
                     f"Chat: {chat.title} (ID: {chat.id})"
            )
    except BadRequest as e:
        message.reply_text(f"Error: {e.message}")

# Check warnings for a user
@send_typing
async def check_warns(update: Update, context: CallbackContext) -> None:
    """Check warnings for a user"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Get the user to check warnings for
    if not message.reply_to_message and not context.args:
        message.reply_text("Reply to a user or provide a username to check warnings.")
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
        
        # Get warnings from database
        warns_data = await db.get_warns(chat.id, target_id)
        
        if not warns_data or not warns_data.get("warns"):
            message.reply_text(f"{target_name} has no warnings.")
            return
        
        warns = warns_data.get("warns", [])
        warn_count = len(warns)
        
        # Format warnings
        warn_text = f"{target_name} has {warn_count}/{MAX_WARNS} warnings:\n\n"
        for i, warn in enumerate(warns, 1):
            reason = warn.get("reason", "No reason provided")
            warn_text += f"{i}. {reason}\n"
        
        message.reply_text(warn_text)
    except BadRequest as e:
        message.reply_text(f"Error: {e.message}")

# Report a message to admins
@send_typing
async def report(update: Update, context: CallbackContext) -> None:
    """Report a message to group admins"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if replying to a message
    if not message.reply_to_message:
        message.reply_text("Reply to a message to report it to admins.")
        return
    
    # Get all admins in the group
    administrators = chat.get_administrators()
    admin_list = [admin.user.id for admin in administrators]
    
    # Format report message
    reported_msg = message.reply_to_message
    report_reason = " ".join(context.args) if context.args else "No reason provided"
    
    report_text = f"⚠️ REPORT ⚠️\n" \
                  f"From: {user.first_name} (ID: {user.id})\n" \
                  f"Message: {reported_msg.link}\n" \
                  f"Reason: {report_reason}"
    
    # Mention all admins
    admin_mention = " ".join([f"[.](tg://user?id={admin_id})" for admin_id in admin_list])
    
    # Send report
    message.reply_text(
        f"{report_text}\n\n{admin_mention}",
        parse_mode="Markdown"
    )

# Define handlers
HANDLERS = [
    CommandHandler("warn", warn_user, filters=~Filters.private),
    CommandHandler("resetwarns", reset_warns, filters=~Filters.private),
    CommandHandler("warns", check_warns, filters=~Filters.private),
    CommandHandler("report", report, filters=~Filters.private)
]