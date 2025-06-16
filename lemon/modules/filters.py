from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, Filters as TgFilters

from lemon.utils.decorators import admin_only, send_typing
from lemon.database import db

# Add a new filter
@send_typing
@admin_only
async def add_filter(update: Update, context: CallbackContext) -> None:
    """Add a new filter to the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if command has arguments
    if not context.args:
        message.reply_text("Please provide a keyword for the filter.")
        return
    
    # Get filter keyword and content
    keyword = context.args[0].lower()
    
    # Check if replying to a message for content
    if message.reply_to_message:
        content = message.reply_to_message.text or message.reply_to_message.caption
        
        # If no text content, check for media
        if not content:
            if message.reply_to_message.photo:
                content = f"[PHOTO]{message.reply_to_message.photo[-1].file_id}"
            elif message.reply_to_message.document:
                content = f"[DOCUMENT]{message.reply_to_message.document.file_id}"
            elif message.reply_to_message.audio:
                content = f"[AUDIO]{message.reply_to_message.audio.file_id}"
            elif message.reply_to_message.video:
                content = f"[VIDEO]{message.reply_to_message.video.file_id}"
            elif message.reply_to_message.sticker:
                content = f"[STICKER]{message.reply_to_message.sticker.file_id}"
            else:
                message.reply_text("Unsupported message type for filter.")
                return
        
        # Check for reply markup
        reply_markup = None
        if message.reply_to_message.reply_markup:
            reply_markup = message.reply_to_message.reply_markup.to_dict()
    else:
        # If not replying, use the rest of the command as content
        if len(context.args) < 2:
            message.reply_text("Please provide content for the filter or reply to a message.")
            return
        content = " ".join(context.args[1:])
        reply_markup = None
    
    # Add filter to database
    await db.add_filter(chat.id, keyword, content, reply_markup)
    
    message.reply_text(f"Filter '{keyword}' added successfully!")

# Remove a filter
@send_typing
@admin_only
async def remove_filter(update: Update, context: CallbackContext) -> None:
    """Remove a filter from the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if command has arguments
    if not context.args:
        message.reply_text("Please provide a keyword to remove.")
        return
    
    # Get filter keyword
    keyword = context.args[0].lower()
    
    # Remove filter from database
    result = await db.remove_filter(chat.id, keyword)
    
    if result:
        message.reply_text(f"Filter '{keyword}' removed successfully!")
    else:
        message.reply_text(f"No filter found with keyword '{keyword}'.")

# List all filters
@send_typing
async def list_filters(update: Update, context: CallbackContext) -> None:
    """List all filters in the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Get all filters from database
    filters = await db.get_filters(chat.id)
    
    if not filters:
        message.reply_text("No filters in this chat.")
        return
    
    # Format filter list
    filter_list = "Filters in this chat:\n\n"
    for i, filter_item in enumerate(filters, 1):
        keyword = filter_item.get("keyword", "unknown")
        filter_list += f"{i}. {keyword}\n"
    
    message.reply_text(filter_list)

# Handle incoming messages for filters
async def handle_filters(update: Update, context: CallbackContext) -> None:
    """Check incoming messages for filters"""
    chat = update.effective_chat
    message = update.effective_message
    
    # Skip in private chats
    if chat.type == "private":
        return
    
    # Skip commands
    if message.text and message.text.startswith("/"):
        return
    
    # Get all filters from database
    filters = await db.get_filters(chat.id)
    
    if not filters:
        return
    
    # Check if message matches any filter
    if message.text:
        text = message.text.lower()
        for filter_item in filters:
            keyword = filter_item.get("keyword", "").lower()
            
            # Check if keyword is in message
            if keyword in text.split():
                content = filter_item.get("content", "")
                reply_markup = filter_item.get("reply_markup")
                
                # Handle different content types
                if content.startswith("[PHOTO]"):
                    file_id = content[7:]
                    message.reply_photo(
                        photo=file_id,
                        reply_markup=reply_markup
                    )
                elif content.startswith("[DOCUMENT]"):
                    file_id = content[10:]
                    message.reply_document(
                        document=file_id,
                        reply_markup=reply_markup
                    )
                elif content.startswith("[AUDIO]"):
                    file_id = content[7:]
                    message.reply_audio(
                        audio=file_id,
                        reply_markup=reply_markup
                    )
                elif content.startswith("[VIDEO]"):
                    file_id = content[7:]
                    message.reply_video(
                        video=file_id,
                        reply_markup=reply_markup
                    )
                elif content.startswith("[STICKER]"):
                    file_id = content[9:]
                    message.reply_sticker(
                        sticker=file_id
                    )
                else:
                    # Text content
                    message.reply_text(
                        content,
                        reply_markup=reply_markup
                    )
                
                # Only respond to the first matching filter
                break

# Define handlers
HANDLERS = [
    CommandHandler("filter", add_filter, filters=~TgFilters.private),
    CommandHandler("stop", remove_filter, filters=~TgFilters.private),
    CommandHandler("filters", list_filters, filters=~TgFilters.private),
    MessageHandler(TgFilters.text & ~TgFilters.command & ~TgFilters.private, handle_filters)
]