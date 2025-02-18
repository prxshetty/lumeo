"""Plotly chart drawing tool."""

import chainlit as cl
import plotly
import json
from utils.common import logger
import asyncio
from tools.stock import query_stock_price_handler

draw_plotly_chart_def = {
    "name": "draw_plotly_chart",
    "description": "Draws stock chart. Auto-fetches data if needed. Provide either chart_data OR symbol+period.",
    "parameters": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Contextual message for the chart"
            },
            "plotly_json_fig": {
                "type": "string",
                "description": "Pre-generated chart data from query_stock_price"
            },
            "symbol": {
                "type": "string",
                "description": "Stock symbol to chart (e.g. NVDA)"
            },
            "period": {
                "type": "string",
                "description": "Time period for chart (e.g. '1mo')"
            }
        },
        "required": ["message"]  
    },
}

async def draw_plotly_chart_handler(message: str, plotly_json_fig: str = None, symbol: str = None, period: str = None):
    try:
        logger.info(f"🎨 Drawing Plotly chart with message: {message}")
        
        # Get parameters from different sources
        symbol = symbol or cl.user_session.get("last_symbol")
        period = period or cl.user_session.get("last_period")
        
        # If no chart data provided
        if not plotly_json_fig:
            logger.info("🔍 No chart data provided - attempting automatic fetch")
            
            if not symbol or not period:
                error_msg = "Need stock symbol and period to fetch data. Please specify like: 'Chart for NVDA last month'"
                logger.error(f"❌ {error_msg}")
                await cl.Message(content=error_msg).send()
                return {"error": error_msg}
            
            logger.info(f"📈 Auto-fetching data for {symbol} ({period})")
            stock_result = await query_stock_price_handler(symbol, period)
            
            if "error" in stock_result:
                return stock_result
            
            plotly_json_fig = stock_result.get("chart_data")
            if not plotly_json_fig:
                return {"error": "Failed to generate chart data"}
            
            cl.user_session.set("chart_data", plotly_json_fig)
            logger.info("✅ Auto-fetched and stored chart data")

        # Existing rendering logic
        fig = plotly.io.from_json(plotly_json_fig)
        await cl.Message(
            content=message,
            elements=[cl.Plotly(name="chart", figure=fig, display="inline")]
        ).send()
        
        return {"status": "success"}
    
    except Exception as e:
        error_msg = f"Chart error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        await cl.Message(content=error_msg).send()
        return {"error": error_msg}

draw_plotly_chart = (draw_plotly_chart_def, draw_plotly_chart_handler)
