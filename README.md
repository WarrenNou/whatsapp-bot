# WhatsApp AI Bot Setup Guide

## Overview

EVA Fx Trading Bot — an AI-powered multi-platform financial trading assistant providing real-time currency exchange rates, market analysis, financial news, and gold price tracking. Available on WhatsApp (Twilio), Telegram, and a web chat interface.

### Key Features

- **FX Trading Rates** — XAF/XOF exchange rates for USD, AED, USDT, CNY, EUR
- **OpenClaw Integration** — Connect to an [OpenClaw](https://github.com/openclaw/openclaw) Gateway for enhanced AI-powered responses and skills
- **Multi-Source Market Data** — Aggregated data from CoinGecko (crypto), ECB (official FX rates), Yahoo Finance (indices), and more
- **Financial News & Analysis** — News from MarketWatch, Reuters, CNN, Yahoo Finance
- **Gold & Commodities** — Real-time gold, silver, oil prices with analysis
- **Daily Rate Broadcasts** — Automated broadcasts at 9 AM, 3 PM, 7 PM Gulf Time
- **Web Chat Interface** — Responsive web UI with live market ticker

## Prerequisites

1. Python 3.8+
2. Twilio Account
3. OpenAI API Key
4. Redis

## Step-by-Step Setup

### 1. Install Dependencies

```bash
# Install required Python packages
pip install -r requirements.txt

# Install ngrok for webhook exposure
brew install ngrok
```

### 2. Create Environment Configuration

Create a `.env` file in your project root:

```
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Twilio Credentials
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# OpenClaw Integration (optional — https://github.com/openclaw/openclaw)
# Set OPENCLAW_GATEWAY_URL to enable OpenClaw-powered responses
OPENCLAW_GATEWAY_URL=
OPENCLAW_API_KEY=
OPENCLAW_TIMEOUT=30
```

### 3. Start Redis

```bash
# On macOS with Homebrew
brew services start redis
```

### 4. Expose Local Server with ngrok

```bash
# Run your Flask app
python app.py

# In another terminal, expose the local server
# Replace 5001 with your actual port
ngrok http 5001
```

### 5. Twilio WhatsApp Sandbox Setup

1. Log in to Twilio Console
2. Navigate to WhatsApp Sandbox
3. Copy the ngrok HTTPS URL
4. Configure the webhook URL in Twilio:
   - Go to Messaging > WhatsApp
   - Set webhook to: `https://your-ngrok-url.io/webhook`

### 6. OpenClaw Setup (Optional)

[OpenClaw](https://github.com/openclaw/openclaw) is an open-source personal AI assistant that can enhance the bot with advanced skills and multi-channel support.

1. Install OpenClaw: `npm install -g openclaw@latest`
2. Run onboarding: `openclaw onboard --install-daemon`
3. Set `OPENCLAW_GATEWAY_URL` in your `.env` to the OpenClaw Gateway URL (default: `http://localhost:3000`)
4. The bot will automatically route messages through OpenClaw when available, falling back to direct OpenAI when not

### 7. Testing

- Send a message to your Twilio WhatsApp Sandbox number
- The bot should respond via WhatsApp
- Visit `http://localhost:5001` for the web chat interface

## Available Commands

| Command | Description |
|---------|-------------|
| `rates` | Current XAF & XOF exchange rates |
| `100 USD` | Calculate XAF/XOF equivalent |
| `crypto` | Live cryptocurrency prices (CoinGecko) |
| `ecb rates` | Official ECB exchange rates |
| `indices` | Global stock market indices |
| `full market` | Comprehensive market overview |
| `financial news` | Latest market headlines |
| `market analysis` | In-depth market analysis |
| `gold prices` | Gold & commodities data |
| `trading insights` | AI-powered trading insights |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Web chat message processing |
| `/api/financial-news` | GET | Financial news |
| `/api/market-analysis` | GET | Market analysis data |
| `/api/trading-insights` | GET | AI trading insights |
| `/api/gold-analysis` | GET | Gold & metals analysis |
| `/api/crypto` | GET | Cryptocurrency prices (CoinGecko) |
| `/api/ecb-rates` | GET | ECB official exchange rates |
| `/api/global-indices` | GET | Global stock market indices |
| `/api/openclaw/status` | GET | OpenClaw Gateway status |
| `/health` | GET | Service health check |
| `/webhook` | POST | WhatsApp (Twilio) webhook |

## Free Data Sources

The bot aggregates financial data from multiple free sources:

- **Yahoo Finance** — FX rates, commodities, stock indices
- **CoinGecko** — Cryptocurrency prices (no API key required)
- **European Central Bank** — Official EUR-based exchange rates (no API key required)
- **MarketWatch / Reuters / CNN / Yahoo RSS** — Financial news feeds
- **Finviz** — Stock screening and analysis
- **Exchange Rate API** — Fallback FX rates

## Troubleshooting

- Ensure all environment variables are set
- Check Redis is running
- Verify Twilio and OpenAI credentials
- Check ngrok connection

## Security Notes

- Never commit `.env` file to version control
- Rotate API keys periodically
- Use strong, unique passwords

## Production Deployment

- Use a production WSGI server (gunicorn)
- Set up proper logging
- Use a cloud service for hosting (Render config included in `render.yaml`)
- Implement additional security measures