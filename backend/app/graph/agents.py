from datetime import timedelta
from typing import List, Dict, Any, Optional


from .state import RunState
from app.models.entities import FlightOption, StayOption, Activity, DayPlan
from app.graph.utils.general_utils import pick, normalize_price, ensure_time_feasible, split_days
from app.graph.utils.postprocess.flights import process_flights
from app.graph.utils.postprocess.stays import process_stays
from app.graph.utils.postprocess.activities import process_activities
from app.graph.utils.postprocess.refine_flights_with_llm import refine_flights_with_llm
import logging
from app.integrations.tavily_client import t_search, t_extract, t_map, enhance_search_with_extraction, t_crawl
from app.graph.utils.postprocess.refine_stays_with_llm import refine_stays_with_llm
from app.graph.utils.postprocess.refine_activities_with_llm import refine_activities_with_llm
from app.integrations.google_places_client import google_places_client
from app.integrations.exceptions import IntegrationError, UpstreamAPIError
from app.integrations.openai_client import call_gpt
import json


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
    state.logs.append({
        "stage": "Destination Research",
        "message": f"Collected {len(all_sources)} sources",
        "destination": destination,
        "counts": {
            "search": len(all_search_results),
            "map": len(all_map_results),
            "crawl": len(crawl_results)
        }
    })
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
    state.logs.append({
        "stage": "Flights Found",
        "message": f"Found {len(unique_results)} raw flight results",
        "count": len(unique_results)
    })

    refined = refine_flights_with_llm(unique_results, state=state)
    print(f"Refined flights: {refined}")

    if not refined:
        candidates = process_flights(unique_results, state.prefs)  # fallback parser
        state.plan.flights = candidates
    else:
        state.plan.flights = refined

    state.logs.append({
        "stage": "Flights Refined",
        "message": f"Selected {len(state.plan.flights)} flight options",
        "count": len(state.plan.flights)
    })

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
    state.logs.append({
        "stage": "Stays Found",
        "message": f"Found {len(unique_results)} raw stay results",
        "count": len(unique_results)
    })

    refined = refine_stays_with_llm(unique_results, state=state)
    print(f"Refined stays: {refined}")

    if not refined:
        candidates = process_stays(unique_results, p)  # fallback parser
        state.plan.stays = candidates
    else:
        state.plan.stays = refined

    state.logs.append({
        "stage": "Stays Refined",
        "message": f"Selected {len(state.plan.stays)} stay options",
        "count": len(state.plan.stays)
    })

    return state



def _fetch_places(hobby: str, destination: str) -> List[Dict]:
    """Fetch places for a hobby and destination using Google Places."""
    if google_places_client is None:
        raise IntegrationError("Google Places API key not configured.")
    return google_places_client.search_places_by_hobby(hobby, destination)

<<<<<<< HEAD
=======
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
    state.logs.append({
        "stage": "Activities Found",
        "message": f"Found {len(unique_results)} raw activity results",
        "count": len(unique_results)
    })
>>>>>>> 0d79b3c (stream responses for user engagement)

# (See complete implementations of _expand_places_with_llm and
#  _generate_llm_fallback_activities further below.)


<<<<<<< HEAD
def _format_activity_response(activities: List[Activity]) -> List[Activity]:
    """Ensure a clean list of Activity items."""
    valid: List[Activity] = []
    for a in activities:
        try:
            if isinstance(a, Activity):
                valid.append(a)
            else:
                valid.append(Activity(**a))
        except Exception:
            continue
    return valid
=======
    # store refined activities into the plan's catalog
    state.plan.activities_catalog = refined
    state.logs.append({
        "stage": "Activities Refined",
        "message": f"Refined to {len(state.plan.activities_catalog)} activities",
        "count": len(state.plan.activities_catalog)
    })
>>>>>>> 0d79b3c (stream responses for user engagement)


def _load_cached_activities(destination: str, hobbies: List[str]) -> Optional[List[Activity]]:
    """Placeholder: load cached activities if available (replace with real cache)."""
    return None


