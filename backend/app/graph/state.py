from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.models.entities import FlightOption, StayOption, Activity, DayPlan


class TripPlan(BaseModel):
    flights: List[FlightOption] = []
    stays: List[StayOption] = []
    activities_catalog: List[Activity] = []
    activities_budget: Optional[float] = None
    activities: List[Dict[str, Any]] = Field(default_factory=list)
    itinerary: List[DayPlan] = Field(default_factory=list)
    budget_summary: Dict[str, Any] = {}
    sources: Dict[str, Any] = {}


class RunState(BaseModel):
    prefs: Any
    plan: TripPlan = TripPlan()
    artifacts: Dict[str, Any] = {}
    done: bool = False
    logs: List[dict] = []
