"""Research tools for AI agents.

This module contains the tools that research agents can use to gather
information from various sources including web search, Wikipedia,
and URL fetching.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

# User-Agent header to comply with Wikipedia and other site policies
# See: https://meta.wikimedia.org/wiki/User-Agent_policy
USER_AGENT = (
    "DeepResearchPOC/1.0 (https://github.com/example/deep-research-poc; "
    "research-bot@example.com) httpx/0.28"
)

# Common headers for HTTP requests
DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/json,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


async def web_search(query: str, num_results: int = 5) -> str:
    """Search the web using DuckDuckGo.
    
    Args:
        query: The search query
        num_results: Number of results to return (default: 5)
    
    Returns:
        JSON string of search results with title, url, and snippet
    """
    from ddgs import DDGS
    
    log = logger.bind(tool="web_search", query=query[:50], num_results=num_results)
    log.info("tool_called")
    
    try:
        with DDGS() as ddgs:
            raw_results: list[dict[str, Any]] = list(
                ddgs.text(query, max_results=num_results)
            )  # type: ignore[assignment]
        
        formatted_results: list[dict[str, str]] = [
            {
                "title": str(result.get("title", "")),
                "url": str(result.get("href", "")),
                "snippet": str(result.get("body", "")),
            }
            for result in raw_results
        ]
        
        log.info("tool_success", num_results_found=len(formatted_results))
        return json.dumps(formatted_results, indent=2)
        
    except Exception as e:
        log.warning("tool_failed", error=str(e))
        return json.dumps({"error": str(e), "results": []})


async def fetch_url(url: str, max_chars: int = 5000) -> str:
    """Fetch and extract content from a URL.
    
    Args:
        url: The URL to fetch
        max_chars: Maximum characters to return (default: 5000)
    
    Returns:
        The page content (truncated) or error message
    """
    log = logger.bind(tool="fetch_url", url=url[:100])
    log.info("tool_called")
    
    try:
        async with httpx.AsyncClient(
            timeout=30.0, headers=DEFAULT_HEADERS
        ) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            content = response.text[:max_chars]
            log.info("tool_success", content_length=len(content))
            return content
    except Exception as e:
        log.warning("tool_failed", error=str(e))
        return f"Failed to fetch {url}: {str(e)}"


async def wikipedia_search(topic: str, max_chars: int = 2000) -> str:
    """Search Wikipedia for information on a topic.
    
    Uses Wikipedia's REST API with proper User-Agent to comply with
    Wikimedia's User-Agent policy.
    
    Args:
        topic: The topic to search for
        max_chars: Maximum characters to return (default: 2000)
    
    Returns:
        Summary information from Wikipedia or error message
    """
    log = logger.bind(tool="wikipedia_search", topic=topic[:50])
    log.info("tool_called")
    
    try:
        # Try the REST API first (more reliable, better formatted)
        # See: https://en.wikipedia.org/api/rest_v1/
        rest_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic}"
        
        async with httpx.AsyncClient(
            timeout=30.0, headers=DEFAULT_HEADERS
        ) as client:
            response = await client.get(rest_url, follow_redirects=True)
            
            if response.status_code == 200:
                data = response.json()
                extract = data.get("extract", "")
                if extract:
                    result = extract[:max_chars]
                    log.info("tool_success", content_length=len(result), api="rest")
                    return f"Wikipedia summary for '{topic}':\n\n{result}"
            
            # Fallback to MediaWiki API if REST API fails
            log.info("rest_api_failed", status=response.status_code, falling_back=True)
            return await _wikipedia_mediawiki_fallback(topic, max_chars, log)
                
    except Exception as e:
        log.warning("tool_failed", error=str(e))
        # Try fallback on exception
        try:
            return await _wikipedia_mediawiki_fallback(topic, max_chars, log)
        except Exception as fallback_error:
            log.warning("fallback_failed", error=str(fallback_error))
            return f"Wikipedia search failed for '{topic}': {str(e)}"


async def _wikipedia_mediawiki_fallback(
    topic: str, max_chars: int, log: Any
) -> str:
    """Fallback to MediaWiki API for Wikipedia search.
    
    Args:
        topic: The topic to search for
        max_chars: Maximum characters to return
        log: Logger instance
    
    Returns:
        Summary information from Wikipedia or error message
    """
    url = "https://en.wikipedia.org/w/api.php"
    params: dict[str, Any] = {
        "action": "query",
        "format": "json",
        "titles": topic,
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
    }
    
    async with httpx.AsyncClient(
        timeout=30.0, headers=DEFAULT_HEADERS
    ) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return f"No Wikipedia page found for: {topic}"
        
        page = next(iter(pages.values()))
        
        # Check for missing page
        if page.get("missing") is not None:
            return f"No Wikipedia page found for: {topic}"
        
        if "extract" in page:
            extract = page["extract"][:max_chars]
            log.info("tool_success", content_length=len(extract), api="mediawiki")
            return f"Wikipedia summary for '{topic}':\n\n{extract}"
        else:
            return f"No content found for: {topic}"


async def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely.
    
    Uses a restricted eval environment for safety.
    
    Args:
        expression: Mathematical expression (e.g., "2 + 2", "10 * 5")
    
    Returns:
        The result of the calculation or error message
    """
    log = logger.bind(tool="calculate", expression=expression[:50])
    log.info("tool_called")
    
    try:
        # Restricted environment for safety
        allowed_names: dict[str, Any] = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
        }
        
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        log.info("tool_success", result=result)
        return f"Result: {result}"
        
    except Exception as e:
        log.warning("tool_failed", error=str(e))
        return f"Calculation failed: {str(e)}"


async def get_current_datetime() -> str:
    """Get the current date and time in ISO format.
    
    Returns:
        Current UTC date and time in ISO format
    """
    now = datetime.now(timezone.utc)
    return f"Current UTC time: {now.isoformat()}"