def _save_cached_activities(destination: str, hobbies: List[str], activities: List[Activity]) -> None:
    """Placeholder: save activities to a cache (replace with real cache)."""
    return None

<<<<<<< HEAD

# Removed older Tavily-heavy activities_agent in favor of Google Places + LLM implementation below.
=======
    # Step 3: save
    state.plan.itinerary = itinerary
    state.logs.append({
        "stage": "Itinerary Drafted",
        "message": f"Drafted itinerary for {days} days",
        "days": days
    })
    return state
>>>>>>> 0d79b3c (stream responses for user engagement)


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
    state.logs.append({
        "stage": "Budget Estimated",
        "message": f"Estimated activities budget ${activities_mid:.2f}",
        "activities_considered": len(activities)
    })

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
    state.logs.append({
        "stage": "Itinerary Synthesized",
        "message": f"Finalized itinerary across {len(days)} days",
        "days": len(days),
        "activities_used": sum(len(v) for k, v in plans[0].items() if isinstance(v, list)) if plans else 0
    })
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
    state.logs.append({
        "stage": "Safety Check",
        "message": f"Pruned duplicate/invalid activities: kept {len(pruned)}",
        "count": len(pruned)
    })
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


def activities_agent(state: RunState) -> RunState:
    """
    Activities agent that combines Google Places results with a generation step
    and falls back to a seeded generator when needed.
    """
    p = state.prefs
    
    # Calculate available days (excluding arrival/departure)
    total_days = (p.end_date - p.start_date).days + 1
    available_days = max(1, total_days - 2)
    total_hobbies = len(p.hobbies)
    
    logger.info(f"Places + generator approach: targeting activities for {total_hobbies} hobbies across {available_days} days")
    
    all_activities = []
    
    # Price ranges by budget level
    price_ranges = {
        "low": {"dining": (8, 25), "activities": (0, 20), "entertainment": (5, 15)},
        "mid": {"dining": (20, 60), "activities": (15, 50), "entertainment": (20, 40)},
        "high": {"dining": (50, 150), "activities": (40, 120), "entertainment": (40, 80)}
    }
    
    # Generate activities for each hobby
    # Multi-tier fallback order: Places → Cache → Generator
    # 1) Try Google Places per hobby; if Places fails (integration issue), attempt cache; else use fallback generator
    for hobby in p.hobbies:
        logger.info(f"Generating activities for hobby: {hobby}")
        places_activities: List[Activity] = []
        try:
            places = _fetch_places(hobby, p.destination)
            if places and len(places) >= 2:
                places_activities = _expand_places_with_generator(places, hobby, p.destination, p.budget_level, price_ranges)
                logger.info(f"Generated {len(places_activities)} activities from Places expansion for {hobby}")
            else:
                logger.info(f"Limited places found for {hobby}")
        except IntegrationError as e:
            logger.warning(f"Places integration unavailable for {hobby}: {e}")
            cached = _load_cached_activities(p.destination, [hobby])
            if cached:
                logger.info(f"Loaded {len(cached)} cached activities for {hobby}")
                places_activities = cached
        except Exception as e:
            logger.warning(f"Google Places search failed for {hobby}: {e}")

        # Fallback: generator-only if we still need activities
        if len(places_activities) < 4:
            fallback_activities = _generate_fallback_activities(hobby, p.destination, p.budget_level, price_ranges)
            logger.info(f"Generated {len(fallback_activities)} activities from fallback generator for {hobby}")
            places_activities.extend(fallback_activities)
        
        # Take up to 6 activities per hobby
        hobby_activities = places_activities[:6]
        all_activities.extend(hobby_activities)
        logger.info(f"Generated {len(hobby_activities)} activities for {hobby}")
<<<<<<< HEAD
=======
        # Progress log per hobby
