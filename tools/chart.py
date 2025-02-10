"""Plotly chart generation tool."""

import json
from typing import Dict, Any
import plotly
import chainlit as cl
import plotly
from utils.common import logger

draw_plotly_chart_def = {
    "name": "draw_plotly_chart",
    "description": "Generate and display interactive Plotly charts in the conversation.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The title of the chart"
            },
            "chart_type": {
                "type": "string",
                "description": "The type of chart to generate",
                "enum": ["line", "bar", "scatter", "pie", "histogram"]
            },
            "data": {
                "type": "object",
                "description": "The data to plot in Plotly format"
            },
            "layout": {
                "type": "object",
                "description": "Additional layout options for the chart"
            }
        },
        "required": ["title", "chart_type", "data"]
    }
}

async def draw_plotly_chart_handler(title: str, chart_type: str, data: Dict[str, Any], layout: Dict[str, Any] = None) -> Dict[str, Any]:
    """Handler function for generating and displaying Plotly charts.
    
    Args:
        title: The title of the chart
        chart_type: The type of chart to generate
        data: The data to plot in Plotly format
        layout: Additional layout options for the chart
        
    Returns:
        Dict containing chart information or error message
    """
    try:
        logger.info(f"📊 Generating {chart_type} chart: {title}")
        
        # Create figure with provided data
        fig = plotly.graph_objects.Figure(data=data)
        
        # Update layout
        fig.update_layout(
            title=title,
            **(layout or {})
        )
        
        # Display chart in conversation
        elements = [
            cl.Plotly(
                name=f"chart_{title.lower().replace(' ', '_')}",
                figure=fig,
                display="inline"
            )
        ]
        
        await cl.Message(
            content=f"📈 Generated chart: {title}",
            elements=elements
        ).send()
        
        logger.info(f"💡 Successfully generated chart: {title}")
        return {
            "title": title,
            "type": chart_type,
            "figure": json.loads(fig.to_json())
        }
        
    except Exception as e:
        logger.error(f"❌ Error generating chart: {str(e)}")
        return {"error": str(e)}

# Export the tool definition and handler
draw_plotly_chart = (draw_plotly_chart_def, draw_plotly_chart_handler)
