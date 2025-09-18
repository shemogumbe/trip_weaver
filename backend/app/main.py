
import json

from datetime import date
from app.models.trip_preferences import TravelerPrefs
from app.graph.state import RunState
from app.graph.build_graph import build_graph

if __name__ == "__main__":
    prefs = TravelerPrefs(
        origin="NBO",
        destination="Dubai",
        start_date=date(2025, 11, 10),
        end_date=date(2025, 11, 16),
        hobbies=["golf", "fine dining"],
        trip_type="honeymoon"
    )
    state = RunState(prefs=prefs)
    graph = build_graph()
    result = graph.invoke(state)

    # format response in json for returning via API
    response = {
        "plan": result["plan"],
        "logs": result.get("logs", [])
    }
    plan = result['plan']
    print(json.dumps(response, indent=2, default=str))

