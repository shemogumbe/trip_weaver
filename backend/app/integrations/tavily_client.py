import os
import logging
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from tavily import TavilyClient

# Load variables from .env into environment
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY not set. Please add it to your .env file.")

tclient = TavilyClient(api_key=TAVILY_API_KEY)
logger = logging.getLogger(__name__)

# Travel-specific domains for better results
TRAVEL_DOMAINS = [
    "booking.com", "expedia.com", "kayak.com", "skyscanner.com", 
    "tripadvisor.com", "getyourguide.com", "viator.com", "airbnb.com",
    "hotels.com", "agoda.com", "priceline.com", "orbitz.com"
]

def t_search(q: str, *, max_results=10, search_depth="advanced", include_travel_domains=True, time_range=None) -> dict:
    """
    Enhanced search with better parameters for travel data.
    """
    include_domains = TRAVEL_DOMAINS if include_travel_domains else []
    
    try:
        result = tclient.search(
            query=q,
            max_results=max_results,
            search_depth=search_depth,
            include_domains=include_domains,
            exclude_domains=["wikipedia.org", "reddit.com"],  # Exclude less reliable sources
            time_range=time_range
        )
        logger.info(f"Search completed for query: {q[:50]}...")
        return result
    except Exception as e:
        logger.error(f"Search failed for query '{q}': {e}")
        return {"results": [], "error": str(e)}


def t_extract(urls: List[str], extract_depth="advanced") -> dict:
    """
    Extract full content from URLs with advanced depth.
    """
    if not urls:
        return {"results": []}
    
    try:
        result = tclient.extract(urls=urls, extract_depth=extract_depth)
        logger.info(f"Extracted content from {len(urls)} URLs")
        return result
    except Exception as e:
        logger.error(f"Extract failed for URLs {urls}: {e}")
        return {"results": [], "error": str(e)}


def t_crawl(urls: List[str], max_depth=2, max_breadth=5) -> dict:
    """
    Crawl websites to get comprehensive data.
    Note: Tavily crawl API requires a single URL, so we process them one by one.
    """
    if not urls:
        return {"results": []}
    
    all_results = []
    for url in urls:
        try:
            result = tclient.crawl(
                url=url, 
                max_depth=max_depth,
                max_breadth=max_breadth
            )
            if result and result.get("results"):
                all_results.extend(result["results"])
            logger.info(f"Crawled URL: {url}")
        except Exception as e:
            logger.warning(f"Crawl failed for URL {url}: {e}")
            continue  # Skip failed URLs instead of failing entirely
    
    logger.info(f"Crawled {len(urls)} URLs, got {len(all_results)} results")
    return {"results": all_results}


def t_map(q: str) -> dict:
    """
    Map API for structured data about destinations.
    Note: This API may have changed or require different parameters.
    """
    try:
        # Try different possible parameter combinations for map API
        try:
            result = tclient.map(query=q)
        except TypeError as e:
            if "missing 1 required positional argument" in str(e):
                # Map API might require a URL parameter now
                logger.warning(f"Map API requires URL parameter, skipping query: {q[:50]}...")
                return {"results": [], "error": "Map API requires URL parameter"}
            else:
                raise e
        
        logger.info(f"Map query completed: {q[:50]}...")
        return result
    except Exception as e:
        logger.warning(f"Map failed for query '{q}': {e}")
        return {"results": [], "error": str(e)}


def get_booking_urls_from_search(search_results: List[Dict]) -> List[str]:
    """
    Extract booking URLs from search results for further processing.
    """
    urls = []
    for result in search_results:
        url = result.get("url", "")
        if any(domain in url.lower() for domain in ["booking.com", "expedia.com", "kayak.com", "getyourguide.com"]):
            urls.append(url)
    return urls


def enhance_search_with_extraction(query: str, max_results=8) -> Dict[str, Any]:
    """
    Combined search + extraction for richer data.
    """
    # Step 1: Search for relevant content
    search_result = t_search(query, max_results=max_results, search_depth="advanced")
    search_results = search_result.get("results", [])
    
    if not search_results:
        return {"search_results": [], "extracted_content": []}
    
    # Step 2: Extract full content from promising URLs
    booking_urls = get_booking_urls_from_search(search_results)
    if booking_urls:
        extract_result = t_extract(booking_urls[:3])  # Limit to top 3 for efficiency
        extracted_content = extract_result.get("results", [])
    else:
        extracted_content = []
    
    return {
        "search_results": search_results,
        "extracted_content": extracted_content,
        "combined_results": search_results + extracted_content
    }
