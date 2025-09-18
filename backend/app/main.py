
import json
from datetime import date
from pydantic import BaseModel
from app.models.trip_preferences import TravelerPrefs
from app.graph.state import RunState
from app.graph.build_graph import build_graph


def _to_dict(obj):
    """Convert BaseModel or dict to plain dict, else return None."""
    if obj is None:
        return None
    if isinstance(obj, BaseModel):
        return obj.dict()
    if isinstance(obj, dict):
        return obj
    return None


def _prune(d: dict, keys: list):
    return {k: d.get(k) for k in keys if d.get(k) is not None}


def format_plan(plan: BaseModel) -> dict:
    # flights
    flights_out = []
    for f in getattr(plan, "flights", []) or []:
        fd = _to_dict(f)
        if not fd:
            continue
        flights_out.append(_prune(fd, ["summary", "depart_time", "arrive_time", "airline", "stops", "est_price", "booking_links"]))

    # stays
    stays_out = []
    for s in getattr(plan, "stays", []) or []:
        sd = _to_dict(s)
        if not sd:
            continue
        stays_out.append(_prune(sd, ["name", "area", "est_price_per_night", "score", "booking_links"]))

    # itinerary / activities
    itinerary_out = []
    for day in getattr(plan, "itinerary", []) or []:
        dd = _to_dict(day) or day
        # date handling
        date_val = dd.get("date") if isinstance(dd, dict) else None

        def serialize_slot(slot):
            # slot may be None, list, BaseModel, or dict
            if slot is None:
                return None
            if isinstance(slot, list):
                if len(slot) == 0:
                    return None
                slot = slot[0]
            sd = _to_dict(slot) or slot if isinstance(slot, dict) else None
            if sd is None and isinstance(slot, dict):
                sd = slot
            if sd is None:
                return None
            return _prune(sd, ["title", "location", "duration_hours", "est_price", "source_url", "tags"])

        morning = serialize_slot(dd.get("morning") if isinstance(dd, dict) else getattr(day, "morning", None))
        afternoon = serialize_slot(dd.get("afternoon") if isinstance(dd, dict) else getattr(day, "afternoon", None))
        evening = serialize_slot(dd.get("evening") if isinstance(dd, dict) else getattr(day, "evening", None))

        itinerary_out.append({"date": date_val, "morning": morning, "afternoon": afternoon, "evening": evening})
    # If the synthesized itinerary has empty slots for all days, try to build a
    # simple schedule from the activities_catalog as a fallback so API output
    # isn't all-empty. This keeps downstream formatting idempotent and avoids
    # changing upstream agents here.
    all_empty = all(d["morning"] is None and d["afternoon"] is None and d["evening"] is None for d in itinerary_out)
    if all_empty:
        catalog = getattr(plan, "activities_catalog", []) or []
        # convert catalog items to dicts
        cat = [_to_dict(c) if not isinstance(c, dict) else c for c in catalog]
        ci = 0
        scheduled = []
        for d in getattr(plan, "itinerary", []) or []:
            dd = _to_dict(d) or d
            date_val = dd.get("date") if isinstance(dd, dict) else None
            morning = None
            afternoon = None
            evening = None
            if ci < len(cat):
                morning = _prune(cat[ci], ["title", "location", "duration_hours", "est_price", "source_url", "tags"]) if cat[ci] else None
                ci += 1
            if ci < len(cat):
                afternoon = _prune(cat[ci], ["title", "location", "duration_hours", "est_price", "source_url", "tags"]) if cat[ci] else None
                ci += 1
            if ci < len(cat):
                evening = _prune(cat[ci], ["title", "location", "duration_hours", "est_price", "source_url", "tags"]) if cat[ci] else None
                ci += 1
            scheduled.append({"date": date_val, "morning": morning, "afternoon": afternoon, "evening": evening})
        itinerary_out = scheduled

    return {"flights": flights_out, "stays": stays_out, "activities": itinerary_out}


if __name__ == "__main__":
    prefs = TravelerPrefs(
        origin="NBO",
        destination="Lagos",
        start_date=date(2025, 11, 10),
        end_date=date(2025, 11, 16),
        hobbies=["night life", "fine dining"],
        trip_type="honeymoon"
    )
    state = RunState(prefs=prefs)
    graph = build_graph()
    result = graph.invoke(state)

    plan = result["plan"]
    formatted = format_plan(plan)
    response = {"plan": formatted, "logs": result.get("logs", [])}
    print(json.dumps(response, indent=2, default=str))

