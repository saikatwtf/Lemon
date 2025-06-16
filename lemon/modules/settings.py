from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler, Filters as TgFilters
from telegram.error import BadRequest

from lemon.utils.decorators import admin_only, bot_admin, send_typing
from lemon.database import db
from lemon.languages import get_text

# Settings command handler
@send_typing
@bot_admin
@admin_only
async def settings(update: Update, context: CallbackContext) -> None:
    """Show and manage bot settings"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Get chat settings
    chat_data = await db.get_chat(chat.id) or {}
    
    # Create keyboard with settings buttons
    keyboard = [
        [
            InlineKeyboardButton("Language", callback_data="settings_language"),
            InlineKeyboardButton("Welcome", callback_data="settings_welcome")
        ],
        [
            InlineKeyboardButton("Filters", callback_data="settings_filters"),
            InlineKeyboardButton("Notes", callback_data="settings_notes")
        ],
        [
            InlineKeyboardButton("Clean Service", callback_data="settings_clean"),
            InlineKeyboardButton("CAPTCHA", callback_data="settings_captcha")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message.reply_text(
        f"Settings for {chat.title}\n\n"
        f"Select a category to configure:",
        reply_markup=reply_markup
    )

# Settings button callback handler
async def settings_button(update: Update, context: CallbackContext) -> None:
    """Handle settings button callbacks"""
    query = update.callback_query
    query.answer()
    
    # Get the category from callback data
    data = query.data.split("_")
    if len(data) < 2:
        return
    
    category = data[1]
    
    # Back button
    keyboard = [[InlineKeyboardButton("Back", callback_data="settings_back")]]
    
    # Show settings based on category
    if category == "language":
        # Language settings
        keyboard = [
            [
                InlineKeyboardButton("English", callback_data="setlang_en"),
                InlineKeyboardButton("Bengali", callback_data="setlang_bn")
            ],
            [InlineKeyboardButton("Back", callback_data="settings_back")]
        ]
        
        query.edit_message_text(
            text="Select a language for the bot:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif category == "back":
        # Return to main settings menu
        keyboard = [
            [
                InlineKeyboardButton("Language", callback_data="settings_language"),
                InlineKeyboardButton("Welcome", callback_data="settings_welcome")
            ],
            [
                InlineKeyboardButton("Filters", callback_data="settings_filters"),
                InlineKeyboardButton("Notes", callback_data="settings_notes")
            ],
            [
                InlineKeyboardButton("Clean Service", callback_data="settings_clean"),
                InlineKeyboardButton("CAPTCHA", callback_data="settings_captcha")
            ]
        ]
        
        query.edit_message_text(
            text=f"Settings for {query.message.chat.title}\n\n"
                 f"Select a category to configure:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    else:
        query.edit_message_text(
            text=f"Settings for {category} will be available soon.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Set language callback handler
async def set_language(update: Update, context: CallbackContext) -> None:
    """Set language for the chat"""
    query = update.callback_query
    query.answer()
    
    # Get the language code from callback data
    data = query.data.split("_")
    if len(data) < 2:
        return
    
    lang_code = data[1]
    chat = query.message.chat
    
    # Update chat settings
    chat_data = await db.get_chat(chat.id) or {}
    chat_data["language"] = lang_code
    await db.update_chat(chat.id, chat_data)
    
    # Return to language settings
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="setlang_en"),
            InlineKeyboardButton("Bengali", callback_data="setlang_bn")
        ],
        [InlineKeyboardButton("Back", callback_data="settings_back")]
    ]
    
    query.edit_message_text(
        text=f"Language has been set to {lang_code.upper()}.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Language command handler
@send_typing
async def language_command(update: Update, context: CallbackContext) -> None:
    """Set user language preference"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    # Create keyboard with language options
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="userlang_en"),
            InlineKeyboardButton("Bengali", callback_data="userlang_bn")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if chat.type == "private":
        # For private chats, set user language
        message.reply_text(
            "Select your preferred language:",
            reply_markup=reply_markup
        )
    else:
        # For groups, show group language and option to set personal preference
        chat_data = await db.get_chat(chat.id) or {}
        group_lang = chat_data.get("language", "en").upper()
        
        message.reply_text(
            f"Current group language: {group_lang}\n\n"
            f"To set your personal language preference, select below:",
            reply_markup=reply_markup
        )

