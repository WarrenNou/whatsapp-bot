#!/usr/bin/env python3
"""
Telegram Bot Setup and Management Script

This script helps you set up and manage your EVA Fx Telegram bot.
"""

import os
import asyncio
import sys
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_requirements():
    """Check if required packages are installed"""
    try:
        import telegram
        print("✅ python-telegram-bot package is installed")
        return True
    except ImportError:
        print("❌ python-telegram-bot package is not installed")
        print("Run: pip install python-telegram-bot[all]")
        return False

def check_token():
    """Check if bot token is configured"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if token:
        print("✅ TELEGRAM_BOT_TOKEN is configured")
        return True
    else:
        print("❌ TELEGRAM_BOT_TOKEN is not set")
        print("Please set your bot token in environment variables or .env file")
        return False

async def test_bot():
    """Test if bot can connect to Telegram"""
    try:
        from telegram_bot import TelegramBot
        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            print("❌ No bot token found")
            return False
        
        bot = TelegramBot(token)
        await bot.setup_bot()
        
        # Test bot info
        bot_info = await bot.application.bot.get_me()
        print(f"✅ Bot connected successfully!")
        print(f"   Bot name: {bot_info.first_name}")
        print(f"   Bot username: @{bot_info.username}")
        print(f"   Bot ID: {bot_info.id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Bot connection failed: {e}")
        return False

async def set_webhook(webhook_url: str):
    """Set webhook URL for the bot"""
    try:
        from telegram_bot import TelegramBot
        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            print("❌ No bot token found")
            return False
        
        bot = TelegramBot(token)
        await bot.setup_bot()
        
        # Set webhook
        success = await bot.application.bot.set_webhook(url=webhook_url)
        
        if success:
            print(f"✅ Webhook set successfully to: {webhook_url}")
            
            # Get webhook info
            webhook_info = await bot.application.bot.get_webhook_info()
            print(f"   Webhook URL: {webhook_info.url}")
            print(f"   Pending updates: {webhook_info.pending_update_count}")
            
            return True
        else:
            print("❌ Failed to set webhook")
            return False
            
    except Exception as e:
        print(f"❌ Webhook setup failed: {e}")
        return False

async def delete_webhook():
    """Delete webhook (for local testing)"""
    try:
        from telegram_bot import TelegramBot
        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            print("❌ No bot token found")
            return False
        
        bot = TelegramBot(token)
        await bot.setup_bot()
        
        # Delete webhook
        success = await bot.application.bot.delete_webhook()
        
        if success:
            print("✅ Webhook deleted successfully")
            print("   Bot is now ready for local polling mode")
            return True
        else:
            print("❌ Failed to delete webhook")
            return False
            
    except Exception as e:
        print(f"❌ Webhook deletion failed: {e}")
        return False

async def run_local():
    """Run bot in local polling mode"""
    try:
        from telegram_bot import TelegramBot
        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            print("❌ No bot token found")
            print("Set TELEGRAM_BOT_TOKEN in your environment variables")
            return
        
        print("🤖 Starting EVA Fx Telegram Bot in local mode...")
        print("Press Ctrl+C to stop")
        
        bot = TelegramBot(token)
        await bot.run_polling()
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot failed to start: {e}")

def print_setup_instructions():
    """Print setup instructions"""
    print("\n" + "="*60)
    print("🤖 EVA Fx Telegram Bot Setup Instructions")
    print("="*60)
    
    print("\n1. Create Your Bot with BotFather:")
    print("   • Open Telegram and search for @BotFather")
    print("   • Send /newbot and follow instructions")
    print("   • Choose a name: EVA Fx Assistant")
    print("   • Choose a username ending in 'bot': evafx_assistant_bot")
    print("   • Copy the token BotFather gives you")
    
    print("\n2. Set Environment Variable:")
    print("   • Add to your .env file:")
    print("     TELEGRAM_BOT_TOKEN=your_bot_token_here")
    print("   • Or export in terminal:")
    print("     export TELEGRAM_BOT_TOKEN=your_bot_token_here")
    
    print("\n3. Install Required Package:")
    print("   pip install python-telegram-bot[all]")
    
    print("\n4. Test Your Bot:")
    print("   python telegram_setup.py --test")
    
    print("\n5. For Local Development:")
    print("   python telegram_setup.py --local")
    
    print("\n6. For Production (Render):")
    print("   python telegram_setup.py --webhook https://whatsapp-bot-96xm.onrender.com/telegram-webhook")
    
    print("\n" + "="*60)

def main():
    """Main setup function"""
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if not args or '--help' in args or '-h' in args:
        print_setup_instructions()
        return
    
    if '--check' in args:
        print("🔍 Checking Telegram bot setup...")
        pkg_ok = check_requirements()
        token_ok = check_token()
        
        if pkg_ok and token_ok:
            print("\n✅ All checks passed! Your bot is ready to use.")
        else:
            print("\n❌ Some requirements are missing. Please fix them first.")
        return
    
    if not check_requirements() or not check_token():
        print("\n❌ Requirements not met. Run with --check to see details.")
        return
    
    if '--test' in args:
        print("🧪 Testing bot connection...")
        asyncio.run(test_bot())
        return
    
    if '--local' in args:
        print("🏠 Running bot in local polling mode...")
        asyncio.run(run_local())
        return
    
    if '--webhook' in args:
        try:
            webhook_url = args[args.index('--webhook') + 1]
            print(f"🔗 Setting webhook to: {webhook_url}")
            asyncio.run(set_webhook(webhook_url))
        except IndexError:
            print("❌ Please provide webhook URL: --webhook https://your-domain.com/telegram-webhook")
        return
    
    if '--delete-webhook' in args:
        print("🗑️ Deleting webhook...")
        asyncio.run(delete_webhook())
        return
    
    # Default: show instructions
    print_setup_instructions()

if __name__ == '__main__':
    main()
