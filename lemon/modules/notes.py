from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, Filters as TgFilters

from lemon.utils.decorators import admin_only, send_typing
from lemon.database import db

# Save a note
@send_typing
@admin_only
async def save_note(update: Update, context: CallbackContext) -> None:
    """Save a note in the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if command has arguments
    if not context.args:
        message.reply_text("Please provide a name for the note.")
        return
    
    # Get note name and content
    note_name = context.args[0].lower()
    
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
                message.reply_text("Unsupported message type for note.")
                return
        
        # Check for reply markup
        reply_markup = None
        if message.reply_to_message.reply_markup:
            reply_markup = message.reply_to_message.reply_markup.to_dict()
    else:
        # If not replying, use the rest of the command as content
        if len(context.args) < 2:
            message.reply_text("Please provide content for the note or reply to a message.")
            return
        content = " ".join(context.args[1:])
        reply_markup = None
    
    # Save note to database
    await db.save_note(chat.id, note_name, content, reply_markup)
    
    message.reply_text(f"Note '{note_name}' saved successfully!")

# Get a note
@send_typing
async def get_note(update: Update, context: CallbackContext) -> None:
    """Get a note from the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    # Check if message starts with #
    if not message.text or not message.text.startswith("#"):
        return
    
    # Get note name
    note_name = message.text[1:].lower().split()[0]
    
    # Get note from database
    note = await db.get_note(chat.id, note_name)
    
    if not note:
        # Note not found
        return
    
    content = note.get("content", "")
    reply_markup = note.get("reply_markup")
    
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

# List all notes
@send_typing
async def list_notes(update: Update, context: CallbackContext) -> None:
    """List all notes in the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Get all notes from database
    notes = await db.get_all_notes(chat.id)
    
    if not notes:
        message.reply_text("No notes in this chat.")
        return
    
    # Format note list
    note_list = "Notes in this chat:\n\n"
    for i, note in enumerate(notes, 1):
        name = note.get("name", "unknown")
        note_list += f"{i}. #{name}\n"
    
    message.reply_text(note_list)

# Delete a note
@send_typing
@admin_only
async def delete_note(update: Update, context: CallbackContext) -> None:
    """Delete a note from the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Check if command has arguments
    if not context.args:
        message.reply_text("Please provide a name for the note to delete.")
        return
    
    # Get note name
    note_name = context.args[0].lower()
    
    # Delete note from database
    result = await db.delete_note(chat.id, note_name)
    
    if result:
        message.reply_text(f"Note '{note_name}' deleted successfully!")
    else:
        message.reply_text(f"No note found with name '{note_name}'.")

# Delete all notes
@send_typing
@admin_only
async def clear_notes(update: Update, context: CallbackContext) -> None:
    """Delete all notes from the chat"""
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.type == "private":
        message.reply_text("This command can only be used in groups.")
        return
    
    # Confirm deletion
    if not context.args or context.args[0].lower() != "confirm":
        message.reply_text(
            "This will delete ALL notes in this chat.\n"
            "To confirm, use /clearnotes confirm"
        )
        return
    
    # Get all notes from database
    notes = await db.get_all_notes(chat.id)
    
    if not notes:
        message.reply_text("No notes in this chat.")
        return
    
    # Delete all notes
    for note in notes:
        name = note.get("name", "")
        await db.delete_note(chat.id, name)
    
    message.reply_text("All notes have been deleted.")

# Define handlers
HANDLERS = [
    CommandHandler("note", save_note, filters=~TgFilters.private),
    CommandHandler("notes", list_notes, filters=~TgFilters.private),
    CommandHandler("clear", delete_note, filters=~TgFilters.private),
    CommandHandler("clearnotes", clear_notes, filters=~TgFilters.private),
    MessageHandler(TgFilters.text & TgFilters.regex(r"^#\w+"), get_note)
]