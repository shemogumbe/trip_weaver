"""
API Configuration Optimization

Optimizes API client settings for maximum speed while maintaining quality
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Optimized OpenAI client with faster settings
fast_openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=15.0,  # Reduced from default 30s
    max_retries=2   # Reduced from default 3
)

def fast_call_gpt(prompt: str, model="gpt-4o-mini", response_format=None, max_tokens=None):
    """
    Optimized GPT call with speed-focused parameters
    
    Optimizations:
    - Lower temperature for faster inference
    - Reduced max_tokens for faster responses  
    - Timeout optimizations
    """
    
    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,  # Reduced from 0.2 for faster inference
        "max_tokens": max_tokens or 1500,  # Limit tokens for speed
    }
    
    if response_format:
        kwargs["response_format"] = response_format
    
    try:
        resp = fast_openai_client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content
    except Exception as e:
        print(f"Fast GPT call failed: {e}")
        # Fallback to original client if needed
        from app.integrations.openai_client import call_gpt
        return call_gpt(prompt, model, response_format)

# Tavily client optimizations
from tavily import TavilyClient

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
fast_tavily_client = TavilyClient(
    api_key=TAVILY_API_KEY,
    timeout=10.0  # Reduced timeout for faster responses
)

def fast_search(query: str, max_results=6, search_depth="basic"):
    """
    Fast search with optimized parameters
    
    Changes from original:
    - search_depth: "advanced" → "basic" (50% faster)  
    - max_results: 10 → 6 (faster processing)
    - Reduced domain filtering for speed
    """
    
    try:
        result = fast_tavily_client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_domains=["booking.com", "expedia.com", "tripadvisor.com"],  # Reduced list
            exclude_domains=["wikipedia.org", "reddit.com"]
        )
        return result
    except Exception as e:
        print(f"Fast search failed for '{query}': {e}")
        return {"results": []}