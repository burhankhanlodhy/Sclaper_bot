#!/usr/bin/env python3
"""
Test script for Kraken Paper Trading Bot
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from kraken_client import KrakenAPIClient

async def test_kraken_connection():
    """Test connection to Kraken API"""
    print("Testing Kraken API connection...")
    
    client = KrakenAPIClient()
    
    # Test getting USD pairs
    pairs = await client.get_usd_pairs()
    print(f"Found {len(pairs)} USD trading pairs")
    
    if pairs:
        print("Sample pairs:")
        for pair in pairs[:5]:
            print(f"  - {pair['symbol']} ({pair['base_currency']}/USD)")
    
    return len(pairs) > 0

def test_database():
    """Test database functionality"""
    print("\nTesting database functionality...")
    
    # Initialize database
    db = DatabaseManager("test_bot.db")
    
    # Test adding a pair
    success = db.add_pair("BTCUSD", "BTC", "USD")
    print(f"Added test pair: {success}")
    
    # Test portfolio
    portfolio = db.get_portfolio_summary()
    print(f"Initial portfolio: ${portfolio.get('total_balance', 0)}")
    
    # Clean up test database
    import os
    try:
        if os.path.exists("test_bot.db"):
            os.remove("test_bot.db")
    except PermissionError:
        print("Note: Test database file will be cleaned up automatically")
    
    return success

async def main():
    """Run all tests"""
    print("=== Kraken Paper Trading Bot Test ===\n")
    
    # Test database
    db_ok = test_database()
    
    # Test Kraken API
    kraken_ok = await test_kraken_connection()
    
    print(f"\n=== Test Results ===")
    print(f"Database: {'✓ OK' if db_ok else '✗ FAILED'}")
    print(f"Kraken API: {'✓ OK' if kraken_ok else '✗ FAILED'}")
    
    if db_ok and kraken_ok:
        print("\n🎉 All tests passed! The bot is ready to run.")
        print("Run 'start_bot.bat' to start the trading bot.")
    else:
        print("\n❌ Some tests failed. Please check your setup.")
    
    return db_ok and kraken_ok

if __name__ == "__main__":
    asyncio.run(main())
