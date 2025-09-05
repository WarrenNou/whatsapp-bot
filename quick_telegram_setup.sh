#!/bin/bash

# Quick setup script for EVA Fx Telegram Bot
# Run this after getting your bot token from @BotFather

echo "🤖 EVA Fx Telegram Bot Quick Setup"
echo "=================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    touch .env
fi

echo "Please enter your Telegram bot token (from @BotFather):"
read -p "Bot Token: " bot_token

if [ ! -z "$bot_token" ]; then
    # Add or update the token in .env file
    if grep -q "TELEGRAM_BOT_TOKEN=" .env; then
        # Update existing line
        sed -i '' "s/TELEGRAM_BOT_TOKEN=.*/TELEGRAM_BOT_TOKEN=$bot_token/" .env
        echo "✅ Updated TELEGRAM_BOT_TOKEN in .env file"
    else
        # Add new line
        echo "TELEGRAM_BOT_TOKEN=$bot_token" >> .env
        echo "✅ Added TELEGRAM_BOT_TOKEN to .env file"
    fi
    
    # Add webhook URL if not exists
    if ! grep -q "TELEGRAM_WEBHOOK_URL=" .env; then
        echo "TELEGRAM_WEBHOOK_URL=https://whatsapp-bot-96xm.onrender.com/telegram-webhook" >> .env
        echo "✅ Added TELEGRAM_WEBHOOK_URL to .env file"
    fi
    
    echo ""
    echo "🎉 Setup complete! Now you can:"
    echo "1. Test your bot: .venv/bin/python telegram_setup.py --test"
    echo "2. Run locally: .venv/bin/python telegram_setup.py --local"
    echo "3. Deploy to production: .venv/bin/python telegram_setup.py --webhook https://whatsapp-bot-96xm.onrender.com/telegram-webhook"
    echo ""
    echo "Your bot will be available at: https://t.me/$(echo $bot_token | cut -d: -f1)_bot"
    
else
    echo "❌ No token provided. Please run this script again with your bot token."
    echo ""
    echo "To get a bot token:"
    echo "1. Open Telegram"
    echo "2. Search for @BotFather"  
    echo "3. Send /newbot"
    echo "4. Follow the instructions"
    echo "5. Copy the token and run this script again"
fi
