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
    """
    Enhanced price extraction with better validation to avoid year/discount confusion.
    """
    import re
    if not text:
        return None
    
    # Remove common non-price numbers that could be confused
    text_clean = re.sub(r'\b(20\d{2}|19\d{2})\b', '', text)  # Remove years
    text_clean = re.sub(r'\b\d+%\s*(off|discount|sale)\b', '', text_clean, flags=re.IGNORECASE)  # Remove discount percentages
    
    # Look for price patterns with currency indicators
    price_patterns = [
        r'(\$|USD|usd)\s*([\d,]+\.?\d*)',  # $123.45 or USD 123.45
        r'([\d,]+\.?\d*)\s*(\$|USD|usd)',  # 123.45 USD
        r'(EUR|eur|€)\s*([\d,]+\.?\d*)',   # EUR 123.45 or €123.45
        r'([\d,]+\.?\d*)\s*(EUR|eur|€)',   # 123.45 EUR
        r'(KES|kes)\s*([\d,]+\.?\d*)',     # KES 123.45
        r'([\d,]+\.?\d*)\s*(KES|kes)',     # 123.45 KES
        r'price[:\s]*([\d,]+\.?\d*)',      # price: 123.45
        r'cost[:\s]*([\d,]+\.?\d*)',       # cost: 123.45
        r'from[:\s]*([\d,]+\.?\d*)',       # from: 123.45
        r'starting[:\s]*([\d,]+\.?\d*)',   # starting: 123.45
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            try:
                # Extract the numeric part
                if len(match.groups()) == 2:
                    value_str = match.group(2) if match.group(1) in ['$', 'USD', 'usd', 'EUR', 'eur', '€', 'KES', 'kes'] else match.group(1)
                else:
                    value_str = match.group(1)
                
                value = float(value_str.replace(",", ""))
                
                # Enhanced sanity filters for different contexts
                # Flight prices: typically $200-$2000
                # Hotel prices: typically $50-$1000 per night
                # Activity prices: typically $10-$500
                if 10 < value < 5000:  # Broader range to catch more valid prices
                    return value
            except (ValueError, IndexError):
                continue
    
    return None


def extract_currency(text: str) -> str:
    """
    Extract currency from text, defaulting to USD if not found.
    """
    if not text:
        return "USD"
    
    text_lower = text.lower()
    
    # Currency detection patterns
    if any(currency in text_lower for currency in ['$', 'usd', 'dollar']):
        return "USD"
    elif any(currency in text_lower for currency in ['€', 'eur', 'euro']):
        return "EUR"
    elif any(currency in text_lower for currency in ['kes', 'kenyan shilling']):
        return "KES"
    elif any(currency in text_lower for currency in ['£', 'gbp', 'pound']):
        return "GBP"
    else:
        return "USD"  # Default assumption


def validate_price_reasonableness(price: float, context: str, currency: str = "USD") -> bool:
    """
    Validate if a price is reasonable for the given context.
    """
    if not price or price <= 0:
        return False
    
    context_lower = context.lower()
    
    # Flight price validation
    if any(word in context_lower for word in ['flight', 'airline', 'plane', 'ticket']):
        if currency == "USD":
            return 100 <= price <= 3000  # $100-$3000 for flights
        elif currency == "EUR":
            return 80 <= price <= 2500   # €80-€2500 for flights
        elif currency == "KES":
            return 10000 <= price <= 300000  # KES 10k-300k for flights
    
    # Hotel price validation
    elif any(word in context_lower for word in ['hotel', 'accommodation', 'stay', 'room']):
        if currency == "USD":
            return 30 <= price <= 1000   # $30-$1000 per night
        elif currency == "EUR":
            return 25 <= price <= 800    # €25-€800 per night
        elif currency == "KES":
            return 3000 <= price <= 100000  # KES 3k-100k per night
    
    # Activity price validation
    elif any(word in context_lower for word in ['activity', 'tour', 'experience', 'ticket', 'entrance']):
        if currency == "USD":
            return 5 <= price <= 500     # $5-$500 for activities
        elif currency == "EUR":
            return 4 <= price <= 400     # €4-€400 for activities
        elif currency == "KES":
            return 500 <= price <= 50000  # KES 500-50k for activities
    
    # Default reasonable range
    return 5 <= price <= 1000



def ensure_time_feasible(day_block: dict) -> dict:
    """
    Enhanced scheduling with duration-based rules:
    - ≤ 4 hours → can schedule other activities that day
    - > 4 hours → following activity must be shorter (≤ 2–3 hours)
    - Very long (≥ 8 hours) → cancel other activities for that day
    """
    def get_activity_duration(activity):
        """Extract duration from activity, defaulting to 2 hours if not specified."""
        if isinstance(activity, dict):
            return activity.get("duration_hours", 2.0)
        elif hasattr(activity, 'duration_hours'):
            return activity.duration_hours or 2.0
        return 2.0
    
    def is_long_activity(duration):
        """Check if activity is considered long (≥ 8 hours)."""
        return duration >= 8.0
    
    def is_medium_activity(duration):
        """Check if activity is medium length (> 4 hours)."""
        return duration > 4.0
    
    # Process each slot
    for slot in ["morning", "afternoon", "evening"]:
        activities = day_block.get(slot, [])
        if not activities:
            continue
            
        # If multiple activities in same slot, keep only the first
        if len(activities) > 1:
            day_block[slot] = activities[:1]
            activities = day_block[slot]
        
        # Check for very long activities (≥ 8 hours) - cancel other slots
        for activity in activities:
            duration = get_activity_duration(activity)
            if is_long_activity(duration):
                # Clear other slots for the day
                for other_slot in ["morning", "afternoon", "evening"]:
                    if other_slot != slot:
                        day_block[other_slot] = []
                break
    
    # Check for medium activities (> 4 hours) and adjust following slots
    for slot_order in [("morning", "afternoon"), ("afternoon", "evening")]:
        current_slot, next_slot = slot_order
        current_activities = day_block.get(current_slot, [])
        
        for activity in current_activities:
            duration = get_activity_duration(activity)
            if is_medium_activity(duration):
                # Check if next slot has activities
                next_activities = day_block.get(next_slot, [])
                if next_activities:
                    # Keep only short activities (≤ 3 hours) in next slot
                    short_activities = []
                    for next_activity in next_activities:
                        next_duration = get_activity_duration(next_activity)
                        if next_duration <= 3.0:
                            short_activities.append(next_activity)
                    day_block[next_slot] = short_activities
                break
    
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