"""Plotly chart drawing tool."""

import chainlit as cl
import plotly
import json
from utils.common import logger
import asyncio

draw_plotly_chart_def = {
    "name": "draw_plotly_chart",
    "description": "Draws a Plotly chart using pre-generated stock data from query_stock_price. REQUIRES: plotly_json_fig from stock data.",
    "parameters": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Contextual message for the chart"
            },
            "plotly_json_fig": {
                "type": "string",
                "description": "MUST USE the chart_data string from query_stock_price results",
            },
        },
        "required": ["message", "plotly_json_fig"],
    },
}

async def draw_plotly_chart_handler(message: str, plotly_json_fig: str):
    try:
        if not plotly_json_fig:
            raise ValueError("Missing chart data - did you run query_stock_price first?")
            
        logger.info(f"🎨 Drawing Plotly chart with message: {message}")
        
        try:
            fig = plotly.io.from_json(plotly_json_fig)
            logger.info("✅ Successfully parsed JSON figure")
        except Exception as parse_error:
            logger.error(f"❌ Failed to parse JSON: {str(parse_error)}")
            logger.error(f"Received JSON: {plotly_json_fig[:200]}...") 
            raise
        
        try:
            await cl.Message(
                content=message,
                elements=[cl.Plotly(name="chart", figure=fig, display="inline")]
            ).send()
            logger.info("✅ Successfully sent chart message")
        except Exception as send_error:
            logger.error(f"❌ Failed to send chart: {str(send_error)}")
            raise
        
        return {"status": "success"}
        
    except Exception as e:
        error_msg = f"Chart error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        await cl.Message(content=error_msg).send()
        return {"error": error_msg}

draw_plotly_chart = (draw_plotly_chart_def, draw_plotly_chart_handler)
