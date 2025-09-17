import os
from dotenv import load_dotenv
from tavily import TavilyClient

# Load variables from .env into environment
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY not set. Please add it to your .env file.")

tclient = TavilyClient(api_key=TAVILY_API_KEY)


def t_search(q: str, *, max_results=10) -> dict:
    return tclient.search(
        query=q,
        max_results=max_results,
        include_domains=[],
        exclude_domains=[]
    )


def t_extract(urls: list[str]) -> dict:
    return tclient.extract(urls=urls)


def t_crawl(urls: list[str]) -> dict:
    return tclient.crawl(urls=urls, max_depth=1)


def t_map(q: str) -> dict:
    # great for “best things to do in …”, “areas to stay in …”
    return tclient.map(query=q)
