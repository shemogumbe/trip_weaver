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

    print(f"flight raw data %s {raw}")

    raw_results = raw.get("results", [])

    refined = refine_flights_with_llm(raw_results, state=state)

    if not refined:
        candidates = process_flights(raw_results, state.prefs)  # your existing parser
        state.plan.flights = candidates
    else:
        state.plan.flights = refined

    return state
    

def stay_agent(state: RunState) -> RunState:
    p = state.prefs
    q = f"hotels in {p.destination} under $250/night {p.start_date}"
    raw = t_search(q, max_results=8)
    # print(f"stay raw data {raw}")
    candidates = process_stays(raw.get("results", []), p)
    state.plan.stays = refine_with_gpt([c.dict() for c in candidates], "Stays")
    return state


def activities_agent(state: RunState) -> RunState:
    p = state.prefs
    all_candidates = []

    for hobby in p.hobbies:
        q = f"{hobby} in {p.destination} price schedule {p.start_date}"
        raw = t_search(q, max_results=6)
        # print(f"activities raw data {raw}")
        candidates = process_activities(raw.get("results", []), p, q)
        all_candidates.extend(candidates)

    state.plan.activities_catalog = refine_with_gpt(
        [c.dict() for c in all_candidates], "Activities"
    )
    return state

def budget_agent(state: RunState) -> RunState:
    nights = (state.prefs.end_date - state.prefs.start_date).days
    stay_low = min([s.est_price_per_night for s in state.plan.stays if s.est_price_per_night] or [60])
    flights_mid = sorted([f.est_price for f in state.plan.flights if f.est_price] or [500])[0]
    activities_mid = sum([a.est_price or 30 for a in state.plan.activities_catalog[:6]]) / max(1, len(state.plan.activities_catalog[:6]))
    total_est = flights_mid + nights * (stay_low + activities_mid)
    state.plan.budget_summary = {
        "nights": nights,
        "flight_est": flights_mid,
        "stay_per_night_est": stay_low,
        "activity_avg_est": activities_mid,
        "trip_total_est": round(total_est, 2)
    }
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
