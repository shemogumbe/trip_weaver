import os
import time
import logging
import asyncio
from datetime import timedelta
from typing import List, Dict, Any

from .state import RunState
from app.models.entities import Activity
from app.graph.utils.general_utils import split_days
from app.graph.utils.postprocess.flights import process_flights
from app.graph.utils.postprocess.stays import process_stays
from app.graph.utils.postprocess.refine_flights_with_llm import refine_flights_with_llm
from app.graph.utils.postprocess.refine_stays_with_llm import refine_stays_with_llm
from app.integrations.tavily_client import (
    t_search,
    t_map,
    enhance_search_with_extraction,
    t_crawl,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SPEED_MODE = os.getenv("SPEED_MODE", "1") == "1"


async def async_destination_research(state: RunState) -> Dict[str, Any]:
    start_time = time.time()
    destination = state.prefs.destination
    logger.info(f"🔍 Starting destination research for {destination}")

    all_search_results = []
    if SPEED_MODE:
        query = f"travel guide {destination} attractions restaurants hotels"
        result = t_search(query, max_results=3, search_depth="basic")
        all_search_results = result.get("results", [])
        all_map_results = []
        crawl_results = []
    else:
        research_queries = [
            f"travel guide {destination} 2025 attractions restaurants hotels",
            f"best time visit {destination} weather climate travel tips",
            f"{destination} travel requirements visa passport entry",
        ]
        for query in research_queries:
            search_data = enhance_search_with_extraction(query, max_results=4)
            all_search_results.extend(search_data.get("combined_results", []))
        map_queries = [
            f"{destination} travel map tourist attractions",
            f"{destination} neighborhoods areas districts",
        ]
        all_map_results = []
        for map_query in map_queries:
            map_result = t_map(map_query)
            if map_result.get("results") and not map_result.get("error"):
                all_map_results.extend(map_result["results"])
        travel_urls = [
            result.get("url", "")
            for result in all_search_results
            if any(
                site in result.get("url", "").lower()
                for site in ["lonelyplanet.com", "tripadvisor.com", "timeout.com"]
            )
        ]
        crawl_results = []
        if travel_urls:
            crawl_result = t_crawl(travel_urls[:1], max_depth=1, max_breadth=2)
            crawl_results = crawl_result.get("results", [])

    all_sources = all_search_results + (
        all_map_results if not SPEED_MODE else []
    ) + (crawl_results if not SPEED_MODE else [])
    sources = {}
    for item in all_sources:
        url = item.get("url", "")
        if isinstance(url, dict):
            url = url.get("url", "") or url.get("href", "") or str(url)
        if url and isinstance(url, str):
            sources[url] = {
                "title": item.get("title", ""),
                "snippet": (
                    item.get("content", "")[:200] + "..."
                    if len(item.get("content", "")) > 200
                    else item.get("content", "")
                ),
            }

    elapsed = time.time() - start_time
    logger.info(f"✅ Destination research completed in {elapsed:.2f}s")

    return {
        "sources": sources,
        "research_data": {
            "search": {"results": all_search_results},
            "map": {"results": all_map_results},
            "crawl": {"results": crawl_results},
        },
    }


async def async_flight_agent(state: RunState) -> Dict[str, Any]:
    start_time = time.time()
    p = state.prefs
    logger.info(f"✈️ Starting flight search: {p.origin} → {p.destination}")

    all_results = []
    if SPEED_MODE:
        queries = [f"{p.origin} to {p.destination} flights {p.start_date} nonstop"]
        for query in queries:
            data = t_search(query, max_results=3, search_depth="basic")
            all_results.extend(data.get("results", []))
    else:
        queries = [
            f"{p.origin} to {p.destination} flights {p.start_date} direct nonstop",
            f"{p.origin} {p.destination} airline schedule {p.start_date}",
            f"flights from {p.origin} to {p.destination} {p.start_date} booking",
        ]
        for query in queries:
            enhanced_data = enhance_search_with_extraction(query, max_results=6)
            all_results.extend(enhanced_data.get("combined_results", []))
        airline_urls = []
        for result in all_results:
            url = result.get("url", "")
            if isinstance(url, dict):
                url = url.get("url", "") or url.get("href", "") or str(url)
            if url and isinstance(url, str) and any(
                site in url.lower() for site in ["kenya-airways.com", "klm.com", "emirates.com"]
            ):
                airline_urls.append(url)
        if airline_urls:
            crawl_result = t_crawl(airline_urls[:1], max_depth=1, max_breadth=2)
            all_results.extend(crawl_result.get("results", []))

    seen_urls = set()
    unique_results = []
    for result in all_results:
        url = result.get("url", "")
        if isinstance(url, dict):
            url = url.get("url", "") or url.get("href", "") or str(url)
        if url and isinstance(url, str) and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)

    logger.info(f"Flight agent collected {len(unique_results)} unique results")

    if SPEED_MODE:
        flights = process_flights(unique_results, state.prefs)
    else:
        refined = refine_flights_with_llm(unique_results, state=state)
        flights = refined if refined else process_flights(unique_results, state.prefs)

    elapsed = time.time() - start_time
    logger.info(f"✅ Flight agent completed in {elapsed:.2f}s - found {len(flights)} flights")
    return {"flights": flights}


