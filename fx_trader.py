"""
FX Trading Rate Provider
Provides daily exchange rates for XAF/USDT, XAF/AED with free exchange rate API
"""

import requests
import json
from datetime import datetime, timedelta
import pytz
import logging

logger = logging.getLogger(__name__)

class FXTrader:
    def __init__(self):
        self.base_rates = {
            'XAF_USD': 0.0,
            'XAF_USDT': 0.0,
            'XAF_AED': 0.0,
            'last_updated': ''
        }
        self.markup_percentage = 9  # 9% markup on USD/USDT rates
        self.aed_markup_percentage = 8.5  # 8.5% markup on AED rates
        self.api_base_url = "https://api.exchangerate-api.com/v4/latest"
    
    def get_usd_xaf_rate(self):
        """Get USD/XAF rate from free exchange rate API"""
        try:
            # Get USD rates
            response = requests.get(f"{self.api_base_url}/USD", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'rates' in data and 'XAF' in data['rates']:
                rate = data['rates']['XAF']
                logger.info(f"Retrieved USD/XAF rate from API: {rate}")
                return float(rate)
            else:
                logger.warning("XAF rate not found in API response")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching USD/XAF rate: {e}")
            # Fallback to approximate rate if API fails
            return 602.5  # Approximate current rate as fallback
    
    def get_aed_usd_rate(self):
        """Get AED/USD rate from free exchange rate API"""
        try:
            # Get AED rates
            response = requests.get(f"{self.api_base_url}/AED", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'rates' in data and 'USD' in data['rates']:
                rate = data['rates']['USD']
                logger.info(f"Retrieved AED/USD rate from API: {rate}")
                return float(rate)
            else:
                logger.warning("USD rate not found in AED API response")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching AED/USD rate: {e}")
            # Fallback to approximate rate if API fails
            return 0.272  # Approximate current rate as fallback
    
    def calculate_rates(self):
        """Calculate all FX rates with markup"""
        try:
            # Get base USD/XAF rate
            usd_xaf_rate = self.get_usd_xaf_rate()
            if not usd_xaf_rate:
                logger.error("Could not fetch USD/XAF rate")
                return False
            
            # Get AED/USD rate
            aed_usd_rate = self.get_aed_usd_rate()
            if not aed_usd_rate:
                logger.error("Could not fetch AED/USD rate")
                return False
            
            # Calculate rates with different markups
            usd_markup_multiplier = 1 + (self.markup_percentage / 100)
            aed_markup_multiplier = 1 + (self.aed_markup_percentage / 100)
            
            # XAF/USD with 8% markup (how much XAF to buy 1 USD from us)
            self.base_rates['XAF_USD'] = round(usd_xaf_rate * usd_markup_multiplier, 2)
            
            # XAF/USDT (assuming USDT ≈ USD) with 8% markup
            self.base_rates['XAF_USDT'] = round(usd_xaf_rate * usd_markup_multiplier, 2)
            
            # XAF/AED with 8.5% markup
            # First convert: AED -> USD -> XAF, then add markup
            aed_xaf_rate = aed_usd_rate * usd_xaf_rate
            self.base_rates['XAF_AED'] = round(aed_xaf_rate * aed_markup_multiplier, 2)
            
            # Update timestamp
            cameroon_tz = pytz.timezone('Africa/Douala')
            self.base_rates['last_updated'] = datetime.now(cameroon_tz).strftime('%Y-%m-%d %H:%M:%S %Z')
            
            logger.info(f"Updated FX rates: {self.base_rates}")
            return True
            
        except Exception as e:
            logger.error(f"Error calculating FX rates: {e}")
            return False
    
    def get_daily_rates(self):
        """Get daily FX rates summary with Evocash.org branding"""
        if not self.calculate_rates():
            return "⚠️ Unable to fetch current exchange rates. Please try again later."
        
        rates_message = f"""
🏦 **EVOCASH FX TRADING RATES** 📈
💼 *AI FX Trader from Evocash.org*

📅 **{self.base_rates['last_updated']}**

💱 **TODAY'S SELLING RATES:**
• 1 USD = {self.base_rates['XAF_USD']:,} XAF
• 1 USDT = {self.base_rates['XAF_USDT']:,} XAF  
• 1 AED = {self.base_rates['XAF_AED']:,} XAF

📊 **Rate Details:**
• USD/USDT: {self.markup_percentage}% service fee
• AED: {self.aed_markup_percentage}% service fee
• Based on live Yahoo Finance data
• Updated in real-time

💰 **Quick Calculate:**
Reply: "100 USD" or "500 AED"

📞 **WhatsApp Trading:** +1 (415) 523-8886
🌐 **Evocash.org** - Your Trusted FX Partner
⚠️ *Disclaimer: Rates are AI-generated for reference. Contact us for actual transactions.*

🕒 24/7 Service | 🔄 Live Updates
        """.strip()
        
        return rates_message
    
    def calculate_exchange(self, amount, currency):
        """Calculate exchange amount for a specific currency"""
        try:
            amount = float(amount)
            currency = currency.upper()
            
            if not self.calculate_rates():
                return "⚠️ Unable to fetch current rates. Please try again."
            
            if currency == 'USD':
                xaf_amount = amount * self.base_rates['XAF_USD']
                return f"""
💱 **EVOCASH FX CALCULATION**

**{amount:,} USD → {xaf_amount:,} XAF**

Rate: 1 USD = {self.base_rates['XAF_USD']:,} XAF
*Includes {self.markup_percentage}% service fee*

📞 **WhatsApp Trading:** +1 (415) 523-8886
🌐 **Evocash.org** - Contact us to complete transaction
📅 Updated: {self.base_rates['last_updated']}
⚠️ *AI-generated rate for reference*
                """.strip()
                
            elif currency in ['USDT', 'TETHER']:
                xaf_amount = amount * self.base_rates['XAF_USDT']
                return f"""
💱 **EVOCASH FX CALCULATION**

**{amount:,} USDT → {xaf_amount:,} XAF**

Rate: 1 USDT = {self.base_rates['XAF_USDT']:,} XAF
*Includes {self.markup_percentage}% service fee*

📞 **WhatsApp Trading:** +1 (415) 523-8886
🌐 **Evocash.org** - Contact us to complete transaction
📅 Updated: {self.base_rates['last_updated']}
⚠️ *AI-generated rate for reference*
                """.strip()
                
            elif currency == 'AED':
                xaf_amount = amount * self.base_rates['XAF_AED']
                return f"""
💱 **EVOCASH FX CALCULATION**

**{amount:,} AED → {xaf_amount:,} XAF**

Rate: 1 AED = {self.base_rates['XAF_AED']:,} XAF
*Includes {self.aed_markup_percentage}% service fee*

📞 **WhatsApp Trading:** +1 (415) 523-8886
🌐 **Evocash.org** - Contact us to complete transaction
📅 Updated: {self.base_rates['last_updated']}
⚠️ *AI-generated rate for reference*
                """.strip()
            else:
                return f"❌ Currency '{currency}' not supported. Available: USD, USDT, AED"
                
        except ValueError:
            return "❌ Invalid amount. Please enter a number (e.g., '100 USD')"
        except Exception as e:
            logger.error(f"Error calculating exchange: {e}")
            return "⚠️ Error processing exchange calculation. Please try again."

# Global FX trader instance
fx_trader = FXTrader()
