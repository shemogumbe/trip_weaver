from app.graph.utils import  normalize_price, extract_times
from app.models.entities import FlightOption

def process_flights(results, prefs):
    options = []
    airlines = ["kenya airways", "emirates", "qatar", "etihad"]

    for r in results:
        text = r.get("content", "").lower()
        url = r.get("url")

        airline = next((a for a in airlines if a in text), None)
        if not airline:
            continue

        depart, arrive = extract_times(r.get("content", ""))
        price = normalize_price(r.get("content", ""))
        if not price:
            continue

        options.append(FlightOption(
            summary=f"{airline.title()} flight {prefs.origin} → {prefs.destination}",
            depart_time=depart,
            arrive_time=arrive,
            airline=airline,
            stops=0 if "nonstop" in text or "direct" in text else 1,
            est_price=price,
            booking_links=[url],
        ))

    return options
