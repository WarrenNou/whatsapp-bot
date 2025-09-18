#!/usr/bin/env python3
"""
Enhanced Gold Price Tracker
Fetches gold prices with different karat calculations and weight conversions (oz and kg)
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Optional

def fetch_gold_price():
    """
    Fetch current gold price using Yahoo Finance API
    Returns price per troy ounce in USD
    """
    # URL for Gold Futures (GC=F)
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
    
    # Using proper headers to avoid rate limiting
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    try:
        # Make the request with timeout
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract the data
        result = data["chart"]["result"][0]
        current_price = result["meta"]["regularMarketPrice"]
        previous_close = result["meta"]["previousClose"]
        currency = result["meta"]["currency"]
        
        # Calculate changes
        price_change = current_price - previous_close
        percent_change = (price_change / previous_close) * 100
        
        # Format and return
        return {
            "symbol": "GC=F",
            "name": "Gold Futures (24K)",
            "price": round(current_price, 2),
            "currency": currency,
            "previous_close": round(previous_close, 2),
            "change": round(price_change, 2),
            "percent_change": round(percent_change, 2),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "Yahoo Finance"
        }
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error fetching gold price: {e}")
        return None
    except (KeyError, ValueError, TypeError) as e:
        print(f"❌ Data parsing error: {e}")
        return None

def fetch_gold_price_fallback():
    """
    Fallback method using alternative API or mock data for demonstration
    """
    # This is a mock example - you could replace with another API
    return {
        "symbol": "GOLD",
        "name": "Gold Futures (24K)",
        "price": 2650.00,  # Example price
        "currency": "USD",
        "previous_close": 2640.00,
        "change": 10.00,
        "percent_change": 0.38,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "Fallback/Demo Data"
    }

def calculate_karat_prices(pure_gold_price: float) -> Dict[str, float]:
    """
    Calculate gold prices for different karat purities
    
    Args:
        pure_gold_price: Price of pure gold (24K) per troy ounce
        
    Returns:
        Dictionary with karat types and their respective prices
    """
    karat_purity = {
        "24K": 1.000,  # 99.9% pure gold
        "22K": 0.917,  # 91.7% pure gold
        "18K": 0.750,  # 75.0% pure gold
        "14K": 0.583,  # 58.3% pure gold
        "10K": 0.417   # 41.7% pure gold
    }
    
    karat_prices = {}
    for karat, purity in karat_purity.items():
        karat_prices[karat] = round(pure_gold_price * purity, 2)
    
    return karat_prices

def convert_troy_ounce_to_kg(price_per_oz: float) -> float:
    """
    Convert troy ounce price to kilogram price
    
    Conversion facts:
    - 1 troy ounce = 31.1035 grams
    - 1 kilogram = 1000 grams
    
    Args:
        price_per_oz: Price per troy ounce
        
    Returns:
        Price per kilogram
    """
    troy_oz_to_grams = 31.1035
    grams_per_kg = 1000
    price_per_kg = price_per_oz * (grams_per_kg / troy_oz_to_grams)
    return round(price_per_kg, 2)

def convert_oz_to_grams(price_per_oz: float) -> float:
    """
    Convert troy ounce price to gram price
    
    Args:
        price_per_oz: Price per troy ounce
        
    Returns:
        Price per gram
    """
    troy_oz_to_grams = 31.1035
    price_per_gram = price_per_oz / troy_oz_to_grams
    return round(price_per_gram, 2)

def fetch_all_gold_prices(use_fallback: bool = False) -> Optional[Dict]:
    """
    Get comprehensive gold price data including different karats and weight units
    
    Args:
        use_fallback: If True, use fallback data instead of API
        
    Returns:
        Complete gold price data dictionary or None if failed
    """
    # Get pure gold price
    if use_fallback:
        gold_data = fetch_gold_price_fallback()
    else:
        gold_data = fetch_gold_price()
        
        # If API fails, try fallback
        if not gold_data:
            print("⚠️  API failed, using fallback data for demonstration...")
            gold_data = fetch_gold_price_fallback()
    
    if not gold_data:
        return None
    
    # Calculate prices for different karats
    karat_prices_oz = calculate_karat_prices(gold_data["price"])
    
    # Calculate prices per kilogram for each karat
    karat_prices_kg = {}
    karat_prices_gram = {}
    
    for karat, price_oz in karat_prices_oz.items():
        karat_prices_kg[karat] = convert_troy_ounce_to_kg(price_oz)
        karat_prices_gram[karat] = convert_oz_to_grams(price_oz)
    
    # Add all price variations to the gold data
    gold_data.update({
        "karat_prices_oz": karat_prices_oz,
        "karat_prices_kg": karat_prices_kg,
        "karat_prices_gram": karat_prices_gram,
        "price_per_kg": convert_troy_ounce_to_kg(gold_data["price"]),
        "price_per_gram": convert_oz_to_grams(gold_data["price"])
    })
    
    return gold_data

def format_gold_price_report(gold_data: Dict) -> str:
    """
    Format gold price data into a comprehensive readable report
    
    Args:
        gold_data: Complete gold price data dictionary
        
    Returns:
        Formatted report string
    """
    if not gold_data:
        return "❌ Unable to fetch gold price data"
    
    # Determine trend emoji
    change_pct = gold_data.get('percent_change', 0)
    if change_pct > 0:
        trend_emoji = "📈"
        trend_text = "UP"
    elif change_pct < 0:
        trend_emoji = "📉" 
        trend_text = "DOWN"
    else:
        trend_emoji = "➡️"
        trend_text = "FLAT"
    
    report = f"""🥇 **COMPREHENSIVE GOLD PRICE REPORT** 🥇
