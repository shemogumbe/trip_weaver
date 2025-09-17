from pydantic import BaseModel
from typing import List, Dict, Any
from app.models.entities import FlightOption, StayOption, Activity, DayPlan


class TripPlan(BaseModel):
    flights: List[FlightOption] = []
    stays: List[StayOption] = []
    activities_catalog: List[Activity] = []
    itinerary: List[DayPlan] = []
    budget_summary: Dict[str, Any] = {}
    sources: Dict[str, Any] = {}


class RunState(BaseModel):
    prefs: Any
    plan: TripPlan = TripPlan()
    artifacts: Dict[str, Any] = {}
    done: bool = False
