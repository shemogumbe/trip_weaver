# app/models/entities.py
from pydantic import BaseModel
from typing import List, Optional


class FlightOption(BaseModel):
    summary: str
    depart_time: Optional[str] = None
    arrive_time: Optional[str] = None
    airline: Optional[str] = None
    flight_number: Optional[str] = None
    stops: Optional[int] = None
    est_price: Optional[float] = None
    booking_links: Optional[List[str]] = []
    source_url: Optional[str] = None
    source_title: Optional[str] = None

class StayOption(BaseModel):
    name: str
    area: str
    est_price_per_night: Optional[float] = None
    score: Optional[float] = None
    highlights: List[str] = []
    booking_links: List[str] = []
    source_url: Optional[str] = None
    source_title: Optional[str] = None


class Activity(BaseModel):
    title: str
    location: str
    duration_hours: Optional[float] = None
    est_price: Optional[float] = None
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    tags: List[str] = []


class DayPlan(BaseModel):
    date: str
    morning: List[Activity] = []
    afternoon: List[Activity] = []
    evening: List[Activity] = []
    notes: List[str] = []
