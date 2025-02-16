"""Plotly chart drawing tool."""

import chainlit as cl
import plotly
import json
from utils.common import logger

draw_plotly_chart_def = {
    "name": "draw_plotly_chart",
    "description": "Draws a Plotly chart based on the provided JSON figure and displays it with an accompanying message.",
    "parameters": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The message to display alongside the chart",
            },
            "plotly_json_fig": {
                "type": "string",
                "description": "A Plotly figure object in JSON format",
            },
        },
        "required": ["message", "plotly_json_fig"],
    },
}

async def draw_plotly_chart_handler(message: str, plotly_json_fig: str):
    try:
        logger.info(f"🎨 Drawing Plotly chart with message: {message}")
        
        if isinstance(plotly_json_fig, str):
            try:
                fig_data = json.loads(plotly_json_fig)
            except json.JSONDecodeError as e:
                cleaned_json = plotly_json_fig.replace("'", '"').strip()
                try:
                    fig_data = json.loads(cleaned_json)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON: {e}")
                    raise ValueError(f"Invalid JSON format: {e}")
        else:
            fig_data = plotly_json_fig
            
        if 'data' not in fig_data or 'layout' not in fig_data:
            raise ValueError("Invalid Plotly figure format - missing data or layout")            
        fig = plotly.graph_objs.Figure(fig_data)
        elements = [
            cl.Plotly(
                name="chart",
                figure=fig,
                display="inline",
                size="large",
            )
        ]        
        await cl.Message(
            content=message,
            elements=elements,
        ).send()
        
        logger.info("💡 Plotly chart displayed successfully")
        return {"status": "success"}
        
    except Exception as e:
        error_msg = f"Error rendering chart: {str(e)}"
        logger.error(f"❌ {error_msg}")
        await cl.Message(content=error_msg).send()
        return {"error": error_msg}

draw_plotly_chart = (draw_plotly_chart_def, draw_plotly_chart_handler)
