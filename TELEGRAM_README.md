# 🤖 EVA Fx Telegram Bot - Quick Reference

## 🚀 Quick Start (5 minutes)

### 1. Get Bot Token
- Open Telegram → Search `@BotFather`
- Send `/newbot` 
- Name: `EVA Fx Assistant`
- Username: `evafx_assistant_bot`
- **Copy the token!**

### 2. Setup (choose one)

**Option A - Interactive Setup:**
```bash
./quick_telegram_setup.sh
```

**Option B - Manual Setup:**
```bash
echo "TELEGRAM_BOT_TOKEN=your_bot_token_here" >> .env
.venv/bin/python telegram_setup.py --test
```

### 3. Run Your Bot

**Local Testing:**
```bash
.venv/bin/python telegram_setup.py --local
```

**Production (Render):**
```bash
.venv/bin/python telegram_setup.py --webhook https://whatsapp-bot-96xm.onrender.com/telegram-webhook
```

## ⚡ Features

- **Smart Commands**: `/start`, `/rates`, `/convert 100 USD to EUR`
- **Natural Language**: "100 USD", "What are today's rates?"
- **Quick Actions**: Inline buttons for common tasks
- **Same AI**: Uses your existing OpenAI integration
- **Same Data**: Shares FX rates with WhatsApp bot

## 🔧 Files Added

- `telegram_bot.py` - Main bot logic
- `telegram_setup.py` - Setup and management script  
- `quick_telegram_setup.sh` - One-click setup
- `TELEGRAM_BOT_SETUP.md` - Detailed documentation
- Flask route: `/telegram-webhook` - Webhook handler

## 🎯 Your Bot Link

After setup, your bot will be available at:
`https://t.me/evafx_assistant_bot` (or your chosen username)

## 🔍 Troubleshooting

```bash
# Check setup
.venv/bin/python telegram_setup.py --check

# Test connection  
.venv/bin/python telegram_setup.py --test

# Delete webhook (for local testing)
.venv/bin/python telegram_setup.py --delete-webhook
```

## 📱 User Experience

Your users can now:
- Chat with EVA AI on Telegram
- Get live FX rates instantly
- Convert currencies with simple commands
- Access your website and Telegram channel
- Same professional experience as WhatsApp

---

**Need detailed help?** See `TELEGRAM_BOT_SETUP.md`
