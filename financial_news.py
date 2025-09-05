"""
Financial News and Market Analysis Module
Integrates with Yahoo Finance and news APIs to provide real-time market insights
"""

import yfinance as yf
import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class FinancialNewsAnalyzer:
    def __init__(self):
        self.news_sources = {
            'marketwatch': 'https://feeds.marketwatch.com/marketwatch/marketpulse/',
            'reuters_business': 'http://feeds.reuters.com/reuters/businessNews',
            'cnn_business': 'http://rss.cnn.com/rss/money_latest.rss',
            'yahoo_finance': 'https://feeds.finance.yahoo.com/rss/2.0/headline'
        }
        
        # FX and commodity symbols for market data
        self.market_symbols = {
            'EUR/USD': 'EURUSD=X',
            'GBP/USD': 'GBPUSD=X', 
            'USD/JPY': 'USDJPY=X',
            'USD/CHF': 'USDCHF=X',
            'AUD/USD': 'AUDUSD=X',
            'USD/CAD': 'USDCAD=X',
            'NZD/USD': 'NZDUSD=X',
            'Gold': 'GC=F',
            'Silver': 'SI=F',
            'Oil_WTI': 'CL=F',
            'Oil_Brent': 'BZ=F',
            'Bitcoin': 'BTC-USD',
            'Ethereum': 'ETH-USD',
            'DXY': 'DX=F'  # US Dollar Index - updated symbol
        }
        
        # Cache for news and market data
        self.news_cache = {}
        self.market_cache = {}
        self.cache_timeout = 300  # 5 minutes
        
    def get_latest_financial_news(self, limit: int = 10) -> List[Dict]:
        """Get latest financial news from multiple sources"""
        cache_key = f"financial_news_{limit}"
        
        # Check cache first
        if self._is_cache_valid(cache_key, self.news_cache):
            return self.news_cache[cache_key]['data']
            
        all_news = []
        
        try:
            # Get Yahoo Finance news
            yahoo_news = self._get_yahoo_finance_news(limit=5)
            all_news.extend(yahoo_news)
            
            # Get additional news sources
            for source_name, feed_url in list(self.news_sources.items())[:2]:  # Limit to avoid timeout
                try:
                    response = requests.get(feed_url, timeout=10)
                    response.raise_for_status()
                    
                    # Parse RSS XML
                    root = ET.fromstring(response.content)
                    
                    # Find all item/entry elements
                    items = root.findall('.//item') or root.findall('.//entry')
                    
                    for item in items[:3]:  # Top 3 from each source
                        title_elem = item.find('title')
                        desc_elem = item.find('description') or item.find('summary')
                        link_elem = item.find('link')
                        date_elem = item.find('pubDate') or item.find('published')
                        
                        title = title_elem.text if title_elem is not None else 'No title'
                        summary = desc_elem.text if desc_elem is not None else 'No summary'
                        url = link_elem.text if link_elem is not None else ''
                        published = date_elem.text if date_elem is not None else ''
                        
                        # Clean HTML from summary
                        if summary:
                            summary = self._clean_html(summary)
                        
                        news_item = {
                            'title': title,
                            'summary': summary,
                            'url': url,
                            'published': published,
                            'source': source_name
                        }
                        all_news.append(news_item)
                        
                except Exception as e:
                    logger.warning(f"Failed to get news from {source_name}: {e}")
                    
            # Sort by relevance to FX/trading
            all_news = self._filter_fx_relevant_news(all_news)
            
            # Cache the results
            self.news_cache[cache_key] = {
                'data': all_news[:limit],
                'timestamp': datetime.now()
            }
            
            return all_news[:limit]
            
        except Exception as e:
            logger.error(f"Error getting financial news: {e}")
            return []
            
    def _get_yahoo_finance_news(self, limit: int = 5) -> List[Dict]:
        """Get news specifically from Yahoo Finance"""
        try:
            # Use Yahoo Finance RSS feed
            response = requests.get(self.news_sources['yahoo_finance'], timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            news_items = []
            
            for item in items[:limit]:
                title_elem = item.find('title')
                desc_elem = item.find('description')
                link_elem = item.find('link')
                date_elem = item.find('pubDate')
                
                title = title_elem.text if title_elem is not None else 'No title'
                summary = desc_elem.text if desc_elem is not None else 'No summary'
                url = link_elem.text if link_elem is not None else ''
                published = date_elem.text if date_elem is not None else ''
                
                if summary:
                    summary = self._clean_html(summary)
                
                news_item = {
                    'title': title,
                    'summary': summary,
                    'url': url,
                    'published': published,
                    'source': 'Yahoo Finance'
                }
                news_items.append(news_item)
                
            return news_items
            
        except Exception as e:
            logger.error(f"Error getting Yahoo Finance news: {e}")
            return []
            
    def get_market_data(self, symbols: Optional[List[str]] = None) -> Dict:
        """Get current market data for FX pairs and commodities"""
        if not symbols:
            symbols = list(self.market_symbols.keys())
            
        cache_key = f"market_data_{'-'.join(symbols)}"
        
        # Check cache
        if self._is_cache_valid(cache_key, self.market_cache):
            return self.market_cache[cache_key]['data']
            
        market_data = {}
        
        try:
            for symbol_name in symbols:
                if symbol_name in self.market_symbols:
                    yahoo_symbol = self.market_symbols[symbol_name]
                    try:
                        ticker = yf.Ticker(yahoo_symbol)
                        
                        # Try different approaches to get data
                        hist = None
                        try:
                            # Try 5 days first
                            hist = ticker.history(period="5d")
                        except:
                            try:
                                # Try 1 day
                                hist = ticker.history(period="1d")
                            except:
                                # Try with different interval
                                hist = ticker.history(period="2d", interval="1d")
                        
                        if hist is not None and not hist.empty:
                            current_price = hist['Close'].iloc[-1]
                            prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                            change = current_price - prev_price
                            change_pct = (change / prev_price) * 100 if prev_price != 0 else 0
                            
                            market_data[symbol_name] = {
                                'price': round(float(current_price), 4),
                                'change': round(float(change), 4),
                                'change_percent': round(float(change_pct), 2),
                                'timestamp': datetime.now().isoformat()
                            }
                        else:
                            # Fallback: provide dummy data to prevent empty responses
                            market_data[symbol_name] = {
                                'price': 'N/A',
                                'change': 0.0,
                                'change_percent': 0.0,
                                'timestamp': datetime.now().isoformat(),
                                'status': 'unavailable'
                            }
                            
                    except Exception as e:
                        logger.warning(f"Failed to get data for {symbol_name} ({yahoo_symbol}): {e}")
                        # Provide fallback data
                        market_data[symbol_name] = {
                            'price': 'N/A',
                            'change': 0.0,
                            'change_percent': 0.0,
                            'timestamp': datetime.now().isoformat(),
                            'status': 'error'
                        }
                        
            # Cache the results even if some failed
            if market_data:
                self.market_cache[cache_key] = {
                    'data': market_data,
                    'timestamp': datetime.now()
                }
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return {}
            
    def get_currency_analysis(self, base_currency: str = "USD") -> Dict:
        """Get comprehensive currency analysis"""
        try:
            # Get major FX pairs data
            fx_pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/USD', 'USD/CAD']
            market_data = self.get_market_data(fx_pairs)
            
            # Get DXY (Dollar Index)
            dxy_data = self.get_market_data(['DXY'])
            
            # Get gold price (inverse correlation with USD)
            gold_data = self.get_market_data(['Gold'])
            
            analysis = {
                'base_currency': base_currency,
                'timestamp': datetime.now().isoformat(),
                'fx_pairs': market_data,
                'dollar_index': dxy_data.get('DXY', {}),
                'gold': gold_data.get('Gold', {}),
                'analysis_summary': self._generate_currency_analysis_summary(market_data, dxy_data, gold_data)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in currency analysis: {e}")
            return {}
            
    def get_commodities_analysis(self) -> Dict:
        """Get commodities market analysis"""
        try:
            commodity_symbols = ['Gold', 'Silver', 'Oil_WTI', 'Oil_Brent']
            market_data = self.get_market_data(commodity_symbols)
            
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'commodities': market_data,
                'analysis_summary': self._generate_commodities_analysis_summary(market_data)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in commodities analysis: {e}")
            return {}
            
    def analyze_news_impact(self, news_items: List[Dict]) -> Dict:
        """Analyze potential market impact of news"""
        try:
            impact_analysis = {
                'high_impact': [],
                'medium_impact': [],
                'low_impact': [],
                'fx_relevant': [],
                'gold_relevant': [],
                'overall_sentiment': 'neutral'
            }
            
            # Keywords for impact classification
            high_impact_keywords = [
                'federal reserve', 'fed', 'interest rate', 'inflation', 'gdp',
                'unemployment', 'central bank', 'monetary policy', 'recession',
                'economic growth', 'trade war', 'geopolitical', 'crisis'
            ]
            
            medium_impact_keywords = [
                'earnings', 'economic data', 'manufacturing', 'consumer confidence',
                'retail sales', 'housing', 'crude oil', 'gold price', 'dollar'
            ]
            
            fx_keywords = [
                'currency', 'forex', 'fx', 'dollar', 'euro', 'pound', 'yen',
                'exchange rate', 'central bank', 'monetary policy'
            ]
            
            gold_keywords = [
                'gold', 'precious metals', 'inflation', 'safe haven',
                'economic uncertainty', 'geopolitical tension'
            ]
            
            positive_sentiment_count = 0
            negative_sentiment_count = 0
            
            for news in news_items:
                title_lower = news['title'].lower()
                summary_lower = news.get('summary', '').lower()
                full_text = f"{title_lower} {summary_lower}"
                
                # Classify impact level
                if any(keyword in full_text for keyword in high_impact_keywords):
                    impact_analysis['high_impact'].append(news)
                elif any(keyword in full_text for keyword in medium_impact_keywords):
                    impact_analysis['medium_impact'].append(news)
                else:
                    impact_analysis['low_impact'].append(news)
                
                # Check FX relevance
                if any(keyword in full_text for keyword in fx_keywords):
                    impact_analysis['fx_relevant'].append(news)
                    
                # Check gold relevance
                if any(keyword in full_text for keyword in gold_keywords):
                    impact_analysis['gold_relevant'].append(news)
                    
                # Simple sentiment analysis
                positive_words = ['up', 'rise', 'gain', 'growth', 'positive', 'strong', 'boost']
                negative_words = ['down', 'fall', 'decline', 'weak', 'negative', 'drop', 'crisis']
                
                positive_score = sum(1 for word in positive_words if word in full_text)
                negative_score = sum(1 for word in negative_words if word in full_text)
                
                if positive_score > negative_score:
                    positive_sentiment_count += 1
                elif negative_score > positive_score:
                    negative_sentiment_count += 1
                    
            # Overall sentiment
            if positive_sentiment_count > negative_sentiment_count:
                impact_analysis['overall_sentiment'] = 'positive'
            elif negative_sentiment_count > positive_sentiment_count:
                impact_analysis['overall_sentiment'] = 'negative'
                
            return impact_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing news impact: {e}")
            return {}
            
    def get_trading_insights(self, user_query: str = "") -> str:
        """Generate comprehensive trading insights based on current market conditions"""
        try:
            # Get fresh data
            news = self.get_latest_financial_news(limit=8)
            currency_analysis = self.get_currency_analysis()
            commodities_analysis = self.get_commodities_analysis()
            news_impact = self.analyze_news_impact(news)
            
            # Generate insights
            insights = []
            insights.append("📊 **Current Market Analysis & Trading Insights**\n")
            
            # Market overview with specific data
            if currency_analysis.get('dollar_index'):
                dxy = currency_analysis['dollar_index']
                price = dxy.get('price', 'N/A')
                change_pct = dxy.get('change_percent', 0)
                trend = "strengthening" if change_pct > 0 else "weakening" if change_pct < 0 else "stable"
                insights.append(f"💵 **US Dollar Index (DXY)**: {price} ({change_pct:+.2f}%) - USD {trend}")
                
            if commodities_analysis.get('commodities', {}).get('Gold'):
                gold = commodities_analysis['commodities']['Gold']
                price = gold.get('price', 'N/A')
                change_pct = gold.get('change_percent', 0)
                insights.append(f"🥇 **Gold**: ${price}/oz ({change_pct:+.2f}%)")
                
            # Top FX pairs performance with specific data
            insights.append("\n🔄 **Major FX Pairs:**")
            fx_data = currency_analysis.get('fx_pairs', {})
            for pair, data in list(fx_data.items())[:4]:
                price = data.get('price', 'N/A')
                change_pct = data.get('change_percent', 0)
                emoji = "🟢" if change_pct > 0 else "🔴" if change_pct < 0 else "⚪"
                insights.append(f"{emoji} **{pair}**: {price} ({change_pct:+.2f}%)")
                
            # Market sentiment with specific news context
            sentiment = news_impact.get('overall_sentiment', 'neutral')
            sentiment_emoji = "😊" if sentiment == 'positive' else "😟" if sentiment == 'negative' else "😐"
            insights.append(f"\n{sentiment_emoji} **Market Sentiment**: {sentiment.title()}")
            
            # High impact news with specific titles
            high_impact_news = news_impact.get('high_impact', [])
            if high_impact_news:
                insights.append(f"\n⚠️ **Key Market Movers** ({len(high_impact_news)} items):")
                for news_item in high_impact_news[:2]:
                    title = news_item['title'][:100] + "..." if len(news_item['title']) > 100 else news_item['title']
                    insights.append(f"• {title}")
                    summary = news_item.get('summary', '')
                    if summary:
                        clean_summary = summary.replace('<p>', '').replace('</p>', '').replace('<br>', ' ')[:120] + "..."
                        insights.append(f"  📝 {clean_summary}")
                        
            # FX specific insights with market context
            fx_relevant_news = news_impact.get('fx_relevant', [])
            if fx_relevant_news:
                insights.append(f"\n💱 **FX Market Impact** ({len(fx_relevant_news)} news items):")
                for fx_news in fx_relevant_news[:1]:
                    title = fx_news['title'][:80] + "..." if len(fx_news['title']) > 80 else fx_news['title']
                    insights.append(f"• {title}")
                insights.append("Recent developments may affect currency pairs.")
                
            # Trading recommendations based on user query
            if user_query.lower():
                specific_insights = self._get_query_specific_insights(user_query, currency_analysis, commodities_analysis, news_impact)
                if specific_insights:
                    insights.append(f"\n🎯 **Specific to your query:**")
                    insights.append(specific_insights)
                    
            # General trading advice with current market context
            insights.append(f"\n💡 **Trading Tips:**")
            
            # Dynamic advice based on current conditions
            if abs(currency_analysis.get('dollar_index', {}).get('change_percent', 0)) > 0.5:
                insights.append("• Strong USD movement detected - monitor USD pairs closely")
            
            if len(high_impact_news) > 2:
                insights.append("• High news flow today - expect increased volatility")
            
            if sentiment != 'neutral':
                insights.append(f"• Market showing {sentiment} bias - align strategies accordingly")
                
            insights.append("• Monitor economic calendar for upcoming releases")
            insights.append("• Consider risk management in volatile conditions")
            insights.append("• Stay updated with central bank communications")
            
            # Add current market hours info
            from datetime import datetime, timezone
            now_utc = datetime.now(timezone.utc)
            current_hour = now_utc.hour
            
            if 13 <= current_hour <= 22:  # London/NY overlap
                insights.append("• Currently in London/NY session overlap - higher liquidity expected")
            elif 0 <= current_hour <= 9:  # Asian session
                insights.append("• Asian session active - focus on JPY and AUD pairs")
            elif 9 <= current_hour <= 17:  # London session
                insights.append("• London session active - EUR and GBP pairs most active")
            
            # Disclaimer
            insights.append(f"\n⚠️ **Disclaimer**: Analysis based on current market data. Not financial advice. Always consult professionals and manage risks.")
            
            return "\n".join(insights)
            
        except Exception as e:
            logger.error(f"Error generating trading insights: {e}")
            return "📊 Unable to generate market insights at this time. Please try again later."
            
    def _get_query_specific_insights(self, query: str, currency_data: Dict, commodities_data: Dict, news_impact: Dict) -> str:
        """Generate insights specific to user's query"""
        query_lower = query.lower()
        
        try:
            # Currency specific queries
            if any(curr in query_lower for curr in ['usd', 'dollar', 'eur', 'euro', 'gbp', 'pound']):
                if 'usd' in query_lower or 'dollar' in query_lower:
                    dxy = currency_data.get('dollar_index', {})
                    if dxy:
                        return f"USD showing {dxy.get('change_percent', 0):+.2f}% change. Consider USD strength in your trades."
                        
            # Gold specific queries
            if 'gold' in query_lower:
                gold = commodities_data.get('commodities', {}).get('Gold', {})
                if gold:
                    gold_relevant_news = len(news_impact.get('gold_relevant', []))
                    return f"Gold at ${gold.get('price', 'N/A')} ({gold.get('change_percent', 0):+.2f}%). {gold_relevant_news} related news items detected."
                    
            # Oil queries
            if 'oil' in query_lower or 'crude' in query_lower:
                oil = commodities_data.get('commodities', {}).get('Oil_WTI', {})
                if oil:
                    return f"WTI Crude at ${oil.get('price', 'N/A')} ({oil.get('change_percent', 0):+.2f}%). Monitor for energy sector impacts."
                    
            # Market trend queries
            if any(word in query_lower for word in ['trend', 'direction', 'forecast']):
                sentiment = news_impact.get('overall_sentiment', 'neutral')
                return f"Current market sentiment is {sentiment}. Consider this in your trend analysis."
                
        except Exception as e:
            logger.error(f"Error in query-specific insights: {e}")
            
        return ""
        
    def _generate_currency_analysis_summary(self, fx_data: Dict, dxy_data: Dict, gold_data: Dict) -> str:
        """Generate currency analysis summary"""
        try:
            summary_points = []
            
            # Dollar strength analysis
            if dxy_data.get('DXY'):
                dxy_change = dxy_data['DXY'].get('change_percent', 0)
                if abs(dxy_change) > 0.5:
                    strength = "strengthening" if dxy_change > 0 else "weakening"
                    summary_points.append(f"USD {strength} ({dxy_change:+.2f}%)")
                    
            # Major pairs analysis
            strong_pairs = []
            weak_pairs = []
            
            for pair, data in fx_data.items():
                change_pct = data.get('change_percent', 0)
                if abs(change_pct) > 0.3:
                    if change_pct > 0:
                        strong_pairs.append(f"{pair} (+{change_pct:.2f}%)")
                    else:
                        weak_pairs.append(f"{pair} ({change_pct:.2f}%)")
                        
            if strong_pairs:
                summary_points.append(f"Strong: {', '.join(strong_pairs[:3])}")
            if weak_pairs:
                summary_points.append(f"Weak: {', '.join(weak_pairs[:3])}")
                
            return " | ".join(summary_points) if summary_points else "Markets showing mixed signals"
            
        except Exception as e:
            logger.error(f"Error generating currency summary: {e}")
            return "Analysis unavailable"
            
    def _generate_commodities_analysis_summary(self, commodities_data: Dict) -> str:
        """Generate commodities analysis summary"""
        try:
            summary_points = []
            
            for commodity, data in commodities_data.items():
                change_pct = data.get('change_percent', 0)
                if abs(change_pct) > 1.0:  # Significant move for commodities
                    direction = "up" if change_pct > 0 else "down"
                    summary_points.append(f"{commodity} {direction} {abs(change_pct):.1f}%")
                    
            return " | ".join(summary_points) if summary_points else "Commodities showing stable trading"
            
        except Exception as e:
            logger.error(f"Error generating commodities summary: {e}")
            return "Analysis unavailable"
            
    def _filter_fx_relevant_news(self, news_items: List[Dict]) -> List[Dict]:
        """Filter and prioritize FX-relevant news"""
        fx_keywords = [
            'currency', 'forex', 'fx', 'dollar', 'euro', 'pound', 'yen',
            'federal reserve', 'fed', 'ecb', 'boe', 'boj', 'central bank',
            'interest rate', 'inflation', 'gdp', 'economic', 'trade',
            'monetary policy', 'employment', 'consumer price'
        ]
        
        scored_news = []
        
        for news in news_items:
            title_lower = news['title'].lower()
            summary_lower = news.get('summary', '').lower()
            full_text = f"{title_lower} {summary_lower}"
            
            # Calculate relevance score
            score = sum(1 for keyword in fx_keywords if keyword in full_text)
            
            scored_news.append({
                'news': news,
                'relevance_score': score
            })
            
        # Sort by relevance score (highest first)
        scored_news.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return [item['news'] for item in scored_news]
        
    def _clean_html(self, text: str) -> str:
        """Clean HTML tags from text"""
        import re
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)
        
    def _is_cache_valid(self, cache_key: str, cache_dict: Dict) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in cache_dict:
            return False
            
        cache_time = cache_dict[cache_key]['timestamp']
        return (datetime.now() - cache_time).seconds < self.cache_timeout

# Test function
def test_financial_analyzer():
    analyzer = FinancialNewsAnalyzer()
    
    print("=== Testing Financial News Analyzer ===")
    
    # Test news retrieval
    print("\n1. Getting latest financial news...")
    news = analyzer.get_latest_financial_news(limit=3)
    for item in news:
        print(f"- {item['title']} [{item['source']}]")
        
    # Test market data
    print("\n2. Getting market data...")
    market_data = analyzer.get_market_data(['EUR/USD', 'Gold', 'DXY'])
    for symbol, data in market_data.items():
        print(f"- {symbol}: {data['price']} ({data['change_percent']:+.2f}%)")
        
    # Test trading insights
    print("\n3. Generating trading insights...")
    insights = analyzer.get_trading_insights("What's happening with USD today?")
    print(insights[:500] + "..." if len(insights) > 500 else insights)

if __name__ == "__main__":
    test_financial_analyzer()