# User language callback handler
async def user_language(update: Update, context: CallbackContext) -> None:
    """Set user language preference"""
    query = update.callback_query
    query.answer()
    
    # Get the language code from callback data
    data = query.data.split("_")
    if len(data) < 2:
        return
    
    lang_code = data[1]
    user = query.from_user
    
    # Update user data
    if not context.user_data:
        context.user_data = {}
    
    context.user_data["language"] = lang_code
    
    # Save to database
    user_data = await db.get_user(user.id) or {}
    user_data["language"] = lang_code
    await db.update_user(user.id, user_data)
    
    query.edit_message_text(
        text=f"Your language preference has been set to {lang_code.upper()}."
    )

# GDPR command handler
@send_typing
async def gdpr_command(update: Update, context: CallbackContext) -> None:
    """Handle GDPR data deletion requests"""
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    
    if chat.type != "private":
        message.reply_text("Please use this command in private chat with the bot.")
        return
    
    # Create confirmation keyboard
    keyboard = [
        [
            InlineKeyboardButton("Yes, delete my data", callback_data="gdpr_confirm"),
            InlineKeyboardButton("No, keep my data", callback_data="gdpr_cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message.reply_text(
        "This will delete all your personal data stored by the bot.\n\n"
        "This includes:\n"
        "- Your language preferences\n"
        "- Your custom settings\n"
        "- Any notes or filters you've created\n\n"
        "Are you sure you want to proceed?",
        reply_markup=reply_markup
    )

# GDPR callback handler
async def gdpr_button(update: Update, context: CallbackContext) -> None:
    """Handle GDPR confirmation buttons"""
    query = update.callback_query
    query.answer()
    
    # Get the action from callback data
    data = query.data.split("_")
    if len(data) < 2:
        return
    
    action = data[1]
    user = query.from_user
    
    if action == "confirm":
        # Delete user data
        await db.async_users.delete_one({"_id": user.id})
        
        # Delete user notes
        await db.async_notes.delete_many({"creator_id": user.id})
        
        # Delete user filters
        await db.async_filters.delete_many({"creator_id": user.id})
        
        # Clear user data from context
        context.user_data.clear()
        
        query.edit_message_text(
            text="Your data has been deleted as per GDPR requirements."
        )
        
        # Log the action
        log_channel = context.bot_data.get("log_channel")
        if log_channel:
            context.bot.send_message(
                chat_id=log_channel,
                text=f"#GDPR_DELETE\n"
                     f"User: {user.first_name} (ID: {user.id})\n"
                     f"Data deleted as per GDPR request."
            )
    
    elif action == "cancel":
        query.edit_message_text(
            text="Data deletion cancelled. Your data remains stored."
        )

# Define handlers
HANDLERS = [
    CommandHandler("settings", lambda update, context: context.dispatcher.run_async(settings, update, context), filters=~TgFilters.private),
    CommandHandler("language", lambda update, context: context.dispatcher.run_async(language_command, update, context)),
    CommandHandler("gdpr", lambda update, context: context.dispatcher.run_async(gdpr_command, update, context)),
    CallbackQueryHandler(lambda update, context: context.dispatcher.run_async(settings_button, update, context), pattern=r"^settings_"),
    CallbackQueryHandler(lambda update, context: context.dispatcher.run_async(set_language, update, context), pattern=r"^setlang_"),
    CallbackQueryHandler(lambda update, context: context.dispatcher.run_async(user_language, update, context), pattern=r"^userlang_"),
    CallbackQueryHandler(lambda update, context: context.dispatcher.run_async(gdpr_button, update, context), pattern=r"^gdpr_")
]