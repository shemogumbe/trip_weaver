from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.models.entities import FlightOption, StayOption, Activity, DayPlan
from pydantic import BaseModel, Field



class TripPlan(BaseModel):
    flights: List[FlightOption] = []
    stays: List[StayOption] = []
    activities_catalog: List[Activity] = []
    activities_budget: Optional[float] = None
    activities: List[Dict[str, Any]] = Field(default_factory=list)

    itinerary: List[DayPlan] = []
    budget_summary: Dict[str, Any] = {}
    sources: Dict[str, Any] = {}
    itinerary: List[DayPlan] = Field(default_factory=list)



class RunState(BaseModel):
    prefs: Any
    plan: TripPlan = TripPlan()
    artifacts: Dict[str, Any] = {}
    done: bool = False
    logs: List[dict] = []
