from fastapi import FastAPI
from datetime import date
from app.models.prefs import TravelerPrefs
from app.graph.state import RunState
from app.graph.build_graph import build_graph

app = FastAPI(title="TripWeaver Backend")
graph = build_graph()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/plan")
def plan(prefs: TravelerPrefs):
    state = RunState(prefs=prefs)
    result = graph.invoke(state)
    return {"plan": result.plan.dict()}
