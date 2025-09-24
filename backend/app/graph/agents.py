from datetime import timedelta
from typing import List


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
        # Ensure url is a string, not a dict
        if isinstance(url, dict):
            url = url.get("url", "") or url.get("href", "") or str(url)
        if url and isinstance(url, str) and any(site in url.lower() for site in ["tripadvisor.com", "lonelyplanet.com", "wikitravel.org", "visit", "tourism"]):
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
        # Ensure url is a string, not a dict
        if isinstance(url, dict):
            url = url.get("url", "") or url.get("href", "") or str(url)
        if url and isinstance(url, str):
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
        # Ensure url is a string, not a dict
        if isinstance(url, dict):
            url = url.get("url", "") or url.get("href", "") or str(url)
        if url and isinstance(url, str) and any(airline in url.lower() for airline in ["kenya-airways.com", "emirates.com", "qatarairways.com"]):
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
        # Ensure url is a string, not a dict
        if isinstance(url, dict):
            url = url.get("url", "") or url.get("href", "") or str(url)
        if url and isinstance(url, str) and url not in seen_urls:
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
        # Ensure url is a string, not a dict
        if isinstance(url, dict):
            url = url.get("url", "") or url.get("href", "") or str(url)
        if url and isinstance(url, str) and any(site in url.lower() for site in ["booking.com", "expedia.com", "hotels.com"]):
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
        # Ensure url is a string, not a dict
        if isinstance(url, dict):
            url = url.get("url", "") or url.get("href", "") or str(url)
        if url and isinstance(url, str) and url not in seen_urls:
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
        # Ensure url is a string, not a dict
        if isinstance(url, dict):
            url = url.get("url", "") or url.get("href", "") or str(url)
        if url and isinstance(url, str) and any(site in url.lower() for site in ["getyourguide.com", "viator.com", "tripadvisor.com", "airbnb.com/experiences"]):
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
        # Ensure url is a string, not a dict
        if isinstance(url, dict):
            url = url.get("url", "") or url.get("href", "") or str(url)
        if url and isinstance(url, str) and url not in seen_urls:
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


# === OPTIMIZED ACTIVITIES AGENTS ===

def generate_activities_with_openai(state: RunState) -> List[Activity]:
    """
    Generate comprehensive activities for the entire trip using OpenAI instead of multiple Tavily calls.
    This replaces ~20 Tavily API calls with 1 OpenAI call.
    """
    from app.integrations.openai_client import call_gpt
    import json
    
    p = state.prefs
    
    # Calculate total trip days (excluding arrival and departure days)
    total_days = (p.end_date - p.start_date).days + 1
    activity_days = max(1, total_days - 2)  # Exclude first and last day
    total_slots = activity_days * 3  # morning, afternoon, evening
    
    # Build comprehensive prompt for activity generation
    hobbies_text = ", ".join(p.hobbies) if p.hobbies else "general tourism"
    
    prompt = f"""You are a travel expert creating a detailed activity itinerary for {p.destination}.

TRIP DETAILS:
- Destination: {p.destination}
- Duration: {total_days} days ({p.start_date} to {p.end_date})
- Trip Type: {p.trip_type}
- Interests/Hobbies: {hobbies_text}
- Budget Level: {p.budget_level}
- Number of Adults: {p.adults}

REQUIREMENTS:
- Generate {total_slots} diverse activities (enough for {activity_days} days × 3 time slots)
- Activities should exclude arrival day ({p.start_date}) and departure day ({p.end_date})
- Mix of: attractions, restaurants, cultural experiences, {hobbies_text}
- Include specific location names, addresses when possible
- Provide realistic duration estimates (0.5-8 hours)
- Estimate prices in USD (can be 0 for free activities)
- Include diverse activity types: sightseeing, dining, entertainment, relaxation
- Consider {p.budget_level} budget level (low=budget-friendly, mid=moderate, high=luxury options)

Return ONLY valid JSON in this exact format:
{{
  "activities": [
    {{
      "title": "Visit Nairobi National Park",
      "location": "Langata Road, Nairobi, Kenya", 
      "duration_hours": 4.0,
      "est_price": 45.0,
      "currency": "USD",
      "source_url": null,
      "source_title": null,
      "tags": ["wildlife", "nature", "photography"]
    }},
    {{
      "title": "Dinner at Carnivore Restaurant",
      "location": "Langata Road, Nairobi, Kenya",
      "duration_hours": 2.5,
      "est_price": 35.0, 
      "currency": "USD",
      "source_url": null,
      "source_title": null,
      "tags": ["dining", "local cuisine", "popular"]
    }}
  ]
}}

Generate exactly {total_slots} activities with variety in pricing, duration, and activity types."""

    try:
        # Call OpenAI to generate activities
        structured = call_gpt(prompt, model="gpt-4o-mini", response_format={"type": "json_object"})
        
        if not structured:
            logger.warning("OpenAI returned empty response for activities")
            return []
            
        # Parse JSON response
        try:
            if isinstance(structured, str):
                data = json.loads(structured)
            else:
                data = structured
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON from OpenAI for activities: %s", e)
            return []
        
        activities_data = data.get("activities", [])
        if not activities_data:
            logger.warning("OpenAI did not return 'activities' key")
            return []
        
        # Convert to Activity objects with validation
        activities = []
        for item in activities_data:
            try:
                # Sanitize data before creating Activity
                clean_item = {
                    "title": str(item.get("title", "Activity")).strip(),
                    "location": str(item.get("location", "Location TBD")).strip(),
                    "duration_hours": float(item.get("duration_hours", 2.0)) if item.get("duration_hours") else 2.0,
                    "est_price": float(item.get("est_price", 0)) if item.get("est_price") else None,
                    "currency": str(item.get("currency", "USD")).strip(),
                    "source_url": item.get("source_url"),
                    "source_title": item.get("source_title"),
                    "tags": [str(tag).strip().lower() for tag in (item.get("tags", []) if isinstance(item.get("tags"), list) else [])]
                }
                
                activity = Activity(**clean_item)
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to create Activity from OpenAI data: {e}, item: {item}")
                continue
        
        logger.info(f"Generated {len(activities)} activities using OpenAI (target was {total_slots})")
        return activities
        
    except Exception as e:
        logger.error(f"Error generating activities with OpenAI: {e}")
        return []


