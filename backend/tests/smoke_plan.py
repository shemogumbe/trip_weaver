"""Minimal smoke test for the planning pipeline.

Run locally: `python backend/tests/smoke_plan.py`
"""

from datetime import date
from app.graph.state import RunState
from app.models.trip_preferences import TravelerPrefs
from app.graph.build_graph import build_graph


def main():
    prefs = TravelerPrefs(
        origin="NBO",
        destination="Dubai",
        start_date=date(2025, 11, 10),
        end_date=date(2025, 11, 16),
        hobbies=["golf", "fine dining"],
        adults=2,
        budget_level="mid",
        trip_type="vacation",
        constraints={},
    )
    state = RunState(prefs=prefs)
    graph = build_graph()
    result = graph.invoke(state)
    plan = result["plan"]
    print("Flights:", len(plan.get("flights", [])))
    print("Stays:", len(plan.get("stays", [])))
    print("Activities:", len(plan.get("activities", [])))
    print("Itinerary days:", len(plan.get("itinerary", [])))


if __name__ == "__main__":
    main()
