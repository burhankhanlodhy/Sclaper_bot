import asyncio
import websockets
import json
import aiohttp
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class KrakenAPIClient:
    def __init__(self, api_key: str = "", api_secret: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.kraken.com"
        self.ws_url = "wss://ws.kraken.com/"
        self.websocket = None
        self.subscriptions = {}
        self.callbacks = {}
        self.successful_subscriptions = set()
        self.failed_subscriptions = set()
        
    async def get_usd_pairs(self) -> List[Dict]:
        """Fetch all USD trading pairs from Kraken"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/0/public/AssetPairs") as response:
                    data = await response.json()
                    
                    if data.get('error'):
                        logger.error(f"Kraken API error: {data['error']}")
                        return []
                    
                    pairs = []
                    for pair_name, pair_info in data['result'].items():
                        # Filter for USD pairs
                        if pair_info.get('quote') == 'ZUSD' or pair_info.get('quote') == 'USD':
                            base_currency = pair_info.get('base', '').replace('Z', '').replace('X', '')
                            quote_currency = pair_info.get('quote', '').replace('Z', '').replace('X', '')
                            
                            if quote_currency == 'USD':
                                pairs.append({
                                    'symbol': pair_name,
                                    'altname': pair_info.get('altname', ''),
                                    'base_currency': base_currency,
                                    'quote_currency': quote_currency,
                                    'pair_decimals': pair_info.get('pair_decimals', 4),
                                    'lot_decimals': pair_info.get('lot_decimals', 8),
                                    'lot_multiplier': pair_info.get('lot_multiplier', 1),
                                    'status': pair_info.get('status', 'online')
                                })
                    
                    logger.info(f"Found {len(pairs)} USD trading pairs")
                    return pairs
                    
        except Exception as e:
            logger.error(f"Error fetching USD pairs: {e}")
            return []
    
    async def get_ticker_data(self, pairs: List[str]) -> Dict:
        """Get ticker data for specified pairs"""
        try:
            pair_string = ",".join(pairs)
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/0/public/Ticker?pair={pair_string}") as response:
                    data = await response.json()
                    
                    if data.get('error'):
                        logger.error(f"Ticker API error: {data['error']}")
                        return {}
                    
                    return data.get('result', {})
                    
        except Exception as e:
            logger.error(f"Error fetching ticker data: {e}")
            return {}
    
    async def get_order_book(self, pair: str, count: int = 10) -> Dict:
        """Get order book data for a specific pair"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/0/public/Depth?pair={pair}&count={count}") as response:
                    data = await response.json()
                    
                    if data.get('error'):
                        logger.error(f"Order book API error: {data['error']}")
                        return {}
                    
                    return data.get('result', {})
                    
        except Exception as e:
            logger.error(f"Error fetching order book for {pair}: {e}")
            return {}
    
    async def connect_websocket(self):
        """Connect to Kraken WebSocket API"""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            logger.info("Connected to Kraken WebSocket")
            
            # Start listening for messages
            asyncio.create_task(self._listen_websocket())
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            self.websocket = None
    
    async def _listen_websocket(self):
        """Listen for WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_websocket_message(data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.websocket = None
        except Exception as e:
            logger.error(f"WebSocket listen error: {e}")
            self.websocket = None
    
    async def _handle_websocket_message(self, data):
        """Handle incoming WebSocket messages"""
        if isinstance(data, dict):
            # Handle subscription confirmations
            if data.get('event') == 'subscriptionStatus':
                status = data.get('status')
                pair = data.get('pair', 'unknown')
                subscription_type = data.get('subscription', {}).get('name', 'unknown')
                
                if status == 'subscribed':
                    logger.info(f"Successfully subscribed to {subscription_type} for {pair}")
                    self.successful_subscriptions.add(f"{pair}:{subscription_type}")
                elif status == 'error':
                    error_msg = data.get('errorMessage', 'Unknown error')
                    logger.warning(f"Subscription failed for {pair} ({subscription_type}): {error_msg}")
                    self.failed_subscriptions.add(f"{pair}:{subscription_type}")
                else:
                    logger.info(f"Subscription status for {pair}: {data}")
                return
            
            # Handle system status
            if data.get('event') == 'systemStatus':
                status = data.get('status', 'unknown')
                logger.info(f"Kraken system status: {status}")
                return
                
        elif isinstance(data, list) and len(data) > 3:
            # Handle ticker data
            channel_id = data[0]
            ticker_data = data[1]
            channel_name = data[2]
            pair = data[3]
            
            if channel_name == 'ticker':
                await self._handle_ticker_update(pair, ticker_data)
            elif channel_name == 'book':
                await self._handle_order_book_update(pair, ticker_data)
    
    async def _handle_ticker_update(self, pair: str, ticker_data: Dict):
        """Handle ticker price updates"""
        try:
            price = float(ticker_data.get('c', [0, 0])[0])  # Last trade price
            bid = float(ticker_data.get('b', [0, 0])[0])    # Best bid
            ask = float(ticker_data.get('a', [0, 0])[0])    # Best ask
            volume = float(ticker_data.get('v', [0, 0])[1]) # 24h volume
            
            # Call registered callbacks
            if 'ticker' in self.callbacks:
                await self.callbacks['ticker'](pair, {
                    'price': price,
                    'bid': bid,
                    'ask': ask,
                    'volume': volume,
                    'timestamp': datetime.now()
                })
                
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Error parsing ticker data for {pair}: {e}")
    
    async def _handle_order_book_update(self, pair: str, book_data: Dict):
        """Handle order book updates"""
        try:
            if 'book' in self.callbacks:
                await self.callbacks['book'](pair, book_data)
                
        except Exception as e:
            logger.error(f"Error handling order book update for {pair}: {e}")
    
    async def subscribe_ticker(self, pairs: List[str]):
        """Subscribe to ticker updates for specified pairs"""
        if not self.websocket:
            await self.connect_websocket()
            # Wait a bit for connection to establish
            await asyncio.sleep(1)
        
        if self.websocket and pairs:
            # Filter out invalid pairs and limit batch size
            valid_pairs = [pair for pair in pairs if pair and len(pair) <= 20]
            
            if len(valid_pairs) > 50:
                logger.warning(f"Batch size {len(valid_pairs)} exceeds recommended 50, limiting to 50")
                valid_pairs = valid_pairs[:50]
            
            subscription_msg = {
                "event": "subscribe",
                "pair": valid_pairs,
                "subscription": {"name": "ticker"}
            }
            
            try:
                await self.websocket.send(json.dumps(subscription_msg))
                logger.info(f"Subscribed to ticker for {len(valid_pairs)} pairs")
            except Exception as e:
                logger.error(f"Failed to send ticker subscription: {e}")
    
    async def subscribe_order_book(self, pairs: List[str], depth: int = 10):
        """Subscribe to order book updates for specified pairs"""
        if not self.websocket:
            await self.connect_websocket()
            await asyncio.sleep(1)
        
        if self.websocket and pairs:
            # Limit order book subscriptions to avoid overwhelming the server
            limited_pairs = pairs[:25] if len(pairs) > 25 else pairs
            valid_pairs = [pair for pair in limited_pairs if pair and len(pair) <= 20]
            
            subscription_msg = {
                "event": "subscribe",
                "pair": valid_pairs,
                "subscription": {"name": "book", "depth": depth}
            }
            
            try:
                await self.websocket.send(json.dumps(subscription_msg))
                logger.info(f"Subscribed to order book for {len(valid_pairs)} pairs")
            except Exception as e:
                logger.error(f"Failed to send order book subscription: {e}")
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register a callback for specific event types"""
        self.callbacks[event_type] = callback
        logger.info(f"Registered callback for {event_type}")
    
    def get_subscription_stats(self) -> Dict:
        """Get statistics about successful and failed subscriptions"""
        return {
            'successful_count': len(self.successful_subscriptions),
            'failed_count': len(self.failed_subscriptions),
            'successful_subscriptions': list(self.successful_subscriptions),
            'failed_subscriptions': list(self.failed_subscriptions)
        }
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("Disconnected from Kraken WebSocket")

class PriceAnalyzer:
    def __init__(self):
        self.price_history = {}
        self.signals = {}
        
    def add_price_data(self, symbol: str, price_data: Dict):
        """Add price data for analysis"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append(price_data)
        
        # Keep only last 100 price points
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]
    
    def generate_buy_signal(self, symbol: str) -> bool:
        """Generate simple buy signal based on price movement"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 5:
            return False
        
        recent_prices = [data['price'] for data in self.price_history[symbol][-5:]]
        
        # Simple moving average crossover strategy
        if len(recent_prices) >= 5:
            short_ma = sum(recent_prices[-3:]) / 3
            long_ma = sum(recent_prices[-5:]) / 5
            
            # Buy signal when short MA crosses above long MA
            return short_ma > long_ma and recent_prices[-1] > recent_prices[-2]
        
        return False
    
    def get_price_change_percentage(self, symbol: str, periods: int = 5) -> float:
        """Calculate price change percentage over specified periods"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < periods:
            return 0.0
        
        current_price = self.price_history[symbol][-1]['price']
        old_price = self.price_history[symbol][-periods]['price']
        
        return ((current_price - old_price) / old_price) * 100