>>>>>>> 0d79b3c (stream responses for user engagement)
        state.logs.append({
            "stage": "Activities Generated",
            "message": f"Generated {len(hobby_activities)} activities for '{hobby}'",
            "hobby": hobby,
            "count": len(hobby_activities)
        })
    
    # Remove duplicates
    unique_activities = []
    seen_titles = set()
    for activity in all_activities:
        if activity.title not in seen_titles:
            unique_activities.append(activity)
            seen_titles.add(activity.title)
    
    # Summary before dedup
    state.logs.append({
        "stage": "Activities Generated",
        "message": f"Generated {len(all_activities)} activities before deduplication",
        "count": len(all_activities)
    })

    logger.info(f"Final activity count: {len(unique_activities)} (after deduplication from {len(all_activities)})")
    state.logs.append({
        "stage": "Activities Deduplicated",
        "message": f"Deduplicated to {len(unique_activities)} activities",
        "count": len(unique_activities)
    })
    
    # Store in catalog and attempt to cache for future reuse
    state.plan.activities_catalog = _format_activity_response(unique_activities)
    try:
        _save_cached_activities(p.destination, p.hobbies, state.plan.activities_catalog)
    except Exception:
        pass
    
    # Distribute activities across days
    itinerary = distribute_activities_across_days(unique_activities, state)
    state.plan.itinerary = itinerary
    state.logs.append({
        "stage": "Itinerary Drafted",
        "message": f"Drafted itinerary with {len(itinerary)} days",
        "days": len(itinerary)
    })
    
    logger.info(f"Google Places + LLM agent: Generated {len(unique_activities)} activities")
    
    return state


def _expand_places_with_generator(places: List[Dict], hobby: str, destination: str, budget_level: str, price_ranges: Dict) -> List[Activity]:
    """Expand real venues into multiple activities using the generator step."""
    
    # Create venue context for LLM
    venue_context = []
    for place in places[:5]:  # Top 5 places
        venue_context.append({
            "name": place.get("name", ""),
            "address": place.get("vicinity", place.get("formatted_address", "")),
            "rating": place.get("rating"),
            "types": place.get("types", [])
        })
    
    # Get price range for this hobby category
    category = _categorize_hobby(hobby)
    price_range = price_ranges.get(budget_level, price_ranges["mid"]).get(category, (20, 50))
    
    prompt = f"""Given these real venues in {destination} for {hobby}, create 6 diverse activities.

REAL VENUES:
{json.dumps(venue_context, indent=2)}

Create 6 different activities using these venues. Each activity should:
- Use actual venue names and addresses from the list above
- Be specific to {hobby} 
- Include realistic pricing ${price_range[0]}-${price_range[1]}
- Have appropriate duration (1.5-4 hours)
- Be diverse (beginner/advanced, solo/group, different times of day)

Return JSON array of activities:
[{{"title": "activity name", "location": "venue name, address", "duration_hours": 2.5, "est_price": 45, "currency": "USD"}}]"""

    try:
        response = call_gpt(
            prompt=prompt,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response)
        activities = []
        
        for item in data.get("activities", data if isinstance(data, list) else []):
            try:
                activity = Activity(
                    title=str(item.get("title", f"{hobby} activity")).strip(),
                    location=str(item.get("location", destination)).strip(),
                    duration_hours=float(item.get("duration_hours", 2.5)),
                    est_price=float(item.get("est_price", 0)) if item.get("est_price") else None,
                    currency=str(item.get("currency", "USD")).strip(),
                    tags=[hobby.lower(), "places", "generated"]
                )
                activities.append(activity)
            except Exception as e:
                logger.warning(f"Failed to create activity from places expansion: {e}")
                continue
        
        return activities
        
    except Exception as e:
        logger.error(f"Places expansion failed for {hobby}: {e}")
        return []


