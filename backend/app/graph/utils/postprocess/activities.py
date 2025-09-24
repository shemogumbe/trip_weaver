import re
from app.graph.utils.general_utils import normalize_price
from app.models.entities import Activity

def process_activities(results, prefs, query):
    activities = []
    for r in results:
        text = r.get("content", "")
        url = r.get("url")

        price = normalize_price(text)
        if not price:
            continue

        dur_match = re.search(r"(\d+)\s*(hours?|hrs?)", text.lower())
        duration = float(dur_match.group(1)) if dur_match else (
            4 if "half day" in text.lower() else 8 if "full day" in text.lower() else 2
        )

        activities.append(Activity(
            title=r.get("title") or "Activity",
            location=prefs.destination,
            duration_hours=duration,
            est_price=price,
            source_url=url,
            tags=[query],
        ))

    return activities
