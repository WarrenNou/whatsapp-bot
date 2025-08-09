"""
Daily Rate Scheduler for Evocash FX Trading Bot
Sends automated rate updates at 9 AM Gulf time
"""

import schedule
import time
import threading
from datetime import datetime
import pytz
import logging
from fx_trader import fx_trader
from twilio.rest import Client
import os

logger = logging.getLogger(__name__)

class DailyRateScheduler:
    def __init__(self, twilio_client, whatsapp_numbers=None):
        self.twilio_client = twilio_client
        self.whatsapp_numbers = whatsapp_numbers or []
        self.gulf_tz = pytz.timezone('Asia/Dubai')  # Gulf time (UAE)
        self.from_number = os.getenv('TWILIO_WHATSAPP_NUMBER')
        
    def add_subscriber(self, phone_number):
        """Add a phone number to receive daily rate updates"""
        if phone_number not in self.whatsapp_numbers:
            self.whatsapp_numbers.append(phone_number)
            logger.info(f"Added subscriber: {phone_number[:6]}***")
    
    def remove_subscriber(self, phone_number):
        """Remove a phone number from daily rate updates"""
        if phone_number in self.whatsapp_numbers:
            self.whatsapp_numbers.remove(phone_number)
            logger.info(f"Removed subscriber: {phone_number[:6]}***")
    
    def get_daily_broadcast_message(self):
        """Get the daily rate broadcast message"""
        daily_rates = fx_trader.get_daily_rates()
        
        broadcast_message = f"""
📢 **DAILY RATE UPDATE** 🌅

{daily_rates}

⚠️ **DISCLAIMER:**
This is an AI FX Trader from **Evocash.org**

🤖 Rates are AI-generated for reference
📞 Contact us for actual transactions
🕘 Next update: Tomorrow 9:00 AM Gulf Time

*Automated Daily Service by Evocash*
        """.strip()
        
        return broadcast_message
    
    def send_daily_rates(self):
        """Send daily rates to all subscribers"""
        try:
            message = self.get_daily_broadcast_message()
            
            for phone_number in self.whatsapp_numbers:
                try:
                    self.twilio_client.messages.create(
                        body=message,
                        from_=self.from_number,
                        to=phone_number
                    )
                    logger.info(f"Daily rate sent to {phone_number[:6]}***")
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Failed to send daily rate to {phone_number[:6]}***: {e}")
            
            logger.info(f"Daily rate broadcast completed to {len(self.whatsapp_numbers)} subscribers")
            
        except Exception as e:
            logger.error(f"Error in daily rate broadcast: {e}")
    
    def start_scheduler(self):
        """Start the daily rate scheduler"""
        # Schedule daily rate at 9:00 AM Gulf time
        schedule.every().day.at("09:00").do(self.send_daily_rates)
        
        logger.info("Daily rate scheduler started - Broadcasting at 9:00 AM Gulf Time")
        
        def run_scheduler():
            while True:
                try:
                    # Check if it's time to run scheduled jobs (in Gulf time)
                    now_gulf = datetime.now(self.gulf_tz)
                    
                    # Convert schedule to Gulf time context
                    schedule.run_pending()
                    time.sleep(60)  # Check every minute
                    
                except Exception as e:
                    logger.error(f"Scheduler error: {e}")
                    time.sleep(60)
        
        # Run scheduler in a separate thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        return scheduler_thread

# Global scheduler instance
daily_scheduler = None

def initialize_scheduler(twilio_client, initial_subscribers=None):
    """Initialize the daily rate scheduler"""
    global daily_scheduler
    daily_scheduler = DailyRateScheduler(twilio_client, initial_subscribers)
    daily_scheduler.start_scheduler()
    return daily_scheduler
