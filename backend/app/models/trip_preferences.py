from pydantic import BaseModel
from datetime import date
from typing import List, Literal, Dict

class TravelerPrefs(BaseModel):
    origin: str
    destination: str
    start_date: date
    end_date: date
    adults: int = 2
    budget_level: Literal["low","mid","high"] = "mid"
    hobbies: List[str] = []
    trip_type: str = "custom"
    constraints: Dict[str, str] = {}
