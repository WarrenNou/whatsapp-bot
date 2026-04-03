import os

class Config:
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL')

    # OpenClaw Integration (https://github.com/openclaw/openclaw)
    OPENCLAW_GATEWAY_URL = os.getenv('OPENCLAW_GATEWAY_URL', '')
    OPENCLAW_API_KEY = os.getenv('OPENCLAW_API_KEY', '')
    OPENCLAW_TIMEOUT = int(os.getenv('OPENCLAW_TIMEOUT', '30'))