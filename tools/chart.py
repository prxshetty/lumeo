"""Plotly chart generation tool."""

import json
from typing import Dict, Any
import plotly
import chainlit as cl
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
                "description": "Type of chart to generate: line, bar, scatter, pie, or histogram"
            },
            "x_data": {
                "type": "string",
                "description": "Comma-separated values for x-axis data points"
            },
            "y_data": {
                "type": "string",
                "description": "Comma-separated values for y-axis data points"
            },
            "x_label": {
                "type": "string",
                "description": "Label for the x-axis"
            },
            "y_label": {
                "type": "string",
                "description": "Label for the y-axis"
            }
        },
        "required": ["title", "chart_type", "x_data", "y_data"]
    }
}

async def draw_plotly_chart_handler(
    title: str,
    chart_type: str,
    x_data: str,
    y_data: str,
    x_label: str = "",
    y_label: str = ""
) -> Dict[str, Any]:
    """Generate and display a Plotly chart.
    
    Args:
        title: The title of the chart
        chart_type: Type of chart to generate
        x_data: Comma-separated values for x-axis
        y_data: Comma-separated values for y-axis
        x_label: Label for x-axis
        y_label: Label for y-axis
        
    Returns:
        Dict containing chart information or error message
    """
    try:
        logger.info(f"📊 Generating {chart_type} chart: {title}")
        
        valid_chart_types = ["line", "bar", "scatter", "pie", "histogram"]
        if chart_type not in valid_chart_types:
            raise ValueError(f"Invalid chart type. Must be one of: {', '.join(valid_chart_types)}")
        
        try:
            x_values = [x.strip() for x in x_data.strip('[]"\'').split(',')]
            y_values = [float(y.strip()) for y in y_data.strip('[]"\'').split(',')]
            
            try:
                x_values = [float(x) for x in x_values]
            except ValueError:
                pass
                
        except Exception as e:
            raise ValueError(f"Error parsing data: {str(e)}")
            
        if chart_type == "pie":
            fig = plotly.graph_objects.Figure(data=[plotly.graph_objects.Pie(
                labels=x_values,
                values=y_values
            )])
        else:
            chart_class = getattr(plotly.graph_objects, chart_type.capitalize())
            fig = plotly.graph_objects.Figure(data=[chart_class(
                x=x_values,
                y=y_values
            )])
        
        layout = {
            "title": title,
            "xaxis_title": x_label,
            "yaxis_title": y_label,
            "template": "plotly_white"
        }
        fig.update_layout(**{k: v for k, v in layout.items() if v})
        
        elements = [
            cl.Plotly(
                name=f"chart_{title.lower().replace(' ', '_')}",
                figure=fig,
                display="inline"
            )
        ]
        
        await cl.Message(
            content=f"📈 Generated {chart_type} chart: {title}",
            elements=elements
        ).send()
        
        logger.info(f"💡 Successfully generated chart: {title}")
        return {
            "title": title,
            "type": chart_type,
            "data_points": len(x_values),
            "x_data": x_values,
            "y_data": y_values,
            "x_label": x_label,
            "y_label": y_label
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error generating chart: {error_msg}")
        return {"error": error_msg}

draw_plotly_chart = (draw_plotly_chart_def, draw_plotly_chart_handler)
