import sqlite3

import sqlite3

try:
    conn = sqlite3.connect('kraken_bot.db')
    cursor = conn.cursor()
    
    # Check for BTC vs XBT
    cursor.execute('SELECT symbol FROM pairs WHERE symbol LIKE "%BTC%" OR symbol LIKE "%XBT%"')
    pairs_btc = cursor.fetchall()
    print('BTC/XBT pairs:')
    for row in pairs_btc:
        print(f'  {row[0]}')
    
    cursor.execute('SELECT DISTINCT symbol FROM price_data WHERE symbol LIKE "%BTC%" OR symbol LIKE "%XBT%"')
    price_btc = cursor.fetchall()
    print('\nBTC/XBT price data:')
    for row in price_btc:
        print(f'  {row[0]}')
    
    # Test format conversion
    def convert_symbol_format(symbol, to_price_data_format=True):
        # Special mappings
        special_mappings = {
            'XBTUSD': 'XBT/USD',  # Kraken uses XBT for Bitcoin
            'XBT/USD': 'XBTUSD'
        }
        
        if to_price_data_format:
            if symbol in special_mappings:
                return special_mappings[symbol]
            if '/' not in symbol and symbol.endswith('USD'):
                base = symbol[:-3]
                return f"{base}/USD"
        else:
            if symbol in special_mappings:
                return special_mappings[symbol]
            if '/' in symbol:
                return symbol.replace('/', '')
        return symbol
    
    # Test symbol conversion
    print('\nTesting symbol conversion:')
    test_symbols = ['XBTUSD', 'ETHUSD', 'AAVEUSD']
    for symbol in test_symbols:
        converted = convert_symbol_format(symbol)
        print(f'  {symbol} -> {converted}')
    
    conn.close()
    
except Exception as e:
    print(f'Error: {e}')
