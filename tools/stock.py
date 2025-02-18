"""Stock price querying tool."""

import yfinance as yf
from typing import Dict, Any
from utils.common import logger
import pandas as pd
import json
import chainlit as cl

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
    """Queries stock price information for a given symbol and time period."""
    try:
        logger.info(f"📈 Fetching stock price for symbol: {symbol}, period: {period}")
        
        symbol = symbol.strip().upper()
        
        valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max']
        if period not in valid_periods:
            raise ValueError(f"Invalid period. Must be one of: {', '.join(valid_periods)}")
        
        logger.info(f"🔍 Querying yfinance for {symbol}...")
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        
        if hist.empty:
            logger.warning(f"⚠️ No data found for symbol: {symbol}")
            return {
                "error": f"No data found for symbol: {symbol}. Please check if the symbol is correct."
            }
            
        logger.info(f"📊 Got {len(hist)} data points for {symbol}")
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        prices = hist['Close'].tolist()
        info = stock.info
        
        # Create optimized Plotly figure structure
        chart_data = {
            "data": [{
                "type": "scatter",
                "mode": "lines+markers",
                "x": dates,
                "y": [float(price) for price in prices],
                "line": {"simplify": True}  
            }],
            "layout": {
                "title": f"{symbol} Stock Prices - Last {period}",
                "showlegend": False,
                "margin": dict(t=40, b=60, l=40, r=20),
                "xaxis": {
                    "tickangle": -45,
                    "type": "date",
                    "tickformat": "%b %d",
                    "automargin": True
                },
                "yaxis": {
                    "automargin": True
                }
            }
        }
        
        json_data = json.dumps(chart_data, separators=(',', ':'))
        logger.info(f"📈 Generated chart data with {len(dates)} points")
        
        result = {
            "symbol": symbol,
            "company": info.get("longName", symbol),
            "period": period,
            "currency": info.get("currency", "USD"),
            "current_price": float(prices[-1]),
            "price_change": float(prices[-1] - prices[0]),
            "price_change_percent": float((prices[-1] - prices[0]) / prices[0] * 100),
            "chart_data": json_data
        }
        
        logger.info(f"💸 Successfully prepared stock data for {symbol}")
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error querying stock price: {error_msg}")
        return {"error": f"Failed to retrieve stock data: {error_msg}"}

query_stock_price = (query_stock_price_def, query_stock_price_handler)
