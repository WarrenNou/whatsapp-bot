# 🤖 EVA Fx Telegram Bot Setup Guide

This guide will help you create and deploy your EVA Fx Telegram bot alongside your existing WhatsApp bot.

## 📋 Prerequisites

1. **Telegram Account**: You need a Telegram account
2. **Bot Token**: Get it from @BotFather on Telegram
3. **Python Environment**: Your existing Flask app environment

## 🚀 Quick Start

### Step 1: Create Your Bot

1. Open Telegram and search for `@BotFather`
2. Start a conversation and send `/newbot`
3. Choose a name: **EVA Fx Assistant**
4. Choose a username ending in "bot": **evafx_assistant_bot**
5. **Save the token** BotFather gives you!

### Step 2: Configure Environment

Add to your `.env` file:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_WEBHOOK_URL=https://whatsapp-bot-96xm.onrender.com/telegram-webhook
```

### Step 3: Install Dependencies

The required package is already added to `requirements.txt`:
```bash
.venv/bin/pip install 'python-telegram-bot[all]'
```

### Step 4: Test Your Bot

```bash
# Check if everything is configured correctly
.venv/bin/python telegram_setup.py --check

# Test bot connection
.venv/bin/python telegram_setup.py --test
```

## 🌐 Deployment Options

### For Local Development

```bash
# Run bot in polling mode (no webhook needed)
.venv/bin/python telegram_setup.py --local
```

### For Production (Render)

```bash
# Set webhook for production
.venv/bin/python telegram_setup.py --webhook https://whatsapp-bot-96xm.onrender.com/telegram-webhook
```

## ✨ Bot Features

Your Telegram bot includes:

### Commands
- `/start` - Welcome message with quick action buttons
- `/help` - Show help information  
- `/rates` - Get current exchange rates
- `/convert <amount> <from> to <to>` - Convert currencies

### Interactive Features
- **Inline Keyboards**: Quick action buttons for rates and conversions
- **Natural Language**: Understands "100 USD to EUR" without commands
- **Smart Parsing**: Recognizes currency mentions and amounts
- **AI Integration**: Uses the same OpenAI integration as WhatsApp bot

### Quick Actions
- 📊 Current exchange rates
- 💱 Currency conversion
- 🌐 Visit your website
- 📱 Join Telegram channel

## 🔧 Integration Details

### Flask Integration
- New endpoint: `/telegram-webhook` 
- Handles webhook updates from Telegram
- Shares the same FX trading logic as WhatsApp bot
- Same rate limiting and Redis integration

### Shared Components
- **FX Trader**: Same exchange rate logic
- **OpenAI API**: Same AI responses
- **Redis**: Same session management
- **Logging**: Integrated logging system

## 🛠️ Troubleshooting

### Common Issues

**Bot not responding:**
```bash
# Check bot connection
.venv/bin/python telegram_setup.py --test
```

**Webhook not working:**
```bash
# Delete webhook and use local mode for testing
.venv/bin/python telegram_setup.py --delete-webhook
.venv/bin/python telegram_setup.py --local
```

**Environment issues:**
```bash
# Check configuration
.venv/bin/python telegram_setup.py --check
```

### Production Deployment

1. **Add environment variables to Render:**
   - `TELEGRAM_BOT_TOKEN` - Your bot token
   - `TELEGRAM_WEBHOOK_URL` - Your webhook URL

2. **Set webhook after deployment:**
   ```bash
   curl -X POST https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook \
   -d "url=https://whatsapp-bot-96xm.onrender.com/telegram-webhook"
   ```

3. **Test the webhook:**
   ```bash
   curl -X GET https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
   ```

## 📱 User Experience

### Example Interactions

**Getting Rates:**
```
User: /rates
Bot: 📊 Current Exchange Rates (Live)
     💰 1 USD = 0.92 EUR
     💰 1 USD = 0.79 GBP
     [Quick conversion buttons]
```

**Currency Conversion:**
```
User: 100 USD to EUR
Bot: 💱 Currency Conversion
     100.00 USD = 92.45 EUR
     Rate: 1 USD = 0.9245 EUR
     ✅ Live rates from reliable sources
```

**Natural Language:**
```
User: What are today's rates?
Bot: [Shows current exchange rates with quick action buttons]
```

## 🔐 Security Features

- **Rate Limiting**: Same limits as WhatsApp bot
- **Input Validation**: Sanitizes all user inputs  
- **Error Handling**: Graceful error responses
- **Logging**: All interactions logged for monitoring

## 📊 Monitoring

All Telegram bot activity is logged to:
- Console output
- `logs/whatsapp_bot.log` file
- Same logging system as existing Flask app

## 🎯 Next Steps

1. **Create your bot** with @BotFather
2. **Add the token** to your environment variables
3. **Test locally** first with polling mode
4. **Deploy to production** with webhook
5. **Share your bot** with users!

Your bot will be available at: `t.me/your_bot_username`

## 💡 Tips

- Test locally before deploying to production
- Use webhook mode for production (better performance)
- Monitor logs for any issues
- Users can find your bot by searching for your bot username
- Add your bot link to your website and marketing materials

---

**Need help?** Check the troubleshooting section or review the setup scripts provided.
