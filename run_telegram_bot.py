#!/usr/bin/env python3
"""
Telegram Bot Runner - Standalone script to run the bot
Works both locally and on cloud platforms like Render
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/telegram_bot.log') if os.path.exists('logs') else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = ['TELEGRAM_BOT_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in your .env file or environment")
        return False
    
    return True

async def run_telegram_bot():
    """Run the Telegram bot with proper error handling"""
    try:
        from telegram_bot import TelegramBot
        
        # Get bot token
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN not found")
            return False
        
        logger.info("Initializing Telegram bot...")
        bot = TelegramBot(token)
        
        # Check if we're on a cloud platform (Render, Heroku, etc.)
        is_cloud_platform = any([
            os.getenv('RENDER'),
            os.getenv('HEROKU'),
            os.getenv('RAILWAY_PROJECT_NAME'),
            os.getenv('VERCEL'),
            os.getenv('PORT')  # Common cloud platform indicator
        ])
        
        if is_cloud_platform:
            logger.info("Cloud platform detected - bot will run in webhook mode when integrated")
            # For cloud platforms, the bot should be integrated with the main Flask app
            logger.info("Note: For cloud deployment, ensure the main Flask app is running")
            logger.info("The bot will handle webhooks via the /telegram-webhook endpoint")
        else:
            logger.info("Local environment detected - running in polling mode")
            await bot.run_polling()
        
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import telegram bot: {e}")
        logger.error("Make sure python-telegram-bot is installed: pip install python-telegram-bot[all]")
        return False
    except Exception as e:
        logger.error(f"Error running telegram bot: {e}")
        return False

async def main():
    """Main function"""
    logger.info("=== Telegram Bot Runner ===")
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Run the bot
    success = await run_telegram_bot()
    if not success:
        sys.exit(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