async def async_stay_agent(state: RunState) -> Dict[str, Any]:
    start_time = time.time()
    p = state.prefs
    logger.info(f"🏨 Starting hotel search in {p.destination}")

    all_results = []
    if SPEED_MODE:
        queries = [f"hotels in {p.destination} {p.start_date} {p.end_date}"]
        for query in queries:
            data = t_search(query, max_results=3, search_depth="basic")
            all_results.extend(data.get("results", []))
    else:
        queries = [
            f"hotels in {p.destination} {p.start_date} {p.end_date}",
            f"best hotels {p.destination} {p.trip_type} accommodation",
            f"{p.destination} hotels booking.com expedia.com {p.start_date}",
        ]
        for query in queries:
            enhanced_data = enhance_search_with_extraction(query, max_results=5)
            all_results.extend(enhanced_data.get("combined_results", []))
        map_query = f"best areas to stay in {p.destination} hotels neighborhoods"
        map_result = t_map(map_query)
        if map_result.get("results") and not map_result.get("error"):
            all_results.extend(map_result["results"])
        booking_urls = []
        for result in all_results:
            url = result.get("url", "")
            if isinstance(url, dict):
                url = url.get("url", "") or url.get("href", "") or str(url)
            if url and isinstance(url, str) and any(
                site in url.lower() for site in ["booking.com", "expedia.com", "hotels.com"]
            ):
                booking_urls.append(url)
        if booking_urls:
            crawl_result = t_crawl(booking_urls[:1], max_depth=1, max_breadth=3)
            all_results.extend(crawl_result.get("results", []))

    seen_urls = set()
    unique_results = []
    for result in all_results:
        url = result.get("url", "")
        if isinstance(url, dict):
            url = url.get("url", "") or url.get("href", "") or str(url)
        if url and isinstance(url, str) and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)

    logger.info(f"Stay agent collected {len(unique_results)} unique results")

    if SPEED_MODE:
        stays = process_stays(unique_results, p)
    else:
        refined = refine_stays_with_llm(unique_results, state=state)
        stays = refined if refined else process_stays(unique_results, p)

    elapsed = time.time() - start_time
    logger.info(f"✅ Stay agent completed in {elapsed:.2f}s - found {len(stays)} hotels")
    return {"stays": stays}


async def async_activities_agent(state: RunState) -> Dict[str, Any]:
    start_time = time.time()
    p = state.prefs
    logger.info(f"🎯 Starting optimized activities search for {p.destination} (OpenAI + 1 Tavily call)")

    context_query = f"travel guide {p.destination} popular attractions 2025"
    search_result = t_search(context_query, max_results=3, search_depth="basic")
    search_results = search_result.get("results", [])

    activities = await async_generate_activities_with_openai(state)
    if not activities:
        activities = [
            Activity(
                title=f"Explore {p.destination} city center",
                location=f"{p.destination} downtown",
                duration_hours=3.0,
                est_price=10.0,
                tags=["sightseeing", "walking"],
            ),
            Activity(
                title=f"Local restaurant in {p.destination}",
                location=f"{p.destination}",
                duration_hours=1.5,
                est_price=25.0,
                tags=["dining", "local cuisine"],
            ),
        ]

    itinerary = distribute_activities_across_days(activities, state)

    elapsed = time.time() - start_time
    logger.info(
        f"✅ Activities agent completed in {elapsed:.2f}s - generated {len(activities)} activities"
    )

    return {
        "activities_catalog": activities,
        "itinerary": itinerary,
        "activities_context": {"search_results": search_results[:3]},
    }


