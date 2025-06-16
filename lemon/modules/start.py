from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler

from lemon.utils.decorators import send_typing

# Start command handler
@send_typing
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    
    # Create keyboard with buttons
    keyboard = [
        [
            InlineKeyboardButton("Commands", callback_data="help_commands"),
            InlineKeyboardButton("Support", url="https://t.me/saikatftw")
        ],
        [
            InlineKeyboardButton("Add to Group", url=f"https://t.me/{context.bot.username}?startgroup=true")
        ],
        [
            InlineKeyboardButton("Source Code", url="https://github.com/saikatwtf/Lemon")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send welcome message
    from lemon.languages import get_text
    
    # Get user's language preference (default to English)
    lang_code = context.user_data.get("language", "en") if context.user_data else "en"
    
    # Get localized welcome message
    welcome_text = get_text("start_message", lang_code, name=user.first_name)
    
    update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup
    )

# Help command handler
@send_typing
def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    # Create keyboard with category buttons
    keyboard = [
        [
            InlineKeyboardButton("Admin", callback_data="help_admin"),
            InlineKeyboardButton("Moderation", callback_data="help_moderation")
        ],
        [
            InlineKeyboardButton("Filters", callback_data="help_filters"),
            InlineKeyboardButton("Notes", callback_data="help_notes")
        ],
        [
            InlineKeyboardButton("Approval", callback_data="help_approval"),
            InlineKeyboardButton("Federation", callback_data="help_federation")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "Here's what I can help you with. Select a category:",
        reply_markup=reply_markup
    )

# Help button callback handler
def help_button(update: Update, context: CallbackContext) -> None:
    """Handle help button callbacks."""
    query = update.callback_query
    query.answer()
    
    # Get the category from callback data
    category = query.data.split("_")[1]
    
    # Back button
    keyboard = [[InlineKeyboardButton("Back", callback_data="help_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Show help text based on category
    if category == "commands":
        text = "Here are the available commands:\n\n" \
               "/start - Start the bot\n" \
               "/help - Show this help message\n" \
               "/settings - Configure bot settings\n" \
               "/language - Change bot language\n" \
               "/privacy - View privacy policy\n" \
               "/gdpr - Request data deletion"
    
    elif category == "admin":
        text = "Admin Commands:\n\n" \
               "/adminlist - List all admins\n" \
               "/promote - Promote a user to admin\n" \
               "/demote - Demote an admin\n" \
               "/pin - Pin a message\n" \
               "/unpin - Unpin a message\n" \
               "/unpinall - Unpin all messages"
    
    elif category == "moderation":
        text = "Moderation Commands:\n\n" \
               "/ban - Ban a user\n" \
               "/unban - Unban a user\n" \
               "/kick - Kick a user\n" \
               "/mute - Mute a user\n" \
               "/unmute - Unmute a user\n" \
               "/warn - Warn a user\n" \
               "/resetwarns - Reset warnings\n" \
               "/warns - Check warnings\n" \
               "/report - Report a message"
    
    elif category == "filters":
        text = "Filter Commands:\n\n" \
               "/filter - Add a new filter\n" \
               "/stop - Remove a filter\n" \
               "/filters - List all filters\n" \
               "/cleanfilters - Remove all filters"
    
    elif category == "notes":
        text = "Notes Commands:\n\n" \
               "/note - Save a note\n" \
               "/notes - List all notes\n" \
               "/clear - Delete a note\n" \
               "/clearnotes - Delete all notes\n" \
               "Use #note_name to retrieve a note"
    
    elif category == "approval":
        text = "Approval Commands:\n\n" \
               "/approve - Approve a user\n" \
               "/disapprove - Disapprove a user\n" \
               "/approved - List approved users\n" \
               "/approval - Check if approved"
    
    elif category == "federation":
        text = "Federation Commands:\n\n" \
               "/newfed - Create a federation\n" \
               "/joinfed - Join a federation\n" \
               "/leavefed - Leave a federation\n" \
               "/fedinfo - Get federation info\n" \
               "/fban - Ban from federation\n" \
               "/unfban - Unban from federation"
    
    elif category == "back":
        # Return to main help menu with keyboard
        keyboard = [
            [
                InlineKeyboardButton("Admin", callback_data="help_admin"),
                InlineKeyboardButton("Moderation", callback_data="help_moderation")
            ],
            [
                InlineKeyboardButton("Filters", callback_data="help_filters"),
                InlineKeyboardButton("Notes", callback_data="help_notes")
            ],
            [
                InlineKeyboardButton("Approval", callback_data="help_approval"),
                InlineKeyboardButton("Federation", callback_data="help_federation")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            text="Here's what I can help you with. Select a category:",
            reply_markup=reply_markup
        )
        return
    
    else:
        text = "Unknown category. Please try again."
    
    # Edit the message with the help text
    query.edit_message_text(text=text, reply_markup=reply_markup)

# Privacy command handler
@send_typing
def privacy_command(update: Update, context: CallbackContext) -> None:
    """Send privacy policy when the command /privacy is issued."""
    update.message.reply_text(
        "Privacy Policy for Lemon Bot:\n\n"
        "1. Data Collection: We collect minimal data necessary for bot functionality.\n"
        "2. Data Usage: Your data is only used to provide bot services.\n"
        "3. Data Sharing: We do not share your data with third parties.\n"
        "4. Data Retention: Data is retained only as long as necessary.\n"
        "5. Data Deletion: You can request data deletion via /gdpr command.\n\n"
        "For more information, contact our support."
    )

# Define handlers
HANDLERS = [
    CommandHandler("start", start),
    CommandHandler("help", help_command),
    CommandHandler("privacy", privacy_command),
    CallbackQueryHandler(help_button, pattern=r"^help_")
]