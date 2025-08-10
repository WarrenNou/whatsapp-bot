"""
External Keep-Alive Service
Use with services like UptimeRobot, Pingdom, or any external monitoring
"""

import requests
import time
import threading
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class ExternalKeepAlive:
    def __init__(self, server_url=None, interval_minutes=5):
        # Auto-detect environment and use appropriate URL
        if server_url:
            self.server_url = server_url
        elif os.getenv('RENDER'):
            # On Render, use the configured service URL
            self.server_url = os.getenv('RENDER_URL', 'https://whatsapp-bot-96xm.onrender.com')
        else:
            # Local development
            self.server_url = f"http://localhost:{os.getenv('PORT', 5001)}"
            
        self.interval_seconds = interval_minutes * 60
        self.running = False
        self.thread = None
        
    def ping_server(self):
        """Ping the server to keep it alive"""
        endpoints = ['/ping', '/health', '/keep-alive']
        
        for endpoint in endpoints:
            try:
                url = f"{self.server_url}{endpoint}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    logger.info(f"Keep-alive successful: {endpoint} - {response.status_code}")
                    return True
                else:
                    logger.warning(f"Keep-alive warning: {endpoint} - {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Keep-alive failed for {endpoint}: {e}")
                continue
        
        logger.error("All keep-alive endpoints failed")
        return False
    
    def start(self):
        """Start the external keep-alive service"""
        if self.running:
            logger.warning("Keep-alive service already running")
            return
            
        self.running = True
        
        def keep_alive_worker():
            logger.info(f"Starting external keep-alive service - pinging every {self.interval_seconds/60} minutes")
            
            while self.running:
                try:
                    self.ping_server()
                    time.sleep(self.interval_seconds)
                except Exception as e:
                    logger.error(f"Keep-alive worker error: {e}")
                    time.sleep(60)  # Retry in 1 minute on error
        
        self.thread = threading.Thread(target=keep_alive_worker, daemon=True)
        self.thread.start()
        
        logger.info(f"External keep-alive service started - interval: {self.interval_seconds/60} minutes")
    
    def stop(self):
        """Stop the external keep-alive service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("External keep-alive service stopped")

# Global external keep-alive instance
external_keep_alive = ExternalKeepAlive()

# Instructions for external monitoring setup
MONITORING_SETUP_INSTRUCTIONS = """
🚀 **FREE SERVER KEEP-ALIVE SETUP INSTRUCTIONS**

**Method 1: UptimeRobot (Recommended)**
1. Go to https://uptimerobot.com (Free account)
2. Add New Monitor:
   - Type: HTTP(s)
   - URL: https://your-app-domain.com/ping
   - Interval: 5 minutes
   - Keyword: "alive" (optional)

**Method 2: Pingdom**
1. Go to https://pingdom.com (Free tier available)  
2. Create HTTP check:
   - URL: https://your-app-domain.com/health
   - Interval: 5 minutes

**Method 3: Manual cURL (For testing)**
```bash
# Run this every 5 minutes
curl https://your-app-domain.com/keep-alive
```

**Available Endpoints:**
- /ping - Basic ping
- /health - Full health check
- /keep-alive - Dedicated keep-alive

**Benefits:**
✅ Prevents free server hibernation
✅ 24/7 monitoring 
✅ Email alerts if server goes down
✅ Multiple datacenter checks
✅ Free tier available on most services

**For Render.com Users:**
Your app URL will be: https://your-app-name.onrender.com
"""

def print_setup_instructions():
    """Print setup instructions for external monitoring"""
    print(MONITORING_SETUP_INSTRUCTIONS)
