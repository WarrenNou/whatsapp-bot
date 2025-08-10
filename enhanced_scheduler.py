"""
Server Keep-Alive and Enhanced Scheduler for FX Trading Bot
Prevents free server from sleeping and adds multiple daily broadcasts
"""

import schedule
import time
import threading
import requests
from datetime import datetime
import pytz
import logging
from fx_trader import fx_trader
from twilio.rest import Client
import os

logger = logging.getLogger(__name__)

class AdvancedScheduler:
    def __init__(self, twilio_client, whatsapp_numbers=None, server_url=None):
        self.twilio_client = twilio_client
        self.whatsapp_numbers = whatsapp_numbers or []
        self.gulf_tz = pytz.timezone('Asia/Dubai')  # Gulf time (UAE)
        self.from_number = os.getenv('TWILIO_WHATSAPP_NUMBER')
        
        # Auto-detect server URL for different environments
        if server_url:
            self.server_url = server_url
        elif os.getenv('RENDER'):
            # On Render, use the configured service URL
            self.server_url = os.getenv('RENDER_URL', 'https://whatsapp-bot-96xm.onrender.com')
        else:
            # Local development
            self.server_url = f"http://localhost:{os.getenv('PORT', 5001)}"
        
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
    
    def keep_server_alive(self):
        """Ping the server to prevent it from sleeping"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=10)
            if response.status_code == 200:
                logger.info("Server keep-alive ping successful")
            else:
                logger.warning(f"Server keep-alive ping returned status: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to ping server for keep-alive: {e}")
            # Try alternative ping to main domain
            try:
                requests.get(self.server_url, timeout=5)
                logger.info("Alternative keep-alive ping successful")
            except:
                logger.error("All keep-alive attempts failed")
    
    def get_morning_broadcast_message(self):
        """Get the 9 AM daily rate broadcast message"""
        daily_rates = fx_trader.get_daily_rates()
        
        broadcast_message = f"""
🌅 **MORNING RATE UPDATE** 📢

{daily_rates}

⏰ **TRADING HOURS:**
• Next updates: 3:00 PM & 7:00 PM Gulf Time
• Markets active all day

⚠️ **DISCLAIMER:**
This is an AI FX Trading Assistant

🤖 Rates are AI-generated for reference
📞 Contact us for actual transactions: +1 (415) 523-8886

*Automated Morning Service*
        """.strip()
        
        return broadcast_message
    
    def get_afternoon_message(self):
        """Get the 3 PM afternoon message"""
        daily_rates = fx_trader.get_daily_rates()
        
        message = f"""
🌞 **AFTERNOON RATE CHECK** 📊

{daily_rates}

⚠️ **TRADING NOTICE:**
🕰️ Day is progressing - Time getting closer to end for today

⏰ **Remaining Today:**
• Final update: 7:00 PM Gulf Time
• New rates: Tomorrow 9:00 AM

💼 **Contact us to trade:** +1 (415) 523-8886
⚠️ AI FX Trading Service
        """.strip()
        
        return message
    
    def get_evening_message(self):
        """Get the 7 PM evening message"""
        daily_rates = fx_trader.get_daily_rates()
        
        message = f"""
🌆 **EVENING FINAL UPDATE** ⏰

{daily_rates}

🚨 **URGENT NOTICE:**
⏰ Time is close to end for today's trading!

⚠️ **Last Chance:**
• Final rates of the day
• Next update: Tomorrow 9:00 AM Gulf Time
• Current rates valid until midnight

🌐 **Contact us to trade:** +1 (415) 523-8886
⚠️ AI FX Trading - Final Call Service
        """.strip()
        
        return message
    
    def send_broadcast(self, message_type="morning"):
        """Send broadcast message to all subscribers"""
        try:
            if message_type == "morning":
                message = self.get_morning_broadcast_message()
            elif message_type == "afternoon":
                message = self.get_afternoon_message()
            elif message_type == "evening":
                message = self.get_evening_message()
            else:
                message = self.get_morning_broadcast_message()
            
            for phone_number in self.whatsapp_numbers:
                try:
                    self.twilio_client.messages.create(
                        body=message,
                        from_=self.from_number,
                        to=phone_number
                    )
                    logger.info(f"{message_type.title()} broadcast sent to {phone_number[:6]}***")
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Failed to send {message_type} broadcast to {phone_number[:6]}***: {e}")
            
            logger.info(f"{message_type.title()} broadcast completed to {len(self.whatsapp_numbers)} subscribers")
            
        except Exception as e:
            logger.error(f"Error in {message_type} broadcast: {e}")
    
    def send_morning_rates(self):
        """Send morning rates at 9 AM"""
        self.send_broadcast("morning")
    
    def send_afternoon_update(self):
        """Send afternoon update at 3 PM"""
        self.send_broadcast("afternoon")
    
    def send_evening_final(self):
        """Send evening final update at 7 PM"""
        self.send_broadcast("evening")
    
    def start_scheduler(self):
        """Start the enhanced scheduler with keep-alive functionality"""
        # Schedule daily broadcasts
        schedule.every().day.at("09:00").do(self.send_morning_rates)
        schedule.every().day.at("15:00").do(self.send_afternoon_update)  # 3 PM
        schedule.every().day.at("19:00").do(self.send_evening_final)     # 7 PM
        
        # Schedule server keep-alive every 10 minutes
        schedule.every(10).minutes.do(self.keep_server_alive)
        
        logger.info("Enhanced scheduler started:")
        logger.info("- Daily rates: 9:00 AM Gulf Time")
        logger.info("- Afternoon update: 3:00 PM Gulf Time") 
        logger.info("- Evening final: 7:00 PM Gulf Time")
        logger.info("- Server keep-alive: Every 10 minutes")
        
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
        
        # Start immediate keep-alive thread
        def keep_alive_worker():
            while True:
                try:
                    self.keep_server_alive()
                    time.sleep(600)  # Every 10 minutes
                except Exception as e:
                    logger.error(f"Keep-alive worker error: {e}")
                    time.sleep(300)  # Retry in 5 minutes if error
        
        keep_alive_thread = threading.Thread(target=keep_alive_worker, daemon=True)
        keep_alive_thread.start()
        
        return scheduler_thread

# Global enhanced scheduler instance
enhanced_scheduler = None

def initialize_enhanced_scheduler(twilio_client, initial_subscribers=None, server_url=None):
    """Initialize the enhanced scheduler with keep-alive functionality"""
    global enhanced_scheduler
    enhanced_scheduler = AdvancedScheduler(twilio_client, initial_subscribers, server_url)
    enhanced_scheduler.start_scheduler()
    return enhanced_scheduler
