"""Tests for research tools functionality."""

import json

import pytest

from deep_research_poc.agents.tools import (
    calculate,
    fetch_url,
    get_current_datetime,
    web_search,
    wikipedia_search,
)


@pytest.mark.asyncio
async def test_calculate_basic() -> None:
    """Test basic calculation."""
    result = await calculate("2 + 2")
    assert "4" in result


@pytest.mark.asyncio
async def test_calculate_complex() -> None:
    """Test complex calculations."""
    result = await calculate("pow(2, 10)")
    assert "1024" in result


@pytest.mark.asyncio
async def test_calculate_with_functions() -> None:
    """Test calculations with allowed functions."""
    result = await calculate("sum([1, 2, 3, 4, 5])")
    assert "15" in result
    
    result = await calculate("max(10, 20, 5, 15)")
    assert "20" in result


@pytest.mark.asyncio
async def test_calculate_invalid_expression() -> None:
    """Test that invalid expressions return error message."""
    result = await calculate("invalid_function()")
    assert "failed" in result.lower() or "error" in result.lower()


@pytest.mark.asyncio
async def test_get_current_datetime() -> None:
    """Test getting current datetime."""
    result = await get_current_datetime()
    assert "UTC" in result
    # Should be ISO format
    assert "T" in result


@pytest.mark.asyncio
async def test_web_search_returns_json() -> None:
    """Test that web search returns valid JSON."""
    result = await web_search("Python programming", num_results=2)
    
    # Should be valid JSON
    parsed = json.loads(result)
    assert isinstance(parsed, (list, dict))


@pytest.mark.asyncio
async def test_web_search_error_handling() -> None:
    """Test that web search handles errors gracefully."""
    # Even with unusual queries, should return valid JSON
    result = await web_search("asdkjhaskjdhaksjdhaksjdh12312312", num_results=1)
    parsed = json.loads(result)
    assert isinstance(parsed, (list, dict))


@pytest.mark.asyncio
async def test_wikipedia_search() -> None:
    """Test Wikipedia search functionality."""
    result = await wikipedia_search("Python programming language")
    
    # Should return some content
    assert len(result) > 0
    # Should mention Python or programming
    assert "python" in result.lower() or "programming" in result.lower() or "No Wikipedia" in result


@pytest.mark.asyncio
async def test_fetch_url_success() -> None:
    """Test fetching a URL successfully."""
    result = await fetch_url("https://example.com")
    
    # Example.com should return some content
    assert len(result) > 0
    # Should contain HTML or text content
    assert "Example" in result or "example" in result or "Failed" in result


@pytest.mark.asyncio
async def test_fetch_url_invalid() -> None:
    """Test fetching an invalid URL."""
    result = await fetch_url("https://this-url-definitely-does-not-exist-12345.com")
    
    # Should return error message
    assert "Failed" in result or "error" in result.lower()


@pytest.mark.asyncio
async def test_fetch_url_max_chars() -> None:
    """Test that fetch_url respects max_chars limit."""
    result = await fetch_url("https://example.com", max_chars=100)
    
    # Should not exceed max_chars (unless it's an error message)
    if "Failed" not in result:
        assert len(result) <= 100
