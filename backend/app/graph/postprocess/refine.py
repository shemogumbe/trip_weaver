import json
import logging
from app.integrations.openai_client import call_gpt

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def refine_with_gpt(items: list, agent_type: str, state=None, model="gpt-4o-mini") -> list:
    if not items:
        logger.warning("No items to refine for %s", agent_type)
        if state:
            state.logs.append({"stage": agent_type, "raw_count": 0, "refined_count": 0})
        return []

    schemas = {
        "Flights": """
        {
          "items": [
            {
              "summary": "Kenya Airways flight NBO → DXB",
              "depart_time": "2025-11-10T16:35",
              "arrive_time": "2025-11-10T22:40",
              "airline": "Kenya Airways",
              "flight_number": "KQ310",
              "stops": 0,
              "price_usd": 520
            }
          ]
        }""",
        "Stays": """
        {
          "items": [
            {
              "hotel_name": "Rove JBR",
              "check_in": "2025-11-10",
              "check_out": "2025-11-15",
              "location": "Jumeirah Beach Residence, Dubai",
              "price_usd_per_night": 104,
              "rating": 9.5
            }
          ]
        }""",
        "Activities": """
        {
          "items": [
            {
              "title": "Dubai Creek Golf Club",
              "date": "2025-11-11",
              "time": "08:00",
              "duration_hours": 4,
              "price_usd": 225,
              "location": "Dubai Creek"
            }
          ]
        }""",
    }

    prompt = f"""
    You are a travel data refiner.
    Input {agent_type} candidates (possibly noisy):

    {json.dumps(items, indent=2)}

    Task: Clean & normalize into {agent_type} options.

    Output: JSON ONLY, exactly in this schema:
    {schemas[agent_type]}
    """

    logger.info("Refining %d %s candidates", len(items), agent_type)
    structured = call_gpt(prompt, model=model)

    # structured is expected to be dict
    refined = structured.get("items") if isinstance(structured, dict) else None
    if not refined:
        logger.warning("GPT returned no items for %s", agent_type)
        refined = items  # fallback to preprocessed

    logger.info("Refined %d %s items", len(refined), agent_type)

    if state:
        state.logs.append({
            "stage": agent_type,
            "raw_count": len(items),
            "refined_count": len(refined),
        })

    return refined
