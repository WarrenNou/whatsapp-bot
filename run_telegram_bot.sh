#!/bin/bash

# Script to run the Telegram bot with proper environment setup

# Change to the project directory
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🤖 Starting EVA Fx Telegram Bot...${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating one...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}Virtual environment created.${NC}"
fi

# Check if requirements are installed
echo -e "${YELLOW}Checking and installing requirements...${NC}"
./venv/bin/pip install -q -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found! Please create it with your bot token.${NC}"
    echo -e "${YELLOW}Example .env content:${NC}"
    echo "TELEGRAM_BOT_TOKEN=your_bot_token_here"
    echo "OPENAI_API_KEY=your_openai_key_here"
    exit 1
fi

# Check if bot token is set
if ! grep -q "TELEGRAM_BOT_TOKEN=" .env; then
    echo -e "${RED}❌ TELEGRAM_BOT_TOKEN not found in .env file!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment ready. Starting bot...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the bot${NC}"
echo ""

# Run the bot
./venv/bin/python telegram_bot.py
