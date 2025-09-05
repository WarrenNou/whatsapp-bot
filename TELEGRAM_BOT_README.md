# EVA Fx Telegram Bot

This Telegram bot provides FX trading rates and currency conversion services. It supports both local development (polling mode) and cloud deployment (webhook mode).

## Features

- 🔄 **Real-time FX Rates**: Get current exchange rates for XAF, XOF, USD, USDT, AED, CNY, EUR
- 💱 **Currency Conversion**: Convert between different currencies with live rates
- 🤖 **AI Integration**: OpenAI-powered responses for general questions
- 📊 **Interactive Buttons**: Quick access to rates and conversions
- 🌐 **Multi-platform**: Works on local development and cloud platforms

## Supported Currencies

- **XAF** (Central African Franc)
- **XOF** (West African Franc) 
- **USD** (US Dollar)
- **USDT** (Tether)
- **AED** (UAE Dirham)
- **CNY** (Chinese Yuan)
- **EUR** (Euro)

## Quick Start

### 1. Setup
```bash
# Run the setup script
./setup_telegram.sh
```

### 2. Configure Bot Token
1. Create a bot with [@BotFather](https://t.me/BotFather) on Telegram
2. Copy the bot token
3. Add it to your `.env` file:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### 3. Run the Bot

#### Local Development (Polling Mode)
```bash
# Start as background service
./telegram_service.sh start

# Check status
./telegram_service.sh status

# View logs
./telegram_service.sh logs

# Stop service
./telegram_service.sh stop
```

#### Or run directly:
```bash
./venv/bin/python run_telegram_bot.py
```

#### Cloud Deployment (Webhook Mode)
The bot automatically detects cloud platforms and runs in webhook mode:
```bash
python app.py
```

## Bot Commands

- `/start` - Welcome message and quick actions
- `/help` - Show help information
- `/rates` - Get current exchange rates
- `/convert [amount] [from] to [to]` - Convert currencies

## Example Usage

```
User: /rates
Bot: Shows current FX rates with interactive buttons

User: /convert 100 USD to XAF  
Bot: 100 USD = 60,450 XAF (Rate: 604.50)

User: Rate for AED
Bot: Current AED rates and conversion options
```

## Architecture

### Local Mode (Development)
- Uses **polling** to get updates from Telegram
- Runs independently of other services
- Perfect for development and testing
- No webhook URL required

### Cloud Mode (Production)  
- Uses **webhooks** to receive updates
- Integrated with main Flask application
- Automatically detected on platforms like Render, Heroku
- Webhook endpoint: `/telegram-webhook`

## File Structure

```
├── telegram_bot.py          # Main bot implementation
├── run_telegram_bot.py      # Standalone bot runner
├── telegram_service.sh      # Service management script
├── setup_telegram.sh        # Setup script
├── app.py                   # Main Flask app (includes webhook)
└── logs/
    ├── telegram_bot.log     # Bot logs
    └── telegram_service.log # Service logs
```

## Service Management

The `telegram_service.sh` script provides easy service management:

```bash
./telegram_service.sh start    # Start bot service
./telegram_service.sh stop     # Stop bot service  
./telegram_service.sh restart  # Restart bot service
./telegram_service.sh status   # Check if running
./telegram_service.sh logs     # View and follow logs
```

## Environment Variables

Required:
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token

Optional:
- `OPENAI_API_KEY` - For AI-powered responses
- `PORT` - Detected automatically on cloud platforms

## Deployment

### Render (Recommended for Production)
1. Connect your GitHub repository
2. Set environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENAI_API_KEY` (optional)
3. Deploy the main Flask app (`app.py`)
4. Bot will automatically run in webhook mode

### Local Development
1. Run setup: `./setup_telegram.sh`
2. Start service: `./telegram_service.sh start`
3. Bot runs in polling mode

### Docker (Optional)
The existing Dockerfile supports the Telegram bot:
```bash
docker build -t eva-fx-bot .
docker run -e TELEGRAM_BOT_TOKEN=your_token eva-fx-bot
```

## Monitoring and Logs

### Local Logs
```bash
# Service logs
tail -f logs/telegram_service.log

# Bot logs  
tail -f logs/telegram_bot.log

# Follow live logs
./telegram_service.sh logs
```

### Cloud Logs
Logs are available through your cloud platform's dashboard (Render, Heroku, etc.)

## Troubleshooting

### Bot Not Responding
1. Check if bot is running: `./telegram_service.sh status`
2. Verify bot token in `.env` file
3. Check logs for errors: `./telegram_service.sh logs`

### Webhook Issues (Cloud)
1. Ensure Flask app is running
2. Check webhook endpoint: `POST /telegram-webhook`
3. Verify bot token in environment variables

### Rate Limit Issues
The bot includes rate limiting protection and handles Telegram API limits automatically.

### Import Errors
Install dependencies: `pip install -r requirements.txt`

## Security

- Bot tokens are stored in environment variables
- No sensitive data in code
- Input validation on all user messages
- Rate limiting protection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test locally using `./telegram_service.sh start`
4. Submit a pull request

## Support

For issues or questions:
1. Check the logs first
2. Review this documentation
3. Open an issue on GitHub

---

**Built with ❤️ for EVA Fx**
