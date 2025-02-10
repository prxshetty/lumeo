"""Stock price querying tool."""

import yfinance as yf
from typing import Dict, Any
from utils.common import logger

query_stock_price_def = {
    "name": "query_stock_price",
    "description": "Query real-time stock price information for a given company or symbol.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The stock symbol or company name to query"
            }
        },
        "required": ["query"]
    }
}

async def query_stock_price_handler(query: str) -> Dict[str, Any]:
    """Handler function for stock price queries.
    
    Args:
        query: The stock symbol or company name to query
        
    Returns:
        Dict containing stock information or error message
    """
    try:
        logger.info(f"📈 Querying stock price for: {query}")
        
        # Extract stock symbol from query (simple extraction)
        symbol = query.upper().split()[0]
        
        # Get stock info
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # Format response
        response = {
            "symbol": symbol,
            "price": info.get("currentPrice", "N/A"),
            "currency": info.get("currency", "USD"),
            "company": info.get("longName", symbol),
            "change": info.get("regularMarketChangePercent", 0),
            "volume": info.get("volume", "N/A"),
            "market_cap": info.get("marketCap", "N/A")
        }
        
        logger.info(f"💡 Successfully retrieved stock info for {symbol}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error querying stock price: {str(e)}")
        return {"error": str(e)}

query_stock_price = (query_stock_price_def, query_stock_price_handler)
