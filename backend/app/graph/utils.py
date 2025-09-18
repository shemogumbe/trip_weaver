import re
from datetime import date, timedelta
from typing import List, Optional


def pick(text: str, options: List[str]) -> Optional[str]:
    """
    Return the first option keyword found in text (case-insensitive).
    """
    if not text:
        return None
    text_lower = text.lower()
    for opt in options:
        if opt.lower() in text_lower:
            return opt
    return None


def normalize_price(text: str) -> Optional[float]:
    import re
    if not text:
        return None
    match = re.search(r"(\$|usd|eur|kes)?\s?([\d,]+\.?\d*)", text, re.IGNORECASE)
    if not match:
        return None
    try:
        value = float(match.group(2).replace(",", ""))
        # sanity filters
        if 5 < value < 10000:
            return value
    except ValueError:
        return None
    return None



def ensure_time_feasible(day_block: dict) -> dict:
    """
    Quick placeholder: ensure no duplicate activities per slot.
    In real implementation: enforce duration, no overlaps, opening hours, etc.
    """
    for slot in ["morning", "afternoon", "evening"]:
        if len(day_block.get(slot, [])) > 1:
            # keep only first activity for now
            day_block[slot] = day_block[slot][:1]
    return day_block


def split_days(start: date, end: date) -> List[str]:
    """
    Return list of ISO date strings for each day in the trip.
    """
    days = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days

def extract_times(text: str):
    """Find two times in HH:MM (with optional AM/PM)."""
    times = re.findall(r"\b([0-2]?\d:[0-5]\d(?:\s?(?:am|pm))?)\b", text)
    depart, arrive = (times + ["TBD", "TBD"])[:2]
    return depart, arrive

def extract_rating(text: str):
    """Extract hotel rating like 4.5/5."""
    match = re.search(r"(\d\.\d)\s*/\s*5", text)
    return float(match.group(1)) if match else None

def strip_listicle(title: str) -> bool:
    """Return True if it's a spammy listicle result."""
    return any(x in title.lower() for x in ["best", "top", "list", "10 ", "20 "])