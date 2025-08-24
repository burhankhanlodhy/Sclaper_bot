import sqlite3
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "kraken_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create pairs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS pairs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT UNIQUE NOT NULL,
                        base_currency TEXT NOT NULL,
                        quote_currency TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create price_data table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS price_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        price REAL NOT NULL,
                        bid REAL,
                        ask REAL,
                        volume REAL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (symbol) REFERENCES pairs (symbol)
                    )
                ''')
                
                # Create trades table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        trade_type TEXT NOT NULL, -- 'BUY' or 'SELL'
                        quantity REAL NOT NULL,
                        entry_price REAL NOT NULL,
                        exit_price REAL,
                        trade_amount REAL NOT NULL,
                        fees REAL NOT NULL,
                        profit_loss REAL DEFAULT 0,
                        status TEXT DEFAULT 'OPEN', -- 'OPEN', 'CLOSED', 'STOPPED'
                        stop_loss_price REAL,
                        take_profit_price REAL,
                        entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        exit_time TIMESTAMP,
                        FOREIGN KEY (symbol) REFERENCES pairs (symbol)
                    )
                ''')
                
                # Create portfolio table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS portfolio (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        total_balance REAL DEFAULT 100.0,
                        available_balance REAL DEFAULT 100.0,
                        total_trades INTEGER DEFAULT 0,
                        winning_trades INTEGER DEFAULT 0,
                        losing_trades INTEGER DEFAULT 0,
                        total_profit_loss REAL DEFAULT 0.0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Insert initial portfolio record if not exists
                cursor.execute('SELECT COUNT(*) FROM portfolio')
                if cursor.fetchone()[0] == 0:
                    cursor.execute('''
                        INSERT INTO portfolio (total_balance, available_balance)
                        VALUES (100.0, 100.0)
                    ''')
                
                # Create order_book table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS order_book (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        bids TEXT, -- JSON string of bid data
                        asks TEXT, -- JSON string of ask data
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (symbol) REFERENCES pairs (symbol)
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def _convert_symbol_format(self, symbol: str, to_price_data_format: bool = True) -> str:
        """Convert between symbol formats: BTCUSD <-> BTC/USD"""
        # Special mappings for Kraken symbols
        special_mappings = {
            'XXBTZUSD': 'XBT/USD',  # Kraken's special Bitcoin format
            'XBT/USD': 'XXBTZUSD',
            'XBTUSD': 'XBT/USD',    # Alternative Bitcoin format
            'XXETHZUSD': 'ETH/USD', # Kraken's special Ethereum format
            'ETH/USD': 'XXETHZUSD'
        }
        
        if to_price_data_format:
            # Convert from pairs format to price_data format
            if symbol in special_mappings:
                return special_mappings[symbol]
            if '/' not in symbol and symbol.endswith('USD'):
                base = symbol[:-3]  # Remove 'USD'
                return f"{base}/USD"
            return symbol
        else:
            # Convert from price_data format to pairs format
            if symbol in special_mappings:
                return special_mappings[symbol]
            if '/' in symbol:
                return symbol.replace('/', '')
            return symbol
    
    def add_pair(self, symbol: str, base_currency: str, quote_currency: str) -> bool:
        """Add a new trading pair to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO pairs (symbol, base_currency, quote_currency)
                    VALUES (?, ?, ?)
                ''', (symbol, base_currency, quote_currency))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error adding pair {symbol}: {e}")
            return False
    
    def update_price_data(self, symbol: str, price: float, bid: float = None, ask: float = None, volume: float = None):
        """Update price data for a symbol"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO price_data (symbol, price, bid, ask, volume)
                    VALUES (?, ?, ?, ?, ?)
                ''', (symbol, price, bid, ask, volume))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error updating price data for {symbol}: {e}")
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get the latest price for a symbol"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Try with the symbol as-is first
                cursor.execute('''
                    SELECT price FROM price_data 
                    WHERE symbol = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''', (symbol,))
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                
                # If not found, try converting the format
                converted_symbol = self._convert_symbol_format(symbol, to_price_data_format=True)
                if converted_symbol != symbol:
                    cursor.execute('''
                        SELECT price FROM price_data 
                        WHERE symbol = ? 
                        ORDER BY timestamp DESC 
                        LIMIT 1
                    ''', (converted_symbol,))
                    result = cursor.fetchone()
                    return result[0] if result else None
                
                return None
        except sqlite3.Error as e:
            logger.error(f"Error getting latest price for {symbol}: {e}")
            return None
    
    def add_trade(self, symbol: str, trade_type: str, quantity: float, entry_price: float, 
                  trade_amount: float, fees: float, stop_loss_price: float, take_profit_price: float) -> int:
        """Add a new trade to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trades (symbol, trade_type, quantity, entry_price, trade_amount, 
                                      fees, stop_loss_price, take_profit_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (symbol, trade_type, quantity, entry_price, trade_amount, fees, stop_loss_price, take_profit_price))
                trade_id = cursor.lastrowid
                
                # Update portfolio available balance
                cursor.execute('''
                    UPDATE portfolio 
                    SET available_balance = available_balance - ?, 
                        total_trades = total_trades + 1,
                        last_updated = CURRENT_TIMESTAMP
                ''', (trade_amount + fees,))
                
                conn.commit()
                return trade_id
        except sqlite3.Error as e:
            logger.error(f"Error adding trade: {e}")
            return None
    
    def close_trade(self, trade_id: int, exit_price: float, exit_time: datetime = None) -> bool:
        """Close an open trade"""
        try:
            if exit_time is None:
                exit_time = datetime.now(timezone.utc)
                
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get trade details
                cursor.execute('''
                    SELECT trade_type, quantity, entry_price, trade_amount, fees
                    FROM trades WHERE id = ? AND status = 'OPEN'
                ''', (trade_id,))
                
                trade = cursor.fetchone()
                if not trade:
                    return False
                
                trade_type, quantity, entry_price, trade_amount, fees = trade
                
                # Calculate profit/loss
                if trade_type == 'BUY':
                    profit_loss = (exit_price - entry_price) * quantity - fees
                else:  # SELL
                    profit_loss = (entry_price - exit_price) * quantity - fees
                
                # Update trade
                cursor.execute('''
                    UPDATE trades 
                    SET exit_price = ?, profit_loss = ?, status = 'CLOSED', exit_time = ?
                    WHERE id = ?
                ''', (exit_price, profit_loss, exit_time, trade_id))
                
                # Update portfolio
                total_return = trade_amount + profit_loss
                cursor.execute('''
                    UPDATE portfolio 
                    SET available_balance = available_balance + ?,
                        total_profit_loss = total_profit_loss + ?,
                        total_balance = total_balance + ?,
                        winning_trades = winning_trades + ?,
                        losing_trades = losing_trades + ?,
                        last_updated = CURRENT_TIMESTAMP
                ''', (total_return, profit_loss, profit_loss, 1 if profit_loss > 0 else 0, 1 if profit_loss <= 0 else 0))
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error closing trade {trade_id}: {e}")
            return False
    
    def get_open_trades(self) -> List[Dict]:
        """Get all open trades"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, symbol, trade_type, quantity, entry_price, trade_amount, 
                           fees, stop_loss_price, take_profit_price, entry_time
                    FROM trades 
                    WHERE status = 'OPEN'
                    ORDER BY entry_time DESC
                ''')
                
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting open trades: {e}")
            return []
    
    def get_trade_history(self, limit: int = 100) -> List[Dict]:
        """Get trade history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM trades 
                    ORDER BY entry_time DESC 
                    LIMIT ?
                ''', (limit,))
                
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting trade history: {e}")
            return []

    def get_all_trades(self) -> List[Dict]:
        """Get all trades without limit (used for stats/exports)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM trades 
                    ORDER BY entry_time DESC
                ''')
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting all trades: {e}")
            return []

    def count_trades(self) -> int:
        """Return total number of trades."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM trades')
                return int(cursor.fetchone()[0])
        except sqlite3.Error as e:
            logger.error(f"Error counting trades: {e}")
            return 0
    
    def get_closed_trades(self, limit: int = 100) -> List[Dict]:
        """Get closed trades only"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM trades 
                    WHERE status IN ('CLOSED', 'STOPPED')
                    ORDER BY exit_time DESC 
                    LIMIT ?
                ''', (limit,))
                
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting closed trades: {e}")
            return []
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM portfolio ORDER BY last_updated DESC LIMIT 1')
                
                result = cursor.fetchone()
                if result:
                    columns = [description[0] for description in cursor.description]
                    portfolio = dict(zip(columns, result))
                    
                    # Calculate win rate
                    total_trades = portfolio.get('total_trades', 0)
                    winning_trades = portfolio.get('winning_trades', 0)
                    portfolio['win_rate'] = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                    
                    # Get additional statistics
                    cursor.execute('SELECT COUNT(*) FROM trades WHERE status = "OPEN"')
                    open_trades_count = cursor.fetchone()[0]
                    
                    cursor.execute('SELECT COUNT(*) FROM trades WHERE status = "CLOSED"')
                    closed_trades_count = cursor.fetchone()[0]
                    
                    cursor.execute('SELECT COUNT(*) FROM trades WHERE status = "STOPPED"')
                    stopped_trades_count = cursor.fetchone()[0]
                    
                    # Calculate total equity (available balance + value of open positions)
                    cursor.execute('''
                        SELECT SUM(quantity * entry_price) 
                        FROM trades 
                        WHERE status = "OPEN"
                    ''')
                    open_positions_value = cursor.fetchone()[0] or 0
                    
                    total_equity = portfolio.get('available_balance', 100) + open_positions_value
                    
                    portfolio['open_trades_count'] = open_trades_count
                    portfolio['closed_trades_count'] = closed_trades_count + stopped_trades_count
                    portfolio['total_equity'] = total_equity
                    
                    return portfolio
                return {}
                
        except sqlite3.Error as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {}
    
    def get_usd_pairs(self) -> List[Dict]:
        """Get all USD trading pairs"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM pairs 
                    WHERE quote_currency = 'USD' AND is_active = 1
                    ORDER BY symbol
                ''')
                
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting USD pairs: {e}")
            return []
    
    def update_order_book(self, symbol: str, bids: List, asks: List):
        """Update order book data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO order_book (symbol, bids, asks)
                    VALUES (?, ?, ?)
                ''', (symbol, json.dumps(bids), json.dumps(asks)))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error updating order book for {symbol}: {e}")

    def get_pair_volume(self, symbol: str) -> Optional[Dict]:
        """Get volume data for a pair"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT AVG(volume) as avg_volume, MAX(volume) as max_volume
                    FROM price_data 
                    WHERE symbol = ? AND volume IS NOT NULL
                    AND timestamp > datetime('now', '-24 hours')
                ''', (symbol,))
                result = cursor.fetchone()
                if result and result[0]:
                    return {
                        'volume': result[0],
                        'max_volume': result[1]
                    }
                return {'volume': 0, 'max_volume': 0}
        except sqlite3.Error as e:
            logger.error(f"Error getting volume for {symbol}: {e}")
            return {'volume': 0, 'max_volume': 0}
    
    def get_price_history(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get price history for a symbol"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Try with the symbol as-is first
                cursor.execute('''
                    SELECT price, bid, ask, volume, timestamp
                    FROM price_data 
                    WHERE symbol = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (symbol, limit))
                
                results = cursor.fetchall()
                
                # If no results, try converting the format
                if not results:
                    converted_symbol = self._convert_symbol_format(symbol, to_price_data_format=True)
                    if converted_symbol != symbol:
                        cursor.execute('''
                            SELECT price, bid, ask, volume, timestamp
                            FROM price_data 
                            WHERE symbol = ?
                            ORDER BY timestamp DESC 
                            LIMIT ?
                        ''', (converted_symbol, limit))
                        results = cursor.fetchall()
                
                price_data = []
                for row in results:
                    price_data.append({
                        'price': row[0],
                        'bid': row[1],
                        'ask': row[2],
                        'volume': row[3],
                        'timestamp': row[4]
                    })
                
                # Reverse to get chronological order
                return price_data[::-1]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting price history for {symbol}: {e}")
            return []
    
    def calculate_technical_indicators(self, symbol: str, limit: int = 100) -> Dict:
        """Calculate technical indicators for a symbol"""
        try:
            price_history = self.get_price_history(symbol, limit)
            
            if len(price_history) < 20:
                return {}
            
            prices = [float(data['price']) for data in price_history]
            
            # Simple Moving Averages
            sma_5 = self._calculate_sma(prices, 5)
            sma_20 = self._calculate_sma(prices, 20)
            
            # Bollinger Bands
            bollinger = self._calculate_bollinger_bands(prices, 20)
            
            return {
                'sma_5': sma_5,
                'sma_20': sma_20,
                'bollinger_upper': bollinger['upper'],
                'bollinger_lower': bollinger['lower'],
                'bollinger_middle': bollinger['middle'],
                'timestamps': [data['timestamp'] for data in price_history]
            }
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators for {symbol}: {e}")
            return {}
    
    def _calculate_sma(self, prices: List[float], period: int) -> List[float]:
        """Calculate Simple Moving Average"""
        sma = []
        for i in range(len(prices)):
            if i < period - 1:
                sma.append(None)
            else:
                avg = sum(prices[i-period+1:i+1]) / period
                sma.append(avg)
        return sma
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2) -> Dict:
        """Calculate Bollinger Bands"""
        import statistics
        import math
        
        upper = []
        lower = []
        middle = []
        
        for i in range(len(prices)):
            if i < period - 1:
                upper.append(None)
                lower.append(None)
                middle.append(None)
            else:
                window = prices[i-period+1:i+1]
                sma = sum(window) / period
                variance = sum((x - sma) ** 2 for x in window) / period
                std = math.sqrt(variance)
                
                middle.append(sma)
                upper.append(sma + (std_dev * std))
                lower.append(sma - (std_dev * std))
        
        return {
            'upper': upper,
            'lower': lower,
            'middle': middle
        }
    
    def get_all_price_data(self, limit: int = 100, symbol: str = None) -> List[Dict]:
        """Get price data from database with optional filtering"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if symbol:
                    cursor.execute('''
                        SELECT id, symbol, price, bid, ask, volume, timestamp
                        FROM price_data 
                        WHERE symbol = ?
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (symbol, limit))
                else:
                    cursor.execute('''
                        SELECT id, symbol, price, bid, ask, volume, timestamp
                        FROM price_data 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (limit,))
                
                results = cursor.fetchall()
                price_data = []
                for row in results:
                    price_data.append({
                        'id': row[0],
                        'symbol': row[1],
                        'price': row[2],
                        'bid': row[3],
                        'ask': row[4],
                        'volume': row[5],
                        'timestamp': row[6]
                    })
                
                return price_data
        except sqlite3.Error as e:
            logger.error(f"Error getting price data: {e}")
            return []

    def count_price_records(self) -> int:
        """Return total number of price_data records."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM price_data')
                return int(cursor.fetchone()[0])
        except sqlite3.Error as e:
            logger.error(f"Error counting price records: {e}")
            return 0
    
    def get_price_data_symbols(self) -> List[str]:
        """Get list of symbols that have price data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT symbol 
                    FROM price_data 
                    ORDER BY symbol
                ''')
                results = cursor.fetchall()
                return [row[0] for row in results]
        except sqlite3.Error as e:
            logger.error(f"Error getting price data symbols: {e}")
            return []

    def clear_trades(self):
        """Clear all trading data and reset portfolio stats counters."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM trades')
                # Reset portfolio counters
                cursor.execute('''
                    UPDATE portfolio
                    SET total_trades = 0,
                        winning_trades = 0,
                        losing_trades = 0,
                        total_profit_loss = 0,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = (SELECT id FROM portfolio ORDER BY last_updated DESC LIMIT 1)
                ''')
                conn.commit()
                logger.info("All trading data cleared successfully")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error clearing trades: {e}")
            return False

    def clear_all_data(self):
        """Clear all data from database and reset portfolio to defaults."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM trades')
                cursor.execute('DELETE FROM price_data')
                # Reset portfolio to defaults (keep single row, reset balances to 100)
                cursor.execute('''
                    UPDATE portfolio
                    SET total_balance = 100.0,
                        available_balance = 100.0,
                        total_trades = 0,
                        winning_trades = 0,
                        losing_trades = 0,
                        total_profit_loss = 0.0,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = (SELECT id FROM portfolio ORDER BY last_updated DESC LIMIT 1)
                ''')
                conn.commit()
                logger.info("All data cleared successfully")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error clearing all data: {e}")
            return False

    def get_database_size(self) -> int:
        """Return the size of the SQLite DB file in bytes."""
        try:
            return os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        except Exception as e:
            logger.error(f"Error getting database size: {e}")
            return 0
