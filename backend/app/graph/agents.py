from datetime import timedelta


from .state import RunState
from app.models.entities import FlightOption, StayOption, Activity, DayPlan
from app.graph.utils import pick, normalize_price, ensure_time_feasible, split_days
from app.graph.postprocess.flights import process_flights
from app.graph.postprocess.stays import process_stays
from app.graph.postprocess.activities import process_activities
from app.graph.postprocess.refine_flights_with_llm import refine_flights_with_llm
from app.graph.postprocess.refine import refine_with_gpt
import logging
from app.integrations.tavily_client import t_search, t_extract, t_map, enhance_search_with_extraction, t_crawl
from app.graph.postprocess.refine_stays_with_llm import refine_stays_with_llm
from app.graph.postprocess.refine_activities_with_llm import refine_activities_with_llm


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def destination_research(state: RunState) -> RunState:
    destination = state.prefs.destination
    
    # Enhanced destination research with multiple data sources
    research_queries = [
        f"{destination} neighborhoods best areas to stay safety transport 2025",
        f"{destination} travel guide local tips culture",
        f"{destination} weather best time to visit {state.prefs.start_date}",
        f"{destination} transportation getting around public transport"
    ]
    
    all_search_results = []
    for query in research_queries:
        enhanced_data = enhance_search_with_extraction(query, max_results=4)
        all_search_results.extend(enhanced_data.get("combined_results", []))
    
    # Use map API for comprehensive destination insights (optional)
    map_queries = [
        f"top things to do in {destination} 2025",
        f"best areas to stay in {destination}",
        f"{destination} local attractions landmarks",
        f"{destination} restaurants food scene"
    ]
    
    all_map_results = []
    for map_query in map_queries:
        map_result = t_map(map_query)
        if map_result.get("results") and not map_result.get("error"):
            all_map_results.extend(map_result["results"])
    
    # Crawl official tourism websites for authoritative information
    tourism_urls = []
    for result in all_search_results + all_map_results:
        url = result.get("url", "")
        if any(site in url.lower() for site in ["tripadvisor.com", "lonelyplanet.com", "wikitravel.org", "visit", "tourism"]):
            tourism_urls.append(url)
    
    crawl_results = []
    if tourism_urls:
        # Limit to 1 URL to avoid API rate limits
        crawl_result = t_crawl(tourism_urls[:1], max_depth=1, max_breadth=2)
        crawl_results = crawl_result.get("results", [])
    
    # Combine all research data
    state.artifacts["destination_research"] = {
        "search": {"results": all_search_results},
        "map": {"results": all_map_results},
        "crawl": {"results": crawl_results}
    }
    
    # Build comprehensive source index
    all_sources = all_search_results + all_map_results + crawl_results
    for item in all_sources:
        url = item.get("url", "")
        if url:
            state.plan.sources[url] = {
                "title": item.get("title", ""),
                "snippet": item.get("content", "")[:200] + "..." if len(item.get("content", "")) > 200 else item.get("content", "")
            }
    
    logger.info(f"Destination research collected {len(all_sources)} sources for {destination}")
    return state

def flight_agent(state: RunState) -> RunState:
    p = state.prefs
    
    # Enhanced multi-query approach for better flight data
    queries = [
        f"{p.origin} to {p.destination} flights {p.start_date} direct nonstop",
        f"{p.origin} {p.destination} airline schedule {p.start_date}",
        f"flights from {p.origin} to {p.destination} {p.start_date} booking"
    ]
    
    all_results = []
    
    # Use enhanced search with extraction for each query
    for query in queries:
        enhanced_data = enhance_search_with_extraction(query, max_results=6)
        all_results.extend(enhanced_data.get("combined_results", []))
    
    # Also try crawling specific airline websites if we have them (limit to avoid API limits)
    airline_urls = []
    for result in all_results:
        url = result.get("url", "")
        if any(airline in url.lower() for airline in ["kenya-airways.com", "emirates.com", "qatarairways.com"]):
            airline_urls.append(url)
    
    if airline_urls:
        # Limit to 1 URL to avoid API rate limits
        crawl_result = t_crawl(airline_urls[:1], max_depth=1, max_breadth=2)
        all_results.extend(crawl_result.get("results", []))
    
    # Remove duplicates based on URL
    seen_urls = set()
    unique_results = []
    for result in all_results:
        url = result.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)
    
    logger.info(f"Flight agent collected {len(unique_results)} unique results")

    refined = refine_flights_with_llm(unique_results, state=state)
    print(f"Refined flights: {refined}")

    if not refined:
        candidates = process_flights(unique_results, state.prefs)  # fallback parser
        state.plan.flights = candidates
    else:
        state.plan.flights = refined

    return state
    

def stay_agent(state: RunState) -> RunState:
    p = state.prefs
    
    # Enhanced multi-query approach for accommodation data
    queries = [
        f"hotels in {p.destination} {p.start_date} {p.end_date}",
        f"best hotels {p.destination} {p.trip_type} accommodation",
        f"{p.destination} hotels booking.com expedia.com {p.start_date}"
    ]
    
    all_results = []
    
    # Use enhanced search with extraction
    for query in queries:
        enhanced_data = enhance_search_with_extraction(query, max_results=5)
        all_results.extend(enhanced_data.get("combined_results", []))
    
    # Use map API for destination-specific hotel areas (optional)
    map_query = f"best areas to stay in {p.destination} hotels neighborhoods"
    map_result = t_map(map_query)
    if map_result.get("results") and not map_result.get("error"):
        all_results.extend(map_result["results"])
    
    # Crawl major booking sites for detailed hotel data (limit to avoid API limits)
    booking_urls = []
    for result in all_results:
        url = result.get("url", "")
        if any(site in url.lower() for site in ["booking.com", "expedia.com", "hotels.com"]):
            booking_urls.append(url)
    
    if booking_urls:
        # Limit to 1 URL to avoid API rate limits
        crawl_result = t_crawl(booking_urls[:1], max_depth=1, max_breadth=3)
        all_results.extend(crawl_result.get("results", []))
    
    # Remove duplicates
    seen_urls = set()
    unique_results = []
    for result in all_results:
        url = result.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)
    
    logger.info(f"Stay agent collected {len(unique_results)} unique results")

    refined = refine_stays_with_llm(unique_results, state=state)
    print(f"Refined stays: {refined}")

    if not refined:
        candidates = process_stays(unique_results, p)  # fallback parser
        state.plan.stays = candidates
    else:
        state.plan.stays = refined

    return state



