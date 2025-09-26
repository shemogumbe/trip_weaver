from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.models.entities import FlightOption, StayOption, Activity, DayPlan



class TripPlan(BaseModel):
    flights: List[FlightOption] = Field(default_factory=list)
    stays: List[StayOption] = Field(default_factory=list)
    activities_catalog: List[Activity] = Field(default_factory=list)
    activities_budget: Optional[float] = None
    activities: List[Dict[str, Any]] = Field(default_factory=list)

    budget_summary: Dict[str, Any] = Field(default_factory=dict)
    sources: Dict[str, Any] = Field(default_factory=dict)
    itinerary: List[DayPlan] = Field(default_factory=list)



class RunState(BaseModel):
    prefs: Any
    plan: TripPlan = Field(default_factory=TripPlan)
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    done: bool = False
    logs: List[dict] = Field(default_factory=list)
