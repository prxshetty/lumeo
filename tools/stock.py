"""Stock price querying tool."""

import yfinance as yf
from typing import Dict, Any
from utils.common import logger
import pandas as pd
import json

query_stock_price_def = {
    "name": "query_stock_price",
    "description": "Queries stock price information for a given symbol and time period.",
    "parameters": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "The stock symbol to query (e.g., 'AAPL' for Apple Inc.)"
            },
            "period": {
                "type": "string",
                "description": "Time period for data retrieval (e.g., '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max')"
            }
        },
        "required": ["symbol", "period"]
    }
}

async def query_stock_price_handler(symbol: str, period: str) -> Dict[str, Any]:
    """Queries stock price information for a given symbol and time period.
    
    Args:
        symbol: The stock symbol to query
        period: Time period for data retrieval
        
    Returns:
        Dict containing stock price data or error message
    """
    try:
        logger.info(f"📈 Fetching stock price for symbol: {symbol}, period: {period}")
        
        symbol = symbol.strip().upper()
        
        valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max']
        if period not in valid_periods:
            raise ValueError(f"Invalid period. Must be one of: {', '.join(valid_periods)}")
        
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        
        if hist.empty:
            logger.warning(f"⚠️ No data found for symbol: {symbol}")
            return {
                "error": f"No data found for symbol: {symbol}. Please check if the symbol is correct."
            }
            
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        prices = hist['Close'].tolist()
        
        info = stock.info
        
        response = {
            "symbol": symbol,
            "company": info.get("longName", symbol),
            "period": period,
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("marketCap", "N/A"),
            "data_points": len(dates),
            "dates": dates,
            "prices": [float(price) for price in prices],
            "current_price": float(prices[-1]),
            "price_change": float(prices[-1] - prices[0]),
            "price_change_percent": float((prices[-1] - prices[0]) / prices[0] * 100),
            "chart_data": {
                "x_data": ",".join(dates),
                "y_data": ",".join([str(float(price)) for price in prices]),
                "x_label": "Date",
                "y_label": f"Price ({info.get('currency', 'USD')})"
            }
        }
        
        logger.info(f"💸 Stock data retrieved successfully for symbol: {symbol}")
        return response
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error querying stock price for symbol: {symbol} - {error_msg}")
        return {
            "error": f"Failed to retrieve stock data: {error_msg}. Please check if the symbol and period are correct."
        }

query_stock_price = (query_stock_price_def, query_stock_price_handler)
