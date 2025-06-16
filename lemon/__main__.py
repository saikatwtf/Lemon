import logging
import os
from dotenv import load_dotenv

from lemon.core.bot import LemonBot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def main():
    """Start the bot"""
    try:
        # Create and start the bot
        bot = LemonBot()
        bot.start()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

if __name__ == "__main__":
    main()