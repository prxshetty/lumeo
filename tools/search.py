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
    """Handler function for internet searches.
    
    Args:
        query: The search query to execute
        search_depth: The depth of search (basic or deep)
        
    Returns:
        Dict containing search results or error message
    """
    try:
        logger.info(f"🔍 Searching for: {query}")
        
        if not tavily_client:
            raise ValueError("Tavily client not initialized. Please check your API key.")
            
        if search_depth not in ["basic", "deep"]:
            raise ValueError("Search depth must be either 'basic' or 'deep'")
            
        search_result = tavily_client.search(
            query=query,
            search_depth="comprehensive" if search_depth == "deep" else "basic"
        )
        
        results = search_result.get("results", [])
        if not results:
            message = f"No results found for '{query}'"
            await cl.Message(content=message).send()
            return {"error": message}
            
        # Format results for display
        formatted_results = "\n".join(
            [
                f"{i+1}. [{result['title']}]({result['url']})\n{result['content'][:200]}..."
                for i, result in enumerate(results[:5])
            ]
        )
        
        message_content = f"Search Results for '{query}':\n\n{formatted_results}"
        await cl.Message(content=message_content).send()
        
        logger.info(f"💡 Found {len(results)} results for query: {query}")
        return {
            "query": query,
            "search_depth": search_depth,
            "total_results": len(results),
            "results": results[:5]
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error executing search: {error_msg}")
        await cl.Message(content=f"An error occurred while performing the search: {error_msg}").send()
        return {"error": f"Search failed: {error_msg}"}

internet_search = (internet_search_def, internet_search_handler)
