# Kraken Paper Trading Bot

A sophisticated Python-based web scraper bot with a modern UI that connects to Kraken Pro API for real-time price tickers, order book depth, and paper trading simulation.

## Features

- **Real-time Data**: Connects to Kraken WebSocket API for live price feeds
- **Paper Trading**: Simulates trading with configurable parameters
- **Modern Web UI**: Bootstrap-based responsive dashboard
- **SQLite Database**: Stores all trading data, price history, and analytics
- **Risk Management**: Built-in stop-loss and take-profit mechanisms
- **USD Pairs Focus**: Automatically fetches and trades all USD trading pairs
- **Real-time Updates**: WebSocket-powered live dashboard updates

## Trading Configuration

- **Starting Balance**: $100
- **Trade Amount**: $10 per trade
- **Maker Fee**: 0.25%
- **Profit Target**: 2%
- **Stop Loss**: 1.5%
- **Port**: 8080 (non-public port)

## Installation

1. Ensure you have Python 3.8+ installed
2. Run `install.bat` to install dependencies
3. Run `start_bot.bat` to start the bot

## Usage

1. Start the bot using `start_bot.bat`
2. Open your browser to `http://localhost:8080`
3. Monitor real-time trading activity on the dashboard
4. Use the controls to start/stop trading or close positions

## Dashboard Features

- **Portfolio Overview**: Real-time balance, P&L, and performance metrics
- **Trading Statistics**: Win rate, total trades, and current positions
- **Open Positions**: Live monitoring of active trades
- **Trade History**: Complete history of all executed trades
- **Real-time Updates**: Automatic refresh of all data

## Database Schema

The bot uses SQLite with the following tables:
- `pairs`: Trading pair information
- `price_data`: Real-time price history
- `trades`: All trade records
- `portfolio`: Portfolio summary and statistics
- `order_book`: Order book depth data

## Files Structure

```
Sclaper_bot/
├── main.py              # FastAPI web server
├── database.py          # Database management
├── kraken_client.py     # Kraken API client
├── trading_bot.py       # Trading logic
├── config.py            # Configuration settings
├── requirements.txt     # Python dependencies
├── templates/           # HTML templates
│   └── dashboard.html   # Main dashboard
├── static/              # Static files
│   ├── style.css        # Custom CSS
│   └── app.js           # JavaScript client
├── install.bat          # Installation script
└── start_bot.bat        # Startup script
```

## API Endpoints

- `GET /` - Main dashboard
- `GET /api/portfolio` - Portfolio summary
- `GET /api/trades` - Trade history
- `GET /api/open-trades` - Open positions
- `GET /api/pairs` - Trading pairs
- `GET /api/performance` - Performance statistics
- `POST /api/toggle-trading` - Start/stop trading
- `POST /api/close-all-positions` - Close all positions
- `WS /ws` - WebSocket for real-time updates

## Safety Features

- Local-only access (127.0.0.1)
- Paper trading only (no real money)
- Built-in risk management
- Position size limits
- Stop-loss protection

## Notes

- This is a paper trading bot - no real money is involved
- Requires active internet connection for Kraken API access
- All data is stored locally in SQLite database
- Bot runs on port 8080 to avoid conflicts with common services
