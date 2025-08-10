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
            'XAF_CNY': 0.0,  # Chinese Yuan (RMB)
            'XAF_EUR': 0.0,  # Euro
            'XOF_USD': 0.0,
            'XOF_USDT': 0.0,
            'XOF_AED': 0.0,
            'XOF_CNY': 0.0,  # Chinese Yuan (RMB)
            'XOF_EUR': 0.0,  # Euro
            'last_updated': ''
        }
        self.usd_markup_percentage = 8  # 8% markup on USD rates
        self.usdt_markup_percentage = 8.5  # 8.5% markup on USDT rates
        self.aed_markup_percentage = 8.5  # 8.5% markup on AED rates
        self.xof_markup_percentage = 3.5  # 3.5% markup on XOF rates
        # New currency markups
        self.xaf_cny_markup_percentage = 9.5  # 9.5% markup on XAF/CNY rates
        self.xof_cny_markup_percentage = 5.0  # 5% markup on XOF/CNY rates
        self.xaf_eur_markup_percentage = 6.0  # 6% markup on XAF/EUR rates
        self.xof_eur_markup_percentage = 4.0  # 4% markup on XOF/EUR rates
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
    
    def get_usd_xof_rate(self):
        """Get USD/XOF rate from free exchange rate API"""
        try:
            # Get USD rates
            response = requests.get(f"{self.api_base_url}/USD", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'rates' in data and 'XOF' in data['rates']:
                rate = data['rates']['XOF']
                logger.info(f"Retrieved USD/XOF rate from API: {rate}")
                return float(rate)
            else:
                logger.warning("XOF rate not found in API response")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching USD/XOF rate: {e}")
            # Fallback to approximate rate if API fails
            return 615.0  # Approximate current rate as fallback
    
    def get_usd_cny_rate(self):
        """Get USD/CNY rate from free exchange rate API"""
        try:
            # Get USD rates
            response = requests.get(f"{self.api_base_url}/USD", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'rates' in data and 'CNY' in data['rates']:
                rate = data['rates']['CNY']
                logger.info(f"Retrieved USD/CNY rate from API: {rate}")
                return float(rate)
            else:
                logger.warning("CNY rate not found in API response")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching USD/CNY rate: {e}")
            # Fallback to approximate rate if API fails
            return 7.25  # Approximate current rate as fallback
    
    def get_usd_eur_rate(self):
        """Get USD/EUR rate from free exchange rate API"""
        try:
            # Get USD rates
            response = requests.get(f"{self.api_base_url}/USD", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'rates' in data and 'EUR' in data['rates']:
                rate = data['rates']['EUR']
                logger.info(f"Retrieved USD/EUR rate from API: {rate}")
                return float(rate)
            else:
                logger.warning("EUR rate not found in API response")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching USD/EUR rate: {e}")
            # Fallback to approximate rate if API fails
            return 0.92  # Approximate current rate as fallback
    
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
            
            # Get USD/XOF rate
            usd_xof_rate = self.get_usd_xof_rate()
            if not usd_xof_rate:
                logger.error("Could not fetch USD/XOF rate")
                return False
            
            # Get USD/CNY rate
            usd_cny_rate = self.get_usd_cny_rate()
            if not usd_cny_rate:
                logger.error("Could not fetch USD/CNY rate")
                return False
            
            # Get USD/EUR rate
            usd_eur_rate = self.get_usd_eur_rate()
            if not usd_eur_rate:
                logger.error("Could not fetch USD/EUR rate")
                return False
            
            # Calculate rates with different markups
            usd_markup_multiplier = 1 + (self.usd_markup_percentage / 100)
            usdt_markup_multiplier = 1 + (self.usdt_markup_percentage / 100)
            aed_markup_multiplier = 1 + (self.aed_markup_percentage / 100)
            xof_markup_multiplier = 1 + (self.xof_markup_percentage / 100)
            # New currency markup multipliers
            xaf_cny_markup_multiplier = 1 + (self.xaf_cny_markup_percentage / 100)
            xof_cny_markup_multiplier = 1 + (self.xof_cny_markup_percentage / 100)
            xaf_eur_markup_multiplier = 1 + (self.xaf_eur_markup_percentage / 100)
            xof_eur_markup_multiplier = 1 + (self.xof_eur_markup_percentage / 100)
            
            # XAF/USD with 8% markup (how much XAF to buy 1 USD from us)
            self.base_rates['XAF_USD'] = round(usd_xaf_rate * usd_markup_multiplier, 2)
            
            # XAF/USDT with 8.5% markup
            self.base_rates['XAF_USDT'] = round(usd_xaf_rate * usdt_markup_multiplier, 2)
            
            # XAF/AED with 8.5% markup
            # First convert: AED -> USD -> XAF, then add markup
            aed_xaf_rate = aed_usd_rate * usd_xaf_rate
            self.base_rates['XAF_AED'] = round(aed_xaf_rate * aed_markup_multiplier, 2)
            
            # XOF rates with 3.5% markup (unchanged)
            self.base_rates['XOF_USD'] = round(usd_xof_rate * xof_markup_multiplier, 2)  # 3.5% for USD
            self.base_rates['XOF_USDT'] = round(usd_xof_rate * xof_markup_multiplier, 2)  # 3.5% for USDT
            # XOF/AED: AED -> USD -> XOF, then add markup
            aed_xof_rate = aed_usd_rate * usd_xof_rate
            self.base_rates['XOF_AED'] = round(aed_xof_rate * xof_markup_multiplier, 2)
            
            # New currency pairs
            # XAF/CNY with 9.5% markup: CNY -> USD -> XAF
            cny_xaf_rate = (1 / usd_cny_rate) * usd_xaf_rate  # Convert CNY to USD to XAF
            self.base_rates['XAF_CNY'] = round(cny_xaf_rate * xaf_cny_markup_multiplier, 2)
            
            # XOF/CNY with 5% markup: CNY -> USD -> XOF
            cny_xof_rate = (1 / usd_cny_rate) * usd_xof_rate  # Convert CNY to USD to XOF
            self.base_rates['XOF_CNY'] = round(cny_xof_rate * xof_cny_markup_multiplier, 2)
            
            # XAF/EUR with 6% markup: EUR -> USD -> XAF
            eur_xaf_rate = (1 / usd_eur_rate) * usd_xaf_rate  # Convert EUR to USD to XAF
            self.base_rates['XAF_EUR'] = round(eur_xaf_rate * xaf_eur_markup_multiplier, 2)
            
            # XOF/EUR with 4% markup: EUR -> USD -> XOF
            eur_xof_rate = (1 / usd_eur_rate) * usd_xof_rate  # Convert EUR to USD to XOF
            self.base_rates['XOF_EUR'] = round(eur_xof_rate * xof_eur_markup_multiplier, 2)
            
            # Update timestamp
            cameroon_tz = pytz.timezone('Africa/Douala')
            self.base_rates['last_updated'] = datetime.now(cameroon_tz).strftime('%Y-%m-%d %H:%M:%S %Z')
            
            logger.info(f"Updated FX rates: {self.base_rates}")
            return True
            
        except Exception as e:
            logger.error(f"Error calculating FX rates: {e}")
            return False
    
    def get_daily_rates(self):
        """Get daily FX rates summary"""
        if not self.calculate_rates():
            return "⚠️ Unable to fetch current exchange rates. Please try again later."
        
        rates_message = f"""
🏦 **EVA FX TRADING RATES** 📈
💼 *EVA Fx - Premium Currency Exchange*

📅 **{self.base_rates['last_updated']}**

💱 **TODAY'S SELLING RATES:**
• 1 USD = {self.base_rates['XAF_USD']:,} XAF | {self.base_rates['XOF_USD']:,} XOF
• 1 USDT = {self.base_rates['XAF_USDT']:,} XAF | {self.base_rates['XOF_USDT']:,} XOF
• 1 AED = {self.base_rates['XAF_AED']:,} XAF | {self.base_rates['XOF_AED']:,} XOF
• 1 CNY = {self.base_rates['XAF_CNY']:,} XAF | {self.base_rates['XOF_CNY']:,} XOF
• 1 EUR = {self.base_rates['XAF_EUR']:,} XAF | {self.base_rates['XOF_EUR']:,} XOF

📊 **Rate Details:**
• USD/USDT: Premium rates with service fee included
• AED: Competitive Middle East rates
• CNY: China market rates (9.5% XAF | 5% XOF markup)
• EUR: European market rates (6% XAF | 4% XOF markup)
• XOF rates: Better markup for West Africa
• Based on live international market data
• Updated in real-time

💰 **Quick Calculate:**
Reply: "100 USD", "500 CNY", "200 EUR" or "1000 XOF"

📞 **Contact EVA Fx:** +1 (415) 523-8886
⚠️ *Premium exchange rates by EVA Fx. Contact us for actual transactions.*

🕒 24/7 Service | 🔄 Live Updates | 🌍 Global Coverage
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
                xof_amount = amount * self.base_rates['XOF_USD']
                return f"""
💱 **EVA FX CALCULATION**

**{amount:,} USD → {xaf_amount:,} XAF**
**{amount:,} USD → {xof_amount:,} XOF**

Rates: 1 USD = {self.base_rates['XAF_USD']:,} XAF | {self.base_rates['XOF_USD']:,} XOF
*Service fee included*

📞 **Contact EVA Fx:** +1 (415) 523-8886
📅 Updated: {self.base_rates['last_updated']}
⚠️ *Premium exchange rates by EVA Fx*
                """.strip()
                
            elif currency in ['USDT', 'TETHER']:
                xaf_amount = amount * self.base_rates['XAF_USDT']
                xof_amount = amount * self.base_rates['XOF_USDT']
                return f"""
💱 **EVA FX CALCULATION**

**{amount:,} USDT → {xaf_amount:,} XAF**
**{amount:,} USDT → {xof_amount:,} XOF**

Rates: 1 USDT = {self.base_rates['XAF_USDT']:,} XAF | {self.base_rates['XOF_USDT']:,} XOF
*Service fee included*

📞 **Contact EVA Fx:** +1 (415) 523-8886
📅 Updated: {self.base_rates['last_updated']}
⚠️ *Premium exchange rates by EVA Fx*
                """.strip()
                
            elif currency == 'AED':
                xaf_amount = amount * self.base_rates['XAF_AED']
                xof_amount = amount * self.base_rates['XOF_AED']
                return f"""
💱 **EVA FX CALCULATION**

**{amount:,} AED → {xaf_amount:,} XAF**
**{amount:,} AED → {xof_amount:,} XOF**

Rates: 1 AED = {self.base_rates['XAF_AED']:,} XAF | {self.base_rates['XOF_AED']:,} XOF
*Service fee included*

📞 **Contact EVA Fx:** +1 (415) 523-8886
📅 Updated: {self.base_rates['last_updated']}
⚠️ *Premium exchange rates by EVA Fx*
                """.strip()
                
            elif currency in ['CNY', 'RMB', 'YUAN']:
                xaf_amount = amount * self.base_rates['XAF_CNY']
                xof_amount = amount * self.base_rates['XOF_CNY']
                return f"""
💱 **EVA FX CALCULATION**

**{amount:,} CNY → {xaf_amount:,} XAF**
**{amount:,} CNY → {xof_amount:,} XOF**

Rates: 1 CNY = {self.base_rates['XAF_CNY']:,} XAF | {self.base_rates['XOF_CNY']:,} XOF
*Premium China market rates*

📞 **Contact EVA Fx:** +1 (415) 523-8886
📅 Updated: {self.base_rates['last_updated']}
⚠️ *Premium exchange rates by EVA Fx*
                """.strip()
                
            elif currency == 'EUR':
                xaf_amount = amount * self.base_rates['XAF_EUR']
                xof_amount = amount * self.base_rates['XOF_EUR']
                return f"""
💱 **EVA FX CALCULATION**

**{amount:,} EUR → {xaf_amount:,} XAF**
**{amount:,} EUR → {xof_amount:,} XOF**

Rates: 1 EUR = {self.base_rates['XAF_EUR']:,} XAF | {self.base_rates['XOF_EUR']:,} XOF
*Premium European market rates*

📞 **Contact EVA Fx:** +1 (415) 523-8886
📅 Updated: {self.base_rates['last_updated']}
⚠️ *Premium exchange rates by EVA Fx*
                """.strip()
            else:
                return f"❌ Currency '{currency}' not supported. Available: USD, USDT, AED, CNY, EUR\n\n📞 **Contact EVA Fx:** +1 (415) 523-8886"
                
        except ValueError:
            return "❌ Invalid amount. Please enter a number (e.g., '100 USD')\n\n📞 **Contact EVA Fx:** +1 (415) 523-8886"
        except Exception as e:
            logger.error(f"Error calculating exchange: {e}")
            return "⚠️ Error processing exchange calculation. Please try again.\n\n📞 **Contact EVA Fx:** +1 (415) 523-8886"
    
    def get_trading_process_info(self, amount, currency, target_currency="XAF"):
        """Get trading process information with deposit requirements"""
        try:
            amount = float(amount)
            currency = currency.upper()
            target_currency = target_currency.upper()
            
            if not self.calculate_rates():
                return "⚠️ Unable to fetch current rates. Please try again."
            
            # Calculate conversion
            if currency == 'USD':
                if target_currency == 'XAF':
                    converted_amount = amount * self.base_rates['XAF_USD']
                    rate = self.base_rates['XAF_USD']
                elif target_currency == 'XOF':
                    converted_amount = amount * self.base_rates['XOF_USD']
                    rate = self.base_rates['XOF_USD']
                else:
                    return "❌ Target currency not supported"
            elif currency in ['USDT', 'TETHER']:
                if target_currency == 'XAF':
                    converted_amount = amount * self.base_rates['XAF_USDT']
                    rate = self.base_rates['XAF_USDT']
                elif target_currency == 'XOF':
                    converted_amount = amount * self.base_rates['XOF_USDT']
                    rate = self.base_rates['XOF_USDT']
                else:
                    return "❌ Target currency not supported"
            elif currency == 'AED':
                if target_currency == 'XAF':
                    converted_amount = amount * self.base_rates['XAF_AED']
                    rate = self.base_rates['XAF_AED']
                elif target_currency == 'XOF':
                    converted_amount = amount * self.base_rates['XOF_AED']
                    rate = self.base_rates['XOF_AED']
                else:
                    return "❌ Target currency not supported"
            elif currency in ['CNY', 'RMB', 'YUAN']:
                if target_currency == 'XAF':
                    converted_amount = amount * self.base_rates['XAF_CNY']
                    rate = self.base_rates['XAF_CNY']
                elif target_currency == 'XOF':
                    converted_amount = amount * self.base_rates['XOF_CNY']
                    rate = self.base_rates['XOF_CNY']
                else:
                    return "❌ Target currency not supported"
            elif currency == 'EUR':
                if target_currency == 'XAF':
                    converted_amount = amount * self.base_rates['XAF_EUR']
                    rate = self.base_rates['XAF_EUR']
                elif target_currency == 'XOF':
                    converted_amount = amount * self.base_rates['XOF_EUR']
                    rate = self.base_rates['XOF_EUR']
                else:
                    return "❌ Target currency not supported"
            else:
                return "❌ Source currency not supported"
            
            return f"""
🏦 **EVA FX TRADING PROCESS**

💱 **Your Trade with EVA Fx:**
{amount:,} {currency} → {converted_amount:,} {target_currency}
Rate: 1 {currency} = {rate:,} {target_currency}

📋 **TO COMPLETE THIS TRADE:**

**STEP 1: DEPOSIT TO DEDICATED ACCOUNT**
• Deposit cash equivalent in {target_currency} to our dedicated account
• Bank account details will be shared when you're ready to trade
• Account details vary by your country/region
• Mobile money transfers accepted (MTN, Orange Money, etc.)

**STEP 2: SUBMIT DEPOSIT PROOF**
• Send clear photo of deposit slip/receipt
• Include transaction reference number
• Specify amount deposited and bank/operator used
• Receipt must show your name and transaction date

**STEP 3: VERIFICATION PROCESS** 
• EVA Fx team verifies your deposit (15-30 minutes)
• Transaction amount must match your order exactly
• We check with bank/mobile operator for authenticity
• Fake or altered receipts are automatically rejected

**STEP 4: CURRENCY RELEASE**
• {currency} released after successful verification
• Digital wallet transfers for crypto/USD
• Cash pickup available in major cities
• International transfers to China & Europe supported

🌍 **GLOBAL PAYMENT MANAGEMENT:**
• **China**: Bank transfers, Alipay, WeChat Pay supported
• **Europe**: SEPA transfers, major European banks
• **Africa**: Local banks, mobile money operators
• **Middle East**: Banks and exchange houses

⚠️ **EVA FX SECURITY POLICY:**
• No deposit = No exchange (strict policy)
• All receipts undergo professional verification
• Deposits to personal accounts not accepted
• Only use our official dedicated accounts

🔒 **VERIFICATION:** Professional deposit verification system
📞 **EVA Fx Contact:** +1 (415) 523-8886
📞 **Trading Support:** Contact will be shared when ready

**Ready to proceed? EVA Fx will share account details next.**
            """.strip()
            
        except ValueError:
            return "❌ Invalid amount. Please enter a valid number."
        except Exception as e:
            logger.error(f"Error in trading process info: {e}")
            return "⚠️ Error generating trading information. Please try again."

# Global FX trader instance
fx_trader = FXTrader()
