"""Internet search tool using Tavily API."""

from typing import Dict, Any, List
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
                "description": "The depth of search (basic or deep)",
                "enum": ["basic", "deep"],
                "default": "basic"
            }
        },
        "required": ["query"]
    }
}

async def internet_search_handler(query: str, search_depth: str = "basic") -> Dict[str, Any]:
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
            
        # Execute search
        search_result = await tavily_client.search(
            query=query,
            search_depth=search_depth,
            max_results=5
        )
        
        # Format results
        formatted_results = []
        for result in search_result.get("results", []):
            formatted_results.append({
                "title": result.get("title"),
                "content": result.get("content"),
                "url": result.get("url"),
                "score": result.get("score", 0)
            })
            
        response = {
            "query": query,
            "results": formatted_results,
            "total_results": len(formatted_results)
        }
        
        logger.info(f"💡 Found {len(formatted_results)} results for query: {query}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error executing search: {str(e)}")
        return {"error": str(e)}

internet_search = (internet_search_def, internet_search_handler)
