import json
import logging
from typing import List
from app.integrations.openai_client import call_gpt
from app.models.entities import Activity
from app.graph.utils import pick

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
            cleaned = pick(a, [
                "title", "location", "duration_hours",
                "est_price", "source_url", "source_title", "tags"
            ])

            # normalize tags
            if isinstance(cleaned.get("tags"), str):
                cleaned["tags"] = [cleaned["tags"]]
            elif not isinstance(cleaned.get("tags"), list):
                cleaned["tags"] = []

            # fallbacks
            cleaned.setdefault("source_url", a.get("source_url") or a.get("url", ""))
            cleaned.setdefault("source_title", a.get("source_title") or a.get("title", ""))

            activities.append(Activity(**cleaned))

        except Exception as e:
            logger.error("Error casting activity option: %s", e)
    print("Refined activities types:", [type(a) for a in activities])

    if state:
        state.logs.append({
            "stage": "Activities",
            "raw_count": len(raw_results),
            "refined_count": len(activities)
        })

    logger.info("Refined %d activity options", len(activities))
    return activities