📅 Last Updated: {gold_data['time']}
📊 Data Source: {gold_data.get('source', 'Unknown')}
{trend_emoji} Market Trend: {trend_text} ({change_pct:+.2f}%)

💰 **Current Gold Price (24K Pure):**
• ${gold_data['price']:,.2f} {gold_data['currency']} per troy ounce
• ${gold_data['price_per_kg']:,.2f} {gold_data['currency']} per kilogram  
• ${gold_data['price_per_gram']:,.2f} {gold_data['currency']} per gram

📊 **Market Change:**
• Previous Close: ${gold_data['previous_close']:,.2f}
• Change: ${gold_data['change']:+,.2f} ({gold_data['percent_change']:+.2f}%)

🔗 **Prices by Karat (per troy ounce):**"""
    
    for karat, price in gold_data["karat_prices_oz"].items():
        report += f"\n• {karat}: ${price:,.2f} {gold_data['currency']}"
    
    report += f"\n\n🔗 **Prices by Karat (per kilogram):**"
    
    for karat, price in gold_data["karat_prices_kg"].items():
        report += f"\n• {karat}: ${price:,.2f} {gold_data['currency']}"
    
    report += f"\n\n🔗 **Prices by Karat (per gram):**"
    
    for karat, price in gold_data["karat_prices_gram"].items():
        report += f"\n• {karat}: ${price:.2f} {gold_data['currency']}"
    
    # Add investment insights
    report += f"\n\n💡 **Investment Insights:**"
    if change_pct > 2:
        report += f"\n• Strong bullish momentum - consider profit-taking levels"
    elif change_pct > 0.5:
        report += f"\n• Positive momentum - good for long positions"
    elif change_pct < -2:
        report += f"\n• Significant decline - potential buying opportunity"
    elif change_pct < -0.5:
        report += f"\n• Mild weakness - monitor for further declines"
    else:
        report += f"\n• Consolidation phase - await directional breakout"
    
    return report

def get_gold_price_json(use_fallback: bool = False) -> str:
    """
    Get gold price data as JSON string
    
    Args:
        use_fallback: If True, use fallback data
        
    Returns:
        JSON string of gold price data
    """
    gold_data = fetch_all_gold_prices(use_fallback)
    if gold_data:
        return json.dumps(gold_data, indent=2)
    else:
        return json.dumps({"error": "Failed to fetch gold price data"}, indent=2)

def main():
    """
    Main function to demonstrate the gold price tracker
    """
    print("🥇 Enhanced Gold Price Tracker 🥇")
    print("=" * 60)
    
    try:
        # Try to get real data first
        print("Fetching live gold price data...")
        gold_data = fetch_all_gold_prices(use_fallback=False)
        
        if gold_data and gold_data.get('source') != 'Fallback/Demo Data':
            print("✅ Successfully fetched live data!")
        else:
            print("⚠️  Using demonstration data (API may be rate-limited)")
            gold_data = fetch_all_gold_prices(use_fallback=True)
        
        if gold_data:
            # Display formatted report
            print("\n" + format_gold_price_report(gold_data))
            
            # Ask if user wants to see raw JSON
            print("\n" + "=" * 60)
            response = input("Would you like to see the raw JSON data? (y/n): ").lower().strip()
            if response in ['y', 'yes']:
                print("\n📋 **RAW JSON DATA:**")
                print(json.dumps(gold_data, indent=2))
        else:
            print("❌ Failed to fetch gold price data from all sources")
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
