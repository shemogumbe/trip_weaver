import json
import logging
from typing import List
from app.integrations.openai_client import call_gpt
from app.models.entities import StayOption
from app.graph.utils import pick

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def refine_stays_with_llm(raw_results: List[dict], state=None, model="gpt-4o-mini") -> List[StayOption]:
    """
    Takes Tavily raw results and asks GPT to return structured stay options.
    """

    if not raw_results:
        logger.warning("No stay results to refine")
        if state:
            state.logs.append({"stage": "Stays", "raw_count": 0, "refined_count": 0})
        return []

    schema = """
{
  "stays": [
    {
      "name": "Rosewood Dubai",
      "area": "Downtown Dubai",
      "est_price_per_night": 150.0,
      "score": 8.7,
      "highlights": ["Pool", "Breakfast included", "Free WiFi"],
      "booking_links": ["https://booking.com/rosewood-dubai"],
      "source_url": "https://booking.com/rosewood-dubai",
      "source_title": "Rosewood Dubai Hotel - Booking.com"
    }
  ]
}
"""

    prompt = f"""
You are a hotel data extractor.
Convert noisy search results about hotels into structured JSON stay options.

Rules:
- Return JSON only.
- Do not include code fences, Markdown, or explanations.
- The response must be a single valid JSON object.
- Required fields: "name" and "area".
- est_price_per_night: numeric if available, else null.
- score: numeric rating (0–10) if available, else null.
- highlights: list of strings (amenities, features).
- booking_links: list of URLs. Use result.url as fallback.
- Always include source_url and source_title.
- Never include explanations.

Schema example:
{schema}

Raw input:
{json.dumps(raw_results, indent=2)}
"""

    logger.info("Refining %d raw stay results", len(raw_results))
    try:
        structured = call_gpt(prompt, model=model, response_format={"type": "json_object"})
    except TypeError:
        structured = call_gpt(prompt, model=model)

    if isinstance(structured, str):
        try:
            structured = json.loads(structured)
        except Exception as e:
            logger.error("Invalid JSON string from GPT: %s", e)
            return []

    if "stays" not in structured:
        logger.warning("GPT did not return 'stays' key")
        if state:
            state.logs.append({
                "stage": "Stays",
                "raw_count": len(raw_results),
                "refined_count": 0,
                "error": "missing stays key"
            })
        return []

    stays = []
    for s in structured["stays"]:
        try:
            cleaned = pick(s, [
                "name", "area", "est_price_per_night", "score",
                "highlights", "booking_links", "source_url", "source_title"
            ])

            # normalize booking_links
            if isinstance(cleaned.get("booking_links"), dict):
                cleaned["booking_links"] = [cleaned["booking_links"].get("url")]
            elif not isinstance(cleaned.get("booking_links"), list):
                cleaned["booking_links"] = []

            # fallbacks
            cleaned.setdefault("source_url", s.get("source_url") or s.get("url", ""))
            cleaned.setdefault("source_title", s.get("source_title") or s.get("title", ""))

            stays.append(StayOption(**cleaned))

        except Exception as e:
            logger.error("Error casting stay option: %s", e)

    if state:
        state.logs.append({
            "stage": "Stays",
            "raw_count": len(raw_results),
            "refined_count": len(stays)
        })

    logger.info("Refined %d stay options", len(stays))
    print(f"Refined stays: {stays}")
    return stays
