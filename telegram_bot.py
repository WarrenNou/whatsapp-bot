import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from fx_trader import FXTrader
from openai import OpenAI
import asyncio
import json
import re
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
        
        # Initialize OpenAI client
        self.openai_client = None
        try:
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                self.openai_client = OpenAI(api_key=openai_key)
                logger.info("OpenAI client initialized for Telegram bot")
            else:
                logger.warning("OpenAI API key not found - AI responses will be limited")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
        
        # Group content moderation settings
        self.group_moderation_enabled = True
        self.spam_keywords = ['spam', 'scam', 'buy now', 'click here', 'limited time']
        
        # AI personality for more human responses
        self.ai_personality = """You are Eva, a friendly and professional FX trading assistant. You help people with currency exchange, rates, and trading information. You are knowledgeable, helpful, and speak in a warm, conversational tone. You work for EVA Fx, a trusted currency exchange service. Always be helpful but also include appropriate disclaimers about trading risks when discussing financial matters."""
        
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
        """Handle incoming text messages"""
        # Add comprehensive null checks
        if not update or not update.message:
            return
            
        # Handle non-text messages (photos, documents, etc.)
        if not hasattr(update.message, 'text') or not update.message.text:
            return
        
        user = update.effective_user
        if not user:
            return
            
        username = user.username if user.username else "Unknown"
        message_text = update.message.text

    async def _get_ai_response(self, message: str, user) -> str:
        """Get AI-powered response for general conversation"""
        if not self.openai_client:
            return "💬 I'm here to help with FX trading! Try asking about rates, conversions, or use /help for more options."
        
        try:
            # Create context-aware prompt
            prompt = f"""
            {self.ai_personality}
            
            Current context: You're chatting with {user.first_name or 'a user'} via Telegram.
            Their message: "{message}"
            
            Important: If they're asking about currency exchange, trading, or rates, be helpful and informative.
            If it's general conversation, be friendly but gently guide them back to FX-related topics.
            Always include relevant disclaimers for financial advice.
            Keep responses concise and engaging.
            Use emojis appropriately to make responses feel warm and human.
            
            Available services:
            - Live exchange rates (XAF, XOF, USD, EUR, AED, USDT, CNY)
            - Currency conversions
            - FX trading guidance
            - Contact via website: https://whatsapp-bot-96xm.onrender.com
            - Telegram bot: https://t.me/evafx_assistant_bot
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Add EVA Fx branding
            return f"{ai_response}\n\n💫 *Eva - Your FX Trading Assistant*"
            
        except Exception as e:
            logger.error(f"AI response error: {e}")
            return "🤖 I'm Eva, your FX assistant! I can help you with currency exchange rates, conversions, and trading information. What would you like to know?"

    async def _moderate_group_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Moderate messages in groups"""
        if not self.group_moderation_enabled:
            return False
            
        message_text = update.message.text.lower()
        user = update.effective_user
        
        # Check for spam keywords
        for keyword in self.spam_keywords:
            if keyword in message_text:
                # Delete the message if bot has admin rights
                try:
                    await update.message.delete()
                    # Send warning
                    warning_msg = await update.message.reply_text(
                        f"⚠️ {user.first_name}, please keep the discussion focused on FX trading topics."
                    )
                    # Auto-delete warning after 10 seconds
                    context.job_queue.run_once(
                        self._delete_message, 
                        10, 
                        data={'chat_id': update.message.chat_id, 'message_id': warning_msg.message_id}
                    )
                    logger.info(f"Moderated message from {user.id} in group {update.message.chat_id}")
                    return True
                except Exception as e:
                    logger.warning(f"Could not moderate message: {e}")
        
        return False

    async def _delete_message(self, context: ContextTypes.DEFAULT_TYPE):
        """Helper function to delete messages"""
        try:
            await context.bot.delete_message(
                chat_id=context.job.data['chat_id'],
                message_id=context.job.data['message_id']
            )
        except Exception as e:
            logger.warning(f"Could not delete message: {e}")

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
