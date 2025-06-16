import logging
import os
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class LemonBot:
    """Main bot class for Lemon Telegram Bot"""
    
    def __init__(self):
        """Initialize the bot with token from environment variables"""
        self.token = os.getenv("BOT_TOKEN")
        if not self.token:
            raise ValueError("No token provided. Set the BOT_TOKEN environment variable.")
        
        self.updater = Updater(self.token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        
        # Bot information
        self.bot = self.updater.bot
        self.bot_id = self.bot.id
        self.bot_username = os.getenv("BOT_USERNAME") or self.bot.username
        
        # Admin information
        self.owner_id = int(os.getenv("OWNER_ID", 0))
        self.sudo_users = [int(user_id) for user_id in os.getenv("SUDO_USERS", "").split(",") if user_id]
        if self.owner_id:
            self.sudo_users.append(self.owner_id)
            
        # Store bot instance in context.bot_data instead of attaching to bot object
        self.dispatcher.bot_data["sudo_users"] = self.sudo_users
        self.dispatcher.bot_data["bot_instance"] = self
        
        # Other settings
        self.log_channel = os.getenv("LOG_CHANNEL")
        self.support_chat = os.getenv("SUPPORT_CHAT")
        self.default_language = os.getenv("DEFAULT_LANGUAGE", "en")
        
        logger.info("Bot initialized")
    
    def register_handlers(self):
        """Register all command and message handlers"""
        from lemon.modules import ALL_HANDLERS
        
        for handler_list in ALL_HANDLERS:
            for handler in handler_list:
                self.dispatcher.add_handler(handler)
        
        logger.info("All handlers registered")
    
    def start(self):
        """Start the bot"""
        # Register handlers
        self.register_handlers()
        
        # Start the Bot
        self.updater.start_polling()
        logger.info("Bot started polling")
        
        # Run the bot until you press Ctrl-C
        self.updater.idle()
    
    def send_log(self, message):
        """Send a log message to the log channel"""
        if self.log_channel:
            try:
                self.bot.send_message(chat_id=self.log_channel, text=message)
                return True
            except Exception as e:
                logger.error(f"Failed to send log message: {e}")
        return False
    
    def is_admin(self, user_id):
        """Check if a user is a bot admin"""
        return user_id in self.sudo_users