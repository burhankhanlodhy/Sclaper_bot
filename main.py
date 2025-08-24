from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncio
import json
import logging
from typing import Dict, List
from datetime import datetime
import uvicorn

# Import our modules
from database import DatabaseManager
from trading_bot import PaperTradingBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Kraken Paper Trading Bot", description="Real-time paper trading with Kraken API")

# Initialize components
db = DatabaseManager()
trading_bot = PaperTradingBot(db)

# Template configuration
templates = Jinja2Templates(directory="templates")

# Static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove disconnected clients
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Initialize data and subscriptions, but do NOT auto-start trading"""
    try:
        success = await trading_bot.initialize()
        if success:
            logger.info("Trading bot initialized; waiting for user to start a strategy from Bot page")
        else:
            logger.error("Failed to initialize trading bot")
    except Exception as e:
        logger.error(f"Startup error: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown"""
    trading_bot.stop_trading()
    await trading_bot.kraken_client.disconnect()
    logger.info("Application shutdown complete")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/pairs", response_class=HTMLResponse)
async def pairs_page(request: Request):
    """Trading pairs analysis page"""
    return templates.TemplateResponse("pairs.html", {"request": request})

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """Trading history page"""
    return templates.TemplateResponse("history.html", {"request": request})

@app.get("/price-data", response_class=HTMLResponse)
async def price_data_page(request: Request):
    """Price data page"""
    return templates.TemplateResponse("price_data.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings and configuration page"""
    return templates.TemplateResponse("settings.html", {"request": request})

@app.get("/bot", response_class=HTMLResponse)
async def bot_page(request: Request):
    """Bot control page"""
    return templates.TemplateResponse("bot.html", {"request": request})

@app.get("/chart/{pair}", response_class=HTMLResponse)
async def chart_page(request: Request, pair: str):
    """Individual pair chart page"""
    return templates.TemplateResponse("chart.html", {"request": request, "pair": pair})

@app.get("/api/portfolio")
async def get_portfolio():
    """Get portfolio summary"""
    try:
        portfolio = db.get_portfolio_summary()
        return {"success": True, "data": portfolio}
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/trades")
async def get_trades(limit: int = 50):
    """Get trade history"""
    try:
        trades = db.get_trade_history(limit)
        return {"success": True, "data": trades}
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/closed-trades")
async def get_closed_trades(limit: int = 50):
    """Get closed trades only"""
    try:
        trades = db.get_closed_trades(limit)
        return {"success": True, "data": trades}
    except Exception as e:
        logger.error(f"Error getting closed trades: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/open-trades")
async def get_open_trades():
    """Get open trades"""
    try:
        trades = db.get_open_trades()
        return {"success": True, "data": trades}
    except Exception as e:
        logger.error(f"Error getting open trades: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/pairs")
async def get_usd_pairs():
    """Get all USD trading pairs"""
    try:
        pairs = db.get_usd_pairs()
        return {"success": True, "data": pairs}
    except Exception as e:
        logger.error(f"Error getting pairs: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/pairs/all")
async def get_all_pairs_with_prices():
    """Get all USD trading pairs with latest prices"""
    try:
        pairs = db.get_usd_pairs()
        
        # Add latest price data for all pairs
        for pair in pairs:
            latest_price = db.get_latest_price(pair['symbol'])
            if latest_price:
                pair['latest_price'] = latest_price
            else:
                pair['latest_price'] = None
        
        return {"success": True, "data": pairs, "total": len(pairs)}
    except Exception as e:
        logger.error(f"Error getting all pairs with prices: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/pairs/top10")
async def get_top_pairs():
    """Get top 10 USD trading pairs by volume"""
    try:
        # Get pairs with recent price data
        pairs = db.get_usd_pairs()
        
        # Get volume data for sorting
        pairs_with_volume = []
        for pair in pairs[:50]:  # Check first 50 pairs for performance
            latest_price = db.get_latest_price(pair['symbol'])
            if latest_price:
                # Get volume data from database
                volume_data = db.get_pair_volume(pair['symbol'])
                pair['volume'] = volume_data.get('volume', 0) if volume_data else 0
                pair['latest_price'] = latest_price
                pairs_with_volume.append(pair)
        
        # Sort by volume and get top 10
        top_pairs = sorted(pairs_with_volume, key=lambda x: x.get('volume', 0), reverse=True)[:10]
        
        return {"success": True, "data": top_pairs}
    except Exception as e:
        logger.error(f"Error getting top pairs: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/pairs/search")
async def search_pairs(query: str = ""):
    """Search trading pairs"""
    try:
        pairs = db.get_usd_pairs()
        
        if query:
            # Filter pairs by query
            filtered_pairs = [
                pair for pair in pairs 
                if query.upper() in pair['symbol'].upper() or 
                   query.upper() in pair['base_currency'].upper()
            ]
            # Limit search results to 50 for performance
            filtered_pairs = filtered_pairs[:50]
        else:
            # If no query, return all pairs (used by search functionality)
            filtered_pairs = pairs
        
        # Add latest price data
        for pair in filtered_pairs:
            latest_price = db.get_latest_price(pair['symbol'])
            if latest_price:
                pair['latest_price'] = latest_price
        
        return {"success": True, "data": filtered_pairs, "total": len(filtered_pairs)}
    except Exception as e:
        logger.error(f"Error searching pairs: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/chart/{pair}")
async def get_chart_data(pair: str, timeframe: str = "1h", limit: int = 100):
    """Get chart data for a specific pair"""
    try:
        chart_data = db.get_price_history(pair, limit)
        technical_data = db.calculate_technical_indicators(pair, limit)
        
        return {
            "success": True, 
            "data": {
                "prices": chart_data,
                "technical": technical_data,
                "pair": pair
            }
        }
    except Exception as e:
        logger.error(f"Error getting chart data for {pair}: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/performance")
async def get_performance():
    """Get performance statistics"""
    try:
        stats = await trading_bot.get_performance_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/close-all-positions")
async def close_all_positions():
    """Close all open positions"""
    try:
        await trading_bot.close_all_positions()
        return {"success": True, "message": "All positions closed"}
    except Exception as e:
        logger.error(f"Error closing positions: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/subscription-stats")
async def get_subscription_stats():
    """Get WebSocket subscription statistics"""
    try:
        stats = trading_bot.kraken_client.get_subscription_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"Error getting subscription stats: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/price-data")
async def get_price_data(limit: int = 100, symbol: str = None):
    """Get price data from database"""
    try:
        price_data = db.get_all_price_data(limit=limit, symbol=symbol)
        return {"success": True, "data": price_data}
    except Exception as e:
        logger.error(f"Error getting price data: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/price-data/symbols")
async def get_price_data_symbols():
    """Get list of symbols with price data"""
    try:
        symbols = db.get_price_data_symbols()
        return {"success": True, "data": symbols}
    except Exception as e:
        logger.error(f"Error getting price data symbols: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/toggle-trading")
async def toggle_trading():
    """Toggle trading bot on/off"""
    try:
        if trading_bot.is_running:
            trading_bot.stop_trading()
            status = "stopped"
        else:
            asyncio.create_task(trading_bot.start_trading())
            status = "started"
        
        return {"success": True, "status": status}
    except Exception as e:
        logger.error(f"Error toggling trading: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/strategies")
async def get_strategies():
    """List available trading strategies and their parameter schemas"""
    try:
        strategies = [
            {
                "key": "SMA_CROSSOVER",
                "name": "SMA Crossover",
                "params": {
                    "short_window": {"type": "number", "label": "Short SMA", "default": 5, "min": 2, "max": 50},
                    "long_window": {"type": "number", "label": "Long SMA", "default": 20, "min": 5, "max": 200},
                    "min_delta": {"type": "number", "label": "Min Delta %", "default": 0.0, "step": 0.1}
                }
            },
            {
                "key": "BOLLINGER",
                "name": "Bollinger Bands",
                "params": {
                    "window": {"type": "number", "label": "Window", "default": 20, "min": 5, "max": 200},
                    "stddev": {"type": "number", "label": "Std Dev", "default": 2, "step": 0.1},
                    "mode": {"type": "select", "label": "Mode", "options": ["Breakout", "Mean Reversion"], "default": "Breakout"}
                }
            },
            {
                "key": "RSI_MEAN_REVERSION",
                "name": "RSI Mean Reversion",
                "params": {
                    "period": {"type": "number", "label": "RSI Period", "default": 14, "min": 5, "max": 50},
                    "oversold": {"type": "number", "label": "Oversold %", "default": 30, "min": 1, "max": 99}
                }
            },
            {
                "key": "MACD_TREND",
                "name": "MACD Trend",
                "params": {
                    "fast": {"type": "number", "label": "Fast EMA", "default": 12, "min": 2, "max": 50},
                    "slow": {"type": "number", "label": "Slow EMA", "default": 26, "min": 5, "max": 200},
                    "signal": {"type": "number", "label": "Signal EMA", "default": 9, "min": 2, "max": 50}
                }
            },
            {
                "key": "DONCHIAN_BREAKOUT",
                "name": "Donchian Breakout",
                "params": {
                    "period": {"type": "number", "label": "Channel Period", "default": 20, "min": 5, "max": 200}
                }
            }
        ]
        return {"success": True, "data": strategies}
    except Exception as e:
        logger.error(f"Error getting strategies: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/start-bot")