def distribute_activities_across_days(activities: List[Activity], state: RunState):
    """
    Distribute activities evenly across available days, excluding arrival and departure days.
    """
    p = state.prefs
    
    # Calculate available days (exclude first and last day)
    total_days = (p.end_date - p.start_date).days + 1
    
    if total_days <= 2:
        # Short trip - use all days
        available_days = list(range(total_days))
    else:
        # Exclude arrival (day 0) and departure (last day)
        available_days = list(range(1, total_days - 1))
    
    # Create itinerary structure
    itinerary = []
    activity_index = 0
    
    for day_num in range(total_days):
        date = (p.start_date + timedelta(days=day_num)).isoformat()
        
        day_plan = {
            "date": date,
            "morning": None,
            "afternoon": None, 
            "evening": None
        }
        
        # Only assign activities to available days (not arrival/departure)
        if day_num in available_days:
            # Morning activity
            if activity_index < len(activities):
                day_plan["morning"] = activities[activity_index]
                activity_index += 1
                
            # Afternoon activity  
            if activity_index < len(activities):
                day_plan["afternoon"] = activities[activity_index]
                activity_index += 1
                
            # Evening activity
            if activity_index < len(activities):
                day_plan["evening"] = activities[activity_index]
                activity_index += 1
        
        itinerary.append(day_plan)
    
    logger.info(f"Distributed {activity_index} activities across {len(available_days)} available days (excluding arrival/departure)")
    return itinerary


def optimized_activities_agent_with_openai(state: RunState) -> RunState:
    """
    ULTRA-OPTIMIZED: Replace ~20 Tavily calls with 1 OpenAI call.
    Uses OpenAI to generate comprehensive activities, then distributes them properly.
    
    Tavily calls: 22 → 1 (95% reduction for activities)
    Methods: Only 1 strategic search call for validation/context
    """
    p = state.prefs
    
    # Step 1: Optional minimal Tavily search for context (just 1 call)
    context_query = f"travel guide {p.destination} popular attractions 2025"
    search_result = t_search(context_query, max_results=5)
    search_results = search_result.get("results", [])
    
    # Store minimal context for potential validation
    state.artifacts["activities_context"] = {
        "search_results": search_results[:3]  # Just top 3 for context
    }
    
    # Step 2: Generate comprehensive activities using OpenAI
    activities = generate_activities_with_openai(state)
    
    if not activities:
        logger.warning("No activities generated by OpenAI, creating minimal fallback")
        # Minimal fallback
        activities = [
            Activity(
                title=f"Explore {p.destination} city center",
                location=f"{p.destination} downtown",
                duration_hours=3.0,
                est_price=10.0,
                tags=["sightseeing", "walking"]
            ),
            Activity(
                title=f"Local restaurant in {p.destination}",
                location=f"{p.destination}",
                duration_hours=1.5,
                est_price=25.0,
                tags=["dining", "local cuisine"]
            )
        ]
    
    # Step 3: Store activities in catalog
    state.plan.activities_catalog = activities
    
    # Step 4: Distribute activities across days (excluding arrival/departure)  
    itinerary = distribute_activities_across_days(activities, state)
    state.plan.itinerary = itinerary
    
    logger.info(f"ULTRA-OPTIMIZED: Generated {len(activities)} activities with 1 Tavily call + 1 OpenAI call (was 22 Tavily calls)")
    
    return state