def _generate_fallback_activities(hobby: str, destination: str, budget_level: str, price_ranges: Dict) -> List[Activity]:
    """Generate activities using a seeded fallback when Places data is limited."""
    
    # Get price range for this hobby category
    category = _categorize_hobby(hobby)
    price_range = price_ranges.get(budget_level, price_ranges["mid"]).get(category, (20, 50))
    
    # Seeded venue knowledge for common destinations
    venue_seeds = _get_venue_seeds(destination, hobby)
    
    prompt = f"""Create 6 diverse {hobby} activities in {destination}.

CONTEXT: Include well-known venues and areas in {destination} for {hobby}.
{f"KNOWN VENUES: {venue_seeds}" if venue_seeds else ""}

Each activity should:
- Use real/realistic venue names in {destination}
- Be specific to {hobby}
- Include realistic pricing ${price_range[0]}-${price_range[1]}
- Have appropriate duration (1.5-4 hours)
- Be diverse (beginner/advanced, solo/group, morning/evening)
- Include specific location details

Return JSON array:
[{{"title": "activity name", "location": "specific venue, area, {destination}", "duration_hours": 2.5, "est_price": 45, "currency": "USD"}}]"""

    try:
        response = call_gpt(
            prompt=prompt,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response)
        activities = []
        
        for item in data.get("activities", data if isinstance(data, list) else []):
            try:
                activity = Activity(
                    title=str(item.get("title", f"{hobby} activity")).strip(),
                    location=str(item.get("location", destination)).strip(),
                    duration_hours=float(item.get("duration_hours", 2.5)),
                    est_price=float(item.get("est_price", 0)) if item.get("est_price") else None,
                    currency=str(item.get("currency", "USD")).strip(),
                    tags=[hobby.lower(), "fallback", "seeded"]
                )
                activities.append(activity)
            except Exception as e:
                logger.warning(f"Failed to create activity from LLM fallback: {e}")
                continue
        
        logger.info(f"Generated {len(activities)} activities from LLM fallback for {hobby}")
        return activities
        
    except Exception as e:
        logger.error(f"LLM fallback failed for {hobby}: {e}")
        return []


def _categorize_hobby(hobby: str) -> str:
    """Categorize hobby for pricing"""
    hobby_lower = hobby.lower()
    if any(word in hobby_lower for word in ["dining", "restaurant", "food", "cuisine"]):
        return "dining"
    elif any(word in hobby_lower for word in ["nightlife", "bar", "club", "entertainment", "music"]):
        return "entertainment"
    else:
        return "activities"


def _get_venue_seeds(destination: str, hobby: str) -> str:
    """Get known venue seeds for popular destinations"""
    dest_lower = destination.lower()
    hobby_lower = hobby.lower()
    
    # Basic venue knowledge for major destinations
    venues = {
        "dubai": {
            "golf": "Emirates Golf Club, Jumeirah Golf Estates, Dubai Creek Golf Club, Arabian Ranches Golf Club",
            "fine dining": "Zuma Dubai, La Petite Maison, At.mosphere, Nobu Dubai, Pierchic",
            "nightlife": "White Dubai, Zero Gravity, Soho Garden, Red Bar, 40 Kong"
        },
        "paris": {
            "fine dining": "Le Jules Verne, L'Ambroisie, Guy Savoy, Alain Ducasse au Plaza Athénée",
            "nightlife": "Hemingway Bar, Buddha-Bar, L'Arc Paris, VIP Room"
        },
        "london": {
            "fine dining": "Sketch, Dinner by Heston, Gordon Ramsay, Rules Restaurant",
            "nightlife": "Fabric, Ministry of Sound, Ronnie Scott's, Sky Garden"
        },
        "tokyo": {
            "fine dining": "Sukiyabashi Jiro, Narisawa, Joël Robuchon, Tempura Kondo",
            "nightlife": "Golden Gai, Robot Restaurant, New York Grill, Womb"
        }
    }
    
    for dest_key, dest_venues in venues.items():
        if dest_key in dest_lower:
            for hobby_key, venue_list in dest_venues.items():
                if hobby_key in hobby_lower or any(word in hobby_lower for word in hobby_key.split()):
                    return venue_list
    
    return ""