def activities_agent(state: RunState) -> RunState:
    p = state.prefs
    all_results = []

    # Enhanced activity search with multiple approaches
    base_queries = [
        f"things to do in {p.destination} {p.start_date}",
        f"{p.destination} attractions activities tours",
        f"best activities {p.destination} {p.trip_type}"
    ]
    
    # Add hobby-specific queries
    for hobby in p.hobbies:
        base_queries.extend([
            f"{hobby} in {p.destination} {p.start_date}",
            f"{hobby} activities {p.destination} tours",
            f"{p.destination} {hobby} experiences"
        ])
    
    # Use enhanced search with extraction for each query
    for query in base_queries:
        enhanced_data = enhance_search_with_extraction(query, max_results=4)
        all_results.extend(enhanced_data.get("combined_results", []))
    
    # Use map API for destination-specific activities (optional)
    map_queries = [
        f"top attractions in {p.destination}",
        f"must see places {p.destination}",
        f"popular activities {p.destination}"
    ]
    
    for map_query in map_queries:
        map_result = t_map(map_query)
        if map_result.get("results") and not map_result.get("error"):
            all_results.extend(map_result["results"])
    
    # Crawl activity booking sites for detailed information (limit to avoid API limits)
    activity_urls = []
    for result in all_results:
        url = result.get("url", "")
        if any(site in url.lower() for site in ["getyourguide.com", "viator.com", "tripadvisor.com", "airbnb.com/experiences"]):
            activity_urls.append(url)
    
    if activity_urls:
        # Limit to 1 URL to avoid API rate limits
        crawl_result = t_crawl(activity_urls[:1], max_depth=1, max_breadth=3)
        all_results.extend(crawl_result.get("results", []))
    
    # Remove duplicates
    seen_urls = set()
    unique_results = []
    for result in all_results:
        url = result.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)
    
    logger.info(f"Activities agent collected {len(unique_results)} unique results")

    # Step 1: refine into Activity objects using LLM
    refined = refine_activities_with_llm(unique_results, state=state)
    print(f"Refined activities: {refined}")

    if not refined:
        # Fallback: use existing parser for each hobby
        all_candidates = []
        for hobby in p.hobbies:
            q = f"{hobby} in {p.destination} price schedule {p.start_date}"
            candidates = process_activities(unique_results, p, q)
            all_candidates.extend(candidates)
        refined = all_candidates

    # store refined activities into the plan's catalog
    state.plan.activities_catalog = refined

    # Step 2: schedule into daily buckets
    days = (p.end_date - p.start_date).days + 1
    itinerary = []
    i = 0

    for d in range(days):
        date = (p.start_date + timedelta(days=d)).isoformat()
        day_plan = {"date": date, "morning": None, "afternoon": None, "evening": None}

        if i < len(refined): 
            day_plan["morning"] = refined[i]; i += 1
        if i < len(refined): 
            day_plan["afternoon"] = refined[i]; i += 1
        if i < len(refined): 
            day_plan["evening"] = refined[i]; i += 1

        itinerary.append(day_plan)

    # Step 3: save
    state.plan.itinerary = itinerary
    return state


def budget_agent(state: RunState) -> RunState:
    activities = state.plan.activities_catalog[:6]

    prices = []
    for a in activities:
        if isinstance(a, dict):
            prices.append(a.get("est_price") or 30)
        else:
            prices.append(a.est_price or 30)

    activities_mid = sum(prices) / max(1, len(prices))
    state.plan.activities_budget = activities_mid

    return state


def itinerary_synthesizer(state: RunState) -> RunState:
    days = split_days(state.prefs.start_date, state.prefs.end_date)
    catalog = state.plan.activities_catalog
    plans = []
    ci, ai = 0, 0
    for d in days:
        block = {"morning": [], "afternoon": [], "evening": [], "notes": []}
        # simple schedule: morning light, afternoon main, evening food/culture
        for slot in ["morning","afternoon","evening"]:
            if ai < len(catalog):
                block[slot].append(catalog[ai])
                ai += 1
        ensure_time_feasible(block)  # raises or trims overlaps
        plans.append(block)

    from .state import DayPlan
    itinerary = []
    for i, d in enumerate(days):
        dp = DayPlan(
            date=d,
            morning=plans[i]["morning"],
            afternoon=plans[i]["afternoon"],
            evening=plans[i]["evening"],
            notes=plans[i]["notes"],
        )
        itinerary.append(dp)
    state.plan.itinerary = itinerary
    return state

def safety_reality_check(state: RunState) -> RunState:
    # remove activities outside operating days, duplicate URLs, etc. (toy impl)
    seen = set()
    pruned = []
    for a in state.plan.activities_catalog:
        if a.source_url and a.source_url in seen:
            continue
        seen.add(a.source_url)
        pruned.append(a)
    state.plan.activities_catalog = pruned
    return state
