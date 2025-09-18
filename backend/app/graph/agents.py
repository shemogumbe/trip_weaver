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
from app.integrations.tavily_client import t_search, t_extract, t_map
from app.graph.postprocess.refine_stays_with_llm import refine_stays_with_llm
from app.graph.postprocess.refine_activities_with_llm import refine_activities_with_llm


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def destination_research(state: RunState) -> RunState:
    q = f"{state.prefs.destination} neighborhoods best areas to stay safety transport 2025"
    sres = t_search(q, max_results=8)
    mres = t_map(f"top things to do in {state.prefs.destination} 2025")
    state.artifacts["destination_research"] = {"search": sres, "map": mres}
    # keep a small source index
    for item in sres.get("results", []):
        state.plan.sources[item["url"]] = {"title": item.get("title"), "snippet": item.get("content")}
    return state

def flight_agent(state: RunState) -> RunState:
    p = state.prefs
    q = f"{p.origin} to {p.destination} direct flight schedule {p.start_date}"
    raw = t_search(q, max_results=8)


    raw_results = raw.get("results", [])

    refined = refine_flights_with_llm(raw_results, state=state)
    print(f"Refined flights: {refined}")

    if not refined:
        candidates = process_flights(raw_results, state.prefs)  # your existing parser
        state.plan.flights = candidates
    else:
        state.plan.flights = refined

    return state
    

def stay_agent(state: RunState) -> RunState:
    p = state.prefs
    q = f"hotels in {p.destination} {p.start_date}"
    raw = t_search(q, max_results=6)

    raw_results = raw.get("results", [])

    refined = refine_stays_with_llm(raw_results, state=state)
    print(f"Refined stays: {refined}")

    if not refined:
        candidates = process_stays(raw_results, p)  # your existing parser
        state.plan.stays = candidates
    else:
        state.plan.stays = refined

    return state



def activities_agent(state: RunState) -> RunState:
    p = state.prefs
    all_candidates = []

    # Collect and process per hobby
    for hobby in p.hobbies:
        q = f"{hobby} in {p.destination} price schedule {p.start_date}"
        raw = t_search(q, max_results=6)
        raw_results = raw.get("results", [])
        
        # Fallback parser needs query
        if not raw_results:
            continue

        candidates = process_activities(raw_results, p, q)
        all_candidates.extend(candidates)

    # Step 1: refine into Activity objects
    refined = refine_activities_with_llm([c.dict() for c in all_candidates], state=state)
    print(f"Refined activities: {refined}")

    if not refined:
        refined = all_candidates  # fallback already Activity objects

    # store refined activities into the plan's catalog so later steps (itinerary_synthesizer)
    # can build daily plans from the same source. Without this, the synthesizer will
    # see an empty catalog and produce empty day slots.
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
