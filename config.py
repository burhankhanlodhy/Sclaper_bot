# Kraken Trading Bot Configuration

# Server Configuration
HOST = "127.0.0.1"  # Only allow local connections
PORT = 8080         # Non-public port

# Trading Configuration
TRADE_AMOUNT = 10.0      # Amount per trade in USD
MAKER_FEE = 0.0025       # 0.25% maker fee
PROFIT_MARGIN = 0.02     # 2% profit target
STOP_LOSS = 0.015        # 1.5% stop loss
STARTING_BALANCE = 100.0 # Starting balance in USD

# Database Configuration
DATABASE_PATH = "kraken_bot.db"

# Kraken API Configuration (Optional - for future private trading)
KRAKEN_API_KEY = ""
KRAKEN_API_SECRET = ""

# WebSocket Configuration
WS_RECONNECT_ATTEMPTS = 5
WS_RECONNECT_DELAY = 1000  # milliseconds

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
