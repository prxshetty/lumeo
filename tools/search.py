"""Internet search tool using Tavily API."""

from typing import Dict, Any
import chainlit as cl
from utils.common import tavily_client, logger

internet_search_def = {
    "name": "internet_search",
    "description": "Search the internet for real-time information using Tavily's search API.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to execute"
            },
            "search_depth": {
                "type": "string",
                "description": "The depth of search - 'basic' for quick results or 'deep' for comprehensive search"
            }
        },
        "required": ["query", "search_depth"]
    }
}

async def internet_search_handler(query: str, search_depth: str) -> Dict[str, Any]:
    """Executes an internet search using the Tavily API and returns the result."""
    try:
        logger.info(f"🕵 Performing internet search for query: '{query}'")
        response = tavily_client.search(query)

        results = response.get("results", [])
        if not results:
            await cl.Message(content=f"No results found for '{query}'.").send()
            return None

        # Send summary first
        summary = response.get("answer", "Here are the top search results:")
        await cl.Message(content=f"**{summary}**").send()

        # Send results as separate messages with better formatting
        for i, result in enumerate(results[:5]):  # Limit to top 5 results
            content = f"### {i+1}. [{result['title']}]({result['url']})\n{result['content'][:250]}..."
            await cl.Message(
                content=content,
                elements=[
                    cl.Text(
                        name=result['title'],
                        content=result['content'],
                        display="side"
                    )
                ]
            ).send()

        logger.info(f"📏 Search results for '{query}' retrieved successfully.")
        return response["results"]
    except Exception as e:
        error_msg = f"Search error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        await cl.Message(content=error_msg).send()
        return {"error": error_msg}

internet_search = (internet_search_def, internet_search_handler)
