import json
import logging
from typing import List
from app.integrations.openai_client import call_gpt
from app.models.entities import FlightOption
from app.graph.utils import pick
import json
import logging
from typing import List, Optional
from app.integrations.openai_client import call_gpt
from app.models.entities import FlightOption
from app.graph.utils import pick

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def refine_flights_with_llm(raw_results: List[dict], state=None, model: str = "gpt-4o-mini") -> List[FlightOption]:
    """
    Takes Tavily raw results and asks GPT to return structured flight options.
    This function defensively sanitizes GPT output so Pydantic validation can't
    raise unexpected type errors (e.g. trying to call .lower() on a dict).
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

    logger.debug("raw structured result: %s", structured)

    # If GPT returns a string, parse JSON
    if isinstance(structured, str):
        try:
            structured = json.loads(structured)
        except Exception as e:
            logger.error("Invalid JSON string from GPT: %s", e)
            return []

    # Expect "flights"
    if not isinstance(structured, dict) or "flights" not in structured or not isinstance(structured["flights"], list):
        logger.warning("GPT did not return 'flights' key or returned invalid shape")
        if state:
            state.logs.append({"stage": "Flights", "raw_count": len(raw_results), "refined_count": 0, "error": "missing or invalid flights key"})
        return []

    def to_str(val: Optional[object]) -> Optional[str]:
        if val is None:
            return None
        if isinstance(val, str):
            return val
        if isinstance(val, (int, float, bool)):
            return str(val)
        if isinstance(val, dict):
            # prefer common textual keys
            for k in ("text", "title", "name", "summary", "url"):
                v = val.get(k)
                if isinstance(v, str):
                    return v
            # fallback to json string so pydantic receives a string
            try:
                return json.dumps(val)
            except Exception:
                return None
        # fallback
        try:
            return str(val)
        except Exception:
            return None

    def sanitize_flight_dict(raw: dict) -> dict:
        # pick only expected keys
        # raw is expected to be a dict; safely extract expected keys instead of
        # calling `pick()` which expects a text string. This avoids AttributeError
        # when GPT returns nested dicts.
        expected_keys = [
            "summary", "depart_time", "arrive_time", "airline",
            "flight_number", "stops", "est_price",
            "booking_links", "source_url", "source_title"
        ]
        cleaned = {k: raw.get(k) for k in expected_keys if k in raw}

        # ensure string fields are strings
        for s in ("summary", "depart_time", "arrive_time", "airline", "flight_number", "source_url", "source_title"):
            if s in cleaned:
                cleaned[s] = to_str(cleaned.get(s))

        # numeric coercion with safe fallbacks
        if "stops" in cleaned:
            try:
                cleaned["stops"] = int(cleaned["stops"]) if cleaned["stops"] is not None else None
            except Exception:
                cleaned["stops"] = None

        if "est_price" in cleaned:
            try:
                cleaned["est_price"] = float(cleaned["est_price"]) if cleaned["est_price"] is not None else None
            except Exception:
                cleaned["est_price"] = None

        # booking_links -> list[str]
        links = cleaned.get("booking_links")
        normalized: List[str] = []
        if isinstance(links, str):
            if links:
                normalized.append(links)
        elif isinstance(links, dict):
            # try common url keys
            url = links.get("url") or links.get("link") or links.get("href") or links.get("value")
            if isinstance(url, str) and url:
                normalized.append(url)
        elif isinstance(links, list):
            for it in links:
                if isinstance(it, str) and it:
                    normalized.append(it)
                elif isinstance(it, dict):
                    url = it.get("url") or it.get("link") or it.get("href") or it.get("value")
                    if isinstance(url, str) and url:
                        normalized.append(url)
                # ignore other types
        cleaned["booking_links"] = normalized

        # restrict to allowed keys only (avoid accidental nested dicts)
        allowed = {"summary", "depart_time", "arrive_time", "airline", "flight_number", "stops", "est_price", "booking_links", "source_url", "source_title"}
        return {k: v for k, v in cleaned.items() if k in allowed}

    flights: List[FlightOption] = []
    for idx, raw in enumerate(structured["flights"]):
        logger.info("processing flight index=%d", idx)
        logger.debug("raw flight: %s", raw)
        try:
            cleaned = sanitize_flight_dict(raw)
        except Exception:
            # already logged
            continue

        logger.debug("sanitized payload before model: %s", cleaned)
        try:
            fo = FlightOption(**cleaned)
            flights.append(fo)
        except Exception:
            logger.exception("FlightOption validation failed for payload: %s", cleaned)
            # continue with next item
            continue

    if state:
        state.logs.append({"stage": "Flights", "raw_count": len(raw_results), "refined_count": len(flights)})

    logger.info("Refined %d flight options", len(flights))
    logger.info("Refined flight options: %s", flights)

    return flights
