import json
import logging
from typing import List, Optional
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
            # safely extract expected keys from the dict (avoid using pick() which expects text)
            expected = [
                "name", "area", "est_price_per_night", "score",
                "highlights", "booking_links", "source_url", "source_title"
            ]
            cleaned = {k: s.get(k) for k in expected if k in s}

            # helper to coerce to str or None
            def to_str(val: Optional[object]) -> Optional[str]:
                if val is None:
                    return None
                if isinstance(val, str):
                    return val
                if isinstance(val, (int, float, bool)):
                    return str(val)
                if isinstance(val, dict):
                    for k in ("text", "title", "name", "summary", "url"):
                        v = val.get(k)
                        if isinstance(v, str):
                            return v
                    try:
                        return json.dumps(val)
                    except Exception:
                        return None
                try:
                    return str(val)
                except Exception:
                    return None

            # sanitize strings
            for fld in ("name", "area", "source_url", "source_title"):
                if fld in cleaned:
                    cleaned[fld] = to_str(cleaned.get(fld))

            # numeric fields
            if "est_price_per_night" in cleaned:
                try:
                    cleaned["est_price_per_night"] = float(cleaned["est_price_per_night"]) if cleaned["est_price_per_night"] is not None else None
                except Exception:
                    cleaned["est_price_per_night"] = None

            if "score" in cleaned:
                try:
                    cleaned["score"] = float(cleaned["score"]) if cleaned["score"] is not None else None
                except Exception:
                    cleaned["score"] = None

            # highlights -> list[str]
            highlights = cleaned.get("highlights")
            norm_highlights: List[str] = []
            if isinstance(highlights, list):
                for it in highlights:
                    if isinstance(it, str) and it:
                        norm_highlights.append(it)
                    elif isinstance(it, dict):
                        txt = to_str(it)
                        if txt:
                            norm_highlights.append(txt)
            elif isinstance(highlights, str) and highlights:
                norm_highlights = [highlights]
            cleaned["highlights"] = norm_highlights

            # booking_links -> list[str]
            links = cleaned.get("booking_links")
            normalized_links: List[str] = []
            if isinstance(links, str) and links:
                normalized_links.append(links)
            elif isinstance(links, dict):
                url = links.get("url") or links.get("link") or links.get("href") or links.get("value")
                if isinstance(url, str) and url:
                    normalized_links.append(url)
            elif isinstance(links, list):
                for it in links:
                    if isinstance(it, str) and it:
                        normalized_links.append(it)
                    elif isinstance(it, dict):
                        url = it.get("url") or it.get("link") or it.get("href") or it.get("value")
                        if isinstance(url, str) and url:
                            normalized_links.append(url)
            cleaned["booking_links"] = normalized_links

            # fallbacks
            cleaned.setdefault("source_url", s.get("source_url") or s.get("url", ""))
            cleaned.setdefault("source_title", s.get("source_title") or s.get("title", ""))

            # restrict keys to stay model
            allowed = {"name", "area", "est_price_per_night", "score", "highlights", "booking_links", "source_url", "source_title"}
            cleaned = {k: v for k, v in cleaned.items() if k in allowed}

            # construct model
            try:
                stays.append(StayOption(**cleaned))
            except Exception:
                logger.exception("Error casting stay option payload=%s", cleaned)
                continue

        except Exception as e:
            logger.exception("Unexpected error processing stay item: %s", e)

    if state:
        state.logs.append({
            "stage": "Stays",
            "raw_count": len(raw_results),
            "refined_count": len(stays)
        })

    logger.info("Refined %d stay options", len(stays))
    print(f"Refined stays: {stays}")
    return stays