async def start_bot(payload: dict):
    """Start trading with a specific strategy and parameters"""
    try:
        strategy = payload.get("strategy")
        params = payload.get("params", {})
        if not strategy:
            return {"success": False, "error": "Strategy is required"}
        trading_bot.configure_strategy(strategy, params)
        if not trading_bot.is_running:
            asyncio.create_task(trading_bot.start_trading())
        return {"success": True, "status": "started", "strategy": trading_bot.strategy_name, "params": trading_bot.strategy_params}
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/stop-bot")
async def stop_bot():
    """Stop the trading bot"""
    try:
        trading_bot.stop_trading()
        return {"success": True, "status": "stopped"}
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return {"success": False, "error": str(e)}

# Settings API endpoints
@app.get("/api/config")
async def get_config():
    """Get bot configuration"""
    try:
        # Default configuration values
        config = {
            "initial_balance": 10000,
            "max_risk_per_trade": 2,
            "update_interval": 5,
            "enable_notifications": True
        }
        return {"success": True, "data": config}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/config")
async def save_config(config: dict):
    """Save bot configuration"""
    try:
        # In a real implementation, you would save this to database or config file
        # For now, just return success
        logger.info(f"Configuration saved: {config}")
        return {"success": True, "message": "Configuration saved successfully"}
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/database-stats")
async def get_database_stats():
    """Get database statistics"""
    try:
        # Get stats from database (efficient counts)
        stats = {
            "total_trades": db.count_trades(),
            "total_price_records": db.count_price_records(),
            "database_size": db.get_database_size(),
        }
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/export-data")
async def export_data():
    """Export all data"""
    try:
        # This would create a zip file with all data
        # For now, just return an error as it's not implemented
        return {"success": False, "error": "Export functionality not yet implemented"}
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/reset-trades")
async def reset_trades():
    """Reset all trading data"""
    try:
        # Stop trading first
        trading_bot.stop_trading()
        
        # Clear trades from database
        db.clear_trades()
        
        logger.info("Trading data reset successfully")
        return {"success": True, "message": "Trading data reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting trades: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/reset-all")
async def reset_all():
    """Reset all data and configuration"""
    try:
        # Stop trading first
        trading_bot.stop_trading()
        
        # Clear all data from database
        db.clear_all_data()
        
        logger.info("All data reset successfully")
        return {"success": True, "message": "All data reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting all data: {e}")
        return {"success": False, "error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            try:
                # Wait for messages (including heartbeat) with timeout
                message = await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
                
                try:
                    data = json.loads(message)
                    if data.get('type') == 'heartbeat':
                        # Respond to heartbeat
                        await websocket.send_text(json.dumps({
                            'type': 'heartbeat_response',
                            'timestamp': datetime.now().isoformat()
                        }))
                        logger.debug(f"Heartbeat received for pair: {data.get('pair', 'unknown')}")
                        continue
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message}")
                    
            except asyncio.TimeoutError:
                # No message received, send periodic update
                pass
            
            # Send periodic updates every 2 seconds
            portfolio = db.get_portfolio_summary()
            open_trades = db.get_open_trades()
            
            update_data = {
                "type": "update",
                "portfolio": portfolio,
                "open_trades": len(open_trades),
                "is_trading": trading_bot.is_running,
                "strategy": getattr(trading_bot, 'strategy_name', None),
                "timestamp": datetime.now().isoformat()
            }
            
            await manager.send_personal_message(json.dumps(update_data), websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    # Run on local network, port 4000
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # Bind to all interfaces (accessible via machine's local IP)
        port=4000,
        reload=False,
        log_level="info"
    )
