# WhatsApp AI Bot Setup Guide

## Prerequisites

1. Python 3.8+
2. Twilio Account
3. OpenAI API Key
4. Redis

## Step-by-Step Setup

### 1. Install Dependencies

```bash
# Install required Python packages
pip install flask flask-limiter twilio openai redis pytz python-dotenv

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

### 6. Testing

- Send a message to your Twilio WhatsApp Sandbox number
- The bot should respond via WhatsApp

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
- Use a cloud service for hosting
- Implement additional security measures
```

### Twilio WhatsApp Sandbox Steps

1. Log in to Twilio Console
2. Go to Messaging > WhatsApp
3. Follow the sandbox setup instructions
4. Add your phone number to the approved list
5. Save the Twilio webhook URL

Would you like me to help you with any of these specific steps? The most critical next steps are:
1. Setting up your `.env` file
2. Configuring the Twilio WhatsApp Sandbox
3. Exposing your local server with ngrok

What would you like to tackle first?