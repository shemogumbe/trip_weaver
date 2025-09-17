from .state import RunState
from app.models.entities import FlightOption, StayOption, Activity, DayPlan
from app.graph.utils import pick, normalize_price, ensure_time_feasible, split_days

from app.integrations.tavily_client import t_search, t_extract, t_map

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
    q = f'flights {p.origin} to {p.destination} {p.start_date} to {p.end_date} cheapest 1 stop 2025'
    sres = t_search(q, max_results=6)
    urls = [r["url"] for r in sres.get("results", [])][:6]
    ex = t_extract(urls)
    state.artifacts["flights"] = {"search": sres, "extract": ex}

    options: list[FlightOption] = []
    for r in sres.get("results", []):
        # very lightweight heuristic parse from snippets
        content = (r.get("content") or "")[:500].lower()
        if "flight" in content or "price" in content:
            options.append(FlightOption(
                summary=r.get("title","flight option"),
                depart_time="TBD", arrive_time="TBD",
                airline=pick(content, ["emirates","qatar","klm","turkish","british","etihad"]) or "various",
                stops=0 if "direct" in content else (1 if "1 stop" in content else 2),
                est_price=normalize_price(content),
                booking_links=[r["url"]],
            ))
    state.plan.flights = options[:8]
    return state

def stay_agent(state: RunState) -> RunState:
    p = state.prefs
    q = f"best hotels and airbnbs in {p.destination} 2025 near city center family friendly rating"
    sres = t_search(q, max_results=10)
    ex = t_extract([r["url"] for r in sres["results"][:10]])
    state.artifacts["stays"] = {"search": sres, "extract": ex}

    options: list[StayOption] = []
    for r in sres.get("results", []):
        content = (r.get("content") or "")[:400]
        options.append(StayOption(
            name=r.get("title","Hotel"),
            area=p.destination,
            est_price_per_night=normalize_price(content),
            score=None,
            highlights=[],
            booking_links=[r["url"]],
        ))
    state.plan.stays = options[:10]
    return state

def activities_agent(state: RunState) -> RunState:
    p = state.prefs
    queries = [
        f"best {hobby} activities in {p.destination} 2025" for hobby in (p.hobbies or ["things to do"])
    ]
    activities = []
    all_urls = []
    for q in queries:
        s = t_search(q, max_results=6)
        state.plan.sources.update({r["url"]: {"title": r["title"]} for r in s.get("results", [])})
        all_urls += [r["url"] for r in s.get("results", [])]
    ex = t_extract(all_urls[:12])
    state.artifacts["activities"] = {"extract": ex}

    for item in ex.get("results", []):
        title = item.get("title") or "Activity"
        url = item.get("url")
        snippet = (item.get("content") or "")[:500]
        activities.append(Activity(
            title=title,
            location=p.destination,
            duration_hours=2.0,
            est_price=normalize_price(snippet),
            source_url=url,
            tags=[t for t in p.hobbies],
        ))
    state.plan.activities_catalog = activities[:20]
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
