import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from fx_trader import FXTrader
from financial_news import FinancialNewsAnalyzer
from openai import OpenAI
import asyncio
import json
import re
from datetime import datetime, time
import pytz
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
        self.financial_analyzer = FinancialNewsAnalyzer()  # Add financial news analyzer
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
        
        # Enhanced group content moderation settings
        self.group_moderation_enabled = True
        self.spam_keywords = [
            'spam', 'scam', 'buy now', 'click here', 'limited time',
            'get rich quick', 'guaranteed profit', 'investment opportunity',
            'crypto scam', 'phishing', 'fake trading', 'ponzi scheme',
            'urgent', 'act now', 'exclusive offer', 'make money fast',
            '🚨', 'warning', 'alert'  # Common scam indicators
        ]
        self.inappropriate_content = [
            'porn', 'xxx', 'adult content', 'nsfw', 'explicit',
            'hate speech', 'racist', 'discrimination'
        ]
        self.off_topic_keywords = [
            'politics', 'election', 'government', 'religion',
            'sports betting', 'casino', 'gambling', 'lottery'
        ]
        
        # Personal greeting database for users
        self.user_greetings = {}  # Store personalized greetings
        self.greeting_variations = [
            "👋 Hi {name}! Ready to explore FX rates?",
            "🌟 Hello {name}! How can I help you with trading today?",
            "💫 Hey there, {name}! Looking for currency rates?",
            "🚀 Welcome back, {name}! What FX info do you need?",
            "✨ Hi {name}! Let's talk currencies and trading!"
        ]
        
        # Daily scheduler settings
        self.scheduled_groups = set()  # Store group IDs for daily rates
        self.daily_rates_time = time(10, 0)  # 10:00 AM
        self.timezone = pytz.timezone('Africa/Lagos')  # WAT timezone
        
        # AI personality for more human responses with financial expertise
        self.ai_personality = """You are Eva, a friendly and professional FX trading assistant with access to real-time financial news and market data. You help people with currency exchange, rates, trading information, and market analysis. You are knowledgeable about:

- Current FX rates and currency trends
- Financial news and market-moving events  
- Gold, commodities, and their correlation with currencies
- Economic indicators and their impact on trading
- Risk management and trading strategies
- Market sentiment analysis

You speak in a warm, conversational tone while providing accurate, data-driven insights. Always include appropriate disclaimers about trading risks when discussing financial matters. When users ask about market conditions, you can reference current news and data to provide informed analysis."""
        
    async def setup_bot(self):
        """Initialize the bot application"""
        self.application = Application.builder().token(self.token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("rates", self.rates_command))
        self.application.add_handler(CommandHandler("convert", self.convert_command))
        
        # Financial news and market analysis commands
        self.application.add_handler(CommandHandler("news", self.news_command))
        self.application.add_handler(CommandHandler("market", self.market_analysis_command))
        self.application.add_handler(CommandHandler("gold", self.gold_analysis_command))
        self.application.add_handler(CommandHandler("insights", self.trading_insights_command))
        
        # Group-specific commands
        self.application.add_handler(CommandHandler("grouphelp", self.group_help_command))
        self.application.add_handler(CommandHandler("grouprates", self.group_rates_command))
        
        # Scheduler commands (admin only)
        self.application.add_handler(CommandHandler("enabledaily", self.enable_daily_rates))
        self.application.add_handler(CommandHandler("disabledaily", self.disable_daily_rates))
        
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Set up bot commands for the menu
        commands = [
            BotCommand("start", "Start the bot and see welcome message"),
            BotCommand("help", "Show help information"),
            BotCommand("rates", "Get current exchange rates"),
            BotCommand("convert", "Convert currencies (e.g., /convert 100 USD to EUR)"),
            BotCommand("news", "Get latest financial news"),
            BotCommand("market", "Comprehensive market analysis"),
            BotCommand("gold", "Gold and precious metals analysis"),
            BotCommand("insights", "AI-powered trading insights"),
            BotCommand("grouprates", "Get compact rates format for groups"),
            BotCommand("grouphelp", "Show group-specific help and commands"),
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info("Telegram bot setup completed")
        
    def get_personal_greeting(self, user, chat_type='private'):
        """Generate personalized greeting for users"""
        if not user:
            return "👋 Hello there! Welcome to EVA Fx Assistant!"
        
        user_id = user.id
        first_name = user.first_name or "friend"
        
        # Check if we've greeted this user before
        if user_id in self.user_greetings:
            # Return user for more casual greeting
            import random
            casual_greetings = [
                f"👋 Welcome back, {first_name}!",
                f"🌟 Hey {first_name}! Good to see you again!",
                f"💫 Hi there, {first_name}! Ready for some FX action?",
                f"🚀 {first_name}! What can I help you with today?",
                f"✨ Hello again, {first_name}!"
            ]
            return random.choice(casual_greetings)
        else:
            # First time user - warm welcome
            self.user_greetings[user_id] = {
                'first_name': first_name,
                'username': user.username,
                'first_seen': datetime.now().isoformat()
            }
            
            if chat_type == 'private':
                return f"👋 Hello {first_name}! I'm Eva, your personal FX assistant. Nice to meet you! I'm here to help you with currency exchange rates, conversions, and trading information."
            else:
                return f"👋 Hi {first_name}! Welcome to the group! I'm Eva, and I'll help with FX rates and trading info."

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced start command with personalization"""
        user = update.effective_user
        chat_type = update.message.chat.type if update.message and update.message.chat else 'private'
        
        # Get personalized greeting
        personal_greeting = self.get_personal_greeting(user, chat_type)
        
        # Get standard disclaimer
        disclaimer = self.fx_trader.get_greeting_and_disclaimer()
        
        # Create inline keyboard with quick actions
        if chat_type == 'private':
            keyboard = [
                [
                    InlineKeyboardButton("📊 Current Rates", callback_data="rates"),
                    InlineKeyboardButton("💱 Convert Currency", callback_data="convert")
                ],
                [
                    InlineKeyboardButton("❓ Help & Commands", callback_data="help"),
                    InlineKeyboardButton("💬 Chat with Eva", callback_data="ai_help")
                ],
                [
                    InlineKeyboardButton("🌐 Visit Website", url="https://whatsapp-bot-96xm.onrender.com"),
                    InlineKeyboardButton("📱 Join Channel", url="https://t.me/+dKTLjP_OHeA3MDE0")
                ]
            ]
        else:
            # Group-specific buttons
            keyboard = [
                [
                    InlineKeyboardButton("📊 Group Rates", callback_data="rates"),
                    InlineKeyboardButton("💱 Quick Convert", callback_data="convert")
                ],
                [
                    InlineKeyboardButton("⏰ Daily Rates", callback_data="daily_help"),
                    InlineKeyboardButton("❓ Group Help", callback_data="group_help")
                ]
            ]
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        full_message = f"{personal_greeting}\n\n{disclaimer}\n\n🚀 **Quick Actions:**"
        
        await update.message.reply_text(full_message, reply_markup=reply_markup, parse_mode='Markdown')
        
        if user:
            logger.info(f"Personalized start command sent to {chat_type} chat - user {user.id} ({user.first_name})")
        else:
            logger.info(f"Start command sent to {chat_type} chat")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced help command with financial features"""
        user = update.effective_user
        chat_type = update.message.chat.type if update.message and update.message.chat else 'private'
        
        if chat_type == 'private':
            help_text = f"""
🤖 **Hi {user.first_name if user else 'there'}! EVA Fx Assistant Help**

**📊 Market & Trading Commands:**
• `/rates` - Live exchange rates with conversion tools
• `/news` - Latest financial news & market updates  
• `/market` - Comprehensive market analysis
• `/gold` - Gold & precious metals analysis
• `/insights` - AI-powered trading insights
• `/convert` - Currency conversion calculator

**🚀 Quick Commands:**
• `/start` - Welcome & quick actions
• `/help` - This help message

**💬 Natural Language:**
Just type naturally! I understand:
• "What are USD rates today?"
• "100 USD to XAF" 
• "What's happening in the markets?"
• "Gold price analysis"
• "Current financial news"

**🎯 Key Features:**
📈 Real-time market data & FX rates
📰 Live financial news analysis  
🤖 AI-powered market insights
💱 Instant currency conversions
🥇 Gold & commodities tracking
📊 Market sentiment analysis

**🌐 Links & Contact:**
• Website: whatsapp-bot-96xm.onrender.com
• Channel: t.me/+dKTLjP_OHeA3MDE0

*I'm here 24/7 to help with your FX and trading needs!* ✨
            """.strip()
        else:
            help_text = f"""
🤖 **Group Help - EVA Fx Assistant**

**📊 Market Commands (Everyone):**
• `/rates` - Live FX rates (group format)
• `/news` - Latest financial headlines
• `/market` - Current market analysis  
• `/gold` - Gold market insights
• `/insights` - Trading analysis & tips
• `/convert` - Currency conversions

**👥 Group Management (Admin):**  
• `/enabledaily` - Daily 10 AM rate broadcasts
• `/disabledaily` - Stop daily broadcasts

**💬 Smart Features:**
• Type currency names for quick info
• Mention @{context.bot.username if context.bot else 'evafx_assistant_bot'} for AI help
• Interactive buttons for easy access
• Real-time financial news integration

**🛡️ Content Guidelines:**
✅ FX trading & market discussions
✅ Rate inquiries & analysis requests
✅ Professional trading conversations  
❌ Spam or inappropriate content
❌ Off-topic discussions

*Keep discussions FX-focused and professional!* 🚀
            """.strip()
            
        await update.message.reply_text(help_text, parse_mode='Markdown')
        logger.info(f"Enhanced help sent to {chat_type} chat - user {user.id if user else 'unknown'}")

    async def rates_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /rates command - works in both private and group chats"""
        try:
            user = update.effective_user
            chat_type = update.message.chat.type if update.message and update.message.chat else 'private'
            
            rates_info = self.fx_trader.get_daily_rates()
            
            # Personal greeting based on chat type
            if chat_type == 'private':
                greeting = f"Hi {user.first_name}! 👋 Here are today's rates:"
                
                # Create quick conversion buttons for private chat
                keyboard = [
                    [
                        InlineKeyboardButton("💱 100 USD", callback_data="convert_100_USD"),
                        InlineKeyboardButton("� 100 EUR", callback_data="convert_100_EUR")
                    ],
                    [
                        InlineKeyboardButton("💱 100 GBP", callback_data="convert_100_GBP"),
                        InlineKeyboardButton("💱 100 AED", callback_data="convert_100_AED")
                    ],
                    [
                        InlineKeyboardButton("� Refresh Rates", callback_data="rates"),
                        InlineKeyboardButton("💬 Ask Eva", callback_data="ai_help")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                full_message = f"{greeting}\n\n{rates_info}"
                await update.message.reply_text(full_message, reply_markup=reply_markup)
                
            else:  # Group chat
                # Compact format for groups with personal touch
                group_name = update.message.chat.title or "group"
                greeting = f"📊 Current rates for {group_name}:"
                
                # Create compact group-friendly message
                compact_rates = f"""
{greeting}

💱 **EVA Fx Rates** - {self.fx_trader.base_rates.get('last_updated', 'Now')}

🇺🇸 **USD**: {self.fx_trader.base_rates.get('XAF_USD', 'N/A')} XAF | {self.fx_trader.base_rates.get('XOF_USD', 'N/A')} XOF
💰 **USDT**: {self.fx_trader.base_rates.get('XAF_USDT', 'N/A')} XAF | {self.fx_trader.base_rates.get('XOF_USDT', 'N/A')} XOF  
🇦🇪 **AED**: {self.fx_trader.base_rates.get('XAF_AED', 'N/A')} XAF | {self.fx_trader.base_rates.get('XOF_AED', 'N/A')} XOF
🇨🇳 **CNY**: {self.fx_trader.base_rates.get('XAF_CNY', 'N/A')} XAF | {self.fx_trader.base_rates.get('XOF_CNY', 'N/A')} XOF
🇪🇺 **EUR**: {self.fx_trader.base_rates.get('XAF_EUR', 'N/A')} XAF | {self.fx_trader.base_rates.get('XOF_EUR', 'N/A')} XOF

💡 _Use /convert for calculations_ • _Mention @{context.bot.username} for help_
                """.strip()
                
                # Add inline buttons for groups
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Convert", callback_data="convert"),
                        InlineKeyboardButton("📊 Detailed View", callback_data="rates_detailed")
                    ],
                    [
                        InlineKeyboardButton("⏰ Enable Daily", callback_data="enable_daily"),
                        InlineKeyboardButton("💬 Ask Eva", callback_data="ai_help")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(compact_rates, reply_markup=reply_markup, parse_mode='Markdown')
            
            logger.info(f"Rates sent to {chat_type} chat - user {user.id} ({user.first_name})")
            
        except Exception as e:
            logger.error(f"Error getting rates: {e}")
            await update.message.reply_text("❌ Sorry, I couldn't get the current rates. Please try again later.")

    async def convert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /convert command - works in both private and group chats"""
        user = update.effective_user
        chat_type = update.message.chat.type if update.message and update.message.chat else 'private'
        
        if not context.args or len(context.args) < 4:
            # Personal help message based on chat type
            if chat_type == 'private':
                help_msg = f"""
💱 **Hi {user.first_name if user else 'there'}! Currency Conversion Help**

**Usage:** `/convert <amount> <from_currency> to <to_currency>`

**Examples:**
• `/convert 100 USD to XAF`
• `/convert 50 AED to XOF`
• `/convert 200 USDT to XAF`
• `/convert 75 EUR to XOF`

**Supported Currencies:** USD, EUR, GBP, AED, CNY, USDT, XAF, XOF

💡 **Tip:** You can also just type "100 USD to XAF" and I'll convert it!
                """.strip()
            else:
                help_msg = f"""
💱 **Currency Conversion in {update.message.chat.title or 'group'}**

**Usage:** `/convert <amount> <from> to <to>`
**Example:** `/convert 100 USD to XAF`

💡 **Quick tip:** Just type "100 USD to XAF" and I'll help!
                """.strip()
                
            await update.message.reply_text(help_msg, parse_mode='Markdown')
            return
            
        try:
            amount = float(context.args[0])
            from_currency = context.args[1].upper()
            to_currency = context.args[3].upper()
            
            # Use the existing get_trading_process_info method for conversions
            result = self.fx_trader.get_trading_process_info(amount, from_currency, to_currency)
            
            # Add personal touch to response
            if chat_type == 'private':
                personalized_result = f"Here you go, {user.first_name if user else 'friend'}! 💫\n\n{result}"
            else:
                personalized_result = f"💱 **Conversion for {user.first_name if user else 'user'}:**\n\n{result}"
            
            await update.message.reply_text(personalized_result, parse_mode='Markdown')
            logger.info(f"Conversion sent to {chat_type} chat - user {user.id if user else 'unknown'}: {amount} {from_currency} to {to_currency}")
            
        except (ValueError, IndexError) as e:
            logger.error(f"Conversion error: {e}")
            await update.message.reply_text("❌ Invalid format. Use: `/convert 100 USD to XAF`", parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Conversion calculation error: {e}")
            await update.message.reply_text("❌ Sorry, I couldn't perform the conversion. Please try again.")

    async def news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get latest financial news"""
        user = update.effective_user
        chat_type = update.message.chat.type if update.message and update.message.chat else 'private'
        
        try:
            # Show loading message
            loading_msg = await update.message.reply_text("📰 Getting latest financial news... ⏳")
            
            # Get fresh financial news
            news_items = self.financial_analyzer.get_latest_financial_news(limit=6)
            
            if not news_items:
                await loading_msg.edit_text("❌ Unable to fetch financial news at this time. Please try again later.")
                return
                
            # Format news for display
            news_message = f"📰 **Latest Financial News**\n"
            news_message += f"🕒 Updated: {datetime.now().strftime('%H:%M %Z')}\n\n"
            
            for i, news in enumerate(news_items[:5], 1):
                title = news['title'][:80] + "..." if len(news['title']) > 80 else news['title']
                summary = news.get('summary', '')
                source = news.get('source', 'Unknown')
                published = news.get('published', '')
                
                news_message += f"**{i}. {title}**\n"
                if summary:
                    # Clean and limit summary
                    clean_summary = summary.replace('<p>', '').replace('</p>', '').replace('<br>', ' ')
                    clean_summary = clean_summary[:150] + "..." if len(clean_summary) > 150 else clean_summary
                    news_message += f"📝 {clean_summary}\n"
                if published:
                    # Format published date
                    try:
                        from datetime import datetime
                        import dateutil.parser
                        pub_date = dateutil.parser.parse(published)
                        formatted_date = pub_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
                        news_message += f"📅 {formatted_date}\n"
                    except:
                        news_message += f"📅 {published}\n"
                news_message += f"📊 Source: {source}\n\n"
                
            # Add market impact analysis button for detailed view
            keyboard = [
                [
                    InlineKeyboardButton("📊 Market Impact", callback_data="news_impact"),
                    InlineKeyboardButton("🔄 Refresh News", callback_data="news_refresh")
                ],
                [
                    InlineKeyboardButton("💡 Trading Insights", callback_data="trading_insights"),
                    InlineKeyboardButton("📈 Market Analysis", callback_data="market_analysis")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Personalize message
            if chat_type == 'private':
                greeting = f"Hi {user.first_name if user else 'there'}! 👋\n\n"
                news_message = greeting + news_message
                
            await loading_msg.edit_text(news_message, reply_markup=reply_markup, parse_mode='Markdown')
            
            logger.info(f"Financial news sent to {chat_type} chat - user {user.id if user else 'unknown'}")
            
        except Exception as e:
            logger.error(f"Error in news_command: {e}")
            try:
                await loading_msg.edit_text("❌ Sorry, couldn't fetch financial news right now. Please try again later.")
            except:
                await update.message.reply_text("❌ Sorry, couldn't fetch financial news right now. Please try again later.")

    async def market_analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get comprehensive market analysis"""
        user = update.effective_user
        chat_type = update.message.chat.type if update.message and update.message.chat else 'private'
        
        try:
            # Show loading message
            loading_msg = await update.message.reply_text("📊 Analyzing current market conditions... ⏳")
            
            # Get market analysis
            currency_analysis = self.financial_analyzer.get_currency_analysis()
            commodities_analysis = self.financial_analyzer.get_commodities_analysis()
            
            if not currency_analysis and not commodities_analysis:
                await loading_msg.edit_text("❌ Unable to fetch market data at this time. Please try again later.")
                return
                
            # Format analysis message
            analysis_message = f"📊 **Market Analysis Overview**\n"
            analysis_message += f"🕒 Updated: {datetime.now().strftime('%H:%M %Z')}\n\n"
            
            # Dollar Index
            if currency_analysis.get('dollar_index'):
                dxy = currency_analysis['dollar_index']
                change_emoji = "🟢" if dxy.get('change_percent', 0) > 0 else "🔴" if dxy.get('change_percent', 0) < 0 else "⚪"
                analysis_message += f"💵 **US Dollar Index (DXY)**\n"
                analysis_message += f"{change_emoji} {dxy.get('price', 'N/A')} ({dxy.get('change_percent', 0):+.2f}%)\n\n"
            
            # Major FX Pairs
            fx_pairs = currency_analysis.get('fx_pairs', {})
            if fx_pairs:
                analysis_message += f"💱 **Major FX Pairs:**\n"
                for pair, data in list(fx_pairs.items())[:4]:
                    change_pct = data.get('change_percent', 0)
                    change_emoji = "🟢" if change_pct > 0 else "🔴" if change_pct < 0 else "⚪"
                    analysis_message += f"{change_emoji} **{pair}**: {data.get('price', 'N/A')} ({change_pct:+.2f}%)\n"
                analysis_message += "\n"
            
            # Commodities
            commodities = commodities_analysis.get('commodities', {})
            if commodities:
                analysis_message += f"🥇 **Key Commodities:**\n"
                for commodity, data in commodities.items():
                    change_pct = data.get('change_percent', 0)
                    change_emoji = "🟢" if change_pct > 0 else "🔴" if change_pct < 0 else "⚪"
                    price = data.get('price', 'N/A')
                    if commodity == 'Gold':
                        analysis_message += f"{change_emoji} **Gold**: ${price} ({change_pct:+.2f}%)\n"
                    elif commodity == 'Oil_WTI':
                        analysis_message += f"{change_emoji} **WTI Oil**: ${price} ({change_pct:+.2f}%)\n"
                    else:
                        analysis_message += f"{change_emoji} **{commodity}**: ${price} ({change_pct:+.2f}%)\n"
            
            # Analysis summary
            summary = currency_analysis.get('analysis_summary', 'Mixed market signals')
            analysis_message += f"\n📈 **Summary**: {summary}\n"
            
            # Add disclaimer
            analysis_message += f"\n⚠️ *Live market data - Not financial advice*"
            
            # Create action buttons
            keyboard = [
                [
                    InlineKeyboardButton("💡 Trading Insights", callback_data="trading_insights"),
                    InlineKeyboardButton("📰 Latest News", callback_data="financial_news")
                ],
                [
                    InlineKeyboardButton("🥇 Gold Analysis", callback_data="gold_analysis"),
                    InlineKeyboardButton("🔄 Refresh Data", callback_data="market_refresh")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Personalize message
            if chat_type == 'private' and user:
                greeting = f"Hi {user.first_name}! Here's your market analysis:\n\n"
                analysis_message = greeting + analysis_message
                
            await loading_msg.edit_text(analysis_message, reply_markup=reply_markup, parse_mode='Markdown')
            
            logger.info(f"Market analysis sent to {chat_type} chat - user {user.id if user else 'unknown'}")
            
        except Exception as e:
            logger.error(f"Error in market_analysis_command: {e}")
            try:
                await loading_msg.edit_text("❌ Sorry, couldn't fetch market analysis right now. Please try again later.")
            except:
                await update.message.reply_text("❌ Sorry, couldn't fetch market analysis right now. Please try again later.")

    async def gold_analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get specific gold market analysis"""
        user = update.effective_user
        
        try:
            # Show loading message
            loading_msg = await update.message.reply_text("🥇 Analyzing gold market... ⏳")
            
            # Get gold-specific data
            gold_data = self.financial_analyzer.get_market_data(['Gold', 'Silver'])
            currency_analysis = self.financial_analyzer.get_currency_analysis()
            news_items = self.financial_analyzer.get_latest_financial_news(limit=10)
            news_impact = self.financial_analyzer.analyze_news_impact(news_items)
            
            # Format gold analysis
            gold_message = f"🥇 **Gold Market Analysis**\n"
            gold_message += f"🕒 Updated: {datetime.now().strftime('%H:%M %Z')}\n\n"
            
            if gold_data.get('Gold'):
                gold = gold_data['Gold']
                change_pct = gold.get('change_percent', 0)
                change_emoji = "🟢" if change_pct > 0 else "🔴" if change_pct < 0 else "⚪"
                gold_message += f"💰 **Current Gold Price**\n"
                gold_message += f"{change_emoji} ${gold.get('price', 'N/A')}/oz ({change_pct:+.2f}%)\n\n"
                
            # Silver comparison
            if gold_data.get('Silver'):
                silver = gold_data['Silver']
                silver_change = silver.get('change_percent', 0)
                silver_emoji = "🟢" if silver_change > 0 else "🔴" if silver_change < 0 else "⚪"
                gold_message += f"🥈 **Silver**: ${silver.get('price', 'N/A')} ({silver_change:+.2f}%)\n"
                
            # USD strength impact
            if currency_analysis.get('dollar_index'):
                dxy = currency_analysis['dollar_index']
                dxy_change = dxy.get('change_percent', 0)
                correlation = "inverse correlation" if dxy_change != 0 else "neutral"
                gold_message += f"\n💵 **USD Impact**: DXY {dxy.get('price', 'N/A')} ({dxy_change:+.2f}%)\n"
                gold_message += f"📊 Gold typically shows {correlation} with USD strength\n"
                
            # News impact
            gold_relevant_news = news_impact.get('gold_relevant', [])
            if gold_relevant_news:
                gold_message += f"\n📰 **News Impact**: {len(gold_relevant_news)} gold-related headlines detected\n"
                gold_message += f"Recent developments may affect precious metals pricing\n"
                
            # Market sentiment
            sentiment = news_impact.get('overall_sentiment', 'neutral')
            sentiment_emoji = "😊" if sentiment == 'positive' else "😟" if sentiment == 'negative' else "😐"
            gold_message += f"\n{sentiment_emoji} **Market Sentiment**: {sentiment.title()}\n"
            
            # Trading considerations
            gold_message += f"\n💡 **Trading Considerations**:\n"
            if abs(gold_data.get('Gold', {}).get('change_percent', 0)) > 1.0:
                gold_message += f"• Significant price movement detected - monitor volatility\n"
            gold_message += f"• Consider USD strength and inflation data\n"
            gold_message += f"• Watch for geopolitical developments\n"
            
            # Disclaimer
            gold_message += f"\n⚠️ *Analysis based on current data - Not investment advice*"
            
            # Create buttons
            keyboard = [
                [
                    InlineKeyboardButton("📊 Full Market", callback_data="market_analysis"),
                    InlineKeyboardButton("💱 FX Impact", callback_data="fx_gold_correlation")
                ],
                [
                    InlineKeyboardButton("📰 Gold News", callback_data="gold_news"),
                    InlineKeyboardButton("🔄 Refresh", callback_data="gold_refresh")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(gold_message, reply_markup=reply_markup, parse_mode='Markdown')
            
            logger.info(f"Gold analysis sent to user {user.id if user else 'unknown'}")
            
        except Exception as e:
            logger.error(f"Error in gold_analysis_command: {e}")
            try:
                await loading_msg.edit_text("❌ Sorry, couldn't fetch gold analysis right now. Please try again later.")
            except:
                await update.message.reply_text("❌ Sorry, couldn't fetch gold analysis right now. Please try again later.")

    async def trading_insights_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get comprehensive trading insights with market context"""
        user = update.effective_user
        chat_type = update.message.chat.type if update.message and update.message.chat else 'private'
        
        try:
            # Show loading message
            loading_msg = await update.message.reply_text("💡 Generating trading insights... ⏳")
            
            # Get user's query from command arguments
            user_query = " ".join(context.args) if context.args else ""
            
            # Generate comprehensive insights
            insights = self.financial_analyzer.get_trading_insights(user_query)
            
            if not insights or len(insights) < 50:
                await loading_msg.edit_text("❌ Unable to generate trading insights at this time. Please try again later.")
                return
                
            # Personalize the insights
            if chat_type == 'private' and user:
                personal_intro = f"Hi {user.first_name}! Here are your personalized trading insights:\n\n"
                insights = personal_intro + insights
            elif chat_type in ['group', 'supergroup']:
                group_intro = f"📊 **Trading Insights for the Group**\n\n"
                insights = group_intro + insights
                
            # Create action buttons
            keyboard = [
                [
                    InlineKeyboardButton("📰 Latest News", callback_data="financial_news"),
                    InlineKeyboardButton("📊 Market Data", callback_data="market_analysis")
                ],
                [
                    InlineKeyboardButton("🥇 Gold Analysis", callback_data="gold_analysis"),
                    InlineKeyboardButton("💱 FX Rates", callback_data="rates")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(insights, reply_markup=reply_markup, parse_mode='Markdown')
            
            logger.info(f"Trading insights sent to {chat_type} chat - user {user.id if user else 'unknown'} - query: '{user_query}'")
            
        except Exception as e:
            logger.error(f"Error in trading_insights_command: {e}")
            try:
                await loading_msg.edit_text("❌ Sorry, couldn't generate trading insights right now. Please try again later.")
            except:
                await update.message.reply_text("❌ Sorry, couldn't generate trading insights right now. Please try again later.")

    async def group_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /grouphelp command - show group-specific help"""
        if update.message.chat.type not in ['group', 'supergroup']:
            await update.message.reply_text("This command is only available in groups. Use /help for private chat commands.")
            return
            
        help_text = """
🏢 *EVA Fx Bot - Group Commands*

*Available Commands:*
/grouprates - Get rates in a compact group format
/grouphelp - Show this group help
/convert [amount] [from] to [to] - Convert currencies

*Group Features:*
• 🤖 Mention the bot for AI assistance
• 💱 Type currency names (USD, XAF, etc.) for quick rates
• 🔄 Interactive rate buttons for easy access
• 📊 Group-friendly compact rate display

*Usage Examples:*
• `/grouprates` - Show all current rates
• `/convert 100 USD to XAF` - Convert currencies  
• "What's the USD rate?" - AI will help
• Just type "USD" or "rates" - Bot will respond

*Tip:* Add bot as admin for best performance in groups.
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        logger.info(f"Group help sent to group {update.message.chat_id}")

    async def group_rates_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /grouprates command - show rates in group-friendly format"""
        try:
            # Get current rates
            rates_data = self.fx_trader.base_rates
            
            if not rates_data or not rates_data.get('last_updated'):
                # Fallback to getting fresh rates
                self.fx_trader.get_daily_rates()
                rates_data = self.fx_trader.base_rates
            
            # Create compact group-friendly message
            compact_rates = f"""
💱 **EVA Fx Rates** - {rates_data.get('last_updated', 'Now')}

🇺🇸 **USD**: {rates_data.get('XAF_USD', 'N/A')} XAF | {rates_data.get('XOF_USD', 'N/A')} XOF
💰 **USDT**: {rates_data.get('XAF_USDT', 'N/A')} XAF | {rates_data.get('XOF_USDT', 'N/A')} XOF  
🇦🇪 **AED**: {rates_data.get('XAF_AED', 'N/A')} XAF | {rates_data.get('XOF_AED', 'N/A')} XOF
🇨🇳 **CNY**: {rates_data.get('XAF_CNY', 'N/A')} XAF | {rates_data.get('XOF_CNY', 'N/A')} XOF
🇪🇺 **EUR**: {rates_data.get('XAF_EUR', 'N/A')} XAF | {rates_data.get('XOF_EUR', 'N/A')} XOF

_Use /convert to calculate amounts_
            """.strip()
            
            # Add inline buttons for groups
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Convert", callback_data="convert"),
                    InlineKeyboardButton("📊 Full Details", callback_data="rates")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(compact_rates, reply_markup=reply_markup, parse_mode='Markdown')
            logger.info(f"Group rates sent to {update.message.chat.type} {update.message.chat_id}")
            
        except Exception as e:
            logger.error(f"Error in group_rates_command: {e}")
            await update.message.reply_text("❌ Sorry, couldn't fetch rates right now. Please try again later.")

    async def enable_daily_rates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enable daily rate broadcasts for this group (admin only)"""
        if not update or not update.message or not update.message.chat:
            return
            
        if update.message.chat.type not in ['group', 'supergroup']:
            await update.message.reply_text("This command is only available in groups.")
            return
            
        # Check if user is admin
        try:
            if not update.effective_user or not context.bot:
                await update.message.reply_text("❌ Could not verify admin status.")
                return
                
            chat_member = await context.bot.get_chat_member(update.message.chat_id, update.effective_user.id)
            if chat_member.status not in ['creator', 'administrator']:
                await update.message.reply_text("❌ Only group admins can enable daily rates.")
                return
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            await update.message.reply_text("❌ Could not verify admin status.")
            return
            
        # Add group to scheduled groups
        group_id = update.message.chat_id
        self.scheduled_groups.add(group_id)
        
        # Schedule daily job if not already scheduled
        await self._schedule_daily_rates(context)
        
        await update.message.reply_text(
            "✅ **Daily FX Rates Enabled!**\n\n"
            f"📅 Daily rates will be sent at {self.daily_rates_time.strftime('%I:%M %p')} WAT\n"
            f"🌍 Timezone: Africa/Lagos (WAT)\n"
            f"🔄 Use `/disabledaily` to stop\n\n"
            "_Next broadcast will happen at the scheduled time._",
            parse_mode='Markdown'
        )
        logger.info(f"Daily rates enabled for group {group_id}")

    async def disable_daily_rates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Disable daily rate broadcasts for this group (admin only)"""
        if not update or not update.message or not update.message.chat:
            return
            
        if update.message.chat.type not in ['group', 'supergroup']:
            await update.message.reply_text("This command is only available in groups.")
            return
            
        # Check if user is admin
        try:
            if not update.effective_user or not context.bot:
                await update.message.reply_text("❌ Could not verify admin status.")
                return
                
            chat_member = await context.bot.get_chat_member(update.message.chat_id, update.effective_user.id)
            if chat_member.status not in ['creator', 'administrator']:
                await update.message.reply_text("❌ Only group admins can disable daily rates.")
                return
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            await update.message.reply_text("❌ Could not verify admin status.")
            return
            
        # Remove group from scheduled groups
        group_id = update.message.chat_id
        self.scheduled_groups.discard(group_id)
        
        await update.message.reply_text(
            "✅ **Daily FX Rates Disabled**\n\n"
            "📅 No more automatic daily rate broadcasts\n"
            "🔄 Use `/enabledaily` to re-enable\n"
            "💡 You can still use `/grouprates` anytime!",
            parse_mode='Markdown'
        )
        logger.info(f"Daily rates disabled for group {group_id}")

    async def _schedule_daily_rates(self, context: ContextTypes.DEFAULT_TYPE):
        """Schedule daily rate broadcasts"""
        try:
            if not context or not context.job_queue:
                logger.warning("Job queue not available for scheduling")
                return
                
            # Remove existing job if any
            current_jobs = context.job_queue.get_jobs_by_name('daily_rates')
            for job in current_jobs:
                job.schedule_removal()
            
            # Schedule new daily job
            context.job_queue.run_daily(
                self._send_daily_rates,
                self.daily_rates_time,
                name='daily_rates'
            )
            logger.info(f"Daily rates job scheduled for {self.daily_rates_time}")
            
        except Exception as e:
            logger.error(f"Error scheduling daily rates: {e}")

    async def _send_daily_rates(self, context: ContextTypes.DEFAULT_TYPE):
        """Send daily rates to all scheduled groups"""
        if not self.scheduled_groups or not context or not context.bot:
            return
            
        try:
            # Get fresh rates
            rates_data = self.fx_trader.base_rates
            if not rates_data or not rates_data.get('last_updated'):
                # Force update rates
                self.fx_trader.get_daily_rates()
                rates_data = self.fx_trader.base_rates
            
            # Create daily broadcast message
            now = datetime.now(self.timezone)
            broadcast_message = f"""
🌅 **Good Morning! Daily FX Rates**
📅 {now.strftime('%A, %B %d, %Y')}
⏰ {now.strftime('%I:%M %p WAT')}

💱 **Today's EVA Fx Rates:**

🇺🇸 **USD**: {rates_data.get('XAF_USD', 'N/A')} XAF | {rates_data.get('XOF_USD', 'N/A')} XOF
💰 **USDT**: {rates_data.get('XAF_USDT', 'N/A')} XAF | {rates_data.get('XOF_USDT', 'N/A')} XOF
🇦🇪 **AED**: {rates_data.get('XAF_AED', 'N/A')} XAF | {rates_data.get('XOF_AED', 'N/A')} XOF
🇨🇳 **CNY**: {rates_data.get('XAF_CNY', 'N/A')} XAF | {rates_data.get('XOF_CNY', 'N/A')} XOF
🇪🇺 **EUR**: {rates_data.get('XAF_EUR', 'N/A')} XAF | {rates_data.get('XOF_EUR', 'N/A')} XOF

💡 _Use /convert for calculations | /disabledaily to stop_
🌐 _Visit: whatsapp-bot-96xm.onrender.com_
            """.strip()
            
            # Send to all scheduled groups
            for group_id in list(self.scheduled_groups):
                try:
                    await context.bot.send_message(
                        chat_id=group_id,
                        text=broadcast_message,
                        parse_mode='Markdown'
                    )
                    logger.info(f"Daily rates sent to group {group_id}")
                except Exception as e:
                    logger.error(f"Failed to send daily rates to group {group_id}: {e}")
                    # Remove failed groups
                    self.scheduled_groups.discard(group_id)
                    
        except Exception as e:
            logger.error(f"Error in daily rates broadcast: {e}")

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
        chat_type = update.message.chat.type if update.message.chat else 'private'
        
        # Group message handling
        if chat_type in ['group', 'supergroup']:
            # In groups, only respond if:
            # 1. Bot is mentioned
            # 2. Message contains currency keywords
            # 3. Message is a direct question about rates/trading
            
            bot_mention = f"@{context.bot.username}" if context.bot.username else ""
            is_mentioned = bot_mention in message_text if bot_mention else False
            
            # Check for currency/trading keywords
            currency_keywords = ['usd', 'eur', 'xaf', 'xof', 'aed', 'usdt', 'cny', 'rate', 'rates', 
                               'exchange', 'convert', 'currency', 'trading', 'fx', 'price', 'eva']
            has_currency_keyword = any(keyword in message_text.lower() for keyword in currency_keywords)
            
            # Only respond in groups if mentioned or contains relevant keywords
            if not (is_mentioned or has_currency_keyword):
                return
                
            # Remove mention from message for processing
            if is_mentioned:
                message_text = message_text.replace(bot_mention, "").strip()
        
        # Group moderation (if enabled)
        if chat_type in ['group', 'supergroup']:
            if await self._moderate_group_message(update, context):
                return  # Message was moderated
        
        logger.info(f"Message from {user.id if user.id else 'Unknown'} ({username}) in {chat_type}: {message_text}")
        
        try:
            # Check for common patterns first
            if any(word in message_text.lower() for word in ['rate', 'rates', 'exchange']):
                if chat_type in ['group', 'supergroup']:
                    # Use compact format for groups
                    await self.group_rates_command(update, context)
                    return
                else:
                    response = self.fx_trader.get_daily_rates()
                
            elif 'convert' in message_text.lower() or ' to ' in message_text.lower():
                response = self._parse_conversion_message(message_text)
                
            elif any(currency in message_text.upper() for currency in ['USD', 'EUR', 'GBP', 'AED', 'USDT', 'XAF', 'XOF', 'CNY']):
                response = self._handle_currency_mention(message_text)
                
            else:
                # Use AI for general conversation
                response = await self._get_ai_response(message_text, user)
            
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            error_msg = "🤖 Sorry, I had a little hiccup there! Could you try rephrasing your question? I'm here to help with FX trading and currency exchange."
            if chat_type in ['group', 'supergroup']:
                error_msg = "🤖 Oops! Try /grouphelp for available commands."
            await update.message.reply_text(error_msg)

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
        """Enhanced content moderation for groups"""
        if not self.group_moderation_enabled or not update.message or not update.message.text:
            return False
            
        message_text = update.message.text.lower()
        user = update.effective_user
        
        # Check for spam, inappropriate content, and off-topic messages
        violation_type = None
        
        # Check for spam keywords
        for keyword in self.spam_keywords:
            if keyword in message_text:
                violation_type = "spam"
                break
                
        # Check for inappropriate content
        if not violation_type:
            for keyword in self.inappropriate_content:
                if keyword in message_text:
                    violation_type = "inappropriate"
                    break
                    
        # Check for off-topic content (less severe)
        if not violation_type:
            for keyword in self.off_topic_keywords:
                if keyword in message_text:
                    violation_type = "off_topic"
                    break
        
        # Handle violations
        if violation_type:
            try:
                # Delete the message if bot has admin rights
                await update.message.delete()
                
                # Send appropriate warning based on violation type
                if violation_type == "spam":
                    warning_msg = await update.message.reply_text(
                        f"⚠️ **{user.first_name if user else 'User'}**, spam content is not allowed here.\n"
                        f"This group is for FX trading discussions only. 🚫",
                        parse_mode='Markdown'
                    )
                elif violation_type == "inappropriate":
                    warning_msg = await update.message.reply_text(
                        f"⚠️ **{user.first_name if user else 'User'}**, inappropriate content detected.\n"
                        f"Please keep discussions professional and FX-related. 🛡️",
                        parse_mode='Markdown'
                    )
                else:  # off_topic
                    warning_msg = await update.message.reply_text(
                        f"💡 **{user.first_name if user else 'User'}**, let's keep the focus on FX trading!\n"
                        f"Ask me about rates, conversions, or trading tips. 📊",
                        parse_mode='Markdown'
                    )
                
                # Auto-delete warning after 15 seconds (longer for better readability)
                if context.job_queue:
                    context.job_queue.run_once(
                        self._delete_message, 
                        15, 
                        data={'chat_id': update.message.chat_id, 'message_id': warning_msg.message_id}
                    )
                
                logger.info(f"Moderated {violation_type} message from {user.id if user else 'unknown'} in group {update.message.chat_id}")
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
