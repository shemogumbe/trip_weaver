import json
import logging
from typing import List, Optional
from app.integrations.openai_client import call_gpt
from app.models.entities import Activity
from app.graph.utils import pick, extract_currency, validate_price_reasonableness

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def refine_activities_with_llm(raw_results: List[dict], state=None, model="gpt-4o-mini") -> List[Activity]:
    """
    Takes Tavily raw results and asks GPT to return structured activity options.
    """

    if not raw_results:
        logger.warning("No activity results to refine")
        if state:
            state.logs.append({"stage": "Activities", "raw_count": 0, "refined_count": 0})
        return []

    schema = """
{
  "activities": [
    {
      "title": "Dubai Desert Safari",
      "location": "Dubai Desert",
      "duration_hours": 4.0,
      "est_price": 60.0,
      "source_url": "https://getyourguide.com/desert-safari",
      "tags": ["adventure", "camel ride", "dune bashing"]
    }
  ]
}
"""

    prompt = f"""
You are an activity data extractor.
Convert noisy search results about activities and tours into structured JSON activity options.

Rules:
- Return JSON only.
- Do not include code fences, Markdown, or explanations.
- The response must be a single valid JSON object.
- Required fields: "title", "location".
- duration_hours: numeric (float) if available, else null.
- est_price: numeric if available, else null.
- tags: list of keywords about the activity.
- source_url: use result.url as fallback.
- Always include source_url and source_title.
- Never include explanations.

Schema example:
{schema}

Raw input:
{json.dumps(raw_results, indent=2)}
"""

    logger.info("Refining %d raw activity results", len(raw_results))
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

    if "activities" not in structured:
        logger.warning("GPT did not return 'activities' key")
        if state:
            state.logs.append({
                "stage": "Activities",
                "raw_count": len(raw_results),
                "refined_count": 0,
                "error": "missing activities key"
            })
        return []

    activities = []
    for a in structured["activities"]:
        try:
            # safely extract expected keys from the dict
            expected = ["title", "location", "duration_hours", "est_price", "source_url", "source_title", "tags"]
            cleaned = {k: a.get(k) for k in expected if k in a}

            # helper to coerce to str
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

            # sanitize string fields
            for fld in ("title", "location", "source_url", "source_title"):
                if fld in cleaned:
                    cleaned[fld] = to_str(cleaned.get(fld))

            # numeric coercion
            if "duration_hours" in cleaned:
                try:
                    cleaned["duration_hours"] = float(cleaned["duration_hours"]) if cleaned["duration_hours"] is not None else None
                except Exception:
                    cleaned["duration_hours"] = None

            if "est_price" in cleaned:
                try:
                    price = float(cleaned["est_price"]) if cleaned["est_price"] is not None else None
                    if price is not None:
                        # Extract currency from the raw data
                        raw_text = str(a.get("content", "")) + " " + str(a.get("title", ""))
                        currency = extract_currency(raw_text)
                        
                        # Validate price reasonableness for activity context
                        if validate_price_reasonableness(price, raw_text, currency):
                            cleaned["est_price"] = price
                            cleaned["currency"] = currency
                            logger.info(f"Validated activity price: {price} {currency}")
                        else:
                            logger.warning(f"Rejected unreasonable activity price: {price} {currency}")
                            cleaned["est_price"] = None
                            cleaned["currency"] = currency
                    else:
                        cleaned["est_price"] = None
                except Exception as e:
                    logger.warning(f"Error validating activity price: {e}")
                    cleaned["est_price"] = None

            # tags -> list[str]
            tags = cleaned.get("tags")
            norm_tags: List[str] = []
            if isinstance(tags, str) and tags:
                norm_tags = [tags]
            elif isinstance(tags, list):
                for it in tags:
                    if isinstance(it, str) and it:
                        norm_tags.append(it)
                    elif isinstance(it, dict):
                        txt = to_str(it)
                        if txt:
                            norm_tags.append(txt)
            cleaned["tags"] = norm_tags

            # fallbacks
            cleaned.setdefault("source_url", a.get("source_url") or a.get("url", ""))
            cleaned.setdefault("source_title", a.get("source_title") or a.get("title", ""))

            # restrict to allowed keys
            allowed = {"title", "location", "duration_hours", "est_price", "currency", "source_url", "source_title", "tags"}
            cleaned = {k: v for k, v in cleaned.items() if k in allowed}

            try:
                activities.append(Activity(**cleaned))
            except Exception:
                logger.exception("Error casting activity option payload=%s", cleaned)
                continue

        except Exception:
            logger.exception("Unexpected error processing activity item: %s", a)
    print("Refined activities types:", [type(a) for a in activities])

    if state:
        state.logs.append({
            "stage": "Activities",
            "raw_count": len(raw_results),
            "refined_count": len(activities)
        })

    logger.info("Refined %d activity options", len(activities))
    return activities
