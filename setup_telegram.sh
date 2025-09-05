#!/bin/bash
# Telegram Bot Setup Script
# This script sets up the Telegram bot for both local and cloud deployment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR"

print_status "Setting up Telegram Bot environment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment and install dependencies
print_status "Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt
print_success "Dependencies installed"

# Create logs directory
mkdir -p logs

# Check environment variables
print_status "Checking environment variables..."

if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating template..."
    cat > .env << 'EOF'
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# OpenAI Configuration (optional but recommended)
OPENAI_API_KEY=your_openai_api_key_here

# Other existing configuration...
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
REDIS_HOST=localhost
REDIS_PORT=6379
EOF
    print_warning "Please edit .env file and add your TELEGRAM_BOT_TOKEN"
    print_warning "To create a Telegram bot:"
    print_warning "1. Message @BotFather on Telegram"
    print_warning "2. Use /newbot command"
    print_warning "3. Follow the instructions"
    print_warning "4. Copy the token to .env file"
else
    # Check if TELEGRAM_BOT_TOKEN is set
    source .env
    if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ "$TELEGRAM_BOT_TOKEN" = "your_bot_token_here" ]; then
        print_warning "TELEGRAM_BOT_TOKEN not configured in .env file"
        print_warning "Please edit .env file and add your bot token"
    else
        print_success "TELEGRAM_BOT_TOKEN is configured"
    fi
fi

# Make scripts executable
chmod +x run_telegram_bot.py
chmod +x telegram_service.sh

print_success "Setup completed!"
echo ""
echo "=== Usage ==="
print_status "Local development (polling mode):"
echo "  ./telegram_service.sh start   # Start as background service"
echo "  ./telegram_service.sh status  # Check status"
echo "  ./telegram_service.sh stop    # Stop service"
echo "  ./telegram_service.sh logs    # View logs"
echo ""
echo "  OR run directly:"
echo "  ./venv/bin/python run_telegram_bot.py"
echo ""
print_status "Cloud deployment (webhook mode):"
echo "  The bot will automatically detect cloud platforms like Render"
echo "  Start the main Flask app and the bot will handle webhooks"
echo "  python app.py"
echo ""
print_status "Testing:"
echo "  1. Start the bot using one of the methods above"
echo "  2. Message your bot on Telegram"
echo "  3. Try commands like /start, /rates, /help"
echo ""

# Detect current environment
if [ -n "$RENDER" ] || [ -n "$HEROKU" ] || [ -n "$PORT" ]; then
    print_status "Cloud platform detected - webhook mode recommended"
else
    print_status "Local environment detected - polling mode available"
fi
