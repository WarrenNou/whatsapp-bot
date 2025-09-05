import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from fx_trader import FXTrader
import asyncio
import json

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.fx_trader = FXTrader()
        self.application = None
        
    async def setup_bot(self):
        """Initialize the bot application"""
        self.application = Application.builder().token(self.token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("rates", self.rates_command))
        self.application.add_handler(CommandHandler("convert", self.convert_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Set up bot commands for the menu
        commands = [
            BotCommand("start", "Start the bot and see welcome message"),
            BotCommand("help", "Show help information"),
            BotCommand("rates", "Get current exchange rates"),
            BotCommand("convert", "Convert currencies (e.g., /convert 100 USD to EUR)"),
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info("Telegram bot setup completed")
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        greeting = self.fx_trader.get_greeting_and_disclaimer()
        
        # Create inline keyboard with quick actions
        keyboard = [
            [
                InlineKeyboardButton("📊 Current Rates", callback_data="rates"),
                InlineKeyboardButton("💱 Convert Currency", callback_data="convert")
            ],
            [
                InlineKeyboardButton("🌐 Visit Website", url="https://whatsapp-bot-96xm.onrender.com"),
                InlineKeyboardButton("📱 Join Channel", url="https://t.me/+dKTLjP_OHeA3MDE0")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_message = f"👋 Hello {user.first_name}!\n\n{greeting}\n\n🚀 Use the buttons below or type your message:"
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
        logger.info(f"Start command sent to user {user.id} ({user.username})")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 *EVA Fx Assistant Help*

*Available Commands:*
/start - Welcome message and quick actions
/help - Show this help message
/rates - Get current exchange rates
/convert - Convert currencies (e.g., /convert 100 USD to EUR)

*Quick Actions:*
• Type currency amounts (e.g., "100 USD", "50 EUR")
• Ask about exchange rates
• Request currency conversions
• Get FX market information

*Examples:*
• "What are today's rates?"
• "100 USD to EUR"
• "Convert 500 GBP to USD"
• "EUR rates"

💬 Just type your message and I'll help you with FX trading information!
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        logger.info(f"Help command sent to user {update.effective_user.id}")

    async def rates_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /rates command"""
        try:
            rates_info = self.fx_trader.get_daily_rates()
            
            # Create quick conversion buttons
            keyboard = [
                [
                    InlineKeyboardButton("100 USD", callback_data="convert_100_USD"),
                    InlineKeyboardButton("100 EUR", callback_data="convert_100_EUR")
                ],
                [
                    InlineKeyboardButton("100 GBP", callback_data="convert_100_GBP"),
                    InlineKeyboardButton("100 JPY", callback_data="convert_100_JPY")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(rates_info, reply_markup=reply_markup)
            logger.info(f"Rates sent to user {update.effective_user.id}")
            
        except Exception as e:
            logger.error(f"Error getting rates: {e}")
            await update.message.reply_text("❌ Sorry, I couldn't get the current rates. Please try again later.")

    async def convert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /convert command"""
        if not context.args or len(context.args) < 4:
            await update.message.reply_text(
                "💱 *Currency Conversion*\n\n"
                "Usage: `/convert <amount> <from_currency> to <to_currency>`\n\n"
                "*Examples:*\n"
                "• `/convert 100 USD to XAF`\n"
                "• `/convert 50 AED to XOF`\n"
                "• `/convert 200 USDT to XAF`",
                parse_mode='Markdown'
            )
            return
            
        try:
            amount = float(context.args[0])
            from_currency = context.args[1].upper()
            to_currency = context.args[3].upper()
            
            # Use the existing get_trading_process_info method for conversions
            result = self.fx_trader.get_trading_process_info(amount, from_currency, to_currency)
            await update.message.reply_text(result)
            logger.info(f"Conversion sent to user {update.effective_user.id}: {amount} {from_currency} to {to_currency}")
            
        except (ValueError, IndexError) as e:
            logger.error(f"Conversion error: {e}")
            await update.message.reply_text("❌ Invalid format. Use: `/convert 100 USD to XAF`", parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Conversion calculation error: {e}")
            await update.message.reply_text("❌ Sorry, I couldn't perform the conversion. Please try again.")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        if callback_data == "rates":
            rates_info = self.fx_trader.get_daily_rates()
            await query.edit_message_text(text=rates_info)
            
        elif callback_data == "convert":
            await query.edit_message_text(
                text="💱 *Currency Conversion*\n\n"
                     "Type your conversion request like:\n"
                     "• `100 USD to EUR`\n"
                     "• `Convert 50 GBP to JPY`\n"
                     "• `200 EUR to USD`",
                parse_mode='Markdown'
            )
            
        elif callback_data.startswith("convert_"):
            # Handle quick conversion buttons (e.g., "convert_100_USD")
            parts = callback_data.split("_")
            amount = float(parts[1])
            from_currency = parts[2]
            
            # For EVA Fx, convert to XAF by default
            to_currency = 'XAF'
            result = self.fx_trader.get_trading_process_info(amount, from_currency, to_currency)
            await query.edit_message_text(text=result)
        
        logger.info(f"Button callback handled: {callback_data} for user {query.from_user.id}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        user = update.effective_user
        message_text = update.message.text.lower()
        
        logger.info(f"Message from {user.id} ({user.username}): {update.message.text}")
        
        try:
            # Check for common patterns
            if any(word in message_text for word in ['rate', 'rates', 'exchange']):
                response = self.fx_trader.get_daily_rates()
                
            elif 'convert' in message_text or 'to' in message_text:
                # Try to parse conversion request
                response = self._parse_conversion_message(update.message.text)
                
            elif any(currency in message_text.upper() for currency in ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD']):
                # Handle currency amount mentions
                response = self._handle_currency_mention(update.message.text)
                
            else:
                # Use OpenAI for general queries (you'll need to implement this)
                response = "💬 I'm here to help with FX trading! Try asking about rates, conversions, or use /help for more options."
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text("❌ Sorry, I encountered an error. Please try again or use /help.")

    def _parse_conversion_message(self, message: str) -> str:
        """Parse conversion requests from natural language"""
        import re
        
        # Pattern to match "100 USD to XAF" or "convert 100 USD to XAF"
        pattern = r'(?:convert\s+)?(\d+(?:\.\d+)?)\s+([A-Z]{3})\s+to\s+([A-Z]{3})'
        match = re.search(pattern, message.upper())
        
        if match:
            amount = float(match.group(1))
            from_currency = match.group(2)
            to_currency = match.group(3)
            
            return self.fx_trader.get_trading_process_info(amount, from_currency, to_currency)
        
        return "💱 I couldn't understand the conversion. Try: '100 USD to XAF'"

    def _handle_currency_mention(self, message: str) -> str:
        """Handle messages mentioning currency amounts"""
        import re
        
        # Pattern to match currency amounts like "100 USD"
        pattern = r'(\d+(?:\.\d+)?)\s+([A-Z]{3})'
        matches = re.findall(pattern, message.upper())
        
        if matches:
            amount, currency = matches[0]
            amount = float(amount)
            
            # For EVA Fx, show calculation result
            return self.fx_trader.calculate_exchange(amount, currency)
        
        return self.fx_trader.get_daily_rates()

    async def run_polling(self):
        """Run the bot in polling mode (for local development)"""
        if not self.application:
            await self.setup_bot()
        
        logger.info("Starting Telegram bot in polling mode...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Keep the bot running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Stopping bot...")
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

    async def handle_webhook(self, update_data: dict):
        """Handle webhook updates (for production)"""
        if not self.application:
            await self.setup_bot()
        
        try:
            update = Update.de_json(update_data, self.application.bot)
            await self.application.process_update(update)
            logger.info("Webhook update processed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error processing webhook update: {e}")
            return False

# For local testing
async def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return
    
    bot = TelegramBot(token)
    await bot.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
