from app.graph.utils import normalize_price, extract_rating, strip_listicle
from app.models.entities import StayOption

def process_stays(results, prefs, query=None):
    options = []
    for r in results:
        title = r.get("title", "").strip()
        text = r.get("content", "")
        url = r.get("url")

        if strip_listicle(title):
            continue

        price = normalize_price(text)
        if not price:
            continue

        score = extract_rating(text)

        options.append(StayOption(
            name=title or "Hotel",
            area=prefs.destination,
            est_price_per_night=price,
            score=score,
            highlights=[],
            booking_links=[url],
            source_url=url,
            source_title=title,
        ))

    return options
