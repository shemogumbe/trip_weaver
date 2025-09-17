# app/models/entities.py
from pydantic import BaseModel
from typing import List, Optional


class FlightOption(BaseModel):
    summary: str
    depart_time: str
    arrive_time: str
    airline: str
    stops: int
    est_price: Optional[float] = None
    booking_links: List[str] = []


class StayOption(BaseModel):
    name: str
    area: str
    est_price_per_night: Optional[float] = None
    score: Optional[float] = None
    highlights: List[str] = []
    booking_links: List[str] = []


class Activity(BaseModel):
    title: str
    location: str
    duration_hours: float
    est_price: Optional[float] = None
    source_url: Optional[str] = None
    tags: List[str] = []


class DayPlan(BaseModel):
    date: str
    morning: List[Activity] = []
    afternoon: List[Activity] = []
    evening: List[Activity] = []
    notes: List[str] = []