async def async_generate_activities_with_openai(state: RunState) -> List[Activity]:
    from app.integrations.openai_client import call_gpt
    import json
    p = state.prefs
    total_days = (p.end_date - p.start_date).days + 1
    activity_days = max(1, total_days - 2)
    total_slots = activity_days * 3
    hobbies_text = ", ".join(p.hobbies) if p.hobbies else "general tourism"
    prompt = f"""You are a travel expert creating a detailed activity itinerary for {p.destination}.

TRIP DETAILS:
- Destination: {p.destination}
- Trip Duration: {total_days} days ({activity_days} activity days)
- Travel Dates: {p.start_date} to {p.end_date}
- Traveler Interests: {hobbies_text}
- Trip Type: {p.trip_type}
- Need {total_slots} activities total (morning/afternoon/evening slots)

REQUIREMENTS:
- Generate exactly {total_slots} diverse activities
- Include mix of: attractions, dining, entertainment, cultural experiences
- Match traveler interests: {hobbies_text}
- Provide realistic prices in USD
- Include specific locations within {p.destination}
- Duration should vary: 1-6 hours per activity
- Mix of different price ranges (budget to premium)

RESPONSE FORMAT (JSON only):
{
  "activities": [
    {
      "title": "Specific activity name",
      "location": "Exact location/area in {p.destination}",
      "duration_hours": 2.5,
      "est_price": 45.0,
      "tags": ["tag1", "tag2", "tag3"]
    }
  ]
}

Generate {total_slots} activities that create a perfect {total_days}-day itinerary for {p.destination}."""
    try:
        structured = call_gpt(prompt, model="gpt-4o-mini")
        if isinstance(structured, str):
            structured = json.loads(structured)
        activities: List[Activity] = []
        for a in structured.get("activities", []):
            try:
                activities.append(
                    Activity(
                        title=a.get("title", ""),
                        location=a.get("location", p.destination),
                        duration_hours=float(a.get("duration_hours", 2.0)),
                        est_price=float(a.get("est_price", 30.0)),
                        tags=a.get("tags", []),
                    )
                )
            except Exception:
                continue
        return activities[:total_slots]
    except Exception:
        return []


def distribute_activities_across_days(activities: List[Activity], state: RunState):
    p = state.prefs
    total_days = (p.end_date - p.start_date).days + 1
    available_days = list(range(total_days)) if total_days <= 2 else list(range(1, total_days - 1))
    itinerary = []
    idx = 0
    for day_num in range(total_days):
        date = (p.start_date + timedelta(days=day_num)).isoformat()
        day_plan = {"date": date, "morning": None, "afternoon": None, "evening": None}
        if day_num in available_days:
            if idx < len(activities):
                day_plan["morning"] = activities[idx]; idx += 1
            if idx < len(activities):
                day_plan["afternoon"] = activities[idx]; idx += 1
            if idx < len(activities):
                day_plan["evening"] = activities[idx]; idx += 1
        itinerary.append(day_plan)
    return itinerary


def calculate_budget(activities: List[Activity]) -> float:
    if not activities:
        return 30.0
    prices = []
    for a in activities[:6]:
        prices.append(a.get("est_price") if isinstance(a, dict) else (a.est_price or 30))
    return sum(prices) / max(1, len(prices))


async def process_trip_async(state: RunState) -> RunState:
    overall_start = time.time()
    logger.info("🚀 Starting ASYNC trip processing pipeline...")
    dest_result = await async_destination_research(state)
    state.plan.sources = dest_result["sources"]
    state.artifacts.update(dest_result.get("research_data", {}))

    parallel_start = time.time()
    logger.info("⚡ Starting parallel data collection phase...")
    agent_timeout = int(os.getenv("AGENT_TIMEOUT_SECONDS", "20" if SPEED_MODE else "40"))

    async def with_timeout(coro, name: str):
        try:
            return await asyncio.wait_for(coro, timeout=agent_timeout)
        except Exception as e:
            logger.warning(f"⏱️ {name} timed out or failed: {e}")
            return e

    results = await asyncio.gather(
        with_timeout(async_flight_agent(state), "flight_agent"),
        with_timeout(async_stay_agent(state), "stay_agent"),
        with_timeout(async_activities_agent(state), "activities_agent"),
        return_exceptions=True,
    )

    flight_result, stay_result, activities_result = results
    if isinstance(flight_result, Exception):
        flight_result = {"flights": []}
    if isinstance(stay_result, Exception):
        stay_result = {"stays": []}
    if isinstance(activities_result, Exception):
        activities_result = {
            "activities_catalog": [],
            "itinerary": [
                {"date": d, "morning": None, "afternoon": None, "evening": None}
                for d in split_days(state.prefs.start_date, state.prefs.end_date)
            ],
            "activities_context": {"search_results": []},
        }

    parallel_elapsed = time.time() - parallel_start
    logger.info(f"⚡ Parallel phase completed in {parallel_elapsed:.2f}s")

    state.plan.flights = flight_result["flights"]
    state.plan.stays = stay_result["stays"]
    state.plan.activities_catalog = activities_result["activities_catalog"]
    state.plan.itinerary = activities_result["itinerary"]
    state.artifacts.update(activities_result.get("activities_context", {}))

    budget_start = time.time()
    state.plan.activities_budget = calculate_budget(state.plan.activities_catalog)
    budget_elapsed = time.time() - budget_start
    logger.info(f"✅ Budget calculation completed in {budget_elapsed:.2f}s")

    overall_elapsed = time.time() - overall_start
    logger.info(
        f"🎉 TOTAL ASYNC PIPELINE COMPLETED in {overall_elapsed:.2f}s"
    )
    logger.info(
        f"📊 Results: {len(state.plan.flights)} flights, {len(state.plan.stays)} hotels, {len(state.plan.activities_catalog)} activities"
    )
    return state
