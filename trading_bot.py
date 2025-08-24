import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from database import DatabaseManager
from kraken_client import KrakenAPIClient, PriceAnalyzer

logger = logging.getLogger(__name__)

class PaperTradingBot:
    def __init__(self, db_manager: DatabaseManager):
        # Core services
        self.db = db_manager
        self.kraken_client = KrakenAPIClient()
        self.price_analyzer = PriceAnalyzer()

        # Risk and trade sizing
        self.trade_amount = 10.0   # $10 per trade
        self.maker_fee = 0.0025    # 0.25% maker fee
        self.profit_margin = 0.02  # 2% profit target
        self.stop_loss = 0.015     # 1.5% stop loss

        # Runtime state
        self.is_running = False
        self.strategy_name = None
        self.strategy_params = {}
        
    async def initialize(self):
        """Initialize the trading bot"""
        try:
            # Fetch and store USD pairs
            usd_pairs = await self.kraken_client.get_usd_pairs()
            for pair in usd_pairs:
                self.db.add_pair(
                    pair['symbol'],
                    pair['base_currency'],
                    pair['quote_currency']
                )
            
            logger.info(f"Initialized {len(usd_pairs)} USD trading pairs")
            
            # Register callbacks for real-time data
            self.kraken_client.register_callback('ticker', self._handle_ticker_update)
            self.kraken_client.register_callback('book', self._handle_order_book_update)
            
            # Subscribe to ticker updates for active pairs in batches
            all_pairs = self.db.get_usd_pairs()
            logger.info(f"Total pairs available: {len(all_pairs)}")
            
            # Prepare pairs for WebSocket subscription
            subscription_pairs = []
            for pair in all_pairs:
                # Convert symbol to WebSocket format (e.g., BTCUSD -> XBT/USD)
                symbol = pair['symbol']
                if symbol.endswith('USD'):
                    base = symbol[:-3]
                    # Special mapping for Bitcoin
                    if base == 'BTC':
                        base = 'XBT'
                    pair_name = f"{base}/USD"
                    subscription_pairs.append(pair_name)
            
            # Remove duplicates and limit to reasonable number
            subscription_pairs = list(set(subscription_pairs))
            logger.info(f"Prepared {len(subscription_pairs)} pairs for subscription")
            
            # Subscribe in batches of 50 to avoid server issues
            batch_size = 50
            ticker_batches = [subscription_pairs[i:i + batch_size] for i in range(0, len(subscription_pairs), batch_size)]
            
            logger.info(f"Subscribing to ticker data in {len(ticker_batches)} batches of {batch_size}")
            
            for i, batch in enumerate(ticker_batches):
                try:
                    await self.kraken_client.subscribe_ticker(batch)
                    logger.info(f"Subscribed to ticker batch {i+1}/{len(ticker_batches)} ({len(batch)} pairs)")
                    # Small delay between batches to avoid overwhelming the server
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.warning(f"Failed to subscribe to ticker batch {i+1}: {e}")
            
            # Subscribe to order book for top 25 pairs only (to avoid overwhelming)
            top_pairs = subscription_pairs[:25]
            if top_pairs:
                try:
                    await self.kraken_client.subscribe_order_book(top_pairs)
                    logger.info(f"Subscribed to order book for top {len(top_pairs)} pairs")
                except Exception as e:
                    logger.warning(f"Failed to subscribe to order book: {e}")
            
            # Wait a moment for subscriptions to complete, then log statistics
            await asyncio.sleep(3)
            stats = self.kraken_client.get_subscription_stats()
            logger.info(f"Subscription Summary: {stats['successful_count']} successful, {stats['failed_count']} failed")
            
            if stats['successful_count'] > 0:
                logger.info(f"Successfully receiving data from {stats['successful_count']} pair subscriptions")
            
            if stats['failed_count'] > 0:
                logger.warning(f"Failed subscriptions: {stats['failed_count']} pairs could not be subscribed")
            
            return True
            
        except Exception as e:
            logger.error(f"Bot initialization error: {e}")
            return False
    
    async def _handle_ticker_update(self, pair: str, ticker_data: Dict):
        """Handle real-time ticker updates"""
        try:
            # Store price data in database
            self.db.update_price_data(
                pair,
                ticker_data['price'],
                ticker_data['bid'],
                ticker_data['ask'],
                ticker_data['volume']
            )
            
            # Add to price analyzer
            self.price_analyzer.add_price_data(pair, ticker_data)
            
            # If bot is not running, do not open/close trades
            if not self.is_running:
                return
            
            # Check for trading signals (open positions)
            await self._check_trading_signals(pair, ticker_data)
            
            # Check open trades for stop loss/take profit (manage positions)
            await self._monitor_open_trades(pair, ticker_data['price'])
            
        except Exception as e:
            logger.error(f"Error handling ticker update for {pair}: {e}")
    
    async def _handle_order_book_update(self, pair: str, book_data: Dict):
        """Handle order book updates"""
        try:
            # Extract bids and asks
            bids = book_data.get('b', [])
            asks = book_data.get('a', [])
            
            # Store in database
            self.db.update_order_book(pair, bids, asks)
            
        except Exception as e:
            logger.error(f"Error handling order book update for {pair}: {e}")
    
    async def _check_trading_signals(self, pair: str, ticker_data: Dict):
        """Check for buy/sell signals and execute trades"""
        try:
            # Extra guard
            if not self.is_running:
                return
            portfolio = self.db.get_portfolio_summary()
            available_balance = portfolio.get('available_balance', 0)
            
            # Check if we have enough balance for a trade
            if available_balance < (self.trade_amount + (self.trade_amount * self.maker_fee)):
                return
            
            # Generate buy signal based on selected strategy
            if self._should_buy(pair):
                await self._execute_buy_trade(pair, ticker_data['price'])
            
        except Exception as e:
            logger.error(f"Error checking trading signals for {pair}: {e}")
    
    async def _execute_buy_trade(self, pair: str, current_price: float):
        """Execute a buy trade"""
        try:
            quantity = self.trade_amount / current_price
            fees = self.trade_amount * self.maker_fee
            stop_loss_price = current_price * (1 - self.stop_loss)
            take_profit_price = current_price * (1 + self.profit_margin)
            
            trade_id = self.db.add_trade(
                symbol=pair,
                trade_type='BUY',
                quantity=quantity,
                entry_price=current_price,
                trade_amount=self.trade_amount,
                fees=fees,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price
            )
            
            if trade_id:
                logger.info(f"Executed BUY trade for {pair}: ${self.trade_amount} at ${current_price:.4f}")
                logger.info(f"Stop Loss: ${stop_loss_price:.4f}, Take Profit: ${take_profit_price:.4f}")
            
        except Exception as e:
            logger.error(f"Error executing buy trade for {pair}: {e}")
    
    async def _monitor_open_trades(self, pair: str, current_price: float):
        """Monitor open trades for stop loss and take profit conditions"""
        try:
            # Extra guard
            if not self.is_running:
                return
            open_trades = self.db.get_open_trades()
            
            for trade in open_trades:
                if trade['symbol'] != pair:
                    continue
                
                trade_id = trade['id']
                entry_price = trade['entry_price']
                stop_loss_price = trade['stop_loss_price']
                take_profit_price = trade['take_profit_price']
                trade_type = trade['trade_type']
                
                should_close = False
                close_reason = ""
                
                if trade_type == 'BUY':
                    # Check take profit
                    if current_price >= take_profit_price:
                        should_close = True
                        close_reason = "Take Profit"
                    # Check stop loss
                    elif current_price <= stop_loss_price:
                        should_close = True
                        close_reason = "Stop Loss"
                
                if should_close:
                    success = self.db.close_trade(trade_id, current_price)
                    if success:
                        profit_loss = (current_price - entry_price) * trade['quantity'] - trade['fees']
                        logger.info(f"Closed {trade_type} trade for {pair} - {close_reason}")
                        logger.info(f"Entry: ${entry_price:.4f}, Exit: ${current_price:.4f}, P&L: ${profit_loss:.2f}")
            
        except Exception as e:
            logger.error(f"Error monitoring open trades for {pair}: {e}")
    
    async def start_trading(self):
        """Start the trading bot"""
        self.is_running = True
        logger.info("Paper trading bot started")
        
        # Keep the bot running
        while self.is_running:
            try:
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(5)
    
    def stop_trading(self):
        """Stop the trading bot"""
        self.is_running = False
        logger.info("Paper trading bot stopped")

    def configure_strategy(self, name: str, params: Dict):
        """Configure the strategy and parameters to use when trading"""
        self.strategy_name = name
        self.strategy_params = params or {}
        logger.info(f"Configured strategy: {name} params={params}")

    def _should_buy(self, symbol: str) -> bool:
        """Strategy router for buy decisions"""
        if not self.strategy_name:
            # If no strategy selected, never trade
            return False
        strat = self.strategy_name.upper()
        if strat == 'SMA_CROSSOVER':
            # Use PriceAnalyzer basic SMA-like logic as a placeholder
            return self.price_analyzer.generate_buy_signal(symbol)
        elif strat == 'BOLLINGER':
            # Placeholder: reuse analyzer; real impl would use bands
            return self.price_analyzer.generate_buy_signal(symbol)
        elif strat == 'RSI_MEAN_REVERSION':
            return self.price_analyzer.generate_buy_signal(symbol)
        elif strat == 'MACD_TREND':
            return self.price_analyzer.generate_buy_signal(symbol)
        elif strat == 'DONCHIAN_BREAKOUT':
            return self.price_analyzer.generate_buy_signal(symbol)
        # Default safe
        return False
    
    async def get_performance_stats(self) -> Dict:
        """Get trading performance statistics"""
        portfolio = self.db.get_portfolio_summary()
        open_trades = self.db.get_open_trades()
        trade_history = self.db.get_trade_history(50)
        
        # Calculate additional stats
        total_value = portfolio.get('total_balance', 100)
        available_balance = portfolio.get('available_balance', 100)
        invested_amount = total_value - available_balance
        
        return {
            'portfolio': portfolio,
            'open_trades_count': len(open_trades),
            'invested_amount': invested_amount,
            'recent_trades': trade_history[:10],
            'total_return_percentage': ((total_value - 100) / 100) * 100
        }
    
    async def close_all_positions(self):
        """Close all open positions at current market price"""
        try:
            open_trades = self.db.get_open_trades()
            
            for trade in open_trades:
                symbol = trade['symbol']
                current_price = self.db.get_latest_price(symbol)
                
                if current_price:
                    success = self.db.close_trade(trade['id'], current_price)
                    if success:
                        logger.info(f"Force closed trade {trade['id']} for {symbol} at ${current_price:.4f}")
            
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
