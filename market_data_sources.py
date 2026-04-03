"""
Additional Free Financial Market Data Sources
Aggregates data from multiple free APIs to provide comprehensive market coverage.
Sources include CoinGecko (crypto), FRED (macro), ECB (FX), and open stock APIs.
"""

import requests
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class MarketDataAggregator:
    """Aggregates financial data from multiple free sources."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes

        # Free API endpoints (no keys required)
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.ecb_rates_url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
        self.fred_base = "https://api.stlouisfed.org/fred"

    # ------------------------------------------------------------------
    # Caching helpers
    # ------------------------------------------------------------------

    def _get_cached(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry and (time.time() - entry['ts']) < self._cache_ttl:
            return entry['data']
        return None

    def _set_cached(self, key: str, data: Any) -> None:
        self._cache[key] = {'data': data, 'ts': time.time()}

    # ------------------------------------------------------------------
    # CoinGecko – Cryptocurrency data (free, no API key)
    # ------------------------------------------------------------------

    def get_crypto_prices(self, coins: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get current cryptocurrency prices from CoinGecko."""
        if coins is None:
            coins = ['bitcoin', 'ethereum', 'tether', 'binancecoin', 'solana',
                     'ripple', 'cardano', 'dogecoin']

        cache_key = f"crypto_{'_'.join(sorted(coins))}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            ids = ','.join(coins)
            resp = requests.get(
                f"{self.coingecko_base}/simple/price",
                params={
                    'ids': ids,
                    'vs_currencies': 'usd',
                    'include_24hr_change': 'true',
                    'include_market_cap': 'true',
                    'include_24hr_vol': 'true'
                },
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                result = self._format_crypto_data(data)
                self._set_cached(cache_key, result)
                return result
            else:
                logger.warning(f"CoinGecko returned status {resp.status_code}")
        except requests.RequestException as e:
            logger.error(f"CoinGecko request failed: {e}")

        return {'error': 'Crypto data temporarily unavailable', 'source': 'coingecko'}

    def _format_crypto_data(self, raw: Dict) -> Dict[str, Any]:
        """Format raw CoinGecko data into a structured response."""
        formatted = {}
        for coin_id, data in raw.items():
            formatted[coin_id] = {
                'price_usd': data.get('usd', 0),
                'change_24h_pct': round(data.get('usd_24h_change', 0), 2),
                'market_cap_usd': data.get('usd_market_cap', 0),
                'volume_24h_usd': data.get('usd_24h_vol', 0),
            }
        return {
            'coins': formatted,
            'source': 'coingecko',
            'timestamp': datetime.utcnow().isoformat()
        }

    def get_crypto_market_summary(self) -> str:
        """Get a formatted crypto market summary string."""
        data = self.get_crypto_prices()
        if 'error' in data:
            return f"⚠️ {data['error']}"

        lines = ["🪙 **CRYPTOCURRENCY MARKET**\n"]
        symbols = {
            'bitcoin': ('₿ Bitcoin', 'BTC'),
            'ethereum': ('Ξ Ethereum', 'ETH'),
            'tether': ('₮ Tether', 'USDT'),
            'binancecoin': ('🔶 BNB', 'BNB'),
            'solana': ('◎ Solana', 'SOL'),
            'ripple': ('✕ XRP', 'XRP'),
            'cardano': ('₳ Cardano', 'ADA'),
            'dogecoin': ('Ð Dogecoin', 'DOGE'),
        }

        coins = data.get('coins', {})
        for coin_id, (name, ticker) in symbols.items():
            coin = coins.get(coin_id)
            if coin:
                price = coin['price_usd']
                change = coin['change_24h_pct']
                arrow = '📈' if change >= 0 else '📉'
                sign = '+' if change >= 0 else ''
                if price >= 1:
                    price_str = f"${price:,.2f}"
                else:
                    price_str = f"${price:.4f}"
                lines.append(f"{name} ({ticker}): {price_str} {arrow} {sign}{change}%")

        lines.append(f"\n📊 Source: CoinGecko | Updated: {data.get('timestamp', 'N/A')[:16]}")
        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # ECB – European Central Bank exchange rates (free, no API key)
    # ------------------------------------------------------------------

    def get_ecb_rates(self) -> Dict[str, Any]:
        """Get official ECB exchange rates (EUR-based)."""
        cached = self._get_cached('ecb_rates')
        if cached:
            return cached

        try:
            resp = requests.get(self.ecb_rates_url, timeout=10)
            if resp.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.content)
                ns = {'gesmes': 'http://www.gesmes.org/xml/2002-08-01',
                      'eurofxref': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'}

                rates = {'EUR': 1.0}
                cube = root.findall('.//eurofxref:Cube/eurofxref:Cube/eurofxref:Cube', ns)
                for item in cube:
                    currency = item.get('currency')
                    rate = item.get('rate')
                    if currency and rate:
                        rates[currency] = float(rate)

                result = {
                    'rates': rates,
                    'base': 'EUR',
                    'source': 'ecb',
                    'timestamp': datetime.utcnow().isoformat()
                }
                self._set_cached('ecb_rates', result)
                return result
            else:
                logger.warning(f"ECB returned status {resp.status_code}")
        except requests.RequestException as e:
            logger.error(f"ECB request failed: {e}")

        return {'error': 'ECB rates temporarily unavailable', 'source': 'ecb'}

    def get_ecb_rates_summary(self) -> str:
        """Get a formatted ECB rates summary string."""
        data = self.get_ecb_rates()
        if 'error' in data:
            return f"⚠️ {data['error']}"

        rates = data.get('rates', {})
        lines = ["🏦 **ECB OFFICIAL EXCHANGE RATES** (Base: EUR)\n"]

        key_currencies = ['USD', 'GBP', 'JPY', 'CHF', 'CNY', 'AUD', 'CAD',
                          'NZD', 'ZAR', 'TRY', 'BRL', 'INR']
        flags = {
            'USD': '🇺🇸', 'GBP': '🇬🇧', 'JPY': '🇯🇵', 'CHF': '🇨🇭',
            'CNY': '🇨🇳', 'AUD': '🇦🇺', 'CAD': '🇨🇦', 'NZD': '🇳🇿',
            'ZAR': '🇿🇦', 'TRY': '🇹🇷', 'BRL': '🇧🇷', 'INR': '🇮🇳',
        }

        for cur in key_currencies:
            rate = rates.get(cur)
            if rate:
                flag = flags.get(cur, '')
                lines.append(f"{flag} EUR/{cur}: {rate:.4f}")

        lines.append(f"\n📊 Source: European Central Bank | Updated: {data.get('timestamp', 'N/A')[:16]}")
        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # Aggregated global market overview
    # ------------------------------------------------------------------

    def get_global_indices(self) -> Dict[str, Any]:
        """Get global stock index data from Yahoo Finance (free)."""
        cached = self._get_cached('global_indices')
        if cached:
            return cached

        indices = {
            'S&P 500': '^GSPC',
            'Dow Jones': '^DJI',
            'NASDAQ': '^IXIC',
            'FTSE 100': '^FTSE',
            'DAX': '^GDAXI',
            'Nikkei 225': '^N225',
        }

        results = {}
        for name, symbol in indices.items():
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                resp = requests.get(url, headers=headers, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    chart_result = data.get('chart', {}).get('result', [])
                    if chart_result:
                        meta = chart_result[0].get('meta', {})
                        price = meta.get('regularMarketPrice', 0)
                        prev_close = meta.get('chartPreviousClose', meta.get('previousClose', 0))
                        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
                        results[name] = {
                            'price': round(price, 2),
                            'change_pct': round(change_pct, 2),
                            'symbol': symbol
                        }
            except requests.RequestException as e:
                logger.debug(f"Failed to fetch {name}: {e}")

        result = {
            'indices': results,
            'source': 'yahoo_finance',
            'timestamp': datetime.utcnow().isoformat()
        }
        self._set_cached('global_indices', result)
        return result

    def get_global_indices_summary(self) -> str:
        """Get formatted global indices summary."""
        data = self.get_global_indices()
        indices = data.get('indices', {})

        if not indices:
            return "⚠️ Global indices data temporarily unavailable"

        lines = ["🌍 **GLOBAL MARKET INDICES**\n"]
        flags = {
            'S&P 500': '🇺🇸', 'Dow Jones': '🇺🇸', 'NASDAQ': '🇺🇸',
            'FTSE 100': '🇬🇧', 'DAX': '🇩🇪', 'Nikkei 225': '🇯🇵',
        }

        for name, info in indices.items():
            flag = flags.get(name, '🏳️')
            price = info['price']
            change = info['change_pct']
            arrow = '📈' if change >= 0 else '📉'
            sign = '+' if change >= 0 else ''
            lines.append(f"{flag} {name}: {price:,.2f} {arrow} {sign}{change:.2f}%")

        lines.append(f"\n📊 Source: Yahoo Finance | Updated: {data.get('timestamp', 'N/A')[:16]}")
        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # Combined market overview
    # ------------------------------------------------------------------

    def get_full_market_overview(self) -> str:
        """Get a comprehensive market overview combining all sources."""
        sections = []

        sections.append("📊 **COMPREHENSIVE MARKET OVERVIEW**")
        sections.append("=" * 40)

        # Global indices
        indices_summary = self.get_global_indices_summary()
        sections.append(indices_summary)
        sections.append("")

        # Crypto
        crypto_summary = self.get_crypto_market_summary()
        sections.append(crypto_summary)
        sections.append("")

        # ECB rates
        ecb_summary = self.get_ecb_rates_summary()
        sections.append(ecb_summary)
        sections.append("")

        sections.append("─" * 40)
        sections.append("🔗 Data from: CoinGecko, ECB, Yahoo Finance")
        sections.append("⚠️ For informational purposes only. Verify before trading.")

        return '\n'.join(sections)


# Module-level singleton
market_data = MarketDataAggregator()
