import json
import logging
from typing import List
from app.integrations.openai_client import call_gpt
from app.models.entities import FlightOption
from app.graph.utils import pick

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def refine_flights_with_llm(raw_results: List[dict], state=None, model="gpt-4o-mini") -> List[FlightOption]:
    """
    Takes Tavily raw results and asks GPT to return structured flight options.
    """

    if not raw_results:
        logger.warning("No flight results to refine")
        if state:
            state.logs.append({"stage": "Flights", "raw_count": 0, "refined_count": 0})
        return []

    schema = """
{
  "flights": [
    {
      "summary": "Kenya Airways flight KQ310 NBO → DXB",
      "depart_time": "08:20",
      "arrive_time": "13:00",
      "airline": "Kenya Airways",
      "flight_number": "KQ310",
      "stops": 0,
      "est_price": 520.0,
      "booking_links": ["https://kenya-airways.com/book/kq310"],
      "source_url": "https://direct-flights.com/nairobi-NBO/dubai-DXB?weekCode=202531",
      "source_title": "Direct flights from Nairobi (NBO) to Dubai (DXB)"
    }
  ]
}
"""

    prompt = f"""
You are a flight data extractor.
Convert noisy search results about flights from Nairobi (NBO) to Dubai (DXB)
into structured JSON flight options.

Rules:
- Return JSON only.
- Do not include code fences, Markdown, or explanations.
- The response must be a single valid JSON object.
- Times: convert to 24h "HH:MM".
- Airline names must be full (e.g. "Kenya Airways").
- Extract flight number if available (e.g. KQ310).
- If price is missing, set "est_price" = null.
- Use result.url as fallback booking link.
- Always include source_url and source_title.
- Never include explanations.

Schema example:
{schema}

Raw input:
{json.dumps(raw_results, indent=2)}
"""

    logger.info("Refining %d raw flight results", len(raw_results))
    try:
        structured = call_gpt(prompt, model=model, response_format={"type": "json_object"})
    except TypeError:
        structured = call_gpt(prompt, model=model)
    print(f"structured: {structured}")
    print(f"type: {type(structured)}")

    if isinstance(structured, str):
        try:
            structured = json.loads(structured)
        except Exception as e:
            logger.error("Invalid JSON string from GPT: %s", e)
            return []

    
    # Expect "flights"
    if "flights" not in structured:
        logger.warning("GPT did not return 'flights' key")
        if state:
            state.logs.append({"stage": "Flights", "raw_count": len(raw_results), "refined_count": 0, "error": "missing flights key"})
        return []

    flights = []
    for f in structured["flights"]:
        try:
            cleaned = pick(f, [
                "summary", "depart_time", "arrive_time", "airline",
                "flight_number", "stops", "est_price",
                "booking_links", "source_url", "source_title"
            ])

            # normalize booking_links
            if isinstance(cleaned.get("booking_links"), dict):
                cleaned["booking_links"] = [cleaned["booking_links"].get("url")]
            elif not isinstance(cleaned.get("booking_links"), list):
                cleaned["booking_links"] = []

            # fallback for required fields
            cleaned.setdefault("flight_number", "UNKNOWN")
            cleaned.setdefault("source_url", f.get("source_url") or f.get("url", ""))
            cleaned.setdefault("source_title", f.get("source_title") or f.get("title", ""))

            flights.append(FlightOption(**cleaned))

        except Exception as e:
            logger.error("Error casting flight option: %s", e)
    if state:
        state.logs.append({
            "stage": "Flights",
            "raw_count": len(raw_results),
            "refined_count": len(flights)
        })

    logger.info("Refined %d flight options", len(flights))
    return flights
